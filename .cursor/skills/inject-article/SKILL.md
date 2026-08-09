---
name: inject-article
description: Use when Dean drops a link he wants in the wiki — an article, blog post, paper, release notes, or repo — with phrasings like "inject this", "add this to the wiki", "process this link", "this looks interesting", or just a bare URL. Verifies the page can be reached and parsed, reports exactly what is blocking extraction and how to fix it, then runs nightly-equivalent triage and wiki synthesis on the material.
---

# Inject an article into the wiki

Dean hands over one or more URLs. You prove the material is actually extractable **before** writing
anything, then process it with the same rules the nightly job uses.

Run the phases in order. Never skip Phase 1, and never write a wiki page from a URL, a title, or your
own memory of a topic — only from text this pipeline actually extracted.

## Phase 1 — Validate reachability and extraction

Check first, stage second. `--check` writes nothing:

```bash
uv run python pipeline/scripts/ingest_url.py --check <url> [<url> ...]
```

Add `--json` when you want to branch on the result programmatically. The script needs the private repo
for staging paths; if it errors about a missing staging directory, set `PRIVATE_REPO_PATH` to the
`dean-wiki-private` checkout (it defaults to `../dean-wiki-private`).

Per-URL verdicts: `ok`, `thin`, `js_required`, `paywalled`, `blocked`, `not_found`, `rate_limited`,
`server_error`, `unreachable`, `unsupported_type`, `needs_pdf_tool`, `duplicate`, `staging_failed`.
Exit code is `0` when every URL is `ok`, `2` when any needs a decision, `1` on an internal failure.

The script already handles these rewrites, so don't pre-transform URLs yourself: arXiv `abs`/`pdf`
links go to `export.arxiv.org`, GitHub repo roots read the README from `raw.githubusercontent.com`,
PDFs go through `pdftotext`, and tracking parameters are stripped.

## Phase 2 — If it isn't `ok`, report and offer fixes

Tell Dean what happened in plain language and offer the concrete fixes for that verdict, then **stop
and wait**. Do not stage, and do not synthesize from a thin body.

| Verdict | What to tell Dean | What to offer |
|---|---|---|
| `thin` | Page was reachable but yielded almost no text | Stage anyway with `--allow-thin`; or he pastes the text and you use `--from-file`; or lower `--min-chars` if the piece really is short |
| `js_required` | Body is client-rendered or behind a bot challenge | He pastes the article into a file for `--from-file`; or supply a plain-text equivalent (docs `.md`, GitHub raw, RSS entry) |
| `paywalled` | Short body plus paywall or sign-in markers | `--from-file` with the text he can see; or an archive/AMP mirror URL |
| `blocked` | Host refused the request (401/403/451) | Try a first-party mirror, then an archive capture of the publisher's own page saved as `.html` for `--from-file`; else he pastes it |
| `not_found` | Link is 404/410 | Confirm the URL, or find the canonical or archived copy |
| `rate_limited` / `server_error` | Host is throttling or down | Retry shortly; or `--from-file` |
| `unreachable` | DNS/TLS/timeout, or restricted network egress | Confirm the URL; if egress is the problem, `--from-file` is the reliable path |
| `unsupported_type` | YouTube, X/Twitter, LinkedIn, or a binary payload | He supplies the transcript or thread text for `--from-file` |
| `needs_pdf_tool` | PDF, and `pdftotext` is missing | Install poppler (`brew install poppler` / `apt-get install poppler-utils`), then re-run |
| `duplicate` | Already ingested (in `.seen_urls.txt`) | Check whether a wiki page already covers it and offer to update that page instead; `--force` to stage a second copy |

Deeper per-host recipes are in [references/fetch-failures.md](references/fetch-failures.md) — read it when
a verdict is `js_required`, `paywalled`, `blocked`, or `unsupported_type` and the table above isn't enough.

Once Dean picks a fix, re-run Phase 1 with the extra flags until the verdict is `ok`.

## Phase 3 — Stage

Same command without `--check`. Record why Dean flagged it — `--note` lands in frontmatter and feeds
both triage and the relevance entry:

```bash
uv run python pipeline/scripts/ingest_url.py --note "why Dean flagged it" <url>
```

This writes `injected-YYYY-MM-DD-<title-slug>.md` into `private/sources/staging/` with
`type: url` and `ingestion_mode: manual-injection`, appends the URL to `.seen_urls.txt` so a later
nightly RSS run won't re-ingest it, and appends a `- **Manual URL**:` line to `.run-summary`.

## Phase 4 — Process it like a nightly run

Follow `CLAUDE.md` exactly, with the one deviation below. In order:

1. Read `private/profile/dean.md` in full.
2. Read the staged file you just wrote.
3. Search `wiki/` for pages already covering this topic (`Glob` on slugs, `Grep` on key terms) and read
   any that match. **Prefer updating an existing page over creating a new one.**
4. Score it 1–10 against the signal threshold, and say the score out loud in your reply.
   - **Deviation from nightly triage**: Dean chose this link deliberately, so the write floor is **6**,
     not 7. Below 6, don't write — report the score and your reasoning and ask whether he wants it anyway.
5. Write or update the page, honoring the placement rules: `engineering-approaches/` only for genuinely
   AI-native workflows or innovative engineering stories, `tools/` only for software tool evaluations,
   `algorithms/` for research-origin findings, `models/` for architectures and releases, `world/` for
   product, culture, and society. No Dean-Relevance section in a public page.

## Phase 4b — Update the timeline

A page write is not finished until its `## Timeline` reflects it, and injection runs are explicitly
covered by that rule. Never hand-write or hand-sort the section:

```bash
uv run python research/scripts/merge_timeline.py <page> \
  --event '2026-07|release|Actor shipped the thing — what became possible.|https://source.url' \
  --event '2026-08|wiki|Page created from the <source> post.'
```

- Month-stamp events from the **source's publication date**, not today's. Check it against the body and
  the feed: extracted `published_at` frontmatter is sometimes wrong.
- Never introduce a date the source does not contain.
- One `wiki` event per page per run, and only when the update materially changed what the page says.
- After merging, regenerate the wiki-wide slider: `uv run python research/scripts/build_global_timeline.py`.
- Sanity-check links with `uv run python research/scripts/wiki_graph.py` — dangling targets should be 0.

## Phase 5 — Bookkeeping

- **Private relevance** (unlike the CI nightly, local runs do this): add or update the page's section in
  `private/relevance/<season>-<year>.md` for the current quarter — spring (Mar–May), summer (Jun–Aug),
  fall (Sep–Nov), winter (Dec–Feb, named for the December year). Create the file if this is the
  quarter's first page.
- **CHANGELOG.md**: append a new entry titled `## [YYYY-MM-DD] Manual Injection` — created/updated pages
  with scores, plus the source URL. Append only; never rewrite history.
- **README.md**: update the `Manual injection` row in the Source coverage table (staged count, coverage
  window `manual`, last wiki-processed date, one-line outcome) and the `_Last table update_` line.
- **INDEX.md**: leave it alone. It regenerates on the weekly run.

## Phase 6 — Commit

Commit the public repo atomically (wiki page, `CHANGELOG.md`, `README.md`) and push to `main`.
**Never commit anything under `private/`** — it is a separate data-only repo. Mention the relevance
file you touched so Dean can commit it there himself.

## Gotchas

- A `duplicate` verdict usually means the nightly run already saw this URL. Check the wiki and the
  changelog before assuming the topic is missing.
- `--from-file` bypasses the network entirely, so the frontmatter still records the original `url`
  while the body comes from Dean's paste. That's the intended escape hatch, not a fallback to guessing.
- Several links at once are fine: pass them in one command and triage each separately. `--from-file`
  supplies one body, so it takes exactly one URL.
- If Dean adds context about *why* the link matters, put it in `--note`. It is the strongest input to the
  relevance assessment, and it's lost if you don't capture it.
