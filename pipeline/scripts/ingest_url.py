"""Fetch ad-hoc URLs, verify the article is extractable, and stage it for wiki triage.

Backs the `inject-article` skill: Dean hands over a link, this script proves the page can
be reached and parsed, and either stages a clean markdown file or reports exactly what is
blocking extraction and how to fix it.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup, Tag

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(filename)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
PRIVATE_REPO_PATH = Path(os.environ.get("PRIVATE_REPO_PATH", "../dean-wiki-private"))
DEFAULT_STAGING_DIR = PRIVATE_REPO_PATH / "sources" / "staging"
SEEN_URLS_FILENAME = ".seen_urls.txt"

# Publishers routinely 403 unknown bot agents, so identify as a normal browser and append
# the bot name for server operators reading logs.
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0.0.0 Safari/537.36 aia-wiki-bot/1.0"
)
REQUEST_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
REQUEST_TIMEOUT = 20
RETRY_STATUS = frozenset({500, 502, 503, 504})
MAX_ATTEMPTS = 3
DEFAULT_MIN_CHARS = 800

TRACKING_PARAM_PREFIXES = ("utm_", "mc_", "pk_")
TRACKING_PARAMS = frozenset({"fbclid", "gclid", "igshid", "ref", "ref_src", "s", "si", "spm"})

JS_SHELL_MARKERS = (
    "enable javascript",
    "javascript is required",
    "javascript is disabled",
    "please turn on javascript",
    "just a moment...",
    "checking your browser",
    "verifying you are human",
)
PAYWALL_MARKERS = (
    "subscribe to continue",
    "subscribers only",
    "already a subscriber",
    "sign in to read",
    "create an account to read",
    "this article is for paid",
    "become a member to read",
)
JUNK_PATTERN = re.compile(
    r"(nav|menu|sidebar|footer|masthead|comment|share|social|subscribe|newsletter"
    r"|cookie|consent|banner|promo|related-|breadcrumb|pagination|toc|advert)",
    re.IGNORECASE,
)
BLOCK_TAGS = ("h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "pre", "blockquote")
CONTENT_SELECTORS = (
    "article",
    "[role=main]",
    "main",
    ".post-content",
    ".entry-content",
    ".article-body",
    ".article-content",
    ".markdown-body",
    "#content",
)
UNSUPPORTED_HOSTS = {
    "youtube.com": "youtube",
    "www.youtube.com": "youtube",
    "youtu.be": "youtube",
    "m.youtube.com": "youtube",
    "twitter.com": "social",
    "x.com": "social",
    "www.twitter.com": "social",
    "www.x.com": "social",
    "linkedin.com": "social",
    "www.linkedin.com": "social",
}


class UrlIngestError(Exception):
    """Base class for every failure this module raises."""


class FetchError(UrlIngestError):
    """The URL could not be retrieved at all (DNS, TLS, timeout, connection reset)."""


class ExtractionError(UrlIngestError):
    """The payload was retrieved but no readable text could be recovered from it."""


class StagingError(UrlIngestError):
    """The staging directory is missing or not writable."""


class Status(StrEnum):
    """Verdict for one URL, used to decide whether staging is safe."""

    OK = "ok"
    THIN = "thin"
    JS_REQUIRED = "js_required"
    PAYWALLED = "paywalled"
    BLOCKED = "blocked"
    NOT_FOUND = "not_found"
    RATE_LIMITED = "rate_limited"
    SERVER_ERROR = "server_error"
    UNREACHABLE = "unreachable"
    UNSUPPORTED_TYPE = "unsupported_type"
    NEEDS_PDF_TOOL = "needs_pdf_tool"
    DUPLICATE = "duplicate"
    STAGING_FAILED = "staging_failed"


REMEDIATION: dict[Status, str] = {
    Status.THIN: (
        "Extraction returned very little text. Re-run with --allow-thin to stage it anyway, "
        "or save the readable text yourself and pass --from-file PATH."
    ),
    Status.JS_REQUIRED: (
        "The page is a JavaScript shell or bot challenge, so there is no server-rendered text. "
        "Open it in a browser, copy the article, and re-run with --from-file PATH. "
        "Some sites also expose a plain version (Substack /p/<slug>?no_cover=true, docs .md, GitHub raw)."
    ),
    Status.PAYWALLED: (
        "The body looks paywalled or login-gated. Paste the text you already have access to and "
        "re-run with --from-file PATH, or supply an archive/AMP mirror URL instead."
    ),
    Status.BLOCKED: (
        "The host refused the request (401/403/451 or a bot challenge). Try a first-party mirror "
        "(export.arxiv.org, raw.githubusercontent.com, the publisher's RSS entry), or --from-file PATH."
    ),
    Status.NOT_FOUND: "The URL is 404/410. Check the link, or find the canonical or archived copy.",
    Status.RATE_LIMITED: "The host returned 429. Wait a few minutes and re-run, or use --from-file PATH.",
    Status.SERVER_ERROR: (
        f"The host failed with a 5xx after {MAX_ATTEMPTS} attempts. Re-run later, or use --from-file PATH."
    ),
    Status.UNREACHABLE: (
        "The host could not be reached (DNS, TLS, timeout, or blocked network egress). Verify the URL "
        "resolves from this machine; if egress is restricted, use --from-file PATH."
    ),
    Status.UNSUPPORTED_TYPE: (
        "This URL type has no text to extract here (video, social post, or binary payload). Provide the "
        "transcript, thread text, or paper text in a local file and re-run with --from-file PATH."
    ),
    Status.NEEDS_PDF_TOOL: (
        "The payload is a PDF and `pdftotext` is not installed. Install poppler "
        "(`brew install poppler` / `apt-get install poppler-utils`) and re-run, or use --from-file PATH."
    ),
    Status.DUPLICATE: (
        "This URL was already ingested (present in .seen_urls.txt or already staged). Re-run with "
        "--force to stage a second copy."
    ),
    Status.STAGING_FAILED: (
        "The article extracted fine but the staging file could not be written. Check that the private "
        "repo checkout is present and writable, or pass --staging-dir."
    ),
}


@dataclass(frozen=True)
class FetchResult:
    """Raw outcome of one HTTP retrieval."""

    url: str
    final_url: str
    status_code: int | None
    content_type: str
    text: str
    payload: bytes
    error: str | None = None


@dataclass(frozen=True)
class Article:
    """Extracted, ready-to-stage representation of a source document."""

    title: str
    body: str
    site_name: str
    published_at: str | None
    extraction: str

    @property
    def word_count(self) -> int:
        """Return the whitespace-delimited word count of the body.

        Returns:
            Number of words in the extracted body text.
        """
        return len(self.body.split())


@dataclass
class Report:
    """Per-URL result reported back to the agent or the terminal."""

    url: str
    status: Status
    reason: str
    final_url: str | None = None
    title: str | None = None
    word_count: int = 0
    extraction: str | None = None
    staged_path: str | None = None
    remediation: str | None = None
    notes: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """Return whether this URL needs no human decision.

        Returns:
            True when the URL was extracted cleanly (staged or check-only).
        """
        return self.status is Status.OK

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-serializable view of the report.

        Returns:
            Mapping of report fields with the status rendered as a plain string.
        """
        return {
            "url": self.url,
            "status": str(self.status),
            "reason": self.reason,
            "final_url": self.final_url,
            "title": self.title,
            "word_count": self.word_count,
            "extraction": self.extraction,
            "staged_path": self.staged_path,
            "remediation": self.remediation,
            "notes": self.notes,
        }


def slugify(value: str, max_length: int | None = None) -> str:
    """Convert arbitrary text into a lowercase hyphenated slug.

    Args:
        value: Text to slugify.
        max_length: Optional maximum slug length before trailing hyphens are trimmed.

    Returns:
        A slug safe for use in file names, or "untitled" when nothing survives.
    """
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    if max_length is not None:
        slug = slug[:max_length].rstrip("-")
    return slug or "untitled"


def normalize_url(raw_url: str) -> str:
    """Canonicalize a pasted URL: add a scheme and drop tracking parameters.

    Args:
        raw_url: URL as pasted by the user, possibly scheme-less or campaign-tagged.

    Returns:
        A normalized absolute URL.
    """
    candidate = raw_url.strip().strip("<>").rstrip(",.")
    if not urlparse(candidate).scheme:
        candidate = f"https://{candidate}"

    parts = urlparse(candidate)
    kept = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key.lower() not in TRACKING_PARAMS and not key.lower().startswith(TRACKING_PARAM_PREFIXES)
    ]
    return urlunparse(parts._replace(query=urlencode(kept), fragment=""))


def fetch_candidates(url: str) -> tuple[list[str], list[str]]:
    """Map a URL to the first-party endpoints most likely to serve plain text.

    Args:
        url: Normalized source URL.

    Returns:
        Tuple of (candidate URLs in priority order, human-readable notes about rewrites).
    """
    parts = urlparse(url)
    host = parts.netloc.lower()
    notes: list[str] = []

    arxiv_id = re.match(r"^/(?:abs|pdf)/(?P<id>[\w.\-/]+?)(?:v\d+)?(?:\.pdf)?$", parts.path)
    if host.endswith("arxiv.org") and arxiv_id:
        notes.append("Rewrote to export.arxiv.org abstract page (arXiv's endpoint for automated access).")
        return [f"https://export.arxiv.org/abs/{arxiv_id.group('id')}"], notes

    repo = re.match(r"^/(?P<owner>[\w.\-]+)/(?P<repo>[\w.\-]+)/?$", parts.path)
    if host in {"github.com", "www.github.com"} and repo:
        owner, name = repo.group("owner"), repo.group("repo")
        notes.append("GitHub repo root: reading the README from raw.githubusercontent.com.")
        return [
            f"https://raw.githubusercontent.com/{owner}/{name}/HEAD/{readme}"
            for readme in ("README.md", "readme.md", "README.rst", "docs/README.md")
        ], notes

    return [url], notes


def fetch(url: str) -> FetchResult:
    """Retrieve a URL, retrying transient server failures.

    Args:
        url: Absolute URL to retrieve.

    Returns:
        A FetchResult carrying the payload, or one whose `error` explains the failure.

    Raises:
        FetchError: Never raised directly; connection failures are reported via `error`.
    """
    last_error: str | None = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        except requests.RequestException as error:
            last_error = f"{type(error).__name__}: {error}"
            logger.warning("Attempt %s/%s failed for %s — %s", attempt, MAX_ATTEMPTS, url, last_error)
            continue

        if response.status_code in RETRY_STATUS and attempt < MAX_ATTEMPTS:
            last_error = f"HTTP {response.status_code}"
            logger.warning("Attempt %s/%s got %s for %s", attempt, MAX_ATTEMPTS, response.status_code, url)
            continue

        return FetchResult(
            url=url,
            final_url=str(response.url),
            status_code=response.status_code,
            content_type=response.headers.get("Content-Type", "").split(";")[0].strip().lower(),
            text=response.text,
            payload=response.content,
        )

    return FetchResult(
        url=url, final_url=url, status_code=None, content_type="", text="", payload=b"", error=last_error
    )


def _select_root(soup: BeautifulSoup) -> Tag | None:
    """Pick the element most likely to contain the article body.

    Args:
        soup: Parsed document.

    Returns:
        The chosen container element, or None when the document has no body.
    """
    for selector in CONTENT_SELECTORS:
        found = soup.select_one(selector)
        if found is not None and len(found.get_text(strip=True)) > 200:
            return found

    divs = [div for div in soup.find_all("div") if isinstance(div, Tag)]
    if divs:
        densest = max(divs, key=lambda div: len(div.get_text(strip=True)))
        if len(densest.get_text(strip=True)) > 200:
            return densest

    return soup.body


def _prune(root: Tag) -> None:
    """Strip chrome, scripts, and boilerplate containers from a content root, in place.

    Args:
        root: Container element to clean.
    """
    junk = root(["script", "style", "noscript", "svg", "form", "iframe", "nav", "aside", "footer"])
    junk += [
        tag
        for attr in ("class", "id")
        for tag in root.find_all(attrs={attr: JUNK_PATTERN})
        if isinstance(tag, Tag) and tag.name in {"div", "section", "ul", "ol", "header", "span"}
    ]

    for tag in junk:
        if not tag.decomposed:
            tag.decompose()


def _block_to_markdown(node: Tag) -> str:
    """Render one block-level element as markdown.

    Args:
        node: Element to render (heading, paragraph, list item, pre, or blockquote).

    Returns:
        Markdown text for the element, or an empty string when it holds no text.
    """
    text = " ".join(node.get_text(" ", strip=True).split())
    if not text:
        return ""

    if node.name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
        level = min(int(node.name[1]) + 1, 6)
        return f"{'#' * level} {text}"
    if node.name == "li":
        return f"- {text}"
    if node.name == "pre":
        return f"```\n{node.get_text('\n', strip=True)}\n```"
    if node.name == "blockquote":
        return "\n".join(f"> {line}" for line in text.splitlines())
    return text


def extract_html(html: str) -> Article:
    """Extract title, metadata, and a markdown body from an HTML document.

    Args:
        html: Raw HTML source.

    Returns:
        An Article with the recovered body text.

    Raises:
        ExtractionError: If the document has no usable content root.
    """
    soup = BeautifulSoup(html, "html.parser")

    def meta(*names: str) -> str | None:
        for name in names:
            tag = soup.find("meta", attrs={"property": name}) or soup.find("meta", attrs={"name": name})
            content = tag.get("content") if isinstance(tag, Tag) else None
            if content:
                return str(content).strip()
        return None

    title = meta("og:title", "twitter:title")
    if not title:
        heading = soup.find("h1")
        title = heading.get_text(" ", strip=True) if isinstance(heading, Tag) else None
    if not title and soup.title is not None:
        title = soup.title.get_text(strip=True)

    published = meta("article:published_time", "date", "citation_publication_date", "dc.date")
    if not published:
        time_tag = soup.find("time")
        if isinstance(time_tag, Tag) and time_tag.get("datetime"):
            published = str(time_tag["datetime"])

    root = _select_root(soup)
    if root is None:
        raise ExtractionError("document has no <body> or content container")

    _prune(root)

    emitted: set[int] = set()
    lines: list[str] = []
    for node in root.find_all(BLOCK_TAGS):
        if not isinstance(node, Tag) or any(id(parent) in emitted for parent in node.parents):
            continue
        rendered = _block_to_markdown(node)
        emitted.add(id(node))
        if rendered:
            lines.append(rendered)

    body = (
        "\n\n".join(lines)
        if lines
        else "\n".join(line.strip() for line in root.get_text("\n").splitlines() if line.strip())
    )

    return Article(
        title=title or "Untitled",
        body=re.sub(r"\n{3,}", "\n\n", body).strip(),
        site_name=meta("og:site_name") or "",
        published_at=published,
        extraction="full",
    )


def extract_pdf(payload: bytes) -> Article:
    """Convert a PDF payload to text using poppler's `pdftotext`.

    Args:
        payload: Raw PDF bytes.

    Returns:
        An Article whose body is the extracted PDF text.

    Raises:
        ExtractionError: If `pdftotext` is unavailable, fails, or yields no text.
    """
    if shutil.which("pdftotext") is None:
        raise ExtractionError("pdftotext-missing")

    try:
        completed = subprocess.run(
            ["pdftotext", "-layout", "-", "-"], input=payload, capture_output=True, timeout=120, check=True
        )
    except (subprocess.SubprocessError, OSError) as error:
        logger.exception("pdftotext failed to convert the payload")
        raise ExtractionError(f"pdftotext failed: {error}") from error

    text = completed.stdout.decode("utf-8", errors="replace").strip()
    if not text:
        raise ExtractionError("pdftotext produced no text (likely a scanned or image-only PDF)")

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return Article(
        title=lines[0] if lines else "Untitled",
        body=re.sub(r"\n{3,}", "\n\n", "\n".join(lines)),
        site_name="",
        published_at=None,
        extraction="pdf-text",
    )


def extract_local_file(path: Path) -> Article:
    """Read a body the user supplied by hand, bypassing the network entirely.

    Args:
        path: Path to an HTML, markdown, or plain-text file.

    Returns:
        An Article built from the file contents.

    Raises:
        ExtractionError: If the file is missing, unreadable, or empty.
    """
    try:
        raw = path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError as error:
        logger.exception("Could not read --from-file path %s", path)
        raise ExtractionError(f"unreadable --from-file path: {error}") from error

    if not raw:
        raise ExtractionError(f"--from-file path is empty: {path}")

    if path.suffix.lower() in {".html", ".htm"}:
        article = extract_html(raw)
        return Article(article.title, article.body, article.site_name, article.published_at, "manual-paste")

    heading = next((line for line in raw.splitlines() if line.startswith("# ")), None)
    title = heading.removeprefix("# ").strip() if heading else path.stem.replace("-", " ").title()
    return Article(title=title, body=raw, site_name="", published_at=None, extraction="manual-paste")


def plain_text_title(url: str, text: str) -> str:
    """Derive a title for a markdown or plain-text payload that carries no metadata.

    Args:
        url: URL the payload was fetched from.
        text: Payload contents.

    Returns:
        `owner/repo` for GitHub raw READMEs, else the first markdown heading, else the file name.
    """
    parts = urlparse(url)
    segments = [segment for segment in parts.path.split("/") if segment]
    if parts.netloc.lower() == "raw.githubusercontent.com" and len(segments) >= 2:
        return f"{segments[0]}/{segments[1]}"

    heading = next((line for line in text.splitlines() if line.startswith("# ")), None)
    if heading:
        return heading.removeprefix("# ").strip()

    return segments[-1] if segments else "Untitled"


def diagnose(result: FetchResult, article: Article | None, error: str | None, min_chars: int) -> tuple[Status, str]:
    """Turn a fetch and extraction attempt into a verdict plus a one-line reason.

    Args:
        result: Outcome of the HTTP retrieval.
        article: Extracted article, or None when extraction failed.
        error: Extraction error message, if any.
        min_chars: Minimum body length considered a usable extraction.

    Returns:
        Tuple of (status, human-readable reason).
    """
    if result.error is not None:
        return Status.UNREACHABLE, f"could not connect: {result.error}"

    code = result.status_code or 0
    haystack = result.text[:20000].lower()
    challenged = any(marker in haystack for marker in JS_SHELL_MARKERS)

    if code in {401, 403, 451}:
        return Status.BLOCKED, f"host returned HTTP {code}"
    if code in {404, 410}:
        return Status.NOT_FOUND, f"host returned HTTP {code}"
    if code == 429:
        return Status.RATE_LIMITED, "host returned HTTP 429"
    if code >= 500:
        return Status.SERVER_ERROR, f"host returned HTTP {code}"
    if code >= 400:
        return Status.BLOCKED, f"host returned HTTP {code}"

    if error == "pdftotext-missing":
        return Status.NEEDS_PDF_TOOL, "payload is a PDF and pdftotext is not installed"
    if article is None:
        if result.content_type and not result.content_type.startswith(
            ("text/", "application/pdf", "application/xhtml")
        ):
            return Status.UNSUPPORTED_TYPE, f"unsupported content type: {result.content_type}"
        return Status.THIN, error or "no text could be extracted"

    if len(article.body) >= min_chars:
        return Status.OK, f"extracted {article.word_count} words"
    if challenged:
        return Status.JS_REQUIRED, "server-rendered HTML is a JavaScript shell or bot challenge"
    if any(marker in haystack for marker in PAYWALL_MARKERS):
        return Status.PAYWALLED, "body is short and the page shows paywall or sign-in markers"
    return Status.THIN, f"only {len(article.body)} chars extracted (floor is {min_chars})"


def resolve_staging_dir(override: str | None) -> Path:
    """Locate the staging directory, refusing to invent a stray private-repo tree.

    Args:
        override: Explicit staging directory from the command line, if given.

    Returns:
        An existing, writable staging directory.

    Raises:
        StagingError: If the private repo is absent or the directory cannot be created.
    """
    staging_dir = Path(override) if override else DEFAULT_STAGING_DIR
    if staging_dir.is_dir():
        return staging_dir

    private_root = staging_dir.parents[1] if override is None else staging_dir.parent
    if not private_root.is_dir():
        raise StagingError(
            f"staging directory {staging_dir} does not exist and neither does {private_root}. "
            "Set PRIVATE_REPO_PATH to the dean-wiki-private checkout, or pass --staging-dir."
        )

    try:
        staging_dir.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        logger.exception("Could not create staging directory %s", staging_dir)
        raise StagingError(f"could not create {staging_dir}: {error}") from error

    return staging_dir


def seen_urls_file(staging_dir: Path) -> Path:
    """Locate the dedup ledger that sits alongside the staging directory.

    Args:
        staging_dir: Resolved staging directory.

    Returns:
        Path of the `.seen_urls.txt` ledger shared with the RSS ingest.
    """
    return staging_dir.parent / SEEN_URLS_FILENAME


def load_seen_urls(staging_dir: Path) -> set[str]:
    """Read the dedup ledger shared with the RSS ingest.

    Args:
        staging_dir: Resolved staging directory.

    Returns:
        Set of URLs already ingested, empty when the ledger does not exist yet.
    """
    ledger = seen_urls_file(staging_dir)
    if not ledger.is_file():
        return set()
    with ledger.open("r", encoding="utf-8") as seen_file:
        return {line.strip() for line in seen_file if line.strip()}


def append_seen_url(staging_dir: Path, url: str) -> None:
    """Record a URL in the dedup ledger so nightly RSS runs skip it.

    Args:
        staging_dir: Resolved staging directory.
        url: URL to record.
    """
    ledger = seen_urls_file(staging_dir)
    try:
        with ledger.open("a", encoding="utf-8") as seen_file:
            seen_file.write(f"{url}\n")
    except OSError:
        logger.exception("Could not update %s — the URL may be re-ingested by a later run", ledger)


def unique_output_path(staging_dir: Path, title: str, fetched_at: datetime) -> Path:
    """Build a collision-free staging path using the `injected-` prefix.

    Args:
        staging_dir: Directory staged files are written to.
        title: Article title used for the slug.
        fetched_at: Timestamp used for the date segment.

    Returns:
        A path that does not yet exist.
    """
    base_name = f"injected-{fetched_at.strftime('%Y-%m-%d')}-{slugify(title, max_length=60)}"
    output_path = staging_dir / f"{base_name}.md"

    counter = 2
    while output_path.exists():
        output_path = staging_dir / f"{base_name}-{counter}.md"
        counter += 1

    return output_path


def stage(staging_dir: Path, url: str, article: Article, note: str | None, fetched_at: datetime) -> Path:
    """Write a staged markdown file with frontmatter the wiki agent can triage.

    Args:
        staging_dir: Directory to write into.
        url: Canonical source URL recorded in frontmatter.
        article: Extracted article content.
        note: Optional reason Dean flagged the link.
        fetched_at: Ingestion timestamp.

    Returns:
        Path of the written file.

    Raises:
        StagingError: If the file cannot be written.
    """
    output_path = unique_output_path(staging_dir, article.title, fetched_at)
    source = article.site_name or urlparse(url).netloc.removeprefix("www.")

    frontmatter = [
        "---",
        f"source: {json.dumps(source, ensure_ascii=False)}",
        f"url: {url}",
        "type: url",
        "ingestion_mode: manual-injection",
        f"title: {json.dumps(article.title, ensure_ascii=False)}",
        f"fetched_at: {fetched_at.isoformat()}",
        f"extraction: {article.extraction}",
        f"word_count: {article.word_count}",
    ]
    if article.published_at:
        frontmatter.append(f"published_at: {article.published_at}")
    if note:
        frontmatter.append(f"injected_note: {json.dumps(note, ensure_ascii=False)}")
    frontmatter.extend(["---", ""])

    try:
        output_path.write_text("\n".join(frontmatter) + article.body + "\n", encoding="utf-8")
    except OSError as error:
        logger.exception("Could not write staged file %s", output_path)
        raise StagingError(f"could not write {output_path}: {error}") from error

    return output_path


def process_url(url: str, staging_dir: Path, seen_urls: set[str], args: argparse.Namespace) -> Report:
    """Fetch, validate, and (unless checking only) stage a single URL.

    Args:
        url: Raw URL as supplied by the user.
        staging_dir: Directory staged files are written to.
        seen_urls: Dedup ledger contents.
        args: Parsed command-line options.

    Returns:
        A Report describing the verdict and any staged file.
    """
    normalized = normalize_url(url)
    report = Report(url=normalized, status=Status.OK, reason="")

    if normalized in seen_urls and not args.force:
        report.status = Status.DUPLICATE
        report.reason = "URL is already in .seen_urls.txt"
        report.remediation = REMEDIATION[Status.DUPLICATE]
        return report

    if args.from_file:
        try:
            article = extract_local_file(Path(args.from_file))
        except ExtractionError as error:
            report.status = Status.THIN
            report.reason = str(error)
            report.remediation = REMEDIATION[Status.THIN]
            return report
        report.notes.append(f"Body taken from local file {args.from_file} (network skipped).")
        return _finalize(report, article, normalized, staging_dir, args)

    host = urlparse(normalized).netloc.lower()
    if host in UNSUPPORTED_HOSTS:
        report.status = Status.UNSUPPORTED_TYPE
        report.reason = f"{UNSUPPORTED_HOSTS[host]} URLs have no extractable article body"
        report.remediation = REMEDIATION[Status.UNSUPPORTED_TYPE]
        return report

    candidates, notes = fetch_candidates(normalized)
    report.notes.extend(notes)

    result: FetchResult | None = None
    for candidate in candidates:
        result = fetch(candidate)
        if result.error is None and (result.status_code or 0) < 400:
            break
    if result is None:  # Defensive: fetch_candidates always yields at least one URL.
        report.status = Status.UNREACHABLE
        report.reason = "no fetch candidates produced for this URL"
        report.remediation = REMEDIATION[Status.UNREACHABLE]
        return report

    report.final_url = result.final_url
    if result.final_url != normalized:
        report.notes.append(f"Fetched {result.final_url}")

    article: Article | None = None
    extraction_error: str | None = None
    try:
        if result.content_type == "application/pdf" or result.final_url.lower().endswith(".pdf"):
            article = extract_pdf(result.payload)
        elif result.content_type in {"text/markdown", "text/plain", "text/x-rst"}:
            article = Article(
                title=plain_text_title(result.final_url, result.text),
                body=result.text.strip(),
                site_name="",
                published_at=None,
                extraction="full",
            )
        elif result.text:
            article = extract_html(result.text)
    except ExtractionError as error:
        extraction_error = str(error)

    status, reason = diagnose(result, article, extraction_error, args.min_chars)
    report.status = status
    report.reason = reason

    if status is Status.THIN and args.allow_thin and article is not None:
        report.notes.append(f"Staged despite thin extraction ({len(article.body)} chars) because --allow-thin was set.")
        return _finalize(report, article, normalized, staging_dir, args)

    if status is not Status.OK or article is None:
        report.remediation = REMEDIATION.get(status)
        if article is not None:
            report.title, report.word_count, report.extraction = article.title, article.word_count, article.extraction
        return report

    return _finalize(report, article, normalized, staging_dir, args)


def _finalize(report: Report, article: Article, url: str, staging_dir: Path, args: argparse.Namespace) -> Report:
    """Attach extraction metadata to a report and stage the file unless checking only.

    Args:
        report: Report to complete.
        article: Extracted article content.
        url: Canonical source URL.
        staging_dir: Directory staged files are written to.
        args: Parsed command-line options.

    Returns:
        The completed report.
    """
    if args.title:
        article = Article(args.title, article.body, article.site_name, article.published_at, article.extraction)

    report.status = Status.OK
    report.title = article.title
    report.word_count = article.word_count
    report.extraction = article.extraction
    if not report.reason:
        report.reason = f"extracted {article.word_count} words"

    if args.check:
        report.notes.append("Check-only run: nothing was written to staging.")
        return report

    try:
        staged_path = stage(staging_dir, url, article, args.note, datetime.now(UTC))
    except StagingError as error:
        report.status = Status.STAGING_FAILED
        report.reason = str(error)
        report.remediation = REMEDIATION[Status.STAGING_FAILED]
        return report

    report.staged_path = str(staged_path)
    if not args.no_seen:
        append_seen_url(staging_dir, url)

    logger.info("Staged %s (%s words)", staged_path.name, article.word_count)
    return report


def write_run_summary(staging_dir: Path, reports: list[Report]) -> None:
    """Append this run's counts to the staging `.run-summary` file.

    Args:
        staging_dir: Directory holding `.run-summary`.
        reports: Reports produced by this run.
    """
    staged = sum(1 for report in reports if report.staged_path)
    attention = sum(1 for report in reports if not report.ok)
    summary = f"- **Manual URL**: {staged} staged, {attention} needs attention (injected via the inject-article skill)"
    try:
        with (staging_dir / ".run-summary").open("a", encoding="utf-8") as summary_file:
            summary_file.write(f"{summary}\n")
    except OSError:
        logger.exception("Could not append to %s/.run-summary", staging_dir)
    logger.info("Final summary: %s", summary)


def print_report(reports: list[Report]) -> None:
    """Print a human-readable verdict block for each URL.

    Args:
        reports: Reports produced by this run.
    """
    for report in reports:
        lines = [f"{report.status.upper()}  {report.url}", f"  reason: {report.reason}"]
        if report.title:
            lines.append(f"  title: {report.title}")
        if report.word_count:
            lines.append(f"  words: {report.word_count} (extraction: {report.extraction})")
        if report.staged_path:
            lines.append(f"  staged: {report.staged_path}")
        lines.extend(f"  note: {note}" for note in report.notes)
        if report.remediation:
            lines.append(f"  fix: {report.remediation}")
        logger.info("\n".join(lines))


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Argument list without the program name.

    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        description="Fetch ad-hoc URLs, verify they are extractable, and stage them for wiki triage."
    )
    parser.add_argument("urls", nargs="+", help="One or more article URLs to inject.")
    parser.add_argument("--check", action="store_true", help="Validate reachability and extraction without staging.")
    parser.add_argument("--from-file", help="Use this local HTML/markdown/text file as the body instead of fetching.")
    parser.add_argument("--title", help="Override the extracted title.")
    parser.add_argument("--note", help="Why this link is interesting — recorded as injected_note in frontmatter.")
    parser.add_argument(
        "--min-chars",
        type=int,
        default=DEFAULT_MIN_CHARS,
        help=f"Minimum extracted body length treated as usable (default {DEFAULT_MIN_CHARS}).",
    )
    parser.add_argument("--allow-thin", action="store_true", help="Stage even when extraction is below --min-chars.")
    parser.add_argument("--force", action="store_true", help="Stage even if the URL is already in .seen_urls.txt.")
    parser.add_argument("--no-seen", action="store_true", help="Do not record the URL in .seen_urls.txt.")
    parser.add_argument("--staging-dir", help="Override the staging directory (default: $PRIVATE_REPO_PATH staging).")
    parser.add_argument("--json", action="store_true", help="Emit a machine-readable report on stdout.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the injector over every supplied URL.

    Args:
        argv: Argument list without the program name; defaults to `sys.argv[1:]`.

    Returns:
        0 when every URL is clean, 2 when any URL needs a human decision, 1 on internal failure.
    """
    args = parse_args(sys.argv[1:] if argv is None else argv)

    if args.from_file and len(args.urls) > 1:
        logger.error("--from-file supplies one body, so pass exactly one URL with it")
        return 1

    try:
        staging_dir = resolve_staging_dir(args.staging_dir)
    except StagingError as error:
        logger.error("%s", error)
        return 1

    seen_urls = load_seen_urls(staging_dir)
    reports = [process_url(url, staging_dir, seen_urls, args) for url in args.urls]

    print_report(reports)
    if not args.check:
        write_run_summary(staging_dir, reports)
    if args.json:
        print(json.dumps([report.as_dict() for report in reports], indent=2))

    return 0 if all(report.ok for report in reports) else 2


if __name__ == "__main__":
    sys.exit(main())
