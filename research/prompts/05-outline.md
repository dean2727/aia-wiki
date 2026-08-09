# Stage 5 — Outline

Decide the shape of the story before writing a word of it. Draft the outline twice: once from what
you believed going in, then again against the evidence. The gap between the two drafts is usually
where the interesting part of the history is, and writing it down stops you from narrating your
priors and citing the timeline as decoration.

## Inputs

- `<run>/timeline.md` — the sorted, sourced events.
- `<run>/findings/*.md` — the reasoning and the contradictions behind them.
- `<run>/gaps.json` — what this run has to answer.

## Task

1. **Draft from priors.** Before re-reading the timeline, sketch how you would have told this story
   from your own knowledge: the eras, the turning points, who mattered.
2. **Draft from evidence.** Now build the real outline from `timeline.md`. Group events into eras
   defined by *what became possible*, not by decade or by paper count. An era ends when a limitation
   is removed.
3. **Record the difference.** Where the evidence contradicted the first draft, say so in one line
   each. This becomes the most valuable part of the report for a reader who shares your priors.

## Output contract

Write `<run>/outline.md`:

```markdown
# Outline — <topic>

## Thesis

<One sentence. The claim the whole narrative supports. Not a summary — a claim.>

## Where my priors were wrong

- I expected the continuous-embedding branch to be the mainline; the evidence says the discrete
  masking branch is what scaled.

## Sections

### 1. <Era name> — <the limitation that defined it>
- Covers: events #1–#3
- Point: <what a reader takes away>
- Ends when: <the event that closed the era>

### 2. …

## Deliberately out of scope

- <Thing a reader might expect that this report will not cover, and why.>
```

## Rules

- **Maximum six sections.** A backfill with ten sections is a literature review, and Dean will not
  read it.
- **Every section names the events it covers.** A section with no events behind it is a section you
  are about to write from memory — cut it or go find the evidence.
- **Sections are turning points, not papers.** "D3PM" is not a section. "Making diffusion work on
  discrete tokens" is.
- **Every high-priority gap from `gaps.json` must land in some section.** If one does not, either the
  research missed it (go back to stage 3) or it was the wrong gap (say so under out of scope).
- The thesis has to be falsifiable by the timeline. "This field has advanced a lot" is not a thesis.
