"""Assemble a finished research run into one report and stage it for wiki ingestion.

The report is a *source document*, not a wiki page: a later run triages it like any other staged
item and decides what the wiki should say. This script's job is to make that report trustworthy —
every section present, every year in the prose anchored to a sourced timeline event, and enough
distinct sources behind it to be worth reading.

Reads one run directory, writes `report.md` into it, and with `--stage` copies it into the private
staging directory. No network or LLM calls.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

try:
    from detect_gaps import distinct_years
    from wiki_graph import WikiGraphError, load_wiki_graph
except ModuleNotFoundError:  # Imported from outside research/scripts/.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from detect_gaps import distinct_years
    from wiki_graph import WikiGraphError, load_wiki_graph

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(filename)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

PRIVATE_REPO_PATH = Path(os.environ.get("PRIVATE_REPO_PATH", "../dean-wiki-private"))
DEFAULT_STAGING_DIR = PRIVATE_REPO_PATH / "sources" / "staging"

# Shorter than this and the run produced notes, not a narrative worth ingesting.
DEFAULT_MIN_WORDS = 600
DEFAULT_MIN_SOURCES = 8
REQUIRED_ARTIFACTS = ("run.json", "timeline.md", "timeline.json", "narrative.md")

TITLE_PATTERN = re.compile(r"\A\s*#\s+.*?$\n?", re.MULTILINE)
HEADING_PATTERN = re.compile(r"^(#{1,5})\s")
FENCE_PATTERN = re.compile(r"^\s*```")
WIKILINK_PATTERN = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")
BLOCKQUOTE_PATTERN = re.compile(r"^>\s+(.+)$", re.MULTILINE)
URL_PATTERN = re.compile(r"https?://[^\s<>)\]\"']+")


class ReportError(Exception):
    """Base class for every failure this module raises."""


class RunNotFoundError(ReportError):
    """The run directory is missing or incomplete."""


class StagingError(ReportError):
    """The staging directory is missing or not writable."""


class Status(StrEnum):
    """Verdict for the report, used to decide whether it is safe to stage."""

    OK = "ok"
    MISSING_ARTIFACT = "missing_artifact"
    EMPTY_TIMELINE = "empty_timeline"
    THIN_NARRATIVE = "thin_narrative"
    UNANCHORED_DATES = "unanchored_dates"
    FEW_SOURCES = "few_sources"
    STAGING_FAILED = "staging_failed"


REMEDIATION: dict[Status, str] = {
    Status.MISSING_ARTIFACT: (
        "A stage has not run yet. Work research/prompts/ in order; build_timeline.py produces the "
        "timeline files and the narrative prompt produces narrative.md."
    ),
    Status.EMPTY_TIMELINE: (
        "timeline.json holds no events, so there is no chronological backbone. Re-run "
        "build_timeline.py after extracting events from findings/."
    ),
    Status.THIN_NARRATIVE: (
        "The narrative is too short to be worth ingesting. Either the research found little (say so "
        "and stop) or the synthesis stage under-wrote it — re-run 06-narrative-synthesis.md."
    ),
    Status.UNANCHORED_DATES: (
        "The narrative names years the timeline does not contain, which is where invented history "
        "comes from. Add the missing events to events.jsonl with sources and rebuild, or cut the claim. "
        "Re-run with --allow-unanchored only when the year is incidental (a quotation, a version number)."
    ),
    Status.FEW_SOURCES: (
        "Too few distinct sources behind the report. Run another perspective, or widen the searches "
        "in 03-perspective-interview.md before staging."
    ),
    Status.STAGING_FAILED: (
        "The report compiled but could not be staged. Check that the private repo checkout is present "
        "and writable, or pass --staging-dir."
    ),
}


@dataclass
class Report:
    """Result of compiling one run, reported back to the agent or the terminal."""

    run_id: str
    status: Status
    reason: str
    topic: str = ""
    event_count: int = 0
    source_count: int = 0
    word_count: int = 0
    span: str = ""
    report_path: str | None = None
    staged_path: str | None = None
    remediation: str | None = None
    notes: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """Return whether the report needs no human decision.

        Returns:
            True when the report compiled and passed every check.
        """
        return self.status is Status.OK

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-serializable view of the report.

        Returns:
            Mapping of report fields with the status rendered as a plain string.
        """
        return {
            "run_id": self.run_id,
            "status": str(self.status),
            "reason": self.reason,
            "topic": self.topic,
            "event_count": self.event_count,
            "source_count": self.source_count,
            "word_count": self.word_count,
            "span": self.span,
            "report_path": self.report_path,
            "staged_path": self.staged_path,
            "remediation": self.remediation,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class RunArtifacts:
    """Everything a completed run produced, loaded off disk."""

    run_dir: Path
    manifest: dict[str, object]
    timeline_markdown: str
    timeline: dict[str, object]
    narrative: str
    findings: tuple[tuple[str, str], ...]
    perspectives: tuple[dict[str, object], ...]
    gaps: tuple[dict[str, object], ...]

    @property
    def events(self) -> list[dict[str, object]]:
        """Return the timeline events.

        Returns:
            Event records in chronological order, empty when the timeline is empty.
        """
        events = self.timeline.get("events", [])
        return list(events) if isinstance(events, list) else []

    @property
    def sources(self) -> list[str]:
        """Collect every distinct source URL the run stands on.

        Returns:
            Timeline sources first, then any extra URLs cited only in the findings.
        """
        ordered = dict.fromkeys(
            url for event in self.events for url in event.get("sources", []) if isinstance(url, str)
        )
        for _, body in self.findings:
            ordered.update(dict.fromkeys(URL_PATTERN.findall(body)))
        return list(ordered)


def read_json(path: Path, default: object) -> object:
    """Read a JSON file, tolerating absence and malformed content.

    Args:
        path: File to read.
        default: Value returned when the file is missing or unreadable.

    Returns:
        The decoded content, or `default`.
    """
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default
    except (OSError, json.JSONDecodeError):
        logger.exception("Could not read %s — continuing without it", path)
        return default


def load_run(run_dir: Path) -> tuple[RunArtifacts | None, list[str]]:
    """Load every artifact a run produced.

    Args:
        run_dir: Run directory.

    Returns:
        Tuple of (artifacts, missing required file names). Artifacts are None when anything
        required is missing.

    Raises:
        RunNotFoundError: If the run directory does not exist or its artifacts cannot be read.
    """
    if not run_dir.is_dir():
        raise RunNotFoundError(f"{run_dir} is not a directory — run start_run.py first")

    missing = [name for name in REQUIRED_ARTIFACTS if not (run_dir / name).is_file()]
    if missing:
        return None, missing

    try:
        findings = tuple(
            (path.stem, path.read_text(encoding="utf-8"))
            for path in sorted((run_dir / "findings").glob("*.md"))
            if path.is_file()
        )
        if not findings:
            return None, ["findings/*.md"]

        perspectives = read_json(run_dir / "perspectives.json", [])
        gaps = read_json(run_dir / "gaps.json", [])

        return (
            RunArtifacts(
                run_dir=run_dir,
                manifest=dict(read_json(run_dir / "run.json", {})),  # type: ignore[arg-type]
                timeline_markdown=(run_dir / "timeline.md").read_text(encoding="utf-8"),
                timeline=dict(read_json(run_dir / "timeline.json", {})),  # type: ignore[arg-type]
                narrative=(run_dir / "narrative.md").read_text(encoding="utf-8"),
                findings=findings,
                perspectives=tuple(perspectives) if isinstance(perspectives, list) else (),
                gaps=tuple(gaps) if isinstance(gaps, list) else (),
            ),
            [],
        )
    except OSError as error:
        logger.exception("Could not read the artifacts in %s", run_dir)
        raise RunNotFoundError(f"could not read the artifacts in {run_dir}: {error}") from error


def demote_headings(text: str, levels: int = 1) -> str:
    """Push every markdown heading down a level so a fragment nests under a parent section.

    Args:
        text: Markdown fragment.
        levels: How many levels to demote by.

    Returns:
        The fragment with headings demoted, leaving fenced code untouched.
    """
    lines: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if FENCE_PATTERN.match(line):
            in_fence = not in_fence
        if not in_fence and HEADING_PATTERN.match(line):
            line = "#" * levels + line
        lines.append(line)
    return "\n".join(lines)


def strip_title(text: str) -> str:
    """Remove a fragment's leading H1 so the assembled report has exactly one.

    Args:
        text: Markdown fragment.

    Returns:
        The fragment without its opening H1.
    """
    return TITLE_PATTERN.sub("", text.lstrip(), count=1).strip()


def timeline_body(text: str) -> str:
    """Keep only the dated sections of the timeline.

    Everything before the first year heading is provenance and instructions addressed to the
    narrative stage, which would only confuse whoever ingests the report later.

    Args:
        text: Full `timeline.md` content.

    Returns:
        The timeline from its first year heading onward, headings demoted one level.
    """
    sections = strip_title(text).split("\n## ", 1)
    return demote_headings(f"## {sections[1]}" if len(sections) == 2 else sections[0])


def lede_for(artifacts: RunArtifacts) -> str:
    """Pick the one-sentence summary that opens the report.

    Args:
        artifacts: Loaded run artifacts.

    Returns:
        The narrative's own opening blockquote, or a generated fallback line.
    """
    match = BLOCKQUOTE_PATTERN.search(artifacts.narrative)
    if match:
        return match.group(1).strip()
    span = artifacts.timeline.get("span")
    window = f"{span[0]}–{span[1]}" if isinstance(span, list) and len(span) == 2 else "the record"
    return f"How {artifacts.manifest.get('topic', artifacts.run_dir.name)} got here, traced across {window}."


def suggested_wiki_pages(artifacts: RunArtifacts) -> list[str]:
    """Resolve which existing wiki pages this report should update.

    Args:
        artifacts: Loaded run artifacts.

    Returns:
        Repo-relative wiki paths: the seed page first, then any page the narrative wikilinks.
    """
    suggested: dict[str, None] = {}
    seed = artifacts.manifest.get("seed_page")
    if isinstance(seed, str) and seed:
        suggested[seed] = None

    try:
        graph = load_wiki_graph()
    except WikiGraphError:
        logger.exception("Could not index the wiki — suggesting the seed page only")
        return list(suggested)

    for target in WIKILINK_PATTERN.findall(artifacts.narrative):
        try:
            suggested[graph.page_for(target).path] = None
        except WikiGraphError:
            logger.warning("Narrative links [[%s]], which is not a wiki page — ignoring it", target.strip())

    return list(suggested)


def unanchored_years(artifacts: RunArtifacts) -> list[str]:
    """Find years the narrative asserts that the timeline cannot support.

    Args:
        artifacts: Loaded run artifacts.

    Returns:
        Sorted years present in the narrative prose but absent from the timeline.
    """
    anchored = {str(event.get("year")) for event in artifacts.events}
    return sorted(distinct_years(artifacts.narrative) - anchored)


def render_report(artifacts: RunArtifacts, sources: list[str], compiled_at: datetime) -> tuple[str, int]:
    """Assemble the full report body, frontmatter included.

    Args:
        artifacts: Loaded run artifacts.
        sources: Distinct source URLs behind the run.
        compiled_at: Timestamp recorded in frontmatter.

    Returns:
        Tuple of (complete markdown text of `report.md`, word count of the body).
    """
    topic = str(artifacts.manifest.get("topic", artifacts.run_dir.name))
    span = artifacts.timeline.get("span")
    span_label = f"{span[0]}–{span[1]}" if isinstance(span, list) and len(span) == 2 else "unknown"
    seed = artifacts.manifest.get("seed_page")

    body = [
        f"# Background: {topic}",
        "",
        f"> {lede_for(artifacts)}",
        "",
        f"**Run**: `{artifacts.manifest.get('run_id', artifacts.run_dir.name)}`",
        f"**Seed page**: {f'`{seed}`' if seed else 'none — researched cold'}",
        f"**Timeline**: {len(artifacts.events)} sourced events, {span_label}",
        f"**Perspectives**: {len(artifacts.perspectives) or len(artifacts.findings)}",
        "",
        "## What this backfill was for",
        "",
    ]

    if artifacts.gaps:
        body += [
            f"- **{gap.get('term', gap.get('subject', 'unnamed'))}** — {gap.get('why', gap.get('detail', ''))}"
            for gap in artifacts.gaps
        ]
    else:
        body.append(
            f"No structured gap list was recorded. The run targeted the background behind {topic} "
            "that existing pages assume without explaining."
        )

    body += [
        "",
        "## Timeline of major improvements",
        "",
        "Every date below is anchored to a cited source; the narrative was written from this list.",
        "",
        timeline_body(artifacts.timeline_markdown),
        "",
        "## Narrative",
        "",
        demote_headings(strip_title(artifacts.narrative)),
        "",
        "## Perspectives researched",
        "",
    ]

    if artifacts.perspectives:
        body += [
            f"- **{perspective.get('name', 'unnamed')}** — {perspective.get('focus', '')}"
            for perspective in artifacts.perspectives
        ]
    else:
        body += [f"- `{name}`" for name, _ in artifacts.findings]

    body += ["", "## Sources", ""]
    citation_counts = {
        url: sum(1 for event in artifacts.events if url in event.get("sources", [])) for url in sources
    }
    body += [
        f"- {url}" + (f" — anchors {count} timeline event(s)" if count else "") for url, count in citation_counts.items()
    ]
    body.append("")

    text = "\n".join(body)
    word_count = len(text.split())
    frontmatter = [
        "---",
        'source: "deep research"',
        "type: research",
        "ingestion_mode: deep-research-backfill",
        f"title: {json.dumps(f'Background: {topic}', ensure_ascii=False)}",
        f"topic: {json.dumps(topic, ensure_ascii=False)}",
        f"run_id: {json.dumps(str(artifacts.manifest.get('run_id', artifacts.run_dir.name)), ensure_ascii=False)}",
        f"fetched_at: {compiled_at.isoformat()}",
        f"timeline_span: {json.dumps(span_label, ensure_ascii=False)}",
        f"event_count: {len(artifacts.events)}",
        f"source_count: {len(sources)}",
        f"word_count: {word_count}",
    ]
    pages = suggested_wiki_pages(artifacts)
    if pages:
        frontmatter.append("suggested_wiki_pages:")
        frontmatter += [f"  - {page}" for page in pages]
    frontmatter += ["---", ""]

    return "\n".join(frontmatter) + text, word_count


def diagnose(artifacts: RunArtifacts, sources: list[str], args: argparse.Namespace) -> tuple[Status, str, list[str]]:
    """Decide whether the report is trustworthy enough to stage.

    Args:
        artifacts: Loaded run artifacts.
        sources: Distinct source URLs behind the run.
        args: Parsed command-line options.

    Returns:
        Tuple of (status, one-line reason, extra notes).
    """
    notes: list[str] = []

    if not artifacts.events:
        return Status.EMPTY_TIMELINE, "timeline.json contains no events", notes

    narrative_words = len(strip_title(artifacts.narrative).split())
    if narrative_words < args.min_words:
        return Status.THIN_NARRATIVE, f"narrative is {narrative_words} words, wanted {args.min_words}", notes

    stray = unanchored_years(artifacts)
    if stray:
        if args.allow_unanchored:
            notes.append(f"Unanchored year(s) kept because --allow-unanchored was set: {', '.join(stray)}")
        else:
            return Status.UNANCHORED_DATES, f"narrative names {', '.join(stray)} with no timeline event", notes

    if len(sources) < args.min_sources:
        return Status.FEW_SOURCES, f"{len(sources)} distinct source(s), wanted {args.min_sources}", notes

    return Status.OK, f"{len(artifacts.events)} events, {narrative_words} words, {len(sources)} sources", notes


def resolve_staging_dir(override: str | None) -> Path:
    """Locate the staging directory, refusing to invent a stray private-repo tree.

    Args:
        override: Explicit staging directory from the command line, if given.

    Returns:
        An existing, writable staging directory.

    Raises:
        StagingError: If the private repo is absent or the directory cannot be created.
    """
    staging_dir = Path(override) if override else DEFAULT_STAGING_DIR
    if staging_dir.is_dir():
        return staging_dir

    private_root = staging_dir.parents[1] if override is None else staging_dir.parent
    if not private_root.is_dir():
        raise StagingError(
            f"staging directory {staging_dir} does not exist and neither does {private_root}. "
            "Set PRIVATE_REPO_PATH to the dean-wiki-private checkout, or pass --staging-dir."
        )

    try:
        staging_dir.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        logger.exception("Could not create staging directory %s", staging_dir)
        raise StagingError(f"could not create {staging_dir}: {error}") from error

    return staging_dir


def unique_output_path(staging_dir: Path, slug: str, compiled_at: datetime) -> Path:
    """Build a collision-free staging path using the `research-` prefix.

    Args:
        staging_dir: Directory staged files are written to.
        slug: Run slug.
        compiled_at: Timestamp used for the date segment.

    Returns:
        A path that does not yet exist.
    """
    base_name = f"research-{compiled_at.strftime('%Y-%m-%d')}-{slug}"
    output_path = staging_dir / f"{base_name}.md"

    counter = 2
    while output_path.exists():
        output_path = staging_dir / f"{base_name}-{counter}.md"
        counter += 1

    return output_path


def stage(staging_dir: Path, slug: str, text: str, compiled_at: datetime) -> Path:
    """Copy the compiled report into the staging directory for a later wiki run.

    Args:
        staging_dir: Directory to write into.
        slug: Run slug used in the file name.
        text: Full report text including frontmatter.
        compiled_at: Timestamp used for the date segment.

    Returns:
        Path of the staged file.

    Raises:
        StagingError: If the file cannot be written.
    """
    output_path = unique_output_path(staging_dir, slug, compiled_at)
    try:
        output_path.write_text(text, encoding="utf-8")
    except OSError as error:
        logger.exception("Could not write staged report %s", output_path)
        raise StagingError(f"could not write {output_path}: {error}") from error
    return output_path


def write_run_summary(staging_dir: Path, report: Report) -> None:
    """Append this run's outcome to the staging `.run-summary` file.

    Args:
        staging_dir: Directory holding `.run-summary`.
        report: The compiled report.
    """
    summary = (
        f"- **Deep research**: 1 report staged ({report.topic} — {report.event_count} events, "
        f"{report.span}, {report.source_count} sources)"
    )
    try:
        with (staging_dir / ".run-summary").open("a", encoding="utf-8") as summary_file:
            summary_file.write(f"{summary}\n")
    except OSError:
        logger.exception("Could not append to %s/.run-summary", staging_dir)
    logger.info("Final summary: %s", summary)


def print_report(report: Report) -> None:
    """Print a human-readable verdict block for the run.

    Args:
        report: The compiled report.
    """
    lines = [f"{report.status.upper()}  {report.run_id}", f"  reason: {report.reason}"]
    if report.event_count:
        lines.append(f"  timeline: {report.event_count} events, {report.span}, {report.source_count} sources")
    if report.report_path:
        lines.append(f"  report: {report.report_path} ({report.word_count} words)")
    if report.staged_path:
        lines.append(f"  staged: {report.staged_path}")
    lines += [f"  note: {note}" for note in report.notes]
    if report.remediation:
        lines.append(f"  fix: {report.remediation}")
    logger.info("\n".join(lines))


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Argument list without the program name.

    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(description="Compile a research run into one report and stage it for ingestion.")
    parser.add_argument("run_dir", help="Research run directory (research/runs/<run-id>).")
    parser.add_argument("--check", action="store_true", help="Validate the run without writing anything.")
    parser.add_argument("--stage", action="store_true", help="Also copy the report into the private staging directory.")
    parser.add_argument(
        "--min-words",
        type=int,
        default=DEFAULT_MIN_WORDS,
        help=f"Narrative length floor before the report counts as substantial (default {DEFAULT_MIN_WORDS}).",
    )
    parser.add_argument(
        "--min-sources",
        type=int,
        default=DEFAULT_MIN_SOURCES,
        help=f"Distinct sources the report must stand on (default {DEFAULT_MIN_SOURCES}).",
    )
    parser.add_argument(
        "--allow-unanchored", action="store_true", help="Accept years in the narrative that no timeline event supports."
    )
    parser.add_argument("--staging-dir", help="Override the staging directory (default: $PRIVATE_REPO_PATH staging).")
    parser.add_argument("--json", action="store_true", help="Emit a machine-readable report on stdout.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Compile one research run.

    Args:
        argv: Argument list without the program name; defaults to `sys.argv[1:]`.

    Returns:
        0 when the report is clean, 2 when it needs a human decision, 1 on internal failure.
    """
    args = parse_args(sys.argv[1:] if argv is None else argv)

    run_dir = Path(args.run_dir)
    try:
        artifacts, missing = load_run(run_dir)
    except RunNotFoundError as error:
        logger.error("%s", error)
        return 1

    if artifacts is None:
        report = Report(
            run_id=run_dir.name,
            status=Status.MISSING_ARTIFACT,
            reason=f"missing {', '.join(missing)}",
            remediation=REMEDIATION[Status.MISSING_ARTIFACT],
        )
        print_report(report)
        if args.json:
            print(json.dumps(report.as_dict(), indent=2))
        return 2

    compiled_at = datetime.now(UTC)
    sources = artifacts.sources
    span = artifacts.timeline.get("span")
    status, reason, notes = diagnose(artifacts, sources, args)

    report = Report(
        run_id=str(artifacts.manifest.get("run_id", run_dir.name)),
        status=status,
        reason=reason,
        topic=str(artifacts.manifest.get("topic", run_dir.name)),
        event_count=len(artifacts.events),
        source_count=len(sources),
        span=f"{span[0]}–{span[1]}" if isinstance(span, list) and len(span) == 2 else "unknown",
        notes=notes,
    )

    if status is Status.OK:
        # Rendered even for --check so a dry run reports exactly what would be written.
        text, report.word_count = render_report(artifacts, sources, compiled_at)

        if args.check:
            report.notes.append("Check-only run: nothing was written.")
        else:
            try:
                report_path = run_dir / "report.md"
                report_path.write_text(text, encoding="utf-8")
                report.report_path = str(report_path)
            except OSError as error:
                logger.exception("Could not write %s", run_dir / "report.md")
                report.status, report.reason = Status.STAGING_FAILED, f"could not write report.md: {error}"

        if args.stage and not args.check and report.ok:
            try:
                staging_dir = resolve_staging_dir(args.staging_dir)
                slug = str(artifacts.manifest.get("slug", run_dir.name))
                report.staged_path = str(stage(staging_dir, slug, text, compiled_at))
                write_run_summary(staging_dir, report)
            except StagingError as error:
                report.status, report.reason = Status.STAGING_FAILED, str(error)

    if not report.ok:
        report.remediation = REMEDIATION[report.status]

    print_report(report)
    if args.json:
        print(json.dumps(report.as_dict(), indent=2))

    return 0 if report.ok else 2


if __name__ == "__main__":
    sys.exit(main())
