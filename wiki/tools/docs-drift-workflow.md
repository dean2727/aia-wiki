# Docs Drift Detector Workflow

> A periodic workflow that detects and fixes drift between `README`/`AGENTS.md` and the actual code, Makefile targets, and env config.

**Category**: tools
**Last updated**: 2026-05-25
**Status**: reference

## What it is

A workflow (`auto_execution_mode: 2`) run quarterly or whenever major features land, whose single job is keeping documentation aligned with reality. It treats the codebase as the source of truth — `make help` output, `.env.example`, CLI entry points, recent commits — and reconciles `README.md`, `AGENTS.md`, and `docs/*.md` against it, adding missing commands, removing deprecated ones, and documenting new env vars and workflows.

It's the standing-maintenance counterpart to [[phase-completion-workflow]] (which syncs docs at phase boundaries) and shares the same `make docs-test` / `make check` gates.

## Why it matters

Docs that lie are worse than no docs — for humans and for agents reading `AGENTS.md`. Drift accumulates silently during fast [[vibe-coding]] waves. A periodic detector turns "the README is probably stale" into a tracked, fixable diff, and ensures hidden automation (like the other workflows) is actually discoverable by teammates.

## How it works

| Step | Action |
|---|---|
| 1. Gather sources | Collect canonical data: `make help`, `.env.example`, CLI entry points; gather `README`, `AGENTS`, `docs/*.md` |
| 2. Compare targets ↔ docs | Diff `make help` against documented commands; add missing, fix/remove deprecated; verify flags & samples |
| 3. Env/config drift | Reconcile `.env.example` with docs; ensure every var has description + default |
| 4. Feature drift | Review recent commits/CHANGELOG; ensure README covers feature/usage/limits; update `AGENTS.md` gotchas |
| 5. Automation notes | Document new scripts/workflows; ensure workflow files are listed somewhere discoverable |
| 6. Final checks | `make docs-test`, `make check`; log changes in a dated drift-log |

## Dean-Relevance
**Fit score**: 8/10
**Adoption path**: immediate
**Why**: Directly serves his zero-tolerance-for-drift, docs-must-match-reality discipline across Crafted/Praxis repos.
**Analogy**: A linter for prose — it fails the build when the README and the Makefile disagree.
**Suggested next step**: Schedule it as a recurring task (or pre-release gate) so doc drift is caught on a cadence, not discovered.
**Watch for**: If drift is found every run, fold `make help`-vs-docs checks into CI so the gate fails automatically.

## Related
- [[phase-completion-workflow]]
- [[dependency-hygiene-workflow]]
- [[repo-init-workflow]]
- [[project-rules-example]]
- [[vibe-coding]]
