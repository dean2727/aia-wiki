"""Turn extracted events into a verified chronological backbone for the narrative stage.

Asking a model to write history straight from search snippets is where invented dates come from.
This script takes the flat `events.jsonl` the research stage produced, validates every record,
parses partial dates, merges near-duplicates, sorts, and emits a numbered timeline. The narrative
stage then writes prose from the timeline only — structure first, prose second.

Reads and writes one run directory. No network or LLM calls.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from difflib import SequenceMatcher
from enum import StrEnum
from pathlib import Path

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
# Same fact phrased two ways by two perspectives; below this they are genuinely different events.
DEFAULT_SIMILARITY = 0.80
REQUIRED_FIELDS = ("date", "event")
# Dropped before comparing events so "Han et al. propose SSD-LM" and "SSD-LM introduces …" line up.
STOPWORDS = frozenset(
    "a an and al as at by et for from in into is its of on or over the their to with".split()
)

DATE_PATTERN = re.compile(
    r"^(?P<approx>~|c\.?\s*|circa\s+|early[-\s]|mid[-\s]|late[-\s])?"
    r"(?P<year>\d{4})"
    r"(?:[-/](?:Q(?P<quarter>[1-4])|(?P<month>\d{1,2})))?"
    r"(?:[-/](?P<day>\d{1,2}))?$",
    re.IGNORECASE,
)
ERA_MONTHS = {"early": 2, "mid": 6, "late": 10}
NORMALIZE_PATTERN = re.compile(r"[^a-z0-9 ]+")
URL_PATTERN = re.compile(r"^https?://")


class TimelineError(Exception):
    """Base class for every failure this module raises."""


class RunDirError(TimelineError):
    """The run directory or its events file is missing."""


class EventDateError(TimelineError):
    """An event carries a date this script cannot place on a timeline."""


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


class EventKind(StrEnum):
    """What kind of thing happened, so the narrative can distinguish ideas from shipping."""

    PAPER = "paper"
    METHOD = "method"
    RELEASE = "release"
    BENCHMARK = "benchmark"
    TOOLING = "tooling"
    ORG = "org"
    MILESTONE = "milestone"


@dataclass(frozen=True)
class EventDate:
    """A parsed point in time that tolerates the partial dates real sources give."""

    raw: str
    year: int
    month: int | None
    day: int | None
    approximate: bool

    @property
    def sort_key(self) -> tuple[int, int, int]:
        """Return the chronological sort key.

        Year-only events sort before dated events in the same year, which reads correctly as
        "sometime that year, before the things we can pin down".

        Returns:
            Tuple of (year, month, day) with unknown components as 0.
        """
        return (self.year, self.month or 0, self.day or 0)

    @property
    def label(self) -> str:
        """Return the display label at the precision the source actually supported.

        Returns:
            An ISO-like label, prefixed with `~` when the date is approximate.
        """
        parts = f"{self.year:04d}"
        if self.month is not None:
            parts += f"-{self.month:02d}"
        if self.day is not None:
            parts += f"-{self.day:02d}"
        return f"~{parts}" if self.approximate else parts


@dataclass(frozen=True)
class Event:
    """One dated, sourced fact on the timeline."""

    date: EventDate
    event: str
    kind: EventKind
    significance: str
    sources: tuple[str, ...]
    confidence: str

    @property
    def precision(self) -> int:
        """Return how precisely this event is dated.

        Returns:
            2 for a full date, 1 for year-month, 0 for year only.
        """
        return (self.date.month is not None) + (self.date.day is not None)

    def as_dict(self, index: int) -> dict[str, object]:
        """Return a JSON-serializable view of the event.

        Args:
            index: Position on the timeline, 1-based.

        Returns:
            Mapping of event fields with the date flattened.
        """
        return {
            "index": index,
            "date": self.date.label,
            "year": self.date.year,
            "month": self.date.month,
            "day": self.date.day,
            "approximate": self.date.approximate,
            "event": self.event,
            "kind": str(self.kind),
            "significance": self.significance,
            "sources": list(self.sources),
            "confidence": self.confidence,
        }


def parse_event_date(raw: str) -> EventDate:
    """Parse the partial date forms sources actually publish.

    Accepts `2017`, `2017-06`, `2017-06-12`, `2017-Q3`, and the approximate `~2017`, `c. 2017`,
    `early 2017`, `mid-2017`, `late 2017` forms.

    Args:
        raw: Date string from an event record.

    Returns:
        The parsed date.

    Raises:
        EventDateError: If the string is not a recognizable date.
    """
    match = DATE_PATTERN.match(raw.strip())
    if match is None:
        raise EventDateError(f"cannot parse date {raw!r}")

    approx_token = (match.group("approx") or "").strip().rstrip("-. ").lower()
    month = int(match.group("month")) if match.group("month") else None
    approximate = bool(approx_token)

    if match.group("quarter"):
        month = (int(match.group("quarter")) - 1) * 3 + 2  # Mid-quarter, so ordering stays sane.
        approximate = True
    elif approx_token in ERA_MONTHS:
        month = ERA_MONTHS[approx_token]

    day = int(match.group("day")) if match.group("day") else None
    if (month is not None and not 1 <= month <= 12) or (day is not None and not 1 <= day <= 31):
        raise EventDateError(f"date {raw!r} has an out-of-range month or day")

    return EventDate(raw=raw.strip(), year=int(match.group("year")), month=month, day=day, approximate=approximate)


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


def normalize(text: str) -> str:
    """Reduce event text to a comparable form for duplicate detection.

    Args:
        text: Event sentence.

    Returns:
        Lowercased text with punctuation stripped and whitespace collapsed.
    """
    return " ".join(NORMALIZE_PATTERN.sub(" ", text.lower()).split())


def similarity(left: str, right: str) -> float:
    """Score how likely two event sentences describe the same event.

    Sequence ratio alone misses reordered paraphrases, which is how two perspectives typically
    report one fact, so the content-word overlap is taken whenever it is the stronger signal.

    Args:
        left: First event sentence.
        right: Second event sentence.

    Returns:
        A score from 0.0 to 1.0.
    """
    ratio = SequenceMatcher(None, normalize(left), normalize(right)).ratio()
    left_tokens = frozenset(normalize(left).split()) - STOPWORDS
    right_tokens = frozenset(normalize(right).split()) - STOPWORDS
    if not left_tokens or not right_tokens:
        return ratio
    overlap = len(left_tokens & right_tokens) / min(len(left_tokens), len(right_tokens))
    return max(ratio, overlap)


def merge_duplicates(events: list[Event], threshold: float) -> tuple[list[Event], list[str]]:
    """Collapse the same event reported by different perspectives into one entry.

    Comparison is scoped to a single year, which keeps it cheap and avoids merging a paper with
    the release it later inspired. Every merge is reported so a wrong one can be caught.

    Args:
        events: Validated events.
        threshold: Similarity score above which two same-year events are the same event.

    Returns:
        Tuple of (merged events, one human-readable note per merge).
    """
    merged: list[Event] = []
    notes: list[str] = []

    for event in events:
        for index, existing in enumerate(merged):
            if existing.date.year != event.date.year:
                continue
            score = similarity(existing.event, event.event)
            if score < threshold:
                continue

            keeper, other = (event, existing) if event.precision > existing.precision else (existing, event)
            merged[index] = replace(
                keeper,
                sources=tuple(dict.fromkeys(keeper.sources + other.sources)),
                significance=max(keeper.significance, other.significance, key=len),
            )
            notes.append(f'{score:.2f} — kept "{truncate(keeper.event)}", absorbed "{truncate(other.event)}"')
            break
        else:
            merged.append(event)

    return merged, notes


def truncate(text: str, limit: int = 70) -> str:
    """Shorten an event sentence for log output.

    Args:
        text: Event sentence.
        limit: Maximum length before the ellipsis.

    Returns:
        The sentence, truncated on a word boundary when it is too long.
    """
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + "…"


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
        help=f"Ratio above which two same-year events are merged (default {DEFAULT_SIMILARITY}).",
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
    events.sort(key=lambda event: (event.date.sort_key, event.event))

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
