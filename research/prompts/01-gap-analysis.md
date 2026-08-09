# Stage 1 — Gap analysis

Work out what the wiki assumes but never explains. This is the "Delta K" step: rather than asking
what would be interesting to research, you ground yourself in the current page and enumerate what
you *cannot* explain from it alone. That produces a concrete list of backfill targets instead of a
vague sense that the page could be deeper.

## Inputs

- `<run>/wiki-context.md` — the seed page, its neighborhood, and every page the wiki already has.
- The output of `detect_gaps.py --page <seed> --json`, which already found the structural holes:
  concepts linked but never defined, and pages that describe a topic with no dated prior art.

## Task

Read the seed page as if it is the only thing you know about the subject. Ignore what you happen to
know from training — the question is what a reader of *this wiki* could not learn from *these pages*.

Then list every term, mechanism, claim, or design choice the page uses without accounting for. For
each one, quote the sentence that raises it.

Pay particular attention to:

- **Named things treated as given** — a technique, format, or system the page names and moves past.
- **Design choices with no alternative** — a number or shape presented as natural ("256-token blocks",
  "three-stage pipeline") where the interesting question is what it replaced and why.
- **Improvements with no baseline** — "faster", "cheaper", "better" with nothing to compare against.
- **Present-tense-only claims** — statements about how things work now, where the page gives no sense
  of how long they have worked that way or what came before.

## Output contract

Write `<run>/gaps.json`. An array, highest priority first, at most 12 entries:

```json
[
  {
    "term": "D3PM / discrete diffusion",
    "kind": "unexplained_origin",
    "why": "The page says diffusion was borrowed from images but never explains how a continuous noising process was made to work over discrete tokens.",
    "evidence": "Text-diffusion models borrow the recipe from image diffusion instead",
    "priority": "high"
  }
]
```

- `kind` — one of `undefined_term`, `unexplained_origin`, `missing_predecessor`, `unexplained_tradeoff`,
  `undated_claim`.
- `evidence` — a short verbatim quote from the seed page or a neighbor. No quote means no gap.
- `priority` — `high`, `medium`, or `low`. High means a reader is blocked without it.

## Rules

- Check the "Everything the wiki already covers" list before recording a gap. If another page
  explains it, the gap is a missing `[[wikilink]]`, not missing research — note it as `low`.
- A gap must be answerable from public sources. "Is this a good idea?" is an opinion, not a gap.
- Prefer gaps that sit *behind* the topic in time. This run exists to explain what led up to the
  page, not to extend it forward.
- Do not perform any web searches in this stage. You are auditing the wiki, not the world.
