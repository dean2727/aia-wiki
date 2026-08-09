"""Merge events into a wiki page's `## Timeline` section, deterministically.

The site renders that section as a month slider, so its format has to be exact and its order has
to be right. Rather than trusting an agent to hand-sort markdown, every write goes through here:
existing bullets are parsed back into events, incoming events are merged and deduplicated against
them, the whole set is sorted oldest first, and the section is rewritten.

Incoming events come from a research run's `timeline.json` (`--from-run`), from the command line
(`--event`), or from a JSON file (`--from-json`). No network or LLM calls.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

try:
    from events import (
        DEFAULT_SIMILARITY,
        URL_PATTERN,
        Event,
        EventDateError,
        EventError,
        EventFormatError,
        EventKind,
        merge_duplicates,
        parse_bullet,
        parse_event_date,
        sort_events,
    )
    from wiki_graph import WikiGraphError, load_wiki_graph
except ModuleNotFoundError:  # Imported from outside research/scripts/.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from events import (
        DEFAULT_SIMILARITY,
        URL_PATTERN,
        Event,
        EventDateError,
        EventError,
        EventFormatError,
        EventKind,
        merge_duplicates,
        parse_bullet,
        parse_event_date,
        sort_events,
    )
    from wiki_graph import WikiGraphError, load_wiki_graph

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(filename)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
TIMELINE_HEADING = "## Timeline"
# The canonical skeleton puts Timeline after How it works; these are what it must precede.
FOLLOWING_SECTIONS = ("## Sources", "## Related")
EVENT_FIELD_SEPARATOR = "|"
EVENT_FIELD_COUNT = 3
LAST_UPDATED_PREFIX = "**Last updated**:"


class MergeError(Exception):
    """Base class for every failure this module raises."""


class PageError(MergeError):
    """The target page is missing, unreadable, or not a wiki page."""


class EventInputError(MergeError):
    """An incoming event could not be read from the command line or a file."""


class Status(StrEnum):
    """Verdict for one merge, used to decide whether the page was left in a good state."""

    OK = "ok"
    UNCHANGED = "unchanged"
    MALFORMED_SECTION = "malformed_section"
    NO_EVENTS = "no_events"
    WRITE_FAILED = "write_failed"


REMEDIATION: dict[Status, str] = {
    Status.MALFORMED_SECTION: (
        "The page's existing Timeline section has bullets that do not parse. Fix the lines named below "
        "to match `- `YYYY-MM` (kind) sentence [source](url)`, or re-run with --replace to discard them."
    ),
    Status.NO_EVENTS: (
        "No incoming events were supplied. Pass --from-run <run-dir>, --from-json <path>, or one or "
        "more --event 'YYYY-MM|kind|sentence|url' arguments."
    ),
    Status.WRITE_FAILED: "The page could not be written. Check that it exists and is writable.",
}


@dataclass
class Report:
    """Result of merging events into one page."""

    page: str
    status: Status
    reason: str
    existing: int = 0
    incoming: int = 0
    total: int = 0
    added: int = 0
    span: str = ""
    remediation: str | None = None
    notes: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """Return whether the merge needs no human decision.

        Returns:
            True when the page was written or was already correct.
        """
        return self.status in {Status.OK, Status.UNCHANGED}

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-serializable view of the report.

        Returns:
            Mapping of report fields with the status rendered as a plain string.
        """
        return {
            "page": self.page,
            "status": str(self.status),
            "reason": self.reason,
            "existing": self.existing,
            "incoming": self.incoming,
            "total": self.total,
            "added": self.added,
            "span": self.span,
            "remediation": self.remediation,
            "notes": self.notes,
            "problems": self.problems,
        }


def resolve_page(reference: str) -> Path:
    """Turn a slug or path into a wiki page path.

    Args:
        reference: Page slug, file name, or path relative to the repo root.

    Returns:
        Path to the markdown file.

    Raises:
        PageError: If no wiki page matches the reference.
    """
    direct = Path(reference)
    if direct.is_file():
        return direct
    candidate = REPO_ROOT / reference
    if candidate.is_file():
        return candidate

    try:
        graph = load_wiki_graph()
        return REPO_ROOT / graph.page_for(reference).path
    except WikiGraphError as error:
        raise PageError(f"{error}. Pass a slug or a path under wiki/.") from error


def split_sections(body: str) -> tuple[list[str], list[str], list[str]]:
    """Split a page around its `## Timeline` section.

    Args:
        body: Full page text.

    Returns:
        Tuple of (lines before the section, lines inside it, lines after it). When the page has no
        Timeline section, the inside list is empty and the split point is chosen so the section
        lands in canonical position.
    """
    lines = body.splitlines()
    try:
        start = next(index for index, line in enumerate(lines) if line.strip() == TIMELINE_HEADING)
    except StopIteration:
        for index, line in enumerate(lines):
            if line.strip() in FOLLOWING_SECTIONS:
                return lines[:index], [], lines[index:]
        return lines, [], []

    end = next(
        (index for index in range(start + 1, len(lines)) if lines[index].startswith("## ")),
        len(lines),
    )
    return lines[:start], lines[start + 1 : end], lines[end:]


def parse_section(section_lines: list[str]) -> tuple[list[Event], list[str], list[str]]:
    """Parse an existing Timeline section into events, prose, and problems.

    Args:
        section_lines: Lines inside the Timeline section, heading excluded.

    Returns:
        Tuple of (parsed events, preserved non-bullet lines such as an arc sentence, problems).
    """
    events: list[Event] = []
    prose: list[str] = []
    problems: list[str] = []

    for number, line in enumerate(section_lines, start=1):
        stripped = line.strip()
        if not stripped:
            continue
        if not stripped.startswith("- "):
            prose.append(stripped)
            continue
        try:
            events.append(parse_bullet(stripped))
        except EventError as error:
            problems.append(f"line {number}: {error} — {stripped[:70]}")

    return events, prose, problems


def parse_event_argument(raw: str) -> Event:
    """Parse a `--event` value into an event.

    Args:
        raw: Pipe-delimited `YYYY-MM|kind|sentence[|url][|url]` value.

    Returns:
        The parsed event.

    Raises:
        EventInputError: If the value has too few fields, an unknown kind, or an unusable date.
    """
    parts = [part.strip() for part in raw.split(EVENT_FIELD_SEPARATOR)]
    if len(parts) < EVENT_FIELD_COUNT:
        raise EventInputError(f"--event {raw!r} needs at least date|kind|sentence")

    date_text, kind_text, sentence, *sources = parts
    if kind_text.lower() not in set(EventKind):
        raise EventInputError(f"--event {raw!r} has unknown kind {kind_text!r}")

    try:
        event_date = parse_event_date(date_text)
    except EventDateError as error:
        raise EventInputError(f"--event {raw!r}: {error}") from error

    return Event(
        date=event_date,
        event=sentence,
        kind=EventKind(kind_text.lower()),
        significance="",
        sources=tuple(url for url in sources if URL_PATTERN.match(url)),
        confidence="unstated",
    )


def load_run_events(run_dir: Path, only: str | None) -> list[Event]:
    """Read a research run's `timeline.json` into events.

    Args:
        run_dir: Research run directory.
        only: Optional case-insensitive substring; when given, only matching events are taken.

    Returns:
        The run's events, filtered.

    Raises:
        EventInputError: If the timeline file is missing or unreadable.
    """
    timeline_path = run_dir / "timeline.json"
    try:
        payload = json.loads(timeline_path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise EventInputError(f"{timeline_path} does not exist — run build_timeline.py first") from error
    except (OSError, json.JSONDecodeError) as error:
        logger.exception("Could not read %s", timeline_path)
        raise EventInputError(f"could not read {timeline_path}: {error}") from error

    events: list[Event] = []
    for record in payload.get("events", []):
        text = str(record.get("event", "")).strip()
        if only and only.lower() not in text.lower():
            continue
        try:
            event_date = parse_event_date(str(record.get("date", "")))
        except EventDateError as error:
            logger.warning("Skipping an event from %s — %s", timeline_path, error)
            continue

        raw_kind = str(record.get("kind", "")).strip().lower()
        events.append(
            Event(
                date=event_date,
                event=text,
                kind=EventKind(raw_kind) if raw_kind in set(EventKind) else EventKind.MILESTONE,
                significance=str(record.get("significance", "")).strip(),
                sources=tuple(str(url) for url in record.get("sources", [])),
                confidence=str(record.get("confidence", "")).strip().lower() or "unstated",
            )
        )
    return events


def collect_incoming(args: argparse.Namespace) -> list[Event]:
    """Gather incoming events from every supplied source.

    Args:
        args: Parsed command-line options.

    Returns:
        Events from `--from-run`, `--from-json`, and `--event`, in that order.

    Raises:
        EventInputError: If any source cannot be read or parsed.
    """
    incoming: list[Event] = []
    if args.from_run:
        incoming += load_run_events(Path(args.from_run), args.only)
    if args.from_json:
        try:
            records = json.loads(Path(args.from_json).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            logger.exception("Could not read %s", args.from_json)
            raise EventInputError(f"could not read {args.from_json}: {error}") from error
        incoming += load_records(records)
    incoming += [parse_event_argument(raw) for raw in args.event or ()]
    return incoming


def load_records(records: object) -> list[Event]:
    """Convert a decoded JSON list of event records into events.

    Args:
        records: Decoded JSON, expected to be a list of objects.

    Returns:
        The parsed events, skipping records with unusable dates.

    Raises:
        EventInputError: If the payload is not a list.
    """
    if not isinstance(records, list):
        raise EventInputError("--from-json expects a JSON array of event objects")

    events: list[Event] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        try:
            event_date = parse_event_date(str(record.get("date", "")))
        except EventDateError as error:
            logger.warning("Skipping a record — %s", error)
            continue
        raw_kind = str(record.get("kind", "")).strip().lower()
        sources = record.get("sources") or ([record["source_url"]] if record.get("source_url") else [])
        events.append(
            Event(
                date=event_date,
                event=str(record.get("event", "")).strip(),
                kind=EventKind(raw_kind) if raw_kind in set(EventKind) else EventKind.MILESTONE,
                significance=str(record.get("significance", "")).strip(),
                sources=tuple(str(url) for url in sources),
                confidence=str(record.get("confidence", "")).strip().lower() or "unstated",
            )
        )
    return events


def render_section(events: list[Event], prose: list[str]) -> list[str]:
    """Render the Timeline section body.

    Args:
        events: Sorted events.
        prose: Preserved non-bullet lines, such as a single arc sentence.

    Returns:
        Lines for the section, heading excluded.
    """
    lines = [TIMELINE_HEADING, ""]
    if prose:
        lines += [*prose, ""]
    lines += [event.to_bullet() for event in events]
    lines.append("")
    return lines


def bump_last_updated(before: list[str], today: str) -> list[str]:
    """Refresh the page's `Last updated` metadata line.

    Args:
        before: Lines preceding the Timeline section.
        today: Date to record, as `YYYY-MM-DD`.

    Returns:
        The lines with the metadata date replaced when the line exists.
    """
    return [f"{LAST_UPDATED_PREFIX} {today}" if line.startswith(LAST_UPDATED_PREFIX) else line for line in before]


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Argument list without the program name.

    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(description="Merge events into a wiki page's Timeline section.")
    parser.add_argument("page", help="Wiki page to update — slug or path under wiki/.")
    parser.add_argument("--from-run", help="Take events from this research run's timeline.json.")
    parser.add_argument("--from-json", help="Take events from a JSON array of event objects.")
    parser.add_argument(
        "--event",
        action="append",
        metavar="'DATE|KIND|SENTENCE[|URL]'",
        help="Add one event inline. Repeatable.",
    )
    parser.add_argument("--only", help="With --from-run, take only events whose text contains this substring.")
    parser.add_argument("--check", action="store_true", help="Validate the page's Timeline section and stop.")
    parser.add_argument("--dry-run", action="store_true", help="Show the merged section without writing it.")
    parser.add_argument("--replace", action="store_true", help="Discard unparseable existing bullets instead of failing.")
    parser.add_argument("--no-bump", action="store_true", help="Leave the page's Last updated line alone.")
    parser.add_argument(
        "--similarity",
        type=float,
        default=DEFAULT_SIMILARITY,
        help=f"Score above which two same-year events are merged (default {DEFAULT_SIMILARITY}).",
    )
    parser.add_argument("--json", action="store_true", help="Emit a machine-readable report on stdout.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Merge events into one wiki page's Timeline section.

    Args:
        argv: Argument list without the program name; defaults to `sys.argv[1:]`.

    Returns:
        0 when the page is in a good state, 2 when it needs a human decision, 1 on internal failure.
    """
    args = parse_args(sys.argv[1:] if argv is None else argv)

    try:
        page_path = resolve_page(args.page)
        body = page_path.read_text(encoding="utf-8")
    except (PageError, OSError) as error:
        logger.error("%s", error)
        return 1

    before, section_lines, after = split_sections(body)
    existing, prose, problems = parse_section(section_lines)
    report = Report(page=str(page_path), status=Status.OK, reason="", existing=len(existing), problems=problems)

    if problems and not args.replace:
        report.status = Status.MALFORMED_SECTION
        report.reason = f"{len(problems)} existing bullet(s) do not parse"
        report.remediation = REMEDIATION[Status.MALFORMED_SECTION]
        print_report(report)
        return 2 if not args.json else _emit(report)

    if args.check:
        report.status = Status.UNCHANGED
        report.total = len(existing)
        report.reason = f"{len(existing)} event(s) parse cleanly"
        print_report(report)
        return 0 if not args.json else _emit(report)

    try:
        incoming = collect_incoming(args)
    except EventInputError as error:
        logger.error("%s", error)
        return 1

    if not incoming:
        report.status = Status.NO_EVENTS
        report.reason = "no incoming events were supplied"
        report.remediation = REMEDIATION[Status.NO_EVENTS]
        print_report(report)
        return 2 if not args.json else _emit(report)

    report.incoming = len(incoming)
    merged, notes = merge_duplicates(existing + incoming, args.similarity)
    merged = sort_events(merged)
    report.notes = notes
    report.total = len(merged)
    report.added = len(merged) - len(existing)
    report.span = f"{merged[0].date.month_key} → {merged[-1].date.month_key}"

    rebuilt = before if args.no_bump else bump_last_updated(before, datetime.now(UTC).strftime("%Y-%m-%d"))
    text = "\n".join([*rebuilt, *render_section(merged, prose), *after]).rstrip() + "\n"

    if args.dry_run:
        report.status = Status.UNCHANGED
        report.reason = f"dry run — would hold {len(merged)} event(s)"
        print_report(report)
        print("\n".join(render_section(merged, prose)))
        return 0 if not args.json else _emit(report)

    if text == body:
        report.status = Status.UNCHANGED
        report.reason = "every incoming event was already present"
        print_report(report)
        return 0 if not args.json else _emit(report)

    try:
        page_path.write_text(text, encoding="utf-8")
    except OSError as error:
        logger.exception("Could not write %s", page_path)
        report.status, report.reason = Status.WRITE_FAILED, str(error)
        report.remediation = REMEDIATION[Status.WRITE_FAILED]
        print_report(report)
        return 2 if not args.json else _emit(report)

    report.reason = f"{report.added} new event(s), {report.total} total"
    print_report(report)
    return 0 if not args.json else _emit(report)


def print_report(report: Report) -> None:
    """Print a human-readable verdict block for the merge.

    Args:
        report: The merge report.
    """
    lines = [f"{report.status.upper()}  {report.page}", f"  reason: {report.reason}"]
    if report.total:
        lines.append(f"  events: {report.existing} existing + {report.incoming} incoming → {report.total}")
    if report.span:
        lines.append(f"  span: {report.span}")
    lines += [f"  merged: {note}" for note in report.notes]
    lines += [f"  problem: {problem}" for problem in report.problems]
    if report.remediation:
        lines.append(f"  fix: {report.remediation}")
    logger.info("\n".join(lines))


def _emit(report: Report) -> int:
    """Print the JSON report and return the exit code it implies.

    Args:
        report: The merge report.

    Returns:
        0 when the merge is in a good state, 2 otherwise.
    """
    print(json.dumps(report.as_dict(), indent=2))
    return 0 if report.ok else 2


if __name__ == "__main__":
    sys.exit(main())
