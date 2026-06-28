"""Fetch recently edited Notion pages under NOTION_ROOT_PAGE_ID and write staging files."""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import requests
import yaml

if str(_repo_root := Path(__file__).resolve().parents[2]) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from seed_from_notion import blocks_to_markdown, slugify  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

REPO_ROOT = _repo_root
SOURCES_FILE = REPO_ROOT / "sources.yml"
WIKI_DIR = REPO_ROOT / "wiki"
PRIVATE_REPO_PATH = Path(os.environ.get("PRIVATE_REPO_PATH", REPO_ROOT.parent / "dean-wiki-private"))
STAGING_DIR = PRIVATE_REPO_PATH / "sources" / "staging"
SEEN_EDITS_FILE = PRIVATE_REPO_PATH / "sources" / ".seen_notion_edits.txt"
DEFAULT_STRUCTURE_PATH = PRIVATE_REPO_PATH / "sources" / "notion" / "seed" / "page-structure.json"

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
DEFAULT_REQUEST_DELAY_SEC = 0.35
HEX32_RE = re.compile(r"^[0-9a-f]{32}$", re.IGNORECASE)


class NotionClientError(Exception):
    pass


@dataclass(frozen=True)
class PageUpdate:
    id: str
    title: str
    last_edited_time: datetime
    last_edited_by: str | None
    url: str


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
        self.request_count = 0

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        url = f"{NOTION_API_BASE}{path}"
        response = self._session.request(method, url, timeout=60, **kwargs)
        self.request_count += 1
        if self._request_delay > 0:
            time.sleep(self._request_delay)
        if not response.ok:
            detail = response.text[:500]
            raise NotionClientError(f"Notion API {response.status_code} {path}: {detail}")
        return response.json()

    def retrieve_page(self, page_id: str) -> dict[str, Any]:
        return self._request("GET", f"/pages/{page_id}")

    def retrieve_database(self, database_id: str) -> dict[str, Any]:
        return self._request("GET", f"/databases/{database_id}")

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

    def search_pages(self, *, start_cursor: str | None = None, page_size: int = 100) -> dict[str, Any]:
        body: dict[str, Any] = {
            "sort": {"timestamp": "last_edited_time", "direction": "descending"},
            "filter": {"property": "object", "value": "page"},
            "page_size": page_size,
        }
        if start_cursor:
            body["start_cursor"] = start_cursor
        return self._request("POST", "/search", json=body)


def normalize_page_id(page_id: str) -> str:
    cleaned = page_id.strip().replace("-", "").lower()
    if not HEX32_RE.fullmatch(cleaned):
        raise ValueError(f"Invalid Notion page id: {page_id!r}")
    return f"{cleaned[:8]}-{cleaned[8:12]}-{cleaned[12:16]}-{cleaned[16:20]}-{cleaned[20:]}"


def notion_page_url(page_id: str) -> str:
    return f"https://www.notion.so/{page_id.replace('-', '')}"


def plain_text(rich_text: list[dict[str, Any]] | None) -> str:
    if not rich_text:
        return ""
    return "".join(part.get("plain_text", "") for part in rich_text)


def page_title_from_properties(properties: dict[str, Any]) -> str:
    for prop in properties.values():
        if prop.get("type") == "title":
            return plain_text(prop.get("title")) or "Untitled"
    return "Untitled"


def parse_notion_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def user_display_name(user: dict[str, Any] | None) -> str | None:
    if not user:
        return None
    person = user.get("person") or {}
    name = person.get("name")
    if isinstance(name, str) and name.strip():
        return name.strip()
    bot = user.get("bot") or {}
    owner = bot.get("owner") or {}
    if owner.get("type") == "user":
        owner_user = owner.get("user") or {}
        owner_name = owner_user.get("name")
        if isinstance(owner_name, str) and owner_name.strip():
            return owner_name.strip()
    return user.get("id")


def edit_seen_key(update: PageUpdate) -> str:
    return f"{update.id}|{update.last_edited_time.isoformat()}"


def load_seen_edits() -> set[str]:
    SEEN_EDITS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SEEN_EDITS_FILE.touch(exist_ok=True)
    with SEEN_EDITS_FILE.open("r", encoding="utf-8") as seen_file:
        return {line.strip() for line in seen_file if line.strip()}


def append_seen_edit(key: str) -> None:
    with SEEN_EDITS_FILE.open("a", encoding="utf-8") as seen_file:
        seen_file.write(f"{key}\n")


def collect_tree_page_ids(node: dict[str, Any]) -> set[str]:
    ids = {normalize_page_id(node["id"])}
    for child in node.get("children", []):
        ids.update(collect_tree_page_ids(child))
    return ids


def build_wiki_slug_index() -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    if not WIKI_DIR.exists():
        return index

    skip_names = {"index.md", "overview.md"}
    for path in WIKI_DIR.rglob("*.md"):
        if path.name in skip_names:
            continue
        rel_path = path.relative_to(REPO_ROOT).as_posix()
        index.setdefault(path.stem, []).append(rel_path)
    return index


def suggest_wiki_pages(title: str, wiki_index: dict[str, list[str]]) -> list[str]:
    title_slug = slugify(title)
    exact = wiki_index.get(title_slug, [])
    if exact:
        return sorted(set(exact))

    partial: list[str] = []
    for stem, paths in wiki_index.items():
        if title_slug in stem or stem in title_slug:
            partial.extend(paths)
    return sorted(set(partial))


def load_wiki_candidate_ids() -> set[str]:
    if not SOURCES_FILE.exists():
        return set()

    try:
        with SOURCES_FILE.open("r", encoding="utf-8") as source_file:
            data = yaml.safe_load(source_file) or {}
    except (OSError, yaml.YAMLError) as error:
        logger.warning("Could not read %s: %s", SOURCES_FILE, error)
        return set()

    notion = data.get("notion") or {}
    entries = notion.get("wiki_candidates") or []
    ids: set[str] = set()
    for entry in entries:
        if isinstance(entry, dict) and entry.get("id"):
            try:
                ids.add(normalize_page_id(str(entry["id"])))
            except ValueError:
                continue
    return ids


def find_subtree_ids(structure: dict[str, Any], target_id: str) -> set[str] | None:
    target_id = normalize_page_id(target_id)
    if normalize_page_id(structure["id"]) == target_id:
        return collect_tree_page_ids(structure)
    for child in structure.get("children", []):
        found = find_subtree_ids(child, target_id)
        if found is not None:
            return found
    return None


def notion_lane(page_id: str, wiki_candidate_ids: set[str], structure_path: Path) -> str | None:
    page_id = normalize_page_id(page_id)
    if page_id in wiki_candidate_ids:
        return "wiki_candidate"

    if not structure_path.exists() or not wiki_candidate_ids:
        return None

    try:
        structure = json.loads(structure_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    for candidate_id in wiki_candidate_ids:
        subtree = find_subtree_ids(structure, candidate_id)
        if subtree and page_id in subtree:
            return "wiki_candidate"

    return None


def load_subtree_page_ids(root_page_id: str, structure_path: Path) -> set[str] | None:
    if not structure_path.exists():
        return None

    try:
        structure = json.loads(structure_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        logger.warning("Could not read structure cache at %s: %s", structure_path, error)
        return None

    cached_root = normalize_page_id(str(structure.get("id", "")))
    if cached_root != normalize_page_id(root_page_id):
        logger.warning(
            "Structure cache root %s does not match requested root %s; ignoring cache",
            cached_root,
            root_page_id,
        )
        return None

    return collect_tree_page_ids(structure)


def parent_page_id(client: NotionClient, parent: dict[str, Any]) -> str | None:
    parent_type = parent.get("type")
    if parent_type == "page_id":
        return normalize_page_id(parent["page_id"])
    if parent_type == "database_id":
        database = client.retrieve_database(parent["database_id"])
        database_parent = database.get("parent") or {}
        if database_parent.get("type") == "page_id":
            return normalize_page_id(database_parent["page_id"])
    return None


def is_under_root(
    client: NotionClient,
    page_id: str,
    root_page_id: str,
    *,
    memo: dict[str, bool],
) -> bool:
    page_id = normalize_page_id(page_id)
    root_page_id = normalize_page_id(root_page_id)
    if page_id == root_page_id:
        return True
    if page_id in memo:
        return memo[page_id]

    current = page_id
    seen: set[str] = set()
    under_root = False

    while current not in seen:
        seen.add(current)
        if current == root_page_id:
            under_root = True
            break

        page = client.retrieve_page(current)
        next_parent = parent_page_id(client, page.get("parent") or {})
        if next_parent is None:
            break
        current = next_parent

    for visited in seen:
        memo[visited] = under_root
    memo[page_id] = under_root
    return under_root


def page_update_from_api(page: dict[str, Any]) -> PageUpdate | None:
    if page.get("in_trash") or page.get("archived"):
        return None

    last_edited_raw = page.get("last_edited_time")
    if not isinstance(last_edited_raw, str):
        return None

    page_id = normalize_page_id(page["id"])
    return PageUpdate(
        id=page_id,
        title=page_title_from_properties(page.get("properties", {})),
        last_edited_time=parse_notion_datetime(last_edited_raw),
        last_edited_by=user_display_name(page.get("last_edited_by")),
        url=notion_page_url(page_id),
    )


def search_recent_updates(
    client: NotionClient,
    root_page_id: str,
    *,
    since: datetime,
    subtree_page_ids: set[str] | None,
) -> list[PageUpdate]:
    """Use Search (sorted by last_edited_time) and stop once results are older than since."""
    updates: list[PageUpdate] = []
    cursor: str | None = None
    ancestry_memo: dict[str, bool] = {}
    search_pages = 0

    while True:
        payload = client.search_pages(start_cursor=cursor)
        results = payload.get("results", [])
        search_pages += 1

        for page in results:
            if page.get("object") != "page":
                continue

            update = page_update_from_api(page)
            if update is None:
                continue

            if update.last_edited_time < since:
                logger.info(
                    "Search early exit after %s page(s); oldest checked edit was before cutoff",
                    search_pages,
                )
                return updates

            page_id = update.id
            if subtree_page_ids is not None:
                in_subtree = page_id in subtree_page_ids
            else:
                in_subtree = is_under_root(
                    client,
                    page_id,
                    root_page_id,
                    memo=ancestry_memo,
                )

            if in_subtree:
                updates.append(update)

        if not payload.get("has_more"):
            break
        cursor = payload.get("next_cursor")
        if not cursor:
            break

    return updates


def fetch_recent_updates(
    client: NotionClient,
    root_page_id: str,
    *,
    since: datetime,
    structure_path: Path,
) -> list[PageUpdate]:
    subtree_page_ids = load_subtree_page_ids(root_page_id, structure_path)
    if subtree_page_ids is not None:
        logger.info(
            "Using cached subtree (%s pages) from %s",
            len(subtree_page_ids),
            structure_path,
        )
    else:
        logger.info(
            "No structure cache; verifying ancestry for recent search hits only "
            "(run seed_from_notion.py --export-structure to speed this up)"
        )

    return search_recent_updates(
        client,
        root_page_id,
        since=since,
        subtree_page_ids=subtree_page_ids,
    )


def unique_output_path(title: str, fetched_at: datetime) -> Path:
    page_slug = slugify(title, max_length=60)
    date_part = fetched_at.strftime("%Y-%m-%d")
    base_name = f"notion-{date_part}-{page_slug}"
    output_path = STAGING_DIR / f"{base_name}.md"

    counter = 2
    while output_path.exists():
        output_path = STAGING_DIR / f"{base_name}-{counter}.md"
        counter += 1

    return output_path


def write_staged_page(
    client: NotionClient,
    update: PageUpdate,
    fetched_at: datetime,
    *,
    wiki_index: dict[str, list[str]],
    wiki_candidate_ids: set[str],
    structure_path: Path,
) -> Path:
    page_slug = slugify(update.title, max_length=70)
    output_path = unique_output_path(update.title, fetched_at)
    blocks = client.list_block_children(update.id)
    pages_with_images: set[tuple[str, str, str]] = set()
    body = blocks_to_markdown(
        client,
        blocks,
        page_id=update.id,
        page_title=update.title,
        page_slug=page_slug,
        output_dir=STAGING_DIR,
        pages_with_images=pages_with_images,
    )

    if pages_with_images:
        logger.warning(
            "Page %s contains image blocks; content may be incomplete — see %s",
            update.title,
            update.url,
        )

    suggested = suggest_wiki_pages(update.title, wiki_index)
    lane = notion_lane(update.id, wiki_candidate_ids, structure_path)

    frontmatter = [
        "---",
        "source: notion",
        f"notion_id: {update.id}",
        f"notion_url: {update.url}",
        "type: notion",
        "ingestion_mode: learning-delta",
        f"title: {json.dumps(update.title, ensure_ascii=False)}",
        f"fetched_at: {fetched_at.isoformat()}",
        f"last_edited_time: {update.last_edited_time.isoformat()}",
    ]
    if lane:
        frontmatter.append(f"notion_lane: {lane}")
    if suggested:
        frontmatter.append("suggested_wiki_pages:")
        frontmatter.extend(f"  - {path}" for path in suggested)
    frontmatter.extend(["---", ""])
    output_path.write_text("\n".join(frontmatter) + body + "\n", encoding="utf-8")
    return output_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch recently edited Notion pages under NOTION_ROOT_PAGE_ID."
    )
    parser.add_argument(
        "--root-page-id",
        default=os.environ.get("NOTION_ROOT_PAGE_ID"),
        help="Root page UUID to scan (default: NOTION_ROOT_PAGE_ID env)",
    )
    parser.add_argument(
        "--hours",
        type=float,
        default=24.0,
        help="Look back this many hours for page edits (default: 24)",
    )
    parser.add_argument(
        "--structure-cache",
        type=Path,
        default=DEFAULT_STRUCTURE_PATH,
        help=f"Cached page tree JSON for fast subtree filtering (default: {DEFAULT_STRUCTURE_PATH})",
    )
    parser.add_argument(
        "--request-delay",
        type=float,
        default=DEFAULT_REQUEST_DELAY_SEC,
        help=f"Delay after each Notion request in seconds (default: {DEFAULT_REQUEST_DELAY_SEC})",
    )
    parser.add_argument(
        "--print-only",
        action="store_true",
        help="List matching pages without writing staging files",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    api_key = os.environ.get("NOTION_API_KEY")
    if not api_key:
        logger.error("NOTION_API_KEY is required")
        return 1

    if not args.root_page_id:
        logger.error("Set NOTION_ROOT_PAGE_ID or pass --root-page-id")
        return 1

    try:
        root_page_id = normalize_page_id(args.root_page_id)
    except ValueError as error:
        logger.error("%s", error)
        return 1

    try:
        STAGING_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        logger.error("STAGING_DIR could not be created: %s", error)
        return 1

    now = datetime.now(UTC)
    since = now - timedelta(hours=args.hours)
    client = NotionClient(api_key, request_delay=args.request_delay)
    seen_edits = load_seen_edits()
    wiki_index = build_wiki_slug_index()
    wiki_candidate_ids = load_wiki_candidate_ids()

    logger.info("Searching Notion for edits under %s since %s", root_page_id, since.isoformat())
    try:
        updates = fetch_recent_updates(
            client,
            root_page_id,
            since=since,
            structure_path=args.structure_cache,
        )
    except NotionClientError as error:
        logger.error("%s", error)
        return 1

    fetched = 0
    skipped_seen = 0

    for update in updates:
        seen_key = edit_seen_key(update)
        if seen_key in seen_edits:
            skipped_seen += 1
            logger.info("Skipping already ingested edit: %s", update.title)
            continue

        if args.print_only:
            edited_by = f" by {update.last_edited_by}" if update.last_edited_by else ""
            print(
                f"- {update.title} ({update.id}) — "
                f"last edited {update.last_edited_time.isoformat()}{edited_by}\n"
                f"  {update.url}"
            )
            continue

        try:
            output_path = write_staged_page(
                client,
                update,
                now,
                wiki_index=wiki_index,
                wiki_candidate_ids=wiki_candidate_ids,
                structure_path=args.structure_cache,
            )
        except NotionClientError as error:
            logger.error("Failed to fetch page %s (%s): %s", update.title, update.id, error)
            continue

        seen_edits.add(seen_key)
        append_seen_edit(seen_key)
        fetched += 1
        logger.info("Wrote Notion staging file: %s", output_path.name)

    logger.info("Done in %s Notion API request(s)", client.request_count)

    if not args.print_only:
        summary = f"- **Notion**: {fetched} fetched, {skipped_seen} skipped (seen), {len(updates)} matched"
        with (STAGING_DIR / ".run-summary").open("a", encoding="utf-8") as summary_file:
            summary_file.write(f"{summary}\n")
        logger.info("Final summary: %s", summary)

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
