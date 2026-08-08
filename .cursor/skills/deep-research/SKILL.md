---
name: deep-research
description: Use when Dean wants the background behind something already in the wiki — phrasings like "backfill this topic", "research the history of X", "what led up to this", "where did this come from", "give me the background on this page", or when a freshly injected article leaves a page describing a new thing with no sense of what came before it. Researches backward in time across several perspectives, builds a sourced timeline of the major improvements, and stages a report for a later wiki run to ingest.
---

# Backfill the background behind a wiki topic

A page arrives from an injected link or a nightly run and describes what something *is*. What it
almost never carries is how the field got there — the prior art, the limitation each step removed,
and why the current design looks the way it does. This skill produces that, as a staged report.

**This skill does not write to the wiki.** It ends by staging a `type: research` report in the
private staging directory. A separate run triages and synthesizes it, exactly like any other staged
source. Keeping research and ingestion apart is deliberate: the report is evidence, and the wiki run
decides what the wiki should say about it.

Run the phases in order. The scripts are deterministic plumbing and make no LLM calls; the prompts in
`research/prompts/` are where your judgement goes. Read each prompt before running its phase.

## Phase 0 — Scope the run

Find the structural holes before deciding anything:

```bash
python research/scripts/detect_gaps.py --page <slug-or-path> --json
```

Read the `SHALLOW HISTORY` and `DANGLING LINK` sections. A seed page that names one year is the
strongest possible signal that a backfill is worth doing. Then scaffold the run:

```bash
python research/scripts/start_run.py --seed-page <slug-or-path>
```

This writes `research/runs/<YYYY-MM-DD>-<slug>/` containing `run.json` and `wiki-context.md` — the
seed page, its link neighborhood, and a one-line definition of every page the wiki already has. That
brief is what keeps the report from restating pages Dean already owns.

Pass `--topic` instead when the subject has no page yet. Exit code `2` means the run already exists;
`--force` regenerates its context against the current wiki.

Before going further, pick a depth. See
[references/research-depth.md](references/research-depth.md) — the choice sets your search budget and
whether perspectives run in parallel, and it is the main cost lever in the whole pipeline.

## Phase 1 — Gap analysis

Follow [`research/prompts/01-gap-analysis.md`](../../../research/prompts/01-gap-analysis.md) and write
`gaps.json`. No web searches in this phase: you are auditing what the wiki cannot explain, grounded
in quotes from the page itself.

If the honest answer is that the page already explains its own background, say so and stop. A run
that produces nothing is a good outcome and costs almost nothing.

## Phase 2 — Perspectives

Follow [`research/prompts/02-perspectives.md`](../../../research/prompts/02-perspectives.md) and write
`perspectives.json` — three or four non-overlapping angles, each claiming specific gaps and carrying
its own search budget. At least one must look strictly backward, at the era before the topic had a
name.

## Phase 3 — Interviews

Follow [`research/prompts/03-perspective-interview.md`](../../../research/prompts/03-perspective-interview.md).

Launch one subagent per perspective, in parallel, in a single message. Give each subagent the
prompt file, its own entry from `perspectives.json`, the path to `wiki-context.md`, its search
budget, and the exact findings file it owns — subagents must not write outside
`findings/<slug>.md`, or they will overwrite each other.

Each perspective is a multi-round interview, not a query list: round one asks the seed questions,
every round after that asks what the last round's sources made askable.

## Phase 4 — Events and timeline

Follow [`research/prompts/04-event-extraction.md`](../../../research/prompts/04-event-extraction.md) to
write `events.jsonl`, then:

```bash
python research/scripts/build_timeline.py research/runs/<run-id>
```

Exit `2` is a decision, not a failure — the verdict names what to fix. Read the `merged:` lines
before moving on; a wrong merge silently drops an event.

## Phase 5 — Outline

Follow [`research/prompts/05-outline.md`](../../../research/prompts/05-outline.md) and write
`outline.md`. Draft it from your priors first, then against the timeline, and record where the two
disagreed.

## Phase 6 — Narrative

Follow [`research/prompts/06-narrative-synthesis.md`](../../../research/prompts/06-narrative-synthesis.md)
and write `narrative.md`. Every year in the prose must exist in `timeline.md`; the compiler enforces
it, and that check is the single best protection against a confidently wrong history.

## Phase 7 — Compile and stage

```bash
python research/scripts/compile_report.py research/runs/<run-id> --stage
```

This assembles `report.md`, validates it, and writes
`private/sources/staging/research-YYYY-MM-DD-<slug>.md` with `type: research` and
`ingestion_mode: deep-research-backfill`, then appends a `- **Deep research**:` line to
`.run-summary`. `PRIVATE_REPO_PATH` defaults to `../dean-wiki-private`.

| Verdict | What it means | What to do |
|---|---|---|
| `missing_artifact` | A phase has not run | Finish it; the message names the file |
| `empty_timeline` | No events survived | Re-run phase 4 |
| `thin_narrative` | Under the word floor | Either the research was thin — say so — or phase 6 under-wrote |
| `unanchored_dates` | A year in the prose has no event behind it | Add the event with its source and rebuild, or cut the claim |
| `few_sources` | Too narrow to stand on | Run another perspective |

`--check` validates without writing. Reach for `--allow-unanchored` only when the year is genuinely
incidental, like a version number or a quotation.

## Phase 8 — Hand off

Tell Dean, in plain language: the topic, how far back the timeline reaches, how many events and
sources stand behind it, the one or two things the research changed your mind about, and the path of
the staged file. Then tell him it is queued — the next wiki run will triage and synthesize it.

Nothing here gets committed to this repo. Run artifacts live in `research/runs/`, which is
gitignored, and the report goes to the private repo. **Never commit anything under `private/`.**

## When not to use this

- **The topic is a week old.** There is no background to find yet. Wait.
- **The page already has a `## Sources` list and names several years.** `detect_gaps.py` will tell
  you; believe it.
- **Dean handed you a link.** That is the `inject-article` skill. Use this one afterward, if the page
  that lands turns out to have no past.

## Gotchas

- The wiki is its own encyclopedia, so `wiki-context.md` replaces the step where a general research
  system would pull related Wikipedia articles for structure. Read it before searching, not after.
- Perspectives that overlap cost real money and return the same sources twice. Merging two weak
  angles into one strong one is almost always the right call.
- `build_timeline.py` and `compile_report.py` both exit `2` for "needs a decision" and `1` only for
  internal failure. Do not treat `2` as a crash.
- Findings files are the audit trail. If the narrative says something the findings do not, the
  narrative is wrong.
