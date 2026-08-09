# Choosing depth, and what it costs

Read this at Phase 0, before writing `perspectives.json`. Depth is the only real cost lever in this
pipeline, and the default should be lower than instinct suggests.

## The cost shape

Token volume is what a research run spends, and it is also most of what explains whether the run was
any good — the number of searches and the amount of material actually read matters more than clever
orchestration. Two consequences follow, and they pull in opposite directions:

- Under-searching cannot be recovered by better prompting. A thin run produces a confident narrative
  over four sources, which is worse than no run.
- Fanning out to many parallel researchers multiplies token spend fast. A multi-agent research system
  can burn on the order of fifteen times the tokens of an ordinary conversation, and most of the
  extra threads return sources the first threads already found.

The resolution is not "use fewer agents" or "use more". It is: **fan out only across questions that
are genuinely independent.** Two perspectives that would search the same terms are one perspective
with a doubled bill.

## Presets

| Depth | Perspectives | Searches each | Use when |
|---|---|---|---|
| `quick` | 2 | 4 | The gap is one undefined term, or you are testing the pipeline |
| `standard` | 3 | 6 | Default. A page with shallow history and two or three real gaps |
| `deep` | 4 | 8–10 | A foundational topic several pages lean on, or a field with a genuinely contested history |

Set `search_budget` per perspective in `perspectives.json`. Budgets are ceilings, not quotas: hand
back what you do not need. Two rounds returning the same sources means the perspective is exhausted,
and spending the rest of the budget only adds noise to the event extraction.

## Parallel or sequential

Run perspectives **in parallel subagents** at `standard` and `deep`. They are independent by
construction — each owns its own gaps and its own findings file — so there is nothing to coordinate
and the wall-clock saving is real.

Run **sequentially in the main context** at `quick`, or whenever the topic is narrow enough that the
second perspective's questions genuinely depend on what the first one found. Fan-out pays for itself
when a question decomposes into independent threads; when the threads have to talk to each other, one
well-equipped researcher is both cheaper and better.

## Scoping upward mid-run

If Phase 3 finds that the topic's history is deeper or more contested than the gap analysis
suggested, add one perspective rather than raising every budget. A new angle finds new sources; a
bigger budget on an exhausted angle finds the same ones again.

If Phase 4 comes back `sparse_timeline`, that is almost always a scoping failure, not a search
failure — the perspectives all pointed at the present. Add a perspective aimed strictly at prior art
and re-run it alone.
