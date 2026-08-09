"""Index `wiki/` as a link graph so a research run knows what is already covered.

Shared library for the research backfill pipeline. `detect_gaps.py` uses it to rank missing
background by how many pages already depend on it, `start_run.py` uses it to assemble the "what the
wiki already knows" brief, and `merge_timeline.py` uses it to resolve a page reference.

It also parses each page's `## Timeline` section into events, which is what makes timeline coverage
a measurable property of a page rather than a guess.

Run it directly for a one-screen health summary of the graph.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path

try:
    from events import Event, EventError, parse_bullet
except ModuleNotFoundError:  # Imported from outside research/scripts/.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from events import Event, EventError, parse_bullet

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(filename)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WIKI_DIR = REPO_ROOT / "wiki"

# `index.md` is Quartz site chrome, not wiki content, so it never counts as a page or a gap.
EXCLUDED_STEMS = frozenset({"index"})
# Hub pages link outward by design; treating them as orphan or thin is pure noise.
HUB_STEMS = frozenset({"overview", "synthesis"})
TIMELINE_HEADING = "Timeline"

FENCE_PATTERN = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)
INLINE_CODE_PATTERN = re.compile(r"`[^`]*`")
WIKILINK_PATTERN = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")
TITLE_PATTERN = re.compile(r"^#\s+(.+)$", re.MULTILINE)
DEFINITION_PATTERN = re.compile(r"^>\s+(.+)$", re.MULTILINE)
HEADING_PATTERN = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
METADATA_PATTERN = re.compile(r"^\*\*(?P<key>[A-Za-z ]+)\*\*:\s*(?P<value>.+?)\s*$", re.MULTILINE)
FRONTMATTER_PATTERN = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)
URL_PATTERN = re.compile(r"https?://[^\s<>)\]\"']+")
ISO_DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")


class WikiGraphError(Exception):
    """Base class for every failure this module raises."""


class WikiNotFoundError(WikiGraphError):
    """The wiki directory does not exist or holds no readable pages."""


class PageNotFoundError(WikiGraphError):
    """A slug or path was requested that the graph does not contain."""


class AmbiguousPageError(WikiGraphError):
    """A bare slug matches more than one page, so the reference cannot be resolved."""


def slugify(value: str, max_length: int | None = None) -> str:
    """Convert arbitrary text into a lowercase hyphenated slug.

    Args:
        value: Text to slugify.
        max_length: Optional maximum slug length before trailing hyphens are trimmed.

    Returns:
        A slug safe for use in file names and link targets, or "untitled" when nothing survives.
    """
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    if max_length is not None:
        slug = slug[:max_length].rstrip("-")
    return slug or "untitled"


def normalize_link_target(target: str) -> str:
    """Reduce a wikilink target to a comparable path, keeping any folder qualification.

    Quartz resolves `[[redis-for-rag]]` by shortest unique name and `[[technical/tools/redis-for-rag]]`
    by path, so both forms have to survive normalization for resolution to match the site.

    Args:
        target: Raw text between the double brackets, alias and anchor already stripped.

    Returns:
        A slash-joined slug path.
    """
    segments = [segment for segment in target.strip().removesuffix(".md").split("/") if segment]
    return "/".join(slugify(segment) for segment in segments)


def strip_code(text: str) -> str:
    """Remove fenced and inline code so mermaid or shell samples cannot forge links.

    Args:
        text: Raw markdown body.

    Returns:
        The body with fenced blocks and inline code spans blanked out.
    """
    return INLINE_CODE_PATTERN.sub(" ", FENCE_PATTERN.sub("\n", text))


def section_lines(body: str, heading: str) -> list[str]:
    """Return the lines inside a named `##` section.

    Args:
        body: Page body with frontmatter removed.
        heading: Section heading text, without the leading hashes.

    Returns:
        The section's lines, or an empty list when the page has no such section.
    """
    lines = body.splitlines()
    try:
        start = next(index for index, line in enumerate(lines) if line.strip() == f"## {heading}")
    except StopIteration:
        return []
    end = next((index for index in range(start + 1, len(lines)) if lines[index].startswith("## ")), len(lines))
    return lines[start + 1 : end]


@dataclass(frozen=True)
class WikiPage:
    """One parsed wiki page and the structure a research run needs from it."""

    path: str
    slug: str
    qualified_slug: str
    title: str
    definition: str
    category: str
    status: str
    last_updated: str
    sections: tuple[str, ...]
    raw_links: tuple[str, ...]
    source_urls: tuple[str, ...]
    timeline: tuple[Event, ...]
    body: str

    @property
    def line_count(self) -> int:
        """Return the number of lines in the page body.

        Returns:
            Line count, used to flag pages too thin to have real background.
        """
        return self.body.count("\n") + 1

    @property
    def word_count(self) -> int:
        """Return the whitespace-delimited word count of the page body.

        Returns:
            Number of words in the page body.
        """
        return len(self.body.split())

    @property
    def is_hub(self) -> bool:
        """Return whether this page is a synthesis or overview hub.

        Returns:
            True when the page exists to link outward rather than to define a topic.
        """
        return Path(self.path).stem in HUB_STEMS

    @property
    def timeline_months(self) -> tuple[str, ...]:
        """Return the distinct month buckets the page's timeline covers.

        Returns:
            Sorted `YYYY-MM` keys, empty when the page has no timeline.
        """
        return tuple(sorted({event.date.month_key for event in self.timeline}))

    @property
    def timeline_years(self) -> frozenset[int]:
        """Return the distinct years the page's timeline covers.

        Returns:
            Set of years, empty when the page has no timeline.
        """
        return frozenset(event.date.year for event in self.timeline)

    @property
    def days_since_update(self) -> int | None:
        """Return the age of the page's `Last updated` line in days.

        Returns:
            Days since the recorded update, or None when the page carries no valid date.
        """
        if not ISO_DATE_PATTERN.fullmatch(self.last_updated):
            return None
        return (date.today() - date.fromisoformat(self.last_updated)).days

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-serializable view of the page metadata.

        Returns:
            Mapping of page fields, excluding the full body.
        """
        return {
            "path": self.path,
            "slug": self.slug,
            "qualified_slug": self.qualified_slug,
            "title": self.title,
            "definition": self.definition,
            "category": self.category,
            "status": self.status,
            "last_updated": self.last_updated,
            "sections": list(self.sections),
            "links": list(self.raw_links),
            "source_urls": list(self.source_urls),
            "timeline": [event.as_dict(index) for index, event in enumerate(self.timeline, start=1)],
            "line_count": self.line_count,
            "word_count": self.word_count,
        }


def parse_timeline(body: str, path: Path) -> tuple[Event, ...]:
    """Parse a page's `## Timeline` section into events.

    Unparseable bullets are logged and skipped rather than raised — one malformed line should not
    make a page invisible to the graph. `merge_timeline.py --check` is what reports them properly.

    Args:
        body: Page body with frontmatter removed.
        path: Page path, for log messages.

    Returns:
        The page's events in document order.
    """
    events: list[Event] = []
    for line in section_lines(body, TIMELINE_HEADING):
        stripped = line.strip()
        if not stripped.startswith("- "):
            continue
        try:
            events.append(parse_bullet(stripped))
        except EventError as error:
            logger.warning("%s: unparseable timeline bullet — %s", path.name, error)
    return tuple(events)


def parse_page(path: Path, wiki_dir: Path) -> WikiPage:
    """Parse one markdown file into a WikiPage.

    Args:
        path: Absolute path to the markdown file.
        wiki_dir: Wiki root, used to compute the repo-relative path label.

    Returns:
        The parsed page. Missing metadata lines come back as empty strings rather than errors,
        because real pages are inconsistent about them.

    Raises:
        OSError: If the file cannot be read.
    """
    raw = path.read_text(encoding="utf-8")
    body = FRONTMATTER_PATTERN.sub("", raw)
    prose = strip_code(body)
    relative = path.relative_to(wiki_dir)

    title_match = TITLE_PATTERN.search(body)
    definition_match = DEFINITION_PATTERN.search(body)
    metadata = {match.group("key").strip().lower(): match.group("value") for match in METADATA_PATTERN.finditer(body)}

    return WikiPage(
        path=str(wiki_dir.name / relative),
        slug=slugify(path.stem),
        qualified_slug=normalize_link_target(str(relative.with_suffix(""))),
        title=title_match.group(1).strip() if title_match else path.stem,
        definition=definition_match.group(1).strip() if definition_match else "",
        category=metadata.get("category", ""),
        status=metadata.get("status", ""),
        last_updated=metadata.get("last updated", ""),
        sections=tuple(HEADING_PATTERN.findall(body)),
        raw_links=tuple(dict.fromkeys(normalize_link_target(target) for target in WIKILINK_PATTERN.findall(prose))),
        source_urls=tuple(dict.fromkeys(extract_source_urls(body))),
        timeline=parse_timeline(body, path),
        body=body.strip(),
    )


def extract_source_urls(body: str) -> list[str]:
    """Pull the URLs a page already cites, preferring its `## Sources` section.

    Args:
        body: Page body with frontmatter removed.

    Returns:
        URLs in document order. Falls back to every URL in the page when there is no
        `## Sources` section, since older pages cite inline.
    """
    sources = section_lines(body, "Sources")
    if sources:
        return URL_PATTERN.findall("\n".join(sources))
    return URL_PATTERN.findall(body)


class WikiGraph:
    """The wiki's pages plus the inbound, outbound, and dangling link structure over them."""

    def __init__(self, pages: list[WikiPage]) -> None:
        """Build the page index and the adjacency indexes from a list of parsed pages.

        Pages are keyed by bare slug when that slug is unique across the wiki, and by their
        folder-qualified slug when it is not — the same rule Quartz applies to `[[wikilinks]]`.

        Args:
            pages: Every page that should participate in the graph.
        """
        bare_counts: defaultdict[str, int] = defaultdict(int)
        for page in pages:
            bare_counts[page.slug] += 1

        self.pages: dict[str, WikiPage] = {}
        self._by_bare: defaultdict[str, list[str]] = defaultdict(list)
        for page in pages:
            key = page.slug if bare_counts[page.slug] == 1 else page.qualified_slug
            self.pages[key] = page
            self._by_bare[page.slug].append(key)

        self.ambiguous_slugs = {slug: keys for slug, keys in self._by_bare.items() if len(keys) > 1}
        for slug, keys in self.ambiguous_slugs.items():
            logger.info("Slug %r is shared by %s — link to them by path", slug, ", ".join(sorted(keys)))

        inbound: defaultdict[str, set[str]] = defaultdict(set)
        dangling: defaultdict[str, set[str]] = defaultdict(set)
        self._outbound: dict[str, frozenset[str]] = {}
        for key, page in self.pages.items():
            resolved: set[str] = set()
            for target in page.raw_links:
                match = self._resolve(target)
                if match is None:
                    dangling[target].add(key)
                elif match != key:
                    resolved.add(match)
                    inbound[match].add(key)
            self._outbound[key] = frozenset(resolved)

        self._inbound = {key: frozenset(sources) for key, sources in inbound.items()}
        self._dangling = {target: frozenset(sources) for target, sources in dangling.items()}

    def __len__(self) -> int:
        """Return the number of indexed pages.

        Returns:
            Page count.
        """
        return len(self.pages)

    @property
    def dangling_links(self) -> dict[str, frozenset[str]]:
        """Return link targets that no page defines.

        Returns:
            Mapping of unresolved target to the keys of the pages that reference it.
        """
        return self._dangling

    def _resolve(self, target: str) -> str | None:
        """Resolve a normalized link target to a page key.

        Args:
            target: Normalized link target, possibly folder-qualified.

        Returns:
            The page key, or None when nothing matches or a bare slug is ambiguous.
        """
        if target in self.pages:
            return target
        if "/" in target:
            matches = [key for key, page in self.pages.items() if page.qualified_slug.endswith(target)]
            return matches[0] if len(matches) == 1 else None
        candidates = self._by_bare.get(target, [])
        return candidates[0] if len(candidates) == 1 else None

    def page_for(self, reference: str) -> WikiPage:
        """Resolve a slug, file name, or path to a page.

        Args:
            reference: Page slug, markdown file name, or path relative to the repo or wiki root.

        Returns:
            The matching page.

        Raises:
            AmbiguousPageError: If a bare slug matches more than one page.
            PageNotFoundError: If no page matches the reference.
        """
        target = normalize_link_target(str(Path(reference).with_suffix("")))
        key = self._resolve(target)
        if key is not None:
            return self.pages[key]

        bare = target.split("/")[-1]
        if bare in self.ambiguous_slugs:
            raise AmbiguousPageError(
                f"{reference!r} matches {', '.join(sorted(self.ambiguous_slugs[bare]))} — qualify it with the folder"
            )
        raise PageNotFoundError(f"no wiki page matches {reference!r}")

    def key_for(self, page: WikiPage) -> str:
        """Return the graph key a page is indexed under.

        Args:
            page: A page from this graph.

        Returns:
            The page's key.

        Raises:
            PageNotFoundError: If the page is not part of this graph.
        """
        for key, candidate in self.pages.items():
            if candidate.path == page.path:
                return key
        raise PageNotFoundError(f"{page.path} is not in this graph")

    def inbound(self, key: str) -> frozenset[str]:
        """Return the pages linking to a page.

        Args:
            key: Target page key.

        Returns:
            Keys of pages that link to it; empty when nothing does.
        """
        return self._inbound.get(key, frozenset())

    def outbound(self, key: str) -> frozenset[str]:
        """Return the resolved pages a page links to.

        Args:
            key: Source page key.

        Returns:
            Keys of existing pages it links to, excluding dangling targets.
        """
        return self._outbound.get(key, frozenset())

    def neighborhood(self, key: str, hops: int = 1) -> list[str]:
        """Walk the undirected link graph outward from a page.

        Args:
            key: Page key to start from.
            hops: How many link hops to expand.

        Returns:
            Neighbor keys ordered by distance then alphabetically, excluding the start page.

        Raises:
            PageNotFoundError: If the starting key is not in the graph.
        """
        if key not in self.pages:
            raise PageNotFoundError(f"no wiki page matches {key!r}")

        seen = {key}
        frontier = [key]
        ordered: list[str] = []
        for _ in range(max(hops, 0)):
            neighbors = sorted({n for current in frontier for n in self.inbound(current) | self.outbound(current)} - seen)
            if not neighbors:
                break
            seen.update(neighbors)
            ordered.extend(neighbors)
            frontier = neighbors
        return ordered

    def pages_mentioning(self, term: str, exclude: str | None = None) -> list[str]:
        """Find pages whose prose names a term, whether or not they link it.

        Args:
            term: Concept name or slug to search for; hyphens match spaces.
            exclude: Optional page key to leave out of the results.

        Returns:
            Keys of matching pages, alphabetically ordered.
        """
        words = [re.escape(word) for word in re.split(r"[-\s/]+", term.strip()) if word]
        if not words:
            return []
        pattern = re.compile(r"\b" + r"[-\s]+".join(words) + r"\b", re.IGNORECASE)
        return sorted(
            key for key, page in self.pages.items() if key != exclude and pattern.search(strip_code(page.body))
        )

    def all_events(self) -> list[tuple[str, Event]]:
        """Collect every timeline event across the wiki.

        Returns:
            (page key, event) pairs sorted oldest first — the input to a wiki-wide timeline.
        """
        pairs = [(key, event) for key, page in self.pages.items() for event in page.timeline]
        return sorted(pairs, key=lambda pair: (pair[1].date.sort_key, pair[0]))


def load_wiki_graph(wiki_dir: Path | None = None) -> WikiGraph:
    """Read every wiki markdown file and build the graph.

    Args:
        wiki_dir: Wiki root to index; defaults to `wiki/` beside this repo's scripts.

    Returns:
        The populated graph.

    Raises:
        WikiNotFoundError: If the directory is missing or contains no readable pages.
    """
    root = wiki_dir or DEFAULT_WIKI_DIR
    if not root.is_dir():
        raise WikiNotFoundError(f"wiki directory {root} does not exist")

    pages: list[WikiPage] = []
    for path in sorted(root.rglob("*.md")):
        if path.stem in EXCLUDED_STEMS:
            continue
        try:
            pages.append(parse_page(path, root))
        except OSError as error:  # Keep one unreadable page from stopping the whole index.
            logger.warning("Skipping %s — %s", path, error)

    if not pages:
        raise WikiNotFoundError(f"no readable wiki pages under {root}")

    logger.info("Indexed %d wiki pages from %s", len(pages), root)
    return WikiGraph(pages)


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Argument list without the program name.

    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(description="Index the wiki as a link graph and print a health summary.")
    parser.add_argument("--wiki-dir", help="Wiki root to index (default: the repo's wiki/).")
    parser.add_argument("--json", action="store_true", help="Emit the full page index as JSON on stdout.")
    parser.add_argument("--events", action="store_true", help="Emit every timeline event across the wiki as JSON.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Index the wiki and report its shape.

    Args:
        argv: Argument list without the program name; defaults to `sys.argv[1:]`.

    Returns:
        0 on success, 1 when the wiki cannot be indexed.
    """
    args = parse_args(sys.argv[1:] if argv is None else argv)

    try:
        graph = load_wiki_graph(Path(args.wiki_dir) if args.wiki_dir else None)
    except WikiGraphError as error:
        logger.error("%s", error)
        return 1

    if args.json:
        print(json.dumps({key: page.as_dict() for key, page in sorted(graph.pages.items())}, indent=2))
        return 0

    if args.events:
        print(
            json.dumps(
                [{"page": key, **event.as_dict()} for key, event in graph.all_events()],
                indent=2,
            )
        )
        return 0

    events = graph.all_events()
    with_timeline = sum(1 for page in graph.pages.values() if page.timeline)
    orphans = [key for key, page in graph.pages.items() if not graph.inbound(key) and not page.is_hub]
    logger.info(
        "\n".join(
            [
                f"pages: {len(graph)}",
                f"resolved links: {sum(len(graph.outbound(key)) for key in graph.pages)}",
                f"dangling targets: {len(graph.dangling_links)}",
                f"pages with no inbound links: {len(orphans)}",
                f"pages with a timeline: {with_timeline}/{len(graph)}",
                f"timeline events: {len(events)}"
                + (f", {events[0][1].date.month_key} → {events[-1][1].date.month_key}" if events else ""),
            ]
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
