"""Seed every wiki page's `## Timeline` section from CHANGELOG history.

One-time migration for the temporal wiki, safe to re-run. It derives `wiki`-kind events — the
page's own edit history — from the Created and Updated bullets in `CHANGELOG.md`, which is the only
dated record of the wiki's own past that exists.

It deliberately does **not** invent substantive events. A page's real history (the papers, the
releases, what each step fixed) comes from a deep-research backfill; nightly runs add the present.
So a freshly seeded timeline is honestly sparse, and `detect_gaps.py` will rank exactly the pages
that need a backfill most.

Writes wiki pages in place through the same code path as `merge_timeline.py`. No network or LLM calls.
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

try:
    from events import Event, EventKind, merge_duplicates, parse_event_date, sort_events
    from merge_timeline import bump_last_updated, parse_section, render_section, split_sections
    from wiki_graph import WikiGraphError, load_wiki_graph, slugify
except ModuleNotFoundError:  # Imported from outside research/scripts/.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from events import Event, EventKind, merge_duplicates, parse_event_date, sort_events
    from merge_timeline import bump_last_updated, parse_section, render_section, split_sections
    from wiki_graph import WikiGraphError, load_wiki_graph, slugify

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(filename)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CHANGELOG = REPO_ROOT / "CHANGELOG.md"

ENTRY_HEADING_PATTERN = re.compile(r"^##\s+\[(?P<date>\d{4}-\d{2}-\d{2})\]\s*(?P<run>.*?)\s*$")
ACTION_PATTERN = re.compile(
    r"^\s*-\s+\*\*(?P<action>Created|Updated)\*\*:\s*`(?P<path>[^`]+\.md)`\s*(?P<reason>.*)$",
)
# The bullets tail off into scores and source citations, which are run bookkeeping, not page history.
REASON_CUTOFF_PATTERN = re.compile(r"\s*(?:\*\*Score|Sources?:)", re.IGNORECASE)
REASON_MAX_CHARS = 180


@dataclass(frozen=True)
class ChangelogAction:
    """One Created or Updated bullet from the changelog."""

    month: str
    action: str
    stem: str
    reason: str

    def to_event(self) -> Event:
        """Render this action as a `wiki`-kind timeline event.

        The reason goes in the significance slot because changelog prose is full of em dashes,
        which are the separator in the bullet grammar.

        Returns:
            The event.
        """
        return Event(
            date=parse_event_date(self.month),
            event=f"Page {self.action.lower()} by a wiki run",
            kind=EventKind.WIKI,
            significance=self.reason,
            sources=(),
            confidence="unstated",
        )


def trim_reason(raw: str) -> str:
    """Reduce a changelog bullet's tail to a single readable clause.

    Args:
        raw: Everything after the backticked path in the bullet.

    Returns:
        A trimmed reason, or an empty string when nothing useful remains.
    """
    reason = REASON_CUTOFF_PATTERN.split(raw.strip(), maxsplit=1)[0]
    reason = reason.lstrip("—- ").strip().rstrip(".")
    # Em dashes are the significance separator in the bullet grammar, so they cannot survive here.
    reason = reason.replace(" — ", "; ").replace("—", "-")
    if len(reason) > REASON_MAX_CHARS:
        reason = reason[:REASON_MAX_CHARS].rsplit(" ", 1)[0] + "…"
    return reason


def parse_changelog(changelog_path: Path) -> dict[str, list[ChangelogAction]]:
    """Read every Created and Updated bullet out of the changelog, keyed by page stem.

    Pages are matched by file stem rather than full path because the wiki was restructured after
    some entries were written, so the recorded paths no longer exist.

    Args:
        changelog_path: Path to `CHANGELOG.md`.

    Returns:
        Mapping of page stem to its actions, oldest first.

    Raises:
        OSError: If the changelog cannot be read.
    """
    actions: defaultdict[str, list[ChangelogAction]] = defaultdict(list)
    month = ""

    for line in changelog_path.read_text(encoding="utf-8").splitlines():
        heading = ENTRY_HEADING_PATTERN.match(line)
        if heading:
            month = heading.group("date")[:7]
            continue

        action = ACTION_PATTERN.match(line)
        if action is None or not month:
            continue

        stem = slugify(Path(action.group("path")).stem)
        actions[stem].append(
            ChangelogAction(
                month=month,
                action=action.group("action"),
                stem=stem,
                reason=trim_reason(action.group("reason")),
            )
        )

    for stem in actions:
        actions[stem].sort(key=lambda item: (item.month, item.action))
    return dict(actions)


def seed_page(page_path: Path, incoming: list[Event], bump: bool) -> tuple[bool, int]:
    """Merge seed events into one page's Timeline section.

    Args:
        page_path: Absolute path to the wiki page.
        incoming: Events to merge in.
        bump: Whether to refresh the page's `Last updated` line.

    Returns:
        Tuple of (whether the file changed, total event count after the merge).

    Raises:
        OSError: If the page cannot be read or written.
    """
    body = page_path.read_text(encoding="utf-8")
    before, section, after = split_sections(body)
    existing, prose, problems = parse_section(section)
    for problem in problems:
        logger.warning("%s: dropping an unparseable bullet — %s", page_path.name, problem)

    merged = sort_events(merge_duplicates(existing + incoming)[0])
    rebuilt = bump_last_updated(before, datetime.now(UTC).strftime("%Y-%m-%d")) if bump else before
    text = "\n".join([*rebuilt, *render_section(merged, prose), *after]).rstrip() + "\n"

    if text == body:
        return False, len(merged)
    page_path.write_text(text, encoding="utf-8")
    return True, len(merged)


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Argument list without the program name.

    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(description="Seed every wiki page's Timeline section from CHANGELOG history.")
    parser.add_argument("--changelog", help=f"Changelog to read (default: {DEFAULT_CHANGELOG.name}).")
    parser.add_argument("--wiki-dir", help="Wiki root to migrate (default: the repo's wiki/).")
    parser.add_argument("--page", help="Migrate only this page (slug or path).")
    parser.add_argument("--dry-run", action="store_true", help="Report what would change without writing.")
    parser.add_argument("--bump", action="store_true", help="Also refresh each page's Last updated line.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Seed Timeline sections across the wiki.

    Args:
        argv: Argument list without the program name; defaults to `sys.argv[1:]`.

    Returns:
        0 on success, 1 when the wiki or changelog cannot be read.
    """
    args = parse_args(sys.argv[1:] if argv is None else argv)

    changelog_path = Path(args.changelog) if args.changelog else DEFAULT_CHANGELOG
    try:
        actions = parse_changelog(changelog_path)
        graph = load_wiki_graph(Path(args.wiki_dir) if args.wiki_dir else None)
    except (OSError, WikiGraphError) as error:
        logger.error("%s", error)
        return 1

    logger.info("Read %d page(s) worth of history from %s", len(actions), changelog_path.name)

    only = slugify(Path(args.page).stem) if args.page else None
    changed = unchanged = without_history = 0

    for key, page in sorted(graph.pages.items()):
        if only and page.slug != only:
            continue

        page_actions = actions.get(page.slug, [])
        if not page_actions:
            without_history += 1
            logger.info("%s: no changelog history — leaving its timeline alone", key)
            continue

        events = [action.to_event() for action in page_actions]
        if args.dry_run:
            logger.info("%s: would seed %d event(s) — %s", key, len(events), ", ".join(e.date.label for e in events))
            continue

        try:
            was_changed, total = seed_page(REPO_ROOT / page.path, events, args.bump)
        except OSError:
            logger.exception("Could not seed %s", page.path)
            return 1

        if was_changed:
            changed += 1
            logger.info("%s: seeded %d event(s), %d total", key, len(events), total)
        else:
            unchanged += 1

    logger.info(
        "Final summary: %d page(s) seeded, %d already current, %d with no changelog history",
        changed,
        unchanged,
        without_history,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
