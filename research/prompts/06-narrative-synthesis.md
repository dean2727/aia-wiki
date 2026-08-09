# Stage 6 — Narrative synthesis

Write the background the seed page assumes. The reader already knows what the topic is — they read
the wiki page. What they are missing is how it got here: what people did before, what each step
fixed, and why the current design looks the way it does.

## Inputs

- `<run>/outline.md` — the shape and the thesis.
- `<run>/timeline.md` — the only source of dates.
- `<run>/findings/*.md` — the detail and the disagreements.
- `<run>/wiki-context.md` — what not to repeat.

## Task

Write `<run>/narrative.md`, following the outline's sections. 800–1600 words.

```markdown
# <Title — the story, not the topic>

> <One sentence. The thesis from the outline, sharpened.>

## <Section from the outline>

<Prose.>

## What is still unsettled

<The open questions, the contradictions the sources did not resolve, and what would settle them.>
```

The report gets triaged and synthesized into the wiki by a later run, so it is a source document,
not a wiki page. Do not add a metadata block, a category, or a status line — `compile_report.py`
writes those.

## The one hard rule

**Every year in your prose must appear in `timeline.md`.** `compile_report.py` checks this and will
reject the report otherwise. If you need a year the timeline does not have, go add the event with its
source and rebuild the timeline. This is not a formality: an unanchored date is the most common way a
research report turns out to be confidently wrong.

## Rules

- **Explain each step as a limitation removed.** "X came next" is a list. "X existed but could not do
  Y, which is what Z fixed" is a history, and it is the thing this whole feature exists to produce.
- **Do not restate the seed page.** Assume the reader just read it. Where the background finally
  connects to the present, say so in a sentence and stop.
- **Link, do not duplicate.** When you touch a topic the wiki already covers, use `[[its-slug]]`.
  The compiler reads those links to suggest which pages the ingest run should update.
- **Keep the disagreements.** Where two sources conflicted, say both and say which one you trust and
  why. A clean story that hides a real dispute is worse than a messy one.
- **No relevance section, no advice to Dean, no "in conclusion".** Personal framing belongs in the
  private quarterly relevance file, written during ingestion, not here.
- Cite inline with bare URLs where a claim is load-bearing or surprising. The compiler collects every
  URL into the report's source list either way.

## Then compile

```bash
python research/scripts/compile_report.py research/runs/<run-id> --stage
```

Exit `2` means it needs a decision: `thin_narrative` (under-written), `unanchored_dates` (a year with
no event behind it), or `few_sources` (the research was too narrow to stand on). Fix the cause rather
than reaching for the override flag.
