# Fetch failure recipes

Read this when `ingest_url.py --check` returns `js_required`, `paywalled`, `blocked`, or
`unsupported_type` and the table in `SKILL.md` isn't enough to unblock Dean.

The goal is always the same: get real text into the pipeline. Every recipe ends either with a URL that
extracts cleanly, or with a local file passed via `--from-file`. Nothing here justifies writing a wiki
page from a headline.

## The universal fallback: `--from-file`

Ask Dean to open the page, select the article, and save it. Then:

```bash
uv run python pipeline/scripts/ingest_url.py --from-file ~/Downloads/article.md \
  --title "Exact Article Title" --note "why it matters" https://original.example.com/post
```

- `.md` / `.txt` are used verbatim; a leading `# Heading` becomes the title.
- `.html` (browser "Save Page As", or DevTools → Copy outer HTML) goes through the same extractor as a
  live fetch, which is usually cleaner than a hand-pasted selection.
- The original URL still goes into frontmatter, so provenance and dedup stay correct.
- Always pass `--title` when the file has no heading, otherwise the title comes from the file name.

## Per-host recipes

| Host | Symptom | Try this |
|---|---|---|
| Substack | `js_required` or thin | The web archive of the post, or the feed entry (`<newsletter>.substack.com/feed`); the nightly RSS ingest may already carry it |
| Medium | `paywalled` | Ask for the friend link (`?sk=` token); it renders the full body server-side |
| X / Twitter, LinkedIn | `unsupported_type` | Ask Dean to paste the thread text; there is no extractable article body and no API access here |
| YouTube | `unsupported_type` | Ask for the transcript (video → Show transcript → copy), save as `.txt`, then `--from-file`. Note the video URL as the source |
| arXiv | thin abstract only | The abstract alone is often enough for triage. For the full paper, pass the `/pdf/` URL once `pdftotext` is installed, or use the HTML version (`arxiv.org/html/<id>`) when it exists |
| GitHub | want more than the README | Point at a specific raw file (`raw.githubusercontent.com/<owner>/<repo>/HEAD/docs/design.md`) rather than the repo root |
| Docs sites (Mintlify, Docusaurus, GitBook) | `js_required` | Many serve a markdown twin: append `.md` to the page URL, or try `/llms.txt` and `/llms-full.txt` at the site root |
| Cloudflare-protected blogs | `blocked` with a challenge page | No programmatic path from here. Use `--from-file` |
| News sites with AMP | `paywalled` | Try the AMP variant (`/amp/`, `?outputType=amp`) — it is frequently server-rendered and ungated |

## Reading the verdict correctly

- **`thin` on a page that genuinely is short** (a release note, a changelog entry, a short announcement)
  is not a failure. Confirm the body is complete, then stage with `--allow-thin` or lower `--min-chars`.
  Say which one you did, because a short body means less to synthesize from.
- **`thin` with boilerplate in the body** (cookie notice, nav labels, "Read more") means the extractor
  picked the wrong container. Go to `--from-file` rather than tuning the threshold.
- **`ok` is about volume, not quality.** Read the staged body before triaging. If it is mostly navigation
  text or a link index, treat it as unwriteable and say so — the same call the nightly run makes for
  headline-only stubs.
- **`unreachable` for every URL at once** usually means network egress is restricted in the current
  environment, not that the sites are down. Say that plainly instead of reporting each link as broken.

## What never to do

- Do not fill gaps from memory or from a web search when extraction fails. The wiki records what the
  source said; a page built from recall is exactly the hallucination risk `CLAUDE.md` forbids.
- Do not stage a body you know is truncated without flagging it. If only part of the article came
  through, say which part, and mark uncertain claims `[Needs Verification]` on the resulting page.
