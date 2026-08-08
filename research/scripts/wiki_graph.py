"""Index `wiki/` as a link graph so a research run knows what is already covered.

Shared library for the research backfill pipeline. `detect_gaps.py` uses it to rank
missing background by how many pages already depend on it, and `start_run.py` uses it to
assemble the "what the wiki already knows" brief — the wiki's own pages standing in for
STORM's table-of-contents seeding step against existing Wikipedia articles.

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
    """Reduce a wikilink target to the slug it resolves to.

    Handles the path-qualified, aliased, and anchored forms Quartz accepts, so
    `[[technical/tools/redis-for-rag|Redis]]` and `[[redis-for-rag]]` collapse to one slug.

    Args:
        target: Raw text between the double brackets, alias and anchor already stripped.

    Returns:
        The bare slug of the link target.
    """
    tail = target.strip().split("/")[-1]
    return slugify(tail.removesuffix(".md"))


def strip_code(text: str) -> str:
    """Remove fenced and inline code so mermaid or shell samples cannot forge links.

    Args:
        text: Raw markdown body.

    Returns:
        The body with fenced blocks and inline code spans blanked out.
    """
    return INLINE_CODE_PATTERN.sub(" ", FENCE_PATTERN.sub("\n", text))


@dataclass(frozen=True)
class WikiPage:
    """One parsed wiki page and the structure a research run needs from it."""

    path: str
    slug: str
    title: str
    definition: str
    category: str
    status: str
    last_updated: str
    sections: tuple[str, ...]
    links: frozenset[str]
    source_urls: tuple[str, ...]
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
        return self.slug in HUB_STEMS or Path(self.path).stem in HUB_STEMS

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
            "title": self.title,
            "definition": self.definition,
            "category": self.category,
            "status": self.status,
            "last_updated": self.last_updated,
            "sections": list(self.sections),
            "links": sorted(self.links),
            "source_urls": list(self.source_urls),
            "line_count": self.line_count,
            "word_count": self.word_count,
        }


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

    title_match = TITLE_PATTERN.search(body)
    definition_match = DEFINITION_PATTERN.search(body)
    metadata = {match.group("key").strip().lower(): match.group("value") for match in METADATA_PATTERN.finditer(body)}

    return WikiPage(
        path=str((wiki_dir.name / path.relative_to(wiki_dir))),
        slug=slugify(path.stem),
        title=title_match.group(1).strip() if title_match else path.stem,
        definition=definition_match.group(1).strip() if definition_match else "",
        category=metadata.get("category", ""),
        status=metadata.get("status", ""),
        last_updated=metadata.get("last updated", ""),
        sections=tuple(HEADING_PATTERN.findall(body)),
        links=frozenset(normalize_link_target(target) for target in WIKILINK_PATTERN.findall(prose)),
        source_urls=tuple(dict.fromkeys(extract_source_urls(body))),
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
    sections = re.split(r"^##\s+", body, flags=re.MULTILINE)
    for section in sections:
        if section.lower().startswith("sources"):
            return URL_PATTERN.findall(section)
    return URL_PATTERN.findall(body)


class WikiGraph:
    """The wiki's pages plus the inbound, outbound, and dangling link structure over them."""

    def __init__(self, pages: list[WikiPage]) -> None:
        """Build the adjacency indexes from a list of parsed pages.

        Args:
            pages: Every page that should participate in the graph.
        """
        self.pages: dict[str, WikiPage] = {}
        self.duplicate_slugs: dict[str, list[str]] = defaultdict(list)
        for page in pages:
            if page.slug in self.pages:
                # Wikilinks address pages by bare slug, so a collision makes `[[slug]]` ambiguous
                # for the wiki itself; keep the first and surface the rest rather than hiding them.
                self.duplicate_slugs[page.slug].append(page.path)
                continue
            self.pages[page.slug] = page

        for slug, paths in self.duplicate_slugs.items():
            logger.warning(
                "Slug %r is claimed by %s and also %s — links to it are ambiguous",
                slug,
                self.pages[slug].path,
                ", ".join(paths),
            )

        inbound: defaultdict[str, set[str]] = defaultdict(set)
        dangling: defaultdict[str, set[str]] = defaultdict(set)
        for page in pages:
            for target in page.links:
                if target == page.slug:
                    continue
                if target in self.pages:
                    inbound[target].add(page.slug)
                else:
                    dangling[target].add(page.slug)

        self._inbound = {slug: frozenset(sources) for slug, sources in inbound.items()}
        self._dangling = {slug: frozenset(sources) for slug, sources in dangling.items()}

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
            Mapping of missing slug to the slugs of the pages that reference it.
        """
        return self._dangling

    def page_for(self, reference: str) -> WikiPage:
        """Resolve a slug, file name, or path to a page.

        Args:
            reference: Page slug, markdown file name, or path relative to the repo or wiki root.

        Returns:
            The matching page.

        Raises:
            PageNotFoundError: If no page matches the reference.
        """
        candidate = slugify(Path(reference).stem)
        if candidate in self.pages:
            return self.pages[candidate]
        raise PageNotFoundError(f"no wiki page matches {reference!r}")

    def inbound(self, slug: str) -> frozenset[str]:
        """Return the pages linking to a slug.

        Args:
            slug: Target page slug.

        Returns:
            Slugs of pages that link to it; empty when nothing does.
        """
        return self._inbound.get(slug, frozenset())

    def outbound(self, slug: str) -> frozenset[str]:
        """Return the resolved pages a slug links to.

        Args:
            slug: Source page slug.

        Returns:
            Slugs of existing pages it links to, excluding dangling targets.
        """
        page = self.pages.get(slug)
        if page is None:
            return frozenset()
        return frozenset(target for target in page.links if target in self.pages)

    def neighborhood(self, slug: str, hops: int = 1) -> list[str]:
        """Walk the undirected link graph outward from a page.

        Args:
            slug: Slug to start from.
            hops: How many link hops to expand.

        Returns:
            Neighbor slugs ordered by distance then alphabetically, excluding the start page.

        Raises:
            PageNotFoundError: If the starting slug is not in the graph.
        """
        if slug not in self.pages:
            raise PageNotFoundError(f"no wiki page matches {slug!r}")

        seen = {slug}
        frontier = [slug]
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
            exclude: Optional slug to leave out of the results.

        Returns:
            Slugs of matching pages, alphabetically ordered.
        """
        words = [re.escape(word) for word in re.split(r"[-\s]+", term.strip()) if word]
        if not words:
            return []
        pattern = re.compile(r"\b" + r"[-\s]+".join(words) + r"\b", re.IGNORECASE)
        return sorted(
            slug for slug, page in self.pages.items() if slug != exclude and pattern.search(strip_code(page.body))
        )


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
        print(json.dumps({slug: page.as_dict() for slug, page in sorted(graph.pages.items())}, indent=2))
        return 0

    link_count = sum(len(graph.outbound(slug)) for slug in graph.pages)
    orphans = [slug for slug, page in graph.pages.items() if not graph.inbound(slug) and not page.is_hub]
    logger.info(
        "\n".join(
            [
                f"pages: {len(graph)}",
                f"resolved links: {link_count}",
                f"dangling targets: {len(graph.dangling_links)}",
                f"pages with no inbound links: {len(orphans)}",
            ]
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
