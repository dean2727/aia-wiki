"""Rank the background the wiki is missing, so a research run knows what to go find.

This is the deterministic half of gap detection: it measures what the link graph can prove
(concepts many pages lean on but none define, pages nothing points at, topics written with no
historical depth) and ranks candidates by how many existing pages already depend on them.

The judgement half — reading a page and enumerating the terms it cannot explain from its own
text — is an LLM step driven by `research/prompts/01-gap-analysis.md`. Run this first; its output
is that prompt's input.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

try:
    from wiki_graph import WikiGraph, WikiGraphError, load_wiki_graph, strip_code
except ModuleNotFoundError:  # Imported from outside research/scripts/.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from wiki_graph import WikiGraph, WikiGraphError, load_wiki_graph, strip_code

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(filename)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# A concept this many pages already lean on is load-bearing, so backfilling it pays off across
# the whole wiki rather than for one page.
DEFAULT_FOUNDATIONAL_REFERENCES = 3
DEFAULT_STALE_DAYS = 90
DEFAULT_MIN_LINES = 30
DEFAULT_MIN_YEARS = 3
DEFAULT_TOP = 15
DEFAULT_HOPS = 1
# Short titles ("Synthesis", "Agents") match too much prose to be evidence of a missing link.
MIN_MENTION_TITLE_CHARS = 8
MAX_MENTION_PAGES = 15
# Only affects the printed report; --json always carries the full list.
MAX_REFERENCES_SHOWN = 8

DANGLING_LINK_WEIGHT = 3
SHALLOW_HISTORY_WEIGHT = 2
METADATA_LINE_PATTERN = re.compile(r"^\*\*[A-Za-z ]+\*\*:.*$", re.MULTILINE)
URL_PATTERN = re.compile(r"https?://\S+")
YEAR_PATTERN = re.compile(r"\b(?:19[89]\d|20[0-4]\d)\b")


class GapKind(StrEnum):
    """The kind of hole a gap represents, which decides how it should be filled."""

    DANGLING_LINK = "dangling_link"
    SHALLOW_HISTORY = "shallow_history"
    UNLINKED_MENTION = "unlinked_mention"
    ORPHAN_PAGE = "orphan_page"
    STALE_PAGE = "stale_page"
    THIN_PAGE = "thin_page"


REMEDIATION: dict[GapKind, str] = {
    GapKind.DANGLING_LINK: (
        "Pages link to this concept but nothing defines it. Best backfill candidates — run "
        "start_run.py on the highest-scoring ones."
    ),
    GapKind.SHALLOW_HISTORY: (
        "The page describes a present-tense state with almost no dated prior art, so a reader "
        "learns what it is but not what it replaced. This is the core backfill case."
    ),
    GapKind.UNLINKED_MENTION: "A page names a topic the wiki already covers without linking it. Add the [[wikilink]].",
    GapKind.ORPHAN_PAGE: "Nothing links here, so the page is unreachable by browsing. Link it from a related page.",
    GapKind.STALE_PAGE: "Fast-moving topic with an old `Last updated` line. Re-check it against current sources.",
    GapKind.THIN_PAGE: "Too short to carry real explanation. Deepen it or merge it into a fuller page.",
}


@dataclass(frozen=True)
class Gap:
    """One ranked hole in the wiki's coverage."""

    kind: GapKind
    subject: str
    detail: str
    score: int
    referenced_by: tuple[str, ...] = ()
    path: str | None = None

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-serializable view of the gap.

        Returns:
            Mapping of gap fields with the kind rendered as a plain string.
        """
        return {
            "kind": str(self.kind),
            "subject": self.subject,
            "detail": self.detail,
            "score": self.score,
            "referenced_by": list(self.referenced_by),
            "path": self.path,
        }


def distinct_years(body: str) -> set[str]:
    """Count the distinct years a text's prose actually names.

    Metadata lines and URLs are dropped first, so neither a page's own `Last updated` stamp nor a
    dated permalink counts as historical depth.

    Args:
        body: Markdown body.

    Returns:
        The set of four-digit years mentioned in the prose.
    """
    prose = URL_PATTERN.sub(" ", METADATA_LINE_PATTERN.sub("", strip_code(body)))
    return set(YEAR_PATTERN.findall(prose))


def find_dangling_links(graph: WikiGraph, scope: set[str] | None) -> list[Gap]:
    """Rank link targets that no page defines.

    Args:
        graph: Indexed wiki graph.
        scope: Optional set of page slugs to restrict referencing pages to.

    Returns:
        Gaps ordered by score, highest first.
    """
    gaps: list[Gap] = []
    for target, sources in graph.dangling_links.items():
        referenced_by = tuple(sorted(sources & scope)) if scope is not None else tuple(sorted(sources))
        if not referenced_by:
            continue
        mentions = len(graph.pages_mentioning(target))
        foundational = " — foundational" if len(referenced_by) >= DEFAULT_FOUNDATIONAL_REFERENCES else ""
        gaps.append(
            Gap(
                kind=GapKind.DANGLING_LINK,
                subject=target,
                detail=f"linked by {len(referenced_by)} page(s), named in {mentions} page(s){foundational}",
                score=DANGLING_LINK_WEIGHT * len(referenced_by) + mentions,
                referenced_by=referenced_by,
            )
        )
    return sorted(gaps, key=lambda gap: (-gap.score, gap.subject))


def find_shallow_history(graph: WikiGraph, scope: set[str] | None, min_years: int) -> list[Gap]:
    """Find pages that explain a topic without placing it in time.

    Args:
        graph: Indexed wiki graph.
        scope: Optional set of page slugs to restrict the scan to.
        min_years: Fewest distinct years a page must name to count as historically grounded.

    Returns:
        Gaps ordered by score, highest first.
    """
    gaps: list[Gap] = []
    for slug, page in graph.pages.items():
        if page.is_hub or (scope is not None and slug not in scope):
            continue
        years = distinct_years(page.body)
        if len(years) >= min_years:
            continue
        inbound = graph.inbound(slug)
        span = ", ".join(sorted(years)) if years else "no years at all"
        gaps.append(
            Gap(
                kind=GapKind.SHALLOW_HISTORY,
                subject=slug,
                detail=f"names {span}; {len(inbound)} page(s) link here",
                score=SHALLOW_HISTORY_WEIGHT * len(inbound) + (min_years - len(years)),
                referenced_by=tuple(sorted(inbound)),
                path=page.path,
            )
        )
    return sorted(gaps, key=lambda gap: (-gap.score, gap.subject))


def find_unlinked_mentions(graph: WikiGraph, scope: set[str] | None) -> list[Gap]:
    """Find pages named in prose elsewhere without a wikilink pointing at them.

    Args:
        graph: Indexed wiki graph.
        scope: Optional set of page slugs to restrict the scan to.

    Returns:
        Gaps ordered by score, highest first.
    """
    gaps: list[Gap] = []
    for slug, page in graph.pages.items():
        if page.is_hub or len(page.title) < MIN_MENTION_TITLE_CHARS or (scope is not None and slug not in scope):
            continue
        mentioning = set(graph.pages_mentioning(page.title, exclude=slug))
        if len(mentioning) > MAX_MENTION_PAGES:
            continue
        missing = tuple(sorted(mentioning - graph.inbound(slug)))
        if not missing:
            continue
        gaps.append(
            Gap(
                kind=GapKind.UNLINKED_MENTION,
                subject=slug,
                detail=f'"{page.title}" is named but not linked by {len(missing)} page(s)',
                score=len(missing),
                referenced_by=missing,
                path=page.path,
            )
        )
    return sorted(gaps, key=lambda gap: (-gap.score, gap.subject))


def find_page_health(graph: WikiGraph, scope: set[str] | None, stale_days: int, min_lines: int) -> list[Gap]:
    """Flag orphaned, stale, and thin pages.

    Args:
        graph: Indexed wiki graph.
        scope: Optional set of page slugs to restrict the scan to.
        stale_days: Age in days past which a page is called stale.
        min_lines: Line count below which a page is called thin.

    Returns:
        Gaps ordered by kind then score.
    """
    gaps: list[Gap] = []
    for slug, page in graph.pages.items():
        if page.is_hub or (scope is not None and slug not in scope):
            continue

        if not graph.inbound(slug):
            gaps.append(
                Gap(
                    kind=GapKind.ORPHAN_PAGE,
                    subject=slug,
                    detail="no page links here",
                    score=1,
                    path=page.path,
                )
            )

        age = page.days_since_update
        if age is not None and age > stale_days:
            gaps.append(
                Gap(
                    kind=GapKind.STALE_PAGE,
                    subject=slug,
                    detail=f"last updated {page.last_updated} ({age} days ago)",
                    score=age,
                    path=page.path,
                )
            )

        if page.line_count < min_lines:
            gaps.append(
                Gap(
                    kind=GapKind.THIN_PAGE,
                    subject=slug,
                    detail=f"{page.line_count} lines, {page.word_count} words",
                    score=min_lines - page.line_count,
                    path=page.path,
                )
            )
    return sorted(gaps, key=lambda gap: (gap.kind, -gap.score, gap.subject))


def resolve_scope(graph: WikiGraph, page: str | None, hops: int) -> tuple[set[str] | None, str | None]:
    """Restrict the scan to one page's neighborhood when a seed page is given.

    Args:
        graph: Indexed wiki graph.
        page: Optional seed page slug or path.
        hops: How many link hops around the seed to include.

    Returns:
        Tuple of (slug scope or None for the whole wiki, resolved seed slug or None).

    Raises:
        WikiGraphError: If the seed page is not in the wiki.
    """
    if page is None:
        return None, None
    seed = graph.page_for(page)
    scope = {seed.slug, *graph.neighborhood(seed.slug, hops)}
    logger.info("Scoped to %s and %d neighbor(s) within %d hop(s)", seed.slug, len(scope) - 1, hops)
    return scope, seed.slug


def collect_gaps(graph: WikiGraph, scope: set[str] | None, args: argparse.Namespace) -> dict[GapKind, list[Gap]]:
    """Run every detector and bucket the results by kind.

    Args:
        graph: Indexed wiki graph.
        scope: Optional set of page slugs to restrict the scan to.
        args: Parsed command-line options.

    Returns:
        Mapping of gap kind to its ranked gaps, truncated to `--top`.
    """
    found: dict[GapKind, list[Gap]] = {kind: [] for kind in GapKind}
    detected = [
        *find_dangling_links(graph, scope),
        *find_shallow_history(graph, scope, args.min_years),
        *find_unlinked_mentions(graph, scope),
        *find_page_health(graph, scope, args.stale_days, args.min_lines),
    ]
    for gap in detected:
        found[gap.kind].append(gap)
    return {kind: gaps[: args.top] for kind, gaps in found.items() if gaps}


def print_gaps(graph: WikiGraph, seed: str | None, found: dict[GapKind, list[Gap]]) -> None:
    """Print a grouped, human-readable gap report.

    Args:
        graph: Indexed wiki graph.
        seed: Resolved seed page slug, if the scan was scoped.
        found: Ranked gaps by kind.
    """
    lines: list[str] = []
    if seed is not None:
        page = graph.pages[seed]
        resolved = len(graph.outbound(seed))
        lines += [
            f"SEED  {page.path} — {page.title}",
            f"  links out to {resolved} page(s), linked from {len(graph.inbound(seed))} page(s)",
            f"  names years: {', '.join(sorted(distinct_years(page.body))) or 'none'}",
            "",
        ]

    if not found:
        lines.append("No gaps detected in scope.")

    for kind, gaps in found.items():
        lines.append(f"{kind.upper().replace('_', ' ')} ({len(gaps)})")
        lines.append(f"  {REMEDIATION[kind]}")
        for gap in gaps:
            lines.append(f"  {gap.score:>4}  {gap.subject} — {gap.detail}")
            if gap.referenced_by:
                shown = ", ".join(gap.referenced_by[:MAX_REFERENCES_SHOWN])
                extra = len(gap.referenced_by) - MAX_REFERENCES_SHOWN
                lines.append(f"        from: {shown}" + (f", +{extra} more" if extra > 0 else ""))
        lines.append("")

    logger.info("\n".join(lines).rstrip())


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Argument list without the program name.

    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(description="Rank the background knowledge the wiki is missing.")
    parser.add_argument("--page", help="Scope the scan to one page and its neighborhood (slug or path).")
    parser.add_argument(
        "--hops", type=int, default=DEFAULT_HOPS, help=f"Link hops around --page to include (default {DEFAULT_HOPS})."
    )
    parser.add_argument(
        "--stale-days",
        type=int,
        default=DEFAULT_STALE_DAYS,
        help=f"Age in days past which a page is stale (default {DEFAULT_STALE_DAYS}).",
    )
    parser.add_argument(
        "--min-lines",
        type=int,
        default=DEFAULT_MIN_LINES,
        help=f"Line count below which a page is thin (default {DEFAULT_MIN_LINES}).",
    )
    parser.add_argument(
        "--min-years",
        type=int,
        default=DEFAULT_MIN_YEARS,
        help=f"Distinct years a page must name to count as historically grounded (default {DEFAULT_MIN_YEARS}).",
    )
    parser.add_argument("--top", type=int, default=DEFAULT_TOP, help=f"Max gaps per kind (default {DEFAULT_TOP}).")
    parser.add_argument("--wiki-dir", help="Wiki root to index (default: the repo's wiki/).")
    parser.add_argument("--json", action="store_true", help="Emit a machine-readable report on stdout.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Scan the wiki and report ranked coverage gaps.

    Args:
        argv: Argument list without the program name; defaults to `sys.argv[1:]`.

    Returns:
        0 on success, 1 when the wiki or seed page cannot be resolved.
    """
    args = parse_args(sys.argv[1:] if argv is None else argv)

    try:
        graph = load_wiki_graph(Path(args.wiki_dir) if args.wiki_dir else None)
        scope, seed = resolve_scope(graph, args.page, args.hops)
    except WikiGraphError as error:
        logger.error("%s", error)
        return 1

    found = collect_gaps(graph, scope, args)

    if args.json:
        print(
            json.dumps(
                {
                    "seed": seed,
                    "scope": sorted(scope) if scope else None,
                    "gaps": {str(kind): [gap.as_dict() for gap in gaps] for kind, gaps in found.items()},
                },
                indent=2,
            )
        )
    else:
        print_gaps(graph, seed, found)

    return 0


if __name__ == "__main__":
    sys.exit(main())
