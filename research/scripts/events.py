"""The event model shared by the timeline builder and the wiki timeline merger.

One event is a dated, sourced fact about a topic. Events are produced by a research run
(`build_timeline.py`) or by a nightly ingest, and they live on a wiki page's `## Timeline`
section as strict-format bullets, which the site renders as a month slider.

This module owns the date grammar, the bullet grammar, and the duplicate-merging rule, so the
two writers cannot drift apart on any of them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from difflib import SequenceMatcher
from enum import StrEnum

# Same fact phrased two ways by two sources; below this they are genuinely different events.
DEFAULT_SIMILARITY = 0.80
# Dropped before comparing events so "Han et al. propose SSD-LM" and "SSD-LM introduces …" line up.
STOPWORDS = frozenset("a an and al as at by et for from in into is its of on or over the their to with".split())

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

BULLET_PATTERN = re.compile(r"^-\s+`(?P<date>[^`]+)`\s+\((?P<kind>[a-z]+)\)\s+(?P<rest>.+?)\s*$")
SOURCE_LINK_PATTERN = re.compile(r"\[source\]\((?P<url>[^)\s]+)\)")
# Significance is split on the first em dash, so event sentences must not contain one.
SIGNIFICANCE_SEPARATOR = " — "


class EventError(Exception):
    """Base class for every failure this module raises."""


class EventDateError(EventError):
    """A date string cannot be placed on a timeline."""


class EventFormatError(EventError):
    """A timeline bullet does not match the required grammar."""


class EventKind(StrEnum):
    """What kind of thing happened, so a reader can tell ideas from shipping from wiki upkeep."""

    PAPER = "paper"
    METHOD = "method"
    RELEASE = "release"
    BENCHMARK = "benchmark"
    TOOLING = "tooling"
    ORG = "org"
    MILESTONE = "milestone"
    WIKI = "wiki"


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

    @property
    def month_key(self) -> str:
        """Return the month bucket the slider files this event under.

        Year-only events land in January of their year; `approximate` records that this was a
        placement decision rather than something a source said.

        Returns:
            A `YYYY-MM` key.
        """
        return f"{self.year:04d}-{self.month or 1:02d}"


def parse_event_date(raw: str) -> EventDate:
    """Parse the partial date forms sources actually publish.

    Accepts `2017`, `2017-06`, `2017-06-12`, `2017-Q3`, and the approximate `~2017`, `c. 2017`,
    `early 2017`, `mid-2017`, `late 2017` forms.

    Args:
        raw: Date string from an event record or timeline bullet.

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


@dataclass(frozen=True)
class Event:
    """One dated, sourced fact on a topic's timeline."""

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

    def as_dict(self, index: int | None = None) -> dict[str, object]:
        """Return a JSON-serializable view of the event.

        Args:
            index: Optional position on the timeline, 1-based.

        Returns:
            Mapping of event fields with the date flattened.
        """
        payload: dict[str, object] = {
            "date": self.date.label,
            "month": self.date.month_key,
            "year": self.date.year,
            "approximate": self.date.approximate,
            "event": self.event,
            "kind": str(self.kind),
            "significance": self.significance,
            "sources": list(self.sources),
            "confidence": self.confidence,
        }
        return {"index": index, **payload} if index is not None else payload

    def to_bullet(self) -> str:
        """Render the event as a wiki `## Timeline` bullet.

        Returns:
            A single-line markdown bullet matching the documented grammar.
        """
        parts = [f"- `{self.date.label}` ({self.kind}) {self.event}"]
        if self.significance:
            parts.append(f"{SIGNIFICANCE_SEPARATOR}{self.significance}")
        parts.extend(f" [source]({url})" for url in self.sources)
        return "".join(parts)


def parse_bullet(line: str) -> Event:
    """Parse one wiki `## Timeline` bullet back into an event.

    Args:
        line: A single bullet line from a page's Timeline section.

    Returns:
        The parsed event.

    Raises:
        EventFormatError: If the line does not match the bullet grammar or names an unknown kind.
        EventDateError: If the backticked date cannot be placed.
    """
    match = BULLET_PATTERN.match(line.strip())
    if match is None:
        raise EventFormatError("expected `- `YYYY-MM` (kind) sentence [source](url)`")

    kind = match.group("kind")
    if kind not in set(EventKind):
        raise EventFormatError(f"unknown kind {kind!r}; expected one of {', '.join(sorted(EventKind))}")

    rest = match.group("rest")
    sources = tuple(dict.fromkeys(SOURCE_LINK_PATTERN.findall(rest)))
    text = SOURCE_LINK_PATTERN.sub("", rest).strip()

    event, _, significance = text.partition(SIGNIFICANCE_SEPARATOR)
    return Event(
        date=parse_event_date(match.group("date")),
        event=event.strip(),
        kind=EventKind(kind),
        significance=significance.strip(),
        sources=sources,
        confidence="unstated",
    )


def normalize(text: str) -> str:
    """Reduce event text to a comparable form for duplicate detection.

    Args:
        text: Event sentence.

    Returns:
        Lowercased text with punctuation stripped and whitespace collapsed.
    """
    return " ".join(NORMALIZE_PATTERN.sub(" ", text.lower()).split())


def truncate(text: str, limit: int = 70) -> str:
    """Shorten an event sentence for log output.

    Args:
        text: Event sentence.
        limit: Maximum length before the ellipsis.

    Returns:
        The sentence, truncated on a word boundary when it is too long.
    """
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + "…"


def similarity(left: str, right: str) -> float:
    """Score how likely two event sentences describe the same event.

    Sequence ratio alone misses reordered paraphrases, which is how two sources typically report
    one fact, so the content-word overlap is taken whenever it is the stronger signal.

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


def merge_duplicates(events: list[Event], threshold: float = DEFAULT_SIMILARITY) -> tuple[list[Event], list[str]]:
    """Collapse the same event reported twice into one entry.

    Comparison is scoped to a single year, which keeps it cheap and avoids merging a paper with
    the release it later inspired. Every merge is reported so a wrong one can be caught.

    Args:
        events: Events to merge, in any order.
        threshold: Similarity score above which two same-year events are the same event.

    Returns:
        Tuple of (merged events, one human-readable note per merge).
    """
    merged: list[Event] = []
    notes: list[str] = []

    for event in events:
        for index, existing in enumerate(merged):
            if existing.date.year != event.date.year or existing.kind is not event.kind:
                continue

            if event.kind is EventKind.WIKI:
                # A page's own edit history is a sequence of distinct acts, never two reports of one
                # fact, so only an exact repeat is a duplicate — that keeps re-runs idempotent
                # without collapsing a May edit into a June one.
                if existing.date.month_key != event.date.month_key or normalize(existing.event) != normalize(
                    event.event
                ):
                    continue
                score = 1.0
            else:
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


def sort_events(events: list[Event]) -> list[Event]:
    """Order events oldest first, deterministically.

    Args:
        events: Events to sort.

    Returns:
        A new list ordered by date then event text.
    """
    return sorted(events, key=lambda event: (event.date.sort_key, event.event))
