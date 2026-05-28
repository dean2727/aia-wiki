# Starting a Project with Vibe Coding

> Dean's end-to-end recipe for spinning up a new project the vibe-coding way: plan hard, scaffold from a template, then ship in logged waves with tests and workflows codified as they emerge.

**Category**: topics
**Last updated**: 2026-05-25
**Status**: reference

## What it is

A staged kickoff procedure that turns [[vibe-coding]] from undisciplined code-blasting into a repeatable project lifecycle. The core move is front-loading a strong plan and a clean repo scaffold, then doing the actual building in named "waves" — each with its own branch, written plan, and post-wave test pass. Decisions and conventions get written into `AGENTS.md` / `WORKFLOWS.md` / `RULES.md` the moment they're made, so the agent's operating context compounds instead of drifting.

The pre-code phase uses a frontier chat model (Grok, Gemini) — not the coding agent — to map the business problem, MVP scope, data domain, and stack. Scaffolding favors a known-good template (e.g. full-stack-fastapi-template, cookiecutter), a monorepo with docker-compose and code-mounted auto-reload, and per-part `AGENTS.md` files (frontend, backend) plus matching Makefiles. Parallel work runs on [[worktrees-parallel-agents]] so agents don't collide.

## Why it matters

This is the connective tissue between "I have an idea" and a maintainable codebase. The wave structure is what stops vibe coding from silently rotting main flows: progress is prioritized over tests *within* a wave, but no wave merges without green smoke tests. Plans-as-source-of-truth and continuously-refined workflows mean the project gets *easier* to extend over time rather than accruing hidden debt.

## How it works

| Stage | Goal | Key actions |
|---|---|---|
| 1. Kickoff | Plan + scaffold | Use Grok/Gemini for problem/domain/stack framing; start from a template; monorepo + docker-compose + auto-reload; init per-part `AGENTS.md`; write a Product + Tech Plan, have the model refine it into `AGENTS.md` + `WORKFLOWS.md` |
| 2. Waves (logged) | Ship fast, leave a trail | Each wave = named goal + branch + short `PLAN.md`; let AI blast code; summarize decisions back into the plan file after each wave |
| 3. Tests per wave | Lock in what was built | At wave end, model proposes unit + integration tests; curate, run, fix; capture recurring failures into `tests/`, `fix-tests.md`, `evals/` |
| 4. Codify workflows | Compound the conventions | Every "do it like this" goes straight into `AGENTS.md`/`WORKFLOWS.md`/`RULES.md`; periodically have the model re-read the repo and propose refined workflows |
| 5. Guardrails | Protect future speed | Minimal CI: lint/format + key integration tests + smoke test; rule: no merging waves without green smoke tests |

## Dean-Relevance

**Adoption path**: immediate
**Why**: This is the literal kickoff procedure for Praxis-style projects on his exact stack (Next.js + FastAPI + Supabase, uv, docker-compose).
**Analogy**: Waves are git-flow for the AI era — each one a sprint with a plan in, tests out, and a merge gate.
**Suggested next step**: Template a reusable `PLAN.md` + per-part `AGENTS.md` starter so wave 1 of the next project is a copy-paste.
**Watch for**: A coding agent shipping first-class native "wave" / multi-plan orchestration would turn this hand-rolled recipe into a built-in mode.

## Related
- [[vibe-coding]]
- [[spec-driven-development]]
- [[worktrees-parallel-agents]]
- [[skills-rules-subagents]]
- [[repo-init-workflow]]
- [[project-rules-example]]
