# Stage 2 — Perspectives

Pick the handful of angles the research will be conducted from. A single query against a topic
returns the topic's own marketing. Several deliberately different angles, each asking its own
follow-up questions, surface the material that actually explains how the field got here.

Three or four perspectives is the working range. Fewer and the research collapses into one thread;
more and you pay for overlap — the cost of a research run scales with the number of independent
search threads, and past a point the extra threads return the same sources.

## Inputs

- `<run>/gaps.json` from stage 1.
- `<run>/wiki-context.md`, for what is already covered and must not be re-researched.

## Task

Design perspectives that between them can answer the high-priority gaps. Adapt them to the topic
rather than reaching for a template, but for a backfill these four angles are usually the right
shape:

| Angle | What it goes after |
|---|---|
| Technical lineage | Where the mechanism came from, which branch of it survived, and what each step fixed |
| Problem and prior art | What people did before this existed, and why that stopped being good enough |
| Scaling and evidence | When the approach first became credible, on what result, and who verified it |
| Deployment reality | What it costs, where it wins, and where the advertised win does not materialize |

Drop any angle that cannot produce **dated, sourced facts** for this topic — the next stages need a
chronology, and a perspective that only yields opinion is wasted budget.

## Output contract

Write `<run>/perspectives.json`. An array of 3–4 entries:

```json
[
  {
    "name": "Technical lineage",
    "slug": "technical-lineage",
    "focus": "Where the mechanism came from and which branch of it survived",
    "gaps": ["D3PM / discrete diffusion"],
    "seed_questions": [
      "What was the earliest published version of this mechanism, and in what field?",
      "What made it unusable for this domain, and who fixed that?",
      "Which competing formulations existed, and why did one win?"
    ],
    "search_budget": 6
  }
]
```

- `slug` — lowercase and hyphenated; it becomes the findings file name.
- `gaps` — which entries from `gaps.json` this perspective is responsible for. Every high-priority
  gap must be claimed by exactly one perspective.
- `seed_questions` — 3–5 opening questions. These are a starting point, not the full interview;
  stage 3 generates follow-ups from what the sources actually say.
- `search_budget` — searches this perspective may spend. See
  [`../../.cursor/skills/deep-research/references/research-depth.md`](../../.cursor/skills/deep-research/references/research-depth.md).

## Rules

- Perspectives must be genuinely non-overlapping. If two would search the same terms, merge them
  and spend the budget on a third angle.
- At least one perspective must look strictly *backward* — the era before the topic had a name.
- Name the perspective by what it investigates, not by a persona. "Deployment reality" is useful;
  "a skeptical engineer" is set dressing.
