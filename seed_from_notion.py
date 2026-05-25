"""Seed the wiki from Notion pages listed in sources.yml.

Default behavior:
  - knowledge_base pages -> private/sources/notion-knowledge/
  - wiki_candidates pages + all descendants -> private/sources/staging/
  - rebuilds a managed AI knowledge baseline section in Dean-Profile.md

Use --export-structure for the older tree JSON export.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from contextlib import nullcontext
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests
import yaml
from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
DEFAULT_REQUEST_DELAY_SEC = 0.35

REPO_ROOT = Path(__file__).resolve().parent
SOURCES_FILE = REPO_ROOT / "sources.yml"
PRIVATE_REPO_PATH = Path(os.environ.get("PRIVATE_REPO_PATH", REPO_ROOT.parent / "dean-wiki-private"))
STAGING_DIR = PRIVATE_REPO_PATH / "sources" / "staging"
NOTION_KNOWLEDGE_DIR = PRIVATE_REPO_PATH / "sources" / "notion-knowledge"
PAGES_WITH_IMAGES_FILE = NOTION_KNOWLEDGE_DIR / "pages_with_images.txt"
NOTION_CACHE_DIR = PRIVATE_REPO_PATH / "sources" / "notion-cache"
DEFAULT_STRUCTURE_PATH = NOTION_CACHE_DIR / "page-structure.json"
DEAN_PROFILE_PATH = PRIVATE_REPO_PATH / "profile" / "Dean-Profile.md"

PROFILE_START_MARKER = "<!-- notion-knowledge-baseline:start -->"
PROFILE_END_MARKER = "<!-- notion-knowledge-baseline:end -->"
HEX32_RE = re.compile(r"^[0-9a-f]{32}$", re.IGNORECASE)

# Dont include notion pages that have many screenshots/images (URL will be empty)
# For these pages, download the PDF manually and supply it in the data for AI to look at
EXCLUDED_WIKI_CANDIDATE_PAGE_IDS = {
    "2762c51a-264f-802d-94d7-fb9d2b8dadf9",
}
EXCLUDED_WIKI_CANDIDATE_TITLES = {
    "Self-Improving AI Agents (Stanford)",
}


class NotionClientError(Exception):
    pass


@dataclass(frozen=True)
class PageRef:
    id: str
    lane: str
    root_id: str
    root_title: str | None = None


@dataclass(frozen=True)
class WrittenPage:
    id: str
    title: str
    lane: str
    path: Path
    headings: list[str]
    excerpt: str
    last_edited_time: str | None


class NotionClient:
    def __init__(self, api_key: str, request_delay: float = DEFAULT_REQUEST_DELAY_SEC) -> None:
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {api_key}",
                "Notion-Version": NOTION_VERSION,
                "Content-Type": "application/json",
            }
        )
        self._request_delay = request_delay

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        url = f"{NOTION_API_BASE}{path}"
        response = self._session.request(method, url, timeout=60, **kwargs)
        if self._request_delay > 0:
            time.sleep(self._request_delay)
        if not response.ok:
            detail = response.text[:500]
            raise NotionClientError(f"Notion API {response.status_code} {path}: {detail}")
        return response.json()

    def retrieve_page(self, page_id: str) -> dict[str, Any]:
        return self._request("GET", f"/pages/{page_id}")

    def list_block_children(self, block_id: str) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        start_cursor: str | None = None
        while True:
            params: dict[str, Any] = {"page_size": 100}
            if start_cursor:
                params["start_cursor"] = start_cursor
            payload = self._request("GET", f"/blocks/{block_id}/children", params=params)
            results.extend(payload.get("results", []))
            if not payload.get("has_more"):
                break
            start_cursor = payload.get("next_cursor")
            if not start_cursor:
                break
        return results

    def download(self, url: str) -> tuple[bytes, str | None]:
        response = self._session.get(url, timeout=60)
        if self._request_delay > 0:
            time.sleep(self._request_delay)
        response.raise_for_status()
        return response.content, response.headers.get("Content-Type")


def normalize_page_id(page_id: str) -> str:
    """Accept UUID with or without dashes; return canonical dashed form."""
    cleaned = page_id.strip().replace("-", "").lower()
    if not HEX32_RE.fullmatch(cleaned):
        raise ValueError(f"Invalid Notion page id: {page_id!r}")
    return f"{cleaned[:8]}-{cleaned[8:12]}-{cleaned[12:16]}-{cleaned[16:20]}-{cleaned[20:]}"


def notion_page_url(page_id: str) -> str:
    return f"https://www.notion.so/{page_id.replace('-', '')}"


def notion_block_url(page_id: str, block_id: str) -> str:
    return f"{notion_page_url(page_id)}#{block_id.replace('-', '')}"


def slugify(value: str, max_length: int | None = None) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    if max_length is not None:
        slug = slug[:max_length].rstrip("-")
    return slug or "untitled"


def plain_text(rich_text: list[dict[str, Any]] | None) -> str:
    if not rich_text:
        return ""
    return "".join(part.get("plain_text", "") for part in rich_text)


def rich_text_to_markdown(rich_text: list[dict[str, Any]] | None) -> str:
    if not rich_text:
        return ""

    parts: list[str] = []
    for item in rich_text:
        text = item.get("plain_text", "")
        href = item.get("href")
        annotations = item.get("annotations", {})

        if not text:
            continue
        if annotations.get("code"):
            text = f"`{text}`"
        if annotations.get("bold"):
            text = f"**{text}**"
        if annotations.get("italic"):
            text = f"*{text}*"
        if annotations.get("strikethrough"):
            text = f"~~{text}~~"
        if href:
            text = f"[{text}]({href})"
        parts.append(text)

    return "".join(parts)


def page_title_from_properties(properties: dict[str, Any]) -> str:
    for prop in properties.values():
        if prop.get("type") == "title":
            return plain_text(prop.get("title")) or "Untitled"
    return "Untitled"


def child_page_blocks(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [block for block in blocks if block.get("type") == "child_page" and not block.get("archived")]


def title_from_child_page_block(block: dict[str, Any]) -> str:
    child = block.get("child_page") or {}
    title = child.get("title")
    if isinstance(title, str) and title.strip():
        return title.strip()
    return "Untitled"


def extract_page_structure(
    client: NotionClient,
    page_id: str,
    *,
    include_root_metadata: bool = True,
    progress: tqdm | None = None,
) -> dict[str, Any]:
    """Recursively extract child-page hierarchy under page_id as JSON-serializable dict."""
    page_id = normalize_page_id(page_id)
    page = client.retrieve_page(page_id)
    blocks = client.list_block_children(page_id)
    children_blocks = child_page_blocks(blocks)

    title = page_title_from_properties(page.get("properties", {}))
    node: dict[str, Any] = {
        "id": page_id,
        "object": "page",
        "title": title,
        "url": notion_page_url(page_id),
        "children": [],
    }
    if include_root_metadata:
        node["created_time"] = page.get("created_time")
        node["last_edited_time"] = page.get("last_edited_time")
        node["archived"] = page.get("archived", False)

    if progress is not None:
        progress.update(1)
        progress.set_postfix_str(title[:48] or page_id, refresh=False)

    for block in children_blocks:
        child_id = normalize_page_id(block["id"])
        child_node = extract_page_structure(
            client,
            child_id,
            include_root_metadata=include_root_metadata,
            progress=progress,
        )
        inline_title = title_from_child_page_block(block)
        if inline_title != "Untitled" and child_node.get("title") in ("", "Untitled"):
            child_node["title"] = inline_title
        node["children"].append(child_node)

    return node


def count_pages(node: dict[str, Any]) -> int:
    return 1 + sum(count_pages(child) for child in node.get("children", []))


def load_sources() -> dict[str, Any]:
    with SOURCES_FILE.open("r", encoding="utf-8") as source_file:
        data = yaml.safe_load(source_file) or {}
    if not isinstance(data, dict):
        raise ValueError("sources.yml must contain a mapping")
    return data


def notion_entries(data: dict[str, Any], key: str) -> list[dict[str, Any]]:
    notion = data.get("notion") or {}
    entries = notion.get(key) or []
    if not isinstance(entries, list):
        raise ValueError(f"sources.yml notion.{key} must be a list")
    return [entry for entry in entries if isinstance(entry, dict) and entry.get("id")]


def load_cached_structure() -> dict[str, Any] | None:
    if not DEFAULT_STRUCTURE_PATH.exists():
        return None
    return json.loads(DEFAULT_STRUCTURE_PATH.read_text(encoding="utf-8"))


def tree_index(root: dict[str, Any]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}

    def walk(node: dict[str, Any]) -> None:
        index[normalize_page_id(node["id"])] = node
        for child in node.get("children", []):
            walk(child)

    walk(root)
    return index


def excluded_wiki_candidate_node(node: dict[str, Any]) -> bool:
    page_id = normalize_page_id(node["id"])
    title = str(node.get("title") or "").strip()
    return page_id in EXCLUDED_WIKI_CANDIDATE_PAGE_IDS or title in EXCLUDED_WIKI_CANDIDATE_TITLES


def collect_tree_ids(node: dict[str, Any]) -> list[str]:
    if excluded_wiki_candidate_node(node):
        return []

    ids = [normalize_page_id(node["id"])]
    for child in node.get("children", []):
        ids.extend(collect_tree_ids(child))
    return ids


def live_descendant_ids(client: NotionClient, page_id: str) -> list[str]:
    page_id = normalize_page_id(page_id)
    if page_id in EXCLUDED_WIKI_CANDIDATE_PAGE_IDS:
        return []

    ids = [page_id]
    for block in child_page_blocks(client.list_block_children(page_id)):
        ids.extend(live_descendant_ids(client, block["id"]))
    return ids


def resolve_page_refs(client: NotionClient, sources: dict[str, Any]) -> list[PageRef]:
    cached_structure = load_cached_structure()
    cached_index = tree_index(cached_structure) if cached_structure else {}
    refs: list[PageRef] = []

    for entry in notion_entries(sources, "knowledge_base"):
        page_id = normalize_page_id(str(entry["id"]))
        node = cached_index.get(page_id)
        refs.append(PageRef(id=page_id, lane="knowledge_base", root_id=page_id, root_title=node.get("title") if node else None))

    seen_wiki_ids: set[str] = set()
    for entry in notion_entries(sources, "wiki_candidates"):
        root_id = normalize_page_id(str(entry["id"]))
        node = cached_index.get(root_id)
        ids = collect_tree_ids(node) if node else live_descendant_ids(client, root_id)
        root_title = node.get("title") if node else None
        for page_id in ids:
            if page_id in seen_wiki_ids:
                continue
            seen_wiki_ids.add(page_id)
            refs.append(PageRef(id=page_id, lane="wiki_candidate", root_id=root_id, root_title=root_title))

    return refs


def escape_table_cell(value: str) -> str:
    return value.replace("\n", " ").replace("|", "\\|").strip()


def block_rich_text(block: dict[str, Any]) -> list[dict[str, Any]]:
    typed = block.get(block.get("type", ""), {})
    return typed.get("rich_text") or []


def image_caption(block: dict[str, Any]) -> str:
    image = block.get("image") or {}
    return rich_text_to_markdown(image.get("caption")) or "Notion image"


def image_source_kind(block: dict[str, Any]) -> str:
    image = block.get("image") or {}
    image_type = image.get("type")
    image_payload = image.get(image_type, {}) if image_type else {}
    url = image_payload.get("url")
    if image_type and url:
        return f"{image_type}.url"
    if image_type:
        return f"{image_type}.missing_url"
    return "missing_file_or_external_url"


def table_rows_to_markdown(rows: list[dict[str, Any]]) -> str:
    rendered_rows: list[list[str]] = []
    for row in rows:
        cells = (row.get("table_row") or {}).get("cells") or []
        rendered_rows.append([escape_table_cell(rich_text_to_markdown(cell)) for cell in cells])

    if not rendered_rows:
        return ""

    column_count = max(len(row) for row in rendered_rows)
    normalized = [row + [""] * (column_count - len(row)) for row in rendered_rows]
    header = normalized[0]
    separator = ["---"] * column_count
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(separator) + " |",
    ]
    for row in normalized[1:]:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def blocks_to_markdown(
    client: NotionClient,
    blocks: list[dict[str, Any]],
    *,
    page_id: str,
    page_title: str,
    page_slug: str,
    output_dir: Path,
    pages_with_images: set[tuple[str, str, str]],
    depth: int = 0,
) -> str:
    lines: list[str] = []

    for block in blocks:
        block_type = block.get("type", "unsupported")
        typed = block.get(block_type) or {}

        if block_type == "paragraph":
            text = rich_text_to_markdown(typed.get("rich_text"))
            if text:
                lines.append(text)
        elif block_type in {"heading_1", "heading_2", "heading_3"}:
            level = {"heading_1": 2, "heading_2": 3, "heading_3": 4}[block_type]
            text = rich_text_to_markdown(typed.get("rich_text"))
            if text:
                lines.append(f"{'#' * level} {text}")
        elif block_type == "bulleted_list_item":
            text = rich_text_to_markdown(typed.get("rich_text"))
            if text:
                lines.append(f"{'  ' * depth}- {text}")
        elif block_type == "numbered_list_item":
            text = rich_text_to_markdown(typed.get("rich_text"))
            if text:
                lines.append(f"{'  ' * depth}1. {text}")
        elif block_type == "to_do":
            text = rich_text_to_markdown(typed.get("rich_text"))
            checked = "x" if typed.get("checked") else " "
            if text:
                lines.append(f"- [{checked}] {text}")
        elif block_type == "quote":
            text = rich_text_to_markdown(typed.get("rich_text"))
            if text:
                lines.append("> " + text.replace("\n", "\n> "))
        elif block_type == "callout":
            text = rich_text_to_markdown(typed.get("rich_text"))
            if text:
                lines.append(f"> **Callout:** {text}")
        elif block_type == "code":
            language = typed.get("language") or ""
            text = plain_text(typed.get("rich_text"))
            lines.append(f"```{language}\n{text}\n```")
        elif block_type == "divider":
            lines.append("---")
        elif block_type == "image":
            pages_with_images.add((page_title, page_id, image_source_kind(block)))
            continue
        elif block_type == "table":
            rows = client.list_block_children(block["id"])
            table = table_rows_to_markdown(rows)
            if table:
                lines.append(table)
        elif block_type in {"bookmark", "embed", "video", "pdf", "equation", "synced_block", "file"}:
            lines.append(f"[Notion {block_type} — see source page]")
        elif block_type in {"child_page", "child_database", "table_row"}:
            continue
        elif block_type == "unsupported":
            lines.append(f"<!-- notion:block:{block.get('id')} type=unsupported -->")
        else:
            text = rich_text_to_markdown(block_rich_text(block))
            if text:
                lines.append(text)
            else:
                lines.append(f"<!-- notion:block:{block.get('id')} type={block_type} -->")

        if block.get("has_children") and block_type not in {"table", "child_page", "child_database"}:
            child_blocks = client.list_block_children(block["id"])
            child_text = blocks_to_markdown(
                client,
                child_blocks,
                page_id=page_id,
                page_title=page_title,
                page_slug=page_slug,
                output_dir=output_dir,
                pages_with_images=pages_with_images,
                depth=depth + 1,
            )
            if child_text:
                lines.append(child_text)

    return "\n\n".join(line for line in lines if line.strip())


def markdown_headings(markdown: str) -> list[str]:
    headings: list[str] = []
    for line in markdown.splitlines():
        match = re.match(r"^#{2,4}\s+(.+)$", line)
        if match:
            headings.append(match.group(1).strip())
    return headings


def markdown_excerpt(markdown: str, max_length: int = 500) -> str:
    cleaned_lines: list[str] = []
    in_code = False
    for line in markdown.splitlines():
        if line.startswith("```"):
            in_code = not in_code
            continue
        if in_code or line.startswith("#") or line.startswith("---") or line.startswith("<!--"):
            continue
        stripped = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", line).strip()
        if stripped:
            cleaned_lines.append(stripped)
    excerpt = " ".join(cleaned_lines)
    return excerpt[:max_length].rstrip()


def unique_output_path(base_dir: Path, base_name: str) -> Path:
    output_path = base_dir / f"{base_name}.md"
    counter = 2
    while output_path.exists():
        output_path = base_dir / f"{base_name}-{counter}.md"
        counter += 1
    return output_path


def write_page_markdown(
    client: NotionClient,
    ref: PageRef,
    fetched_at: datetime,
    pages_with_images: set[tuple[str, str, str]],
) -> WrittenPage:
    page = client.retrieve_page(ref.id)
    title = page_title_from_properties(page.get("properties", {}))
    page_slug = slugify(title, max_length=70)
    output_dir = NOTION_KNOWLEDGE_DIR if ref.lane == "knowledge_base" else STAGING_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    if ref.lane == "knowledge_base":
        output_path = output_dir / f"{page_slug}.md"
        source_type = "notion-knowledge"
    else:
        date_part = fetched_at.strftime("%Y-%m-%d")
        output_path = output_dir / f"notion-{date_part}-{page_slug}.md"
        source_type = "notion-wiki-candidate"

    blocks = client.list_block_children(ref.id)
    body = blocks_to_markdown(
        client,
        blocks,
        page_id=ref.id,
        page_title=title,
        page_slug=page_slug,
        output_dir=output_dir,
        pages_with_images=pages_with_images,
    )
    headings = markdown_headings(body)
    excerpt = markdown_excerpt(body)
    last_edited_time = page.get("last_edited_time")

    frontmatter = [
        "---",
        "source: notion",
        f"notion_id: {ref.id}",
        f"notion_url: {notion_page_url(ref.id)}",
        f"type: {source_type}",
        f"title: {json.dumps(title, ensure_ascii=False)}",
        f"fetched_at: {fetched_at.isoformat()}",
        f"last_edited_time: {last_edited_time or ''}",
    ]
    if ref.root_id != ref.id:
        frontmatter.append(f"root_notion_id: {ref.root_id}")
    if ref.root_title:
        frontmatter.append(f"root_title: {json.dumps(ref.root_title, ensure_ascii=False)}")
    frontmatter.extend(["---", ""])

    output_path.write_text("\n".join(frontmatter) + body + "\n", encoding="utf-8")
    return WrittenPage(
        id=ref.id,
        title=title,
        lane=ref.lane,
        path=output_path,
        headings=headings,
        excerpt=excerpt,
        last_edited_time=last_edited_time,
    )


def relative_to_private(path: Path) -> str:
    try:
        return str(path.relative_to(PRIVATE_REPO_PATH))
    except ValueError:
        return str(path)


def build_profile_baseline_section(written_pages: list[WrittenPage], seeded_at: datetime) -> str:
    knowledge_pages = [page for page in written_pages if page.lane == "knowledge_base"]
    lines = [
        PROFILE_START_MARKER,
        "## 10. AI knowledge baseline (from Notion)",
        "",
        f"*Last seeded: {seeded_at.date().isoformat()}. Source: Notion `knowledge_base` pages in `sources.yml`.*",
        "",
        "### Topics Dean has documented deeply",
        "",
        "| Topic | Notion source | Depth signal |",
        "| --- | --- | --- |",
    ]

    for page in knowledge_pages:
        depth_signal = ", ".join(page.headings[:5]) if page.headings else "No extracted headings"
        rel_path = relative_to_private(page.path)
        lines.append(f"| {page.title} | `{rel_path}` | {depth_signal} |")

    lines.extend(["", "### Per-topic summaries", ""])

    for page in knowledge_pages:
        related = ", ".join(page.headings[:8]) if page.headings else "No headings extracted"
        excerpt = page.excerpt or "No substantive text extracted from this page."
        lines.extend(
            [
                f"#### {page.title}",
                f"- **Knows:** {excerpt}",
                f"- **Related subtopics:** {related}",
                "- **Not wiki fodder:** foundational — use this to calibrate depth and avoid re-teaching basics.",
                "",
            ]
        )

    lines.append(PROFILE_END_MARKER)
    return "\n".join(lines).rstrip() + "\n"


def update_sources_line(profile_text: str, seeded_at: datetime) -> str:
    source_addition = f"Notion knowledge_base seed ({seeded_at.date().isoformat()})"
    lines = profile_text.splitlines()
    for index, line in enumerate(lines[:20]):
        if line.startswith("*Sources:"):
            if source_addition not in line:
                lines[index] = line.rstrip("*") + f", {source_addition}.*"
            return "\n".join(lines) + "\n"
    return profile_text


def update_dean_profile(written_pages: list[WrittenPage], seeded_at: datetime) -> bool:
    if not DEAN_PROFILE_PATH.exists():
        logger.warning("Dean profile not found: %s", DEAN_PROFILE_PATH)
        return False

    profile_text = DEAN_PROFILE_PATH.read_text(encoding="utf-8")
    profile_text = update_sources_line(profile_text, seeded_at)
    section = build_profile_baseline_section(written_pages, seeded_at)

    if PROFILE_START_MARKER in profile_text and PROFILE_END_MARKER in profile_text:
        pattern = re.compile(
            re.escape(PROFILE_START_MARKER) + r".*?" + re.escape(PROFILE_END_MARKER),
            re.DOTALL,
        )
        updated = pattern.sub(section.strip(), profile_text)
    else:
        updated = profile_text.rstrip() + "\n\n---\n\n" + section

    DEAN_PROFILE_PATH.write_text(updated.rstrip() + "\n", encoding="utf-8")
    return True


def write_pages_with_images_report(pages_with_images: set[tuple[str, str, str]]) -> None:
    NOTION_KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Pages with Notion image blocks",
        "",
        "These pages contained image blocks during Notion seed extraction.",
        "Images are intentionally omitted from scraped markdown; use PDFs or the source Notion page when the visual content matters.",
        "",
        "| Title | Notion ID | Image source returned by API |",
        "| --- | --- | --- |",
    ]
    for title, page_id, source_kind in sorted(pages_with_images, key=lambda item: item[0].lower()):
        lines.append(f"| {title} | `{page_id}` | {source_kind} |")
    PAGES_WITH_IMAGES_FILE.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def configured_ids(sources: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for key in ("knowledge_base", "wiki_candidates"):
        for entry in notion_entries(sources, key):
            ids.add(normalize_page_id(str(entry["id"])))
    return ids


def validate_sources() -> int:
    structure = load_cached_structure()
    if not structure:
        logger.error("No cached structure found at %s", DEFAULT_STRUCTURE_PATH)
        return 1

    sources = load_sources()
    configured = configured_ids(sources)
    index = tree_index(structure)
    missing_roots = sorted(configured - set(index.keys()))
    uncategorized = sorted(set(index.keys()) - configured)

    if missing_roots:
        logger.warning("Configured IDs missing from cached structure:")
        for page_id in missing_roots:
            logger.warning("- %s", page_id)

    logger.info("Cached pages: %s; configured roots: %s", len(index), len(configured))
    logger.info("Uncategorized cached pages (descendants may still be covered by wiki roots): %s", len(uncategorized))
    for page_id in uncategorized[:50]:
        node = index[page_id]
        logger.info("- %s — %s", page_id, node.get("title", "Untitled"))
    if len(uncategorized) > 50:
        logger.info("... %s more", len(uncategorized) - 50)
    return 0


def export_structure(args: argparse.Namespace, client: NotionClient) -> int:
    if not args.root_page_id:
        logger.error("Set NOTION_ROOT_PAGE_ID or pass --root-page-id")
        return 1

    try:
        root_page_id = normalize_page_id(args.root_page_id)
    except ValueError as error:
        logger.error("%s", error)
        return 1

    logger.info("Extracting page structure from %s", root_page_id)
    try:
        progress_cm: Any = nullcontext() if args.no_progress else tqdm(desc="Notion pages", unit="page", dynamic_ncols=True)
        with progress_cm as progress:
            bar = None if args.no_progress else progress
            structure = extract_page_structure(client, root_page_id, progress=bar)
    except NotionClientError as error:
        logger.error("%s", error)
        return 1

    page_count = count_pages(structure)
    logger.info("Found %s page(s) under root %r", page_count, structure.get("title"))
    payload = json.dumps(structure, indent=2, ensure_ascii=False) + "\n"

    if args.print:
        print(payload, end="")

    if args.dry_run:
        logger.info("Dry run — skipping write to %s", args.output)
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload, encoding="utf-8")
    logger.info("Wrote page structure to %s", args.output)
    return 0


def ingest_seed(args: argparse.Namespace, client: NotionClient) -> int:
    fetched_at = datetime.now(UTC)
    sources = load_sources()
    refs = resolve_page_refs(client, sources)
    if not refs:
        logger.warning("No Notion seed pages configured in sources.yml")
        return 0

    written: list[WrittenPage] = []
    pages_with_images: set[tuple[str, str, str]] = set()
    try:
        progress_cm: Any = nullcontext() if args.no_progress else tqdm(total=len(refs), desc="Notion pages", unit="page", dynamic_ncols=True)
        with progress_cm as progress:
            for ref in refs:
                page = write_page_markdown(client, ref, fetched_at, pages_with_images)
                written.append(page)
                if not args.no_progress:
                    progress.update(1)
                    progress.set_postfix_str(page.title[:48] or page.id, refresh=False)
    except (NotionClientError, requests.RequestException, OSError, ValueError) as error:
        logger.error("%s", error)
        return 1

    profile_updated = False
    if not args.skip_profile:
        profile_updated = update_dean_profile(written, fetched_at)

    write_pages_with_images_report(pages_with_images)

    knowledge_count = sum(1 for page in written if page.lane == "knowledge_base")
    wiki_count = sum(1 for page in written if page.lane == "wiki_candidate")
    logger.info("Wrote %s knowledge page(s), %s wiki candidate page(s)", knowledge_count, wiki_count)
    logger.info("Wrote image-page report: %s", PAGES_WITH_IMAGES_FILE)
    if profile_updated:
        logger.info("Updated Dean profile baseline: %s", DEAN_PROFILE_PATH)
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed aia-wiki from Notion pages in sources.yml.")
    parser.add_argument(
        "--root-page-id",
        default=os.environ.get("NOTION_ROOT_PAGE_ID"),
        help="Base page UUID for --export-structure (default: NOTION_ROOT_PAGE_ID env)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_STRUCTURE_PATH,
        help=f"Write structure JSON here for --export-structure (default: {DEFAULT_STRUCTURE_PATH})",
    )
    parser.add_argument("--print", action="store_true", help="Also print exported structure JSON to stdout")
    parser.add_argument("--dry-run", action="store_true", help="For --export-structure, do not write the JSON file")
    parser.add_argument("--no-progress", action="store_true", help="Disable tqdm progress bar")
    parser.add_argument("--export-structure", action="store_true", help="Export Notion page tree JSON instead of seeding markdown")
    parser.add_argument("--validate-sources", action="store_true", help="Report cached pages not listed directly in sources.yml")
    parser.add_argument("--skip-profile", action="store_true", help="Do not update Dean-Profile.md after knowledge_base fetch")
    parser.add_argument(
        "--request-delay",
        type=float,
        default=DEFAULT_REQUEST_DELAY_SEC,
        help=f"Delay after each Notion request in seconds (default: {DEFAULT_REQUEST_DELAY_SEC})",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.validate_sources:
        return validate_sources()

    api_key = os.environ.get("NOTION_API_KEY")
    if not api_key:
        logger.error("NOTION_API_KEY is required")
        return 1

    client = NotionClient(api_key, request_delay=args.request_delay)
    if args.export_structure:
        return export_structure(args, client)
    return ingest_seed(args, client)


if __name__ == "__main__":
    sys.exit(main())
