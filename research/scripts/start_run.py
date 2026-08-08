"""Scaffold a research run and brief it on what the wiki already knows.

STORM seeds an article by pulling the tables of contents of related Wikipedia pages. This wiki
is its own encyclopedia, so the equivalent move is to hand the researcher the seed page, its link
neighborhood, and a one-line definition of every page that already exists — which is what
`wiki-context.md` is. Everything downstream reads it first so the report fills gaps instead of
restating pages Dean already has.

Writes nothing outside the run directory and makes no network or LLM calls.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

try:
    from detect_gaps import distinct_years
    from wiki_graph import WikiGraph, WikiGraphError, load_wiki_graph, slugify
except ModuleNotFoundError:  # Imported from outside research/scripts/.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from detect_gaps import distinct_years
    from wiki_graph import WikiGraph, WikiGraphError, load_wiki_graph, slugify

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(filename)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

RESEARCH_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNS_DIR = RESEARCH_ROOT / "runs"
DEFAULT_HOPS = 1
MAX_SLUG_LENGTH = 60
# Long enough to tell two adjacent topics apart, short enough that 60+ of them stay scannable.
DEFINITION_PREVIEW_CHARS = 200


class RunSetupError(Exception):
    """Base class for every failure this module raises."""


class SeedPageError(RunSetupError):
    """The named seed page is not in the wiki."""


class RunExistsError(RunSetupError):
    """A run directory with this id already exists."""


@dataclass(frozen=True)
class RunManifest:
    """Static description of one research run, written to `run.json`."""

    run_id: str
    topic: str
    slug: str
    seed_page: str | None
    seed_title: str | None
    seed_urls: tuple[str, ...]
    neighborhood: tuple[str, ...]
    hops: int
    wiki_pages_indexed: int
    created_at: str

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-serializable view of the manifest.

        Returns:
            Mapping of manifest fields.
        """
        return {
            "run_id": self.run_id,
            "topic": self.topic,
            "slug": self.slug,
            "seed_page": self.seed_page,
            "seed_title": self.seed_title,
            "seed_urls": list(self.seed_urls),
            "neighborhood": list(self.neighborhood),
            "hops": self.hops,
            "wiki_pages_indexed": self.wiki_pages_indexed,
            "created_at": self.created_at,
        }


def truncate(text: str, limit: int) -> str:
    """Shorten text to a character budget without cutting mid-word.

    Args:
        text: Text to shorten.
        limit: Maximum length before the ellipsis.

    Returns:
        The original text, or a word-boundary truncation ending in an ellipsis.
    """
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "…"


def render_neighbor(graph: WikiGraph, slug: str, seed_slug: str | None) -> list[str]:
    """Render one neighboring page as a context block.

    Args:
        graph: Indexed wiki graph.
        slug: Neighbor page slug.
        seed_slug: Seed page slug, used to label the direction of the relationship.

    Returns:
        Markdown lines describing the neighbor.
    """
    page = graph.pages[slug]
    if seed_slug is None:
        relation = "related"
    elif seed_slug in graph.inbound(slug):
        relation = "linked from the seed page"
    else:
        relation = "links to the seed page"

    years = sorted(distinct_years(page.body))
    return [
        f"### {page.title} — `{page.path}`",
        f"_{relation}; status {page.status or 'unset'}; updated {page.last_updated or 'unknown'}_",
        "",
        f"> {page.definition}" if page.definition else "> (no definition line)",
        "",
        f"- Sections: {' | '.join(page.sections) or 'none'}",
        f"- Years named: {', '.join(years) or 'none'}",
        f"- Links out: {', '.join(f'[[{target}]]' for target in sorted(page.links)) or 'none'}",
        "",
    ]


def build_wiki_context(graph: WikiGraph, manifest: RunManifest, seed_slug: str | None) -> str:
    """Assemble the "what the wiki already knows" brief for a run.

    Args:
        graph: Indexed wiki graph.
        manifest: Run manifest describing the topic and scope.
        seed_slug: Resolved seed page slug, if one was given.

    Returns:
        The full markdown body of `wiki-context.md`.
    """
    lines = [
        f"# Wiki context — {manifest.topic}",
        "",
        f"_Generated {manifest.created_at} by `start_run.py`. Regenerate rather than hand-edit._",
        "",
        "This is the state of the wiki **before** this research run. Read it first. The report you produce",
        "should supply the background these pages assume and never restate, not repeat what is already here.",
        "",
    ]

    if seed_slug is not None:
        seed = graph.pages[seed_slug]
        lines += [
            f"## Seed page — `{seed.path}`",
            "",
            f"_Years it names: {', '.join(sorted(distinct_years(seed.body))) or 'none'} — everything earlier is the gap._",
            "",
            seed.body,
            "",
        ]

    lines += [f"## Neighborhood — {len(manifest.neighborhood)} page(s) within {manifest.hops} hop(s)", ""]
    if manifest.neighborhood:
        for slug in manifest.neighborhood:
            lines += render_neighbor(graph, slug, seed_slug)
    else:
        lines += ["No linked neighbors. This topic is isolated in the wiki, so the backfill is starting cold.", ""]

    scope = {seed_slug, *manifest.neighborhood} if seed_slug else set(manifest.neighborhood)
    undefined = sorted(
        ((target, sources & scope) for target, sources in graph.dangling_links.items() if sources & scope),
        key=lambda item: (-len(item[1]), item[0]),
    )
    lines += ["## Undefined concepts these pages already lean on", ""]
    if undefined:
        lines += [
            f"- `{target}` — linked by {', '.join(sorted(sources))}, but no page defines it"
            for target, sources in undefined
        ]
    else:
        lines.append("None — every link in this neighborhood resolves.")
    lines.append("")

    lines += [
        f"## Everything the wiki already covers ({len(graph)} pages)",
        "",
        "Do not create a page for anything on this list; extend it instead.",
        "",
    ]
    for slug, page in sorted(graph.pages.items()):
        definition = truncate(page.definition, DEFINITION_PREVIEW_CHARS) if page.definition else "(no definition)"
        lines.append(f"- `{slug}` — {definition}")
    lines.append("")

    lines += ["## Sources these pages already cite", ""]
    cited = dict.fromkeys(url for slug in scope for url in graph.pages[slug].source_urls)
    lines += [f"- {url}" for url in cited] if cited else ["None recorded."]
    lines.append("")

    return "\n".join(lines)


def build_manifest(graph: WikiGraph, args: argparse.Namespace) -> tuple[RunManifest, str | None]:
    """Resolve the seed page and topic into a run manifest.

    Args:
        graph: Indexed wiki graph.
        args: Parsed command-line options.

    Returns:
        Tuple of (manifest, resolved seed slug or None).

    Raises:
        SeedPageError: If a seed page was given but does not exist in the wiki.
    """
    seed = None
    if args.seed_page:
        try:
            seed = graph.page_for(args.seed_page)
        except WikiGraphError as error:
            raise SeedPageError(
                f"{error}. Pass a slug or a path under wiki/, or drop --seed-page to research a topic cold."
            ) from error

    topic = args.topic or (seed.title if seed else "")
    slug = slugify(topic, MAX_SLUG_LENGTH)
    created_at = datetime.now(UTC)

    return (
        RunManifest(
            run_id=f"{created_at.strftime('%Y-%m-%d')}-{slug}",
            topic=topic,
            slug=slug,
            seed_page=seed.path if seed else None,
            seed_title=seed.title if seed else None,
            seed_urls=tuple(seed.source_urls) if seed else (),
            neighborhood=tuple(graph.neighborhood(seed.slug, args.hops)) if seed else (),
            hops=args.hops,
            wiki_pages_indexed=len(graph),
            created_at=created_at.isoformat(),
        ),
        seed.slug if seed else None,
    )


def create_run(graph: WikiGraph, manifest: RunManifest, seed_slug: str | None, runs_dir: Path, force: bool) -> Path:
    """Create the run directory and write its starting artifacts.

    Args:
        graph: Indexed wiki graph.
        manifest: Run manifest to persist.
        seed_slug: Resolved seed page slug, if one was given.
        runs_dir: Directory that holds all runs.
        force: Overwrite `run.json` and `wiki-context.md` if the run already exists.

    Returns:
        Path of the run directory.

    Raises:
        RunExistsError: If the run directory exists and `force` is not set.
        RunSetupError: If the run directory or its files cannot be written.
    """
    run_dir = runs_dir / manifest.run_id
    if run_dir.exists() and not force:
        raise RunExistsError(f"run directory {run_dir} already exists — pass --force to regenerate its context")

    try:
        (run_dir / "findings").mkdir(parents=True, exist_ok=True)
        (run_dir / "run.json").write_text(json.dumps(manifest.as_dict(), indent=2) + "\n", encoding="utf-8")
        (run_dir / "wiki-context.md").write_text(build_wiki_context(graph, manifest, seed_slug), encoding="utf-8")
    except OSError as error:
        logger.exception("Could not create run directory %s", run_dir)
        raise RunSetupError(f"could not create {run_dir}: {error}") from error

    return run_dir


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Argument list without the program name.

    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(description="Scaffold a research run and brief it on existing wiki coverage.")
    parser.add_argument("--topic", help="Topic to research (defaults to the seed page title).")
    parser.add_argument("--seed-page", help="Wiki page the backfill is for — slug or path under wiki/.")
    parser.add_argument(
        "--hops",
        type=int,
        default=DEFAULT_HOPS,
        help=f"Link hops around the seed page to include as context (default {DEFAULT_HOPS}).",
    )
    parser.add_argument("--runs-dir", help="Override the runs directory (default: research/runs).")
    parser.add_argument("--wiki-dir", help="Wiki root to index (default: the repo's wiki/).")
    parser.add_argument("--force", action="store_true", help="Regenerate context for an existing run.")
    parser.add_argument("--json", action="store_true", help="Emit the run manifest on stdout.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Create a research run directory for a topic.

    Args:
        argv: Argument list without the program name; defaults to `sys.argv[1:]`.

    Returns:
        0 on success, 2 when the run already exists, 1 on any other failure.
    """
    args = parse_args(sys.argv[1:] if argv is None else argv)

    if not args.topic and not args.seed_page:
        logger.error("Pass --topic, --seed-page, or both — there is nothing to research otherwise")
        return 1

    try:
        graph = load_wiki_graph(Path(args.wiki_dir) if args.wiki_dir else None)
        manifest, seed_slug = build_manifest(graph, args)
    except (WikiGraphError, RunSetupError) as error:
        logger.error("%s", error)
        return 1

    runs_dir = Path(args.runs_dir) if args.runs_dir else DEFAULT_RUNS_DIR
    try:
        run_dir = create_run(graph, manifest, seed_slug, runs_dir, args.force)
    except RunExistsError as error:
        logger.error("%s", error)
        return 2
    except RunSetupError as error:
        logger.error("%s", error)
        return 1

    if args.json:
        print(json.dumps({**manifest.as_dict(), "run_dir": str(run_dir)}, indent=2))

    logger.info(
        "\n".join(
            [
                f"Run {manifest.run_id} ready at {run_dir}",
                f"  topic: {manifest.topic}",
                f"  seed: {manifest.seed_page or 'none — researching cold'}",
                f"  context: {len(manifest.neighborhood)} neighbor page(s), {manifest.wiki_pages_indexed} indexed",
                "",
                "Next: work through research/prompts/ in order, starting with 01-gap-analysis.md.",
            ]
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
