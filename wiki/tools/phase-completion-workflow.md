# Phase Completion Workflow

> A fully-automated `/complete-phase` workflow that wraps up a development phase across any repo: roadmap update, docs sync, quality gates, and commit — no mid-run prompts.

**Category**: tools
**Last updated**: 2026-05-25
**Status**: reference

## What it is

A slash-command-style workflow (`auto_execution_mode: 3` — runs end-to-end without asking) for closing out a wave/phase consistently. It parses the phase name from the invocation, flips its status to ✅/COMPLETED in the roadmap, updates `README.md` and `AGENTS.md` with new capabilities and lessons, runs the quality gates, stages everything, and commits with a structured message. It exists to make "finishing" a phase a deterministic action rather than a set of things you hope you remembered.

It's the natural closer for a wave in [[starting-a-project-vibe-coding]], and it leans on the same `make check` / `make test` gates as [[fix-tests-workflow]].

## Why it matters

The expensive failure mode in [[vibe-coding]] is documentation and roadmap drift — code moves, the plan-of-record doesn't. Automating the wrap-up keeps the roadmap test-verifiable and the docs honest at the exact moment they're most likely to rot. One command means it actually happens every time.

## How it works

| Step | Action |
|---|---|
| 1. Identify phase | Parse phase name/alias from the invoking command; map shorthand to official roadmap name |
| 2. Update roadmap | Flip status 🔄/PENDING → ✅/COMPLETED with a one-line summary; tick checklist items |
| 3. Update docs | `README.md` (new commands/capabilities), `AGENTS.md` (lessons/constraints), repo-specific notes |
| 4. Verify gates | Run `make check`, `make test`, `make docs-test`; fix before proceeding; capture metrics |
| 5. Stage | `git add -A` |
| 6. Commit message | Structured `feat: Complete [Phase] – [descriptor]` with key outcomes |
| 7. Commit & report | Commit; output phase name, accomplishments, follow-up TODOs |

Execution rule: no prompts mid-run; stop only on blocking errors.

## Dean-Relevance
**Fit score**: 9/10
**Adoption path**: immediate
**Why**: It's the automated end-of-wave ritual that fits his plans-as-source-of-truth, hooks-over-manual-steps discipline exactly.
**Analogy**: A CI job you run by hand at the finish line — it stamps the phase done and refuses to lie about it.
**Suggested next step**: Wire this as a `/complete-phase` command (or commit hook) in Crafted/Praxis so roadmap + docs update atomically with each merge.
**Watch for**: Coverage or doc-build gates failing here regularly would mean promoting [[coverage-booster-workflow]] / [[docs-drift-workflow]] to run automatically as part of it.

## Related
- [[starting-a-project-vibe-coding]]
- [[fix-tests-workflow]]
- [[docs-drift-workflow]]
- [[spec-driven-development]]
- [[vibe-coding]]
