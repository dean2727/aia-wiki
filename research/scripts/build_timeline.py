"""Turn extracted events into a verified chronological backbone for the narrative stage.

Asking a model to write history straight from search snippets is where invented dates come from.
This script takes the flat `events.jsonl` the research stage produced, validates every record,
parses partial dates, merges near-duplicates, sorts, and emits a numbered timeline. The narrative
stage then writes prose from the timeline only — structure first, prose second.

The event model lives in `events.py`, shared with `merge_timeline.py` so the two writers cannot
drift apart on the date grammar or the duplicate rule.

Reads and writes one run directory. No network or LLM calls.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

try:
    from events import (
        DEFAULT_SIMILARITY,
        URL_PATTERN,
        Event,
        EventDateError,
        EventKind,
        merge_duplicates,
        parse_event_date,
        sort_events,
    )
except ModuleNotFoundError:  # Imported from outside research/scripts/.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from events import (
        DEFAULT_SIMILARITY,
        URL_PATTERN,
        Event,
        EventDateError,
        EventKind,
        merge_duplicates,
        parse_event_date,
        sort_events,
    )

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(filename)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

DEFAULT_EVENTS_FILENAME = "events.jsonl"
# A backfill that lands under this is not a history, it is a press release with dates.
DEFAULT_MIN_EVENTS = 8
DEFAULT_MIN_YEARS = 3
REQUIRED_FIELDS = ("date", "event")


class TimelineError(Exception):
    """Base class for every failure this module raises."""


class RunDirError(TimelineError):
    """The run directory or its events file is missing."""


class Status(StrEnum):
    """Verdict for the timeline, used to decide whether the narrative stage can start."""

    OK = "ok"
    NO_EVENTS = "no_events"
    MALFORMED_RECORDS = "malformed_records"
    UNPARSEABLE_DATES = "unparseable_dates"
    MISSING_SOURCES = "missing_sources"
    SPARSE_TIMELINE = "sparse_timeline"
    WRITE_FAILED = "write_failed"


REMEDIATION: dict[Status, str] = {
    Status.NO_EVENTS: (
        "events.jsonl is empty or has no valid records. Re-run the extraction prompt "
        "(research/prompts/04-event-extraction.md) over research/runs/<run>/findings/."
    ),
    Status.MALFORMED_RECORDS: (
        "Some lines are not JSON objects with `date` and `event`. Fix or delete those lines and re-run; "
        "one object per line, no trailing commas, no wrapping array."
    ),
    Status.UNPARSEABLE_DATES: (
        "Some dates are not YYYY, YYYY-MM, YYYY-MM-DD, YYYY-Q1, or an `early/mid/late/~` form. "
        "If a source genuinely gives no date, drop the event — an undated event cannot anchor a narrative."
    ),
    Status.MISSING_SOURCES: (
        "Some events carry no source URL. Add the URL that supports each one, or re-run with "
        "--drop-unsourced to discard them. An unsourced date is a guess."
    ),
    Status.SPARSE_TIMELINE: (
        "Too few events or too narrow a span to call this a history. Run more perspectives, or search "
        "explicitly for prior art before the topic existed. Re-run with --allow-sparse to accept it anyway."
    ),
    Status.WRITE_FAILED: "The timeline could not be written. Check that the run directory is present and writable.",
}


def coerce_sources(record: dict[str, object]) -> tuple[str, ...]:
    """Read the source URLs off an event record in either accepted shape.

    Args:
        record: Decoded event record.

    Returns:
        Deduplicated source URLs, keeping only well-formed http(s) links.
    """
    raw = record.get("sources") or record.get("source_url") or ()
    candidates = [raw] if isinstance(raw, str) else [str(item) for item in raw if item]
    return tuple(dict.fromkeys(url.strip() for url in candidates if URL_PATTERN.match(url.strip())))


def load_events(events_path: Path) -> tuple[list[Event], list[str]]:
    """Read and validate `events.jsonl`.

    Args:
        events_path: Path to the newline-delimited JSON events file.

    Returns:
        Tuple of (valid events, one problem string per rejected line).

    Raises:
        RunDirError: If the events file does not exist.
    """
    if not events_path.is_file():
        raise RunDirError(f"{events_path} does not exist — the extraction stage has not run yet")

    events: list[Event] = []
    problems: list[str] = []
    for number, line in enumerate(events_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip() or line.lstrip().startswith("//"):
            continue

        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            problems.append(f"line {number}: not valid JSON ({error.msg})")
            continue

        if not isinstance(record, dict) or any(not str(record.get(field, "")).strip() for field in REQUIRED_FIELDS):
            problems.append(f"line {number}: needs non-empty {' and '.join(REQUIRED_FIELDS)}")
            continue

        try:
            event_date = parse_event_date(str(record["date"]))
        except EventDateError as error:
            problems.append(f"line {number}: {error}")
            continue

        raw_kind = str(record.get("kind", "")).strip().lower()
        if raw_kind and raw_kind not in set(EventKind):
            logger.warning("Line %d: unknown kind %r — recording it as %s", number, raw_kind, EventKind.MILESTONE)

        events.append(
            Event(
                date=event_date,
                event=str(record["event"]).strip(),
                kind=EventKind(raw_kind) if raw_kind in set(EventKind) else EventKind.MILESTONE,
                significance=str(record.get("significance", "")).strip(),
                sources=coerce_sources(record),
                confidence=str(record.get("confidence", "")).strip().lower() or "unstated",
            )
        )

    return events, problems


def render_timeline(topic: str, events: list[Event], generated_at: str) -> str:
    """Render the sorted events as the numbered timeline the narrative stage reads.

    Args:
        topic: Run topic, used in the heading.
        events: Sorted, merged events.
        generated_at: ISO timestamp of this build.

    Returns:
        The full markdown body of `timeline.md`.
    """
    years = [event.date.year for event in events]
    source_count = len({url for event in events for url in event.sources})

    lines = [
        f"# Timeline — {topic}",
        "",
        f"_{len(events)} events, {min(years)}–{max(years)}, from {source_count} source(s). "
        f"Generated {generated_at} by `build_timeline.py` from `events.jsonl` — edit the events file "
        "and re-run, never this file._",
        "",
        "Every date here is anchored to a source. Write the narrative from these events only: a year that",
        "does not appear below does not appear in the prose.",
        "",
    ]

    current_year: int | None = None
    for index, event in enumerate(events, start=1):
        if event.date.year != current_year:
            current_year = event.date.year
            lines += [f"## {current_year}", ""]
        lines.append(f"**Event #{index}** [{event.date.label}] ({event.kind}) — {event.event}")
        if event.significance:
            lines.append(f"  - why it mattered: {event.significance}")
        lines.append(f"  - sources: {', '.join(event.sources) if event.sources else 'NONE'}")
        if event.confidence in {"low", "medium"}:
            lines.append(f"  - confidence: {event.confidence}")
        lines.append("")

    return "\n".join(lines)


def diagnose(events: list[Event], problems: list[str], args: argparse.Namespace) -> tuple[Status, str]:
    """Decide whether the timeline is solid enough to narrate from.

    Args:
        events: Merged events.
        problems: Rejected-line messages from loading.
        args: Parsed command-line options.

    Returns:
        Tuple of (status, one-line reason).
    """
    if problems:
        malformed = [problem for problem in problems if "cannot parse date" in problem or "out-of-range" in problem]
        if len(malformed) == len(problems):
            return Status.UNPARSEABLE_DATES, f"{len(malformed)} event(s) have dates that cannot be placed"
        return Status.MALFORMED_RECORDS, f"{len(problems)} line(s) were rejected"

    if not events:
        return Status.NO_EVENTS, "no valid events survived validation"

    unsourced = sum(1 for event in events if not event.sources)
    if unsourced and not args.drop_unsourced:
        return Status.MISSING_SOURCES, f"{unsourced} event(s) carry no source URL"

    distinct_years = len({event.date.year for event in events})
    if not args.allow_sparse and (len(events) < args.min_events or distinct_years < args.min_years):
        return (
            Status.SPARSE_TIMELINE,
            f"{len(events)} event(s) across {distinct_years} year(s); "
            f"wanted {args.min_events} across {args.min_years}",
        )

    return Status.OK, f"{len(events)} event(s) across {distinct_years} year(s)"


def resolve_topic(run_dir: Path) -> str:
    """Read the run topic from `run.json`, falling back to the directory name.

    Args:
        run_dir: Run directory.

    Returns:
        The topic string.
    """
    manifest_path = run_dir / "run.json"
    try:
        return str(json.loads(manifest_path.read_text(encoding="utf-8"))["topic"])
    except (OSError, json.JSONDecodeError, KeyError):
        logger.warning("Could not read a topic from %s — using the directory name", manifest_path)
        return run_dir.name


def write_timeline(run_dir: Path, topic: str, events: list[Event], generated_at: str) -> tuple[Path, Path]:
    """Write `timeline.md` and `timeline.json` into the run directory.

    Args:
        run_dir: Run directory.
        topic: Run topic.
        events: Sorted, merged events.
        generated_at: ISO timestamp of this build.

    Returns:
        Tuple of (markdown path, json path).

    Raises:
        TimelineError: If either file cannot be written.
    """
    markdown_path = run_dir / "timeline.md"
    json_path = run_dir / "timeline.json"
    payload = {
        "topic": topic,
        "generated_at": generated_at,
        "span": [events[0].date.year, events[-1].date.year],
        "events": [event.as_dict(index) for index, event in enumerate(events, start=1)],
    }

    try:
        markdown_path.write_text(render_timeline(topic, events, generated_at), encoding="utf-8")
        json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    except OSError as error:
        logger.exception("Could not write the timeline into %s", run_dir)
        raise TimelineError(f"could not write the timeline into {run_dir}: {error}") from error

    return markdown_path, json_path


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Argument list without the program name.

    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(description="Validate, merge, and sort extracted events into a timeline.")
    parser.add_argument("run_dir", help="Research run directory (research/runs/<run-id>).")
    parser.add_argument("--events", help=f"Override the events file (default: <run_dir>/{DEFAULT_EVENTS_FILENAME}).")
    parser.add_argument("--check", action="store_true", help="Validate the events without writing the timeline.")
    parser.add_argument(
        "--min-events",
        type=int,
        default=DEFAULT_MIN_EVENTS,
        help=f"Events required before the timeline counts as a history (default {DEFAULT_MIN_EVENTS}).",
    )
    parser.add_argument(
        "--min-years",
        type=int,
        default=DEFAULT_MIN_YEARS,
        help=f"Distinct years the timeline must span (default {DEFAULT_MIN_YEARS}).",
    )
    parser.add_argument(
        "--similarity",
        type=float,
        default=DEFAULT_SIMILARITY,
        help=f"Score above which two same-year events are merged (default {DEFAULT_SIMILARITY}).",
    )
    parser.add_argument("--drop-unsourced", action="store_true", help="Discard events with no source URL.")
    parser.add_argument("--allow-sparse", action="store_true", help="Accept a short or narrow timeline.")
    parser.add_argument("--json", action="store_true", help="Emit a machine-readable report on stdout.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Build the timeline for one research run.

    Args:
        argv: Argument list without the program name; defaults to `sys.argv[1:]`.

    Returns:
        0 when the timeline is solid, 2 when it needs a human decision, 1 on internal failure.
    """
    args = parse_args(sys.argv[1:] if argv is None else argv)

    run_dir = Path(args.run_dir)
    if not run_dir.is_dir():
        logger.error("%s is not a directory — run start_run.py first", run_dir)
        return 1

    events_path = Path(args.events) if args.events else run_dir / DEFAULT_EVENTS_FILENAME
    try:
        events, problems = load_events(events_path)
    except RunDirError as error:
        logger.error("%s", error)
        return 1

    if args.drop_unsourced:
        kept = [event for event in events if event.sources]
        if len(kept) != len(events):
            logger.warning("Dropped %d unsourced event(s)", len(events) - len(kept))
        events = kept

    events, merges = merge_duplicates(events, args.similarity)
    events = sort_events(events)

    status, reason = diagnose(events, problems, args)
    generated_at = datetime.now(UTC).isoformat()
    topic = resolve_topic(run_dir)
    written: list[str] = []

    if status is Status.OK and not args.check:
        try:
            written = [str(path) for path in write_timeline(run_dir, topic, events, generated_at)]
        except TimelineError as error:
            status, reason = Status.WRITE_FAILED, str(error)

    lines = [f"{status.upper()}  {run_dir}", f"  reason: {reason}"]
    lines += [f"  merged: {note}" for note in merges]
    lines += [f"  problem: {problem}" for problem in problems]
    lines += [f"  wrote: {path}" for path in written]
    if args.check and status is Status.OK:
        lines.append("  note: check-only run, nothing was written")
    if status is not Status.OK:
        lines.append(f"  fix: {REMEDIATION[status]}")
    logger.info("\n".join(lines))

    if args.json:
        print(
            json.dumps(
                {
                    "run_dir": str(run_dir),
                    "status": str(status),
                    "reason": reason,
                    "event_count": len(events),
                    "merged": merges,
                    "problems": problems,
                    "written": written,
                    "events": [event.as_dict(index) for index, event in enumerate(events, start=1)],
                },
                indent=2,
            )
        )

    return 0 if status is Status.OK else 2


if __name__ == "__main__":
    sys.exit(main())
