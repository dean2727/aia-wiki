# Stage 3 — Perspective interview

Run one perspective as a multi-round interview against the sources. Round one asks the seed
questions. Every round after that asks questions *generated from what the previous round returned* —
this is the mechanic that separates research from search. A fixed list of queries finds what you
already suspected; follow-up questions find what you did not know to ask.

Run perspectives in parallel, one subagent per perspective, each writing only its own findings file.

## Inputs

- One entry from `<run>/perspectives.json`.
- `<run>/wiki-context.md`, so you never research something the wiki already covers.

## Task

1. **Round 1** — search on the perspective's seed questions. Read the results properly; skim only to
   decide whether to read.
2. **Follow up** — from what you just read, write the next questions. Good follow-ups chase a name
   you had not heard, a claim with no evidence behind it, a date that does not fit, or a "this
   replaced X" where X is unfamiliar.
3. **Repeat** until the search budget is spent or rounds stop producing new material. Two rounds
   returning the same sources means you are done; hand the budget back rather than padding.
4. **Record contradictions rather than resolving them.** If two sources disagree on a date or on who
   was first, write both down with both URLs. The synthesis stage decides.

## Output contract

Write `<run>/findings/<perspective-slug>.md`:

```markdown
# <Perspective name>

## Round 1 — <the question you asked>

<What the sources say, in prose. Every claim carries the URL that supports it inline.>

### Dated facts

- 2021-07 — Austin et al. publish D3PM, redefining the corruption process over discrete state
  spaces. https://arxiv.org/abs/2107.03006
- 2022-05 — Diffusion-LM takes the opposite approach, running diffusion over continuous word
  embeddings. https://arxiv.org/abs/2205.14217

### Still unknown

- Whether the discrete branch won on quality or on engineering convenience — no source says directly.

## Round 2 — <the follow-up question, and one line on what prompted it>

…
```

The `### Dated facts` blocks are the input to stage 4, so keep them mechanical: one fact per bullet,
the date first, the URL last.

## Rules

- **Primary sources only.** The paper, the repo, the release notes, the first-party blog. A summary
  of a paper is not the paper. If only summaries exist, say so and mark the claim uncertain.
- **Cite the earliest source that supports a claim.** This is a backfill; a 2026 retrospective saying
  "since 2021" is weaker than the 2021 paper.
- **Never cite the wiki back to itself.** Pages in `wiki-context.md` are what you are trying to
  supplement, so they cannot be evidence.
- **Do not invent precision.** If a source says "in 2022", write `2022`, not `2022-01`.
- Every claim needs a URL next to it. A claim you cannot source belongs under `### Still unknown`.
- Stay inside your perspective. If you find excellent material belonging to another perspective,
  note it in one line and move on — the other subagent is already on it.
