"""Fetch RSS/Atom sources and write new entries to private staging."""

from __future__ import annotations

import logging
import os
import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from time import struct_time
from typing import Any

from bs4 import BeautifulSoup
from dateutil import parser as date_parser
import feedparser
import requests
import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCES_FILE = REPO_ROOT / "sources.yml"
PRIVATE_REPO_PATH = Path(os.environ.get("PRIVATE_REPO_PATH", "../dean-wiki-private"))
STAGING_DIR = PRIVATE_REPO_PATH / "sources" / "staging"
SEEN_URLS_FILE = PRIVATE_REPO_PATH / "sources" / ".seen_urls.txt"
USER_AGENT = "aia-wiki-bot/1.0"


def slugify(value: str, max_length: int | None = None) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    if max_length is not None:
        slug = slug[:max_length].rstrip("-")
    return slug or "untitled"


def load_sources() -> list[dict[str, str]]:
    try:
        with SOURCES_FILE.open("r", encoding="utf-8") as source_file:
            data = yaml.safe_load(source_file) or {}
    except OSError as error:
        logger.error("sources.yml not found or unreadable: %s", error)
        raise

    feeds = data.get("rss", [])
    if not isinstance(feeds, list):
        logger.error("sources.yml rss key must be a list")
        raise ValueError("sources.yml rss key must be a list")

    return feeds


def load_seen_urls() -> set[str]:
    SEEN_URLS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SEEN_URLS_FILE.touch(exist_ok=True)
    with SEEN_URLS_FILE.open("r", encoding="utf-8") as seen_file:
        return {line.strip() for line in seen_file if line.strip()}


def append_seen_url(url: str) -> None:
    with SEEN_URLS_FILE.open("a", encoding="utf-8") as seen_file:
        seen_file.write(f"{url}\n")


def entry_datetime(entry: Any) -> datetime | None:
    parsed = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if isinstance(parsed, struct_time):
        return datetime(*parsed[:6], tzinfo=UTC)

    date_value = getattr(entry, "published", None) or getattr(entry, "updated", None)
    if not date_value:
        return None

    try:
        parsed_date = date_parser.parse(date_value)
    except (TypeError, ValueError):
        return None

    if parsed_date.tzinfo is None:
        return parsed_date.replace(tzinfo=UTC)
    return parsed_date.astimezone(UTC)


def rss_entry_content(entry: Any) -> str | None:
    summary = getattr(entry, "summary", None)
    if summary:
        return str(summary)

    content = getattr(entry, "content", None)
    if content:
        first_content = content[0]
        value = first_content.get("value") if isinstance(first_content, dict) else getattr(first_content, "value", None)
        if value:
            return str(value)

    return None


def extract_article_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript", "svg", "nav", "footer", "header", "form"]):
        tag.decompose()

    article = soup.find("article") or soup.find("main") or soup.body
    if article is None:
        return ""

    lines = [line.strip() for line in article.get_text("\n").splitlines()]
    return "\n".join(line for line in lines if line)


def fetch_article_content(url: str) -> str | None:
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=10)
    response.raise_for_status()

    text = extract_article_text(response.text)
    return text or None


def entry_content(entry: Any) -> str:
    content = rss_entry_content(entry)
    if content:
        return content

    title = str(getattr(entry, "title", "Untitled"))
    link = getattr(entry, "link", None)
    if not link:
        return title

    try:
        article_content = fetch_article_content(str(link))
    except requests.RequestException as error:
        logger.warning("Failed to fetch full article content for %s: %s", link, error)
        return title

    if article_content:
        logger.info("Fetched full article content for: %s", title)
        return article_content

    logger.warning("Article page had no extractable text, falling back to title: %s", title)
    return title


def unique_output_path(feed_name: str, title: str, fetched_at: datetime) -> Path:
    feed_slug = slugify(feed_name)
    title_slug = slugify(title, max_length=60)
    date_part = fetched_at.strftime("%Y-%m-%d")
    base_name = f"{feed_slug}-{date_part}-{title_slug}"
    output_path = STAGING_DIR / f"{base_name}.md"

    counter = 2
    while output_path.exists():
        output_path = STAGING_DIR / f"{base_name}-{counter}.md"
        counter += 1

    return output_path


def write_entry(feed_name: str, entry: Any) -> Path:
    fetched_at = datetime.now(UTC)
    title = str(getattr(entry, "title", "Untitled"))
    link = str(getattr(entry, "link", ""))
    output_path = unique_output_path(feed_name, title, fetched_at)
    body = entry_content(entry)

    output_path.write_text(
        "\n".join(
            [
                "---",
                f"source: {feed_name}",
                f"url: {link}",
                "type: rss",
                f"title: {title}",
                f"fetched_at: {fetched_at.isoformat()}",
                "---",
                "",
                body,
                "",
            ]
        ),
        encoding="utf-8",
    )
    return output_path


def fetch_feed(feed: dict[str, str]) -> Any:
    response = requests.get(feed["url"], headers={"User-Agent": USER_AGENT}, timeout=10)
    response.raise_for_status()
    return feedparser.parse(response.text)


def main() -> int:
    try:
        STAGING_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        logger.error("STAGING_DIR could not be created: %s", error)
        return 1

    try:
        feeds = load_sources()
        seen_urls = load_seen_urls()
    except (OSError, ValueError):
        return 1

    cutoff = datetime.now(UTC) - timedelta(hours=24)
    fetched = 0
    skipped_seen = 0
    skipped_old = 0
    feeds_failed = 0

    for feed in feeds:
        feed_name = feed.get("name", "Unknown Feed")
        feed_url = feed.get("url")
        if not feed_url:
            logger.warning("Feed fetch failed for %s: missing url", feed_name)
            feeds_failed += 1
            continue

        logger.info("Starting fetch for feed: %s", feed_name)
        try:
            parsed_feed = fetch_feed(feed)
        except Exception as error:  # Keep one broken feed from stopping the run.
            logger.warning("Feed fetch failed for %s (%s): %s", feed_name, feed_url, error)
            feeds_failed += 1
            continue

        entries = getattr(parsed_feed, "entries", [])
        feed_new = 0
        logger.info("Feed %s returned %s entries", feed_name, len(entries))

        for entry in entries:
            title = str(getattr(entry, "title", "Untitled"))
            link = getattr(entry, "link", None)
            if not link:
                logger.warning("Entry has no link, skipping: %s", title)
                skipped_seen += 1
                continue

            link = str(link)
            if link in seen_urls:
                skipped_seen += 1
                continue

            published_at = entry_datetime(entry)
            if published_at is None:
                logger.warning("Entry has no date, including: %s", title)
            elif published_at < cutoff:
                skipped_old += 1
                continue

            output_path = write_entry(feed_name, entry)
            seen_urls.add(link)
            append_seen_url(link)
            fetched += 1
            feed_new += 1
            logger.info("Wrote RSS staging file: %s", output_path.name)

        logger.info("Feed %s: %s entries found, %s new", feed_name, len(entries), feed_new)

    summary = (
        f"- **RSS**: {fetched} fetched, {skipped_seen} skipped (seen), "
        f"{skipped_old} skipped (old), {feeds_failed} feeds failed"
    )
    with (STAGING_DIR / ".run-summary").open("a", encoding="utf-8") as summary_file:
        summary_file.write(f"{summary}\n")
    logger.info("Final summary: %s", summary)

    return 0


if __name__ == "__main__":
    sys.exit(main())
