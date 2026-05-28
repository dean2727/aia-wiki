# Spec-Driven Development

> Working from explicit specs and a project "constitution" so both you and the AI have a clear definition of done before any code is written.

**Category**: topics
**Last updated**: 2026-05-25
**Status**: baseline

## What it is

SDD is the discipline of writing a specification before implementation — so there's a clear done-signal, a correctness reference, and recoverable context — and of governing the project with a persistent "constitution" (CLAUDE.md / AGENTS.md) read at the start of every session. It's the structured antidote to [[vibe-coding]]: plan-first, phase-based, context-aware.

Skip it for trivial changes (renaming a button). Use it when work spans sessions, needs approach clarity, will be maintained, or has complex edge cases.

## Why it matters

Without a spec: vague requirements, no validation reference, costly iteration cycles, cross-session inconsistency, undefined edge cases. A spec front-loads the thinking and makes it durable across sessions and agents — which is exactly where long AI-assisted projects rot. It also enables parallel development (see [[worktrees-parallel-agents]]) and consistent integration.

## How it works

**Project constitution** (the rules layer — overlaps with [[skills-rules-subagents]] rules): tech stack, architectural principles, code standards, SDD workflow. Lives in CLAUDE.md / AGENTS.md as persistent memory/governance. See [[project-rules-example]] for a worked artifact.

**Phased workflow** — reset context between phases so the model gets fresh, precise direction and stale assumptions don't accumulate:

| Phase | Output |
|---|---|
| 1 — Specification | WHAT the feature does |
| 2 — Technical design | HOW to implement |
| 3 — Task breakdown | Small, manageable tasks |
| 4 — Implementation | Task-by-task coding |

Bootstrap via `/init` to generate a CLAUDE.md template (see [[repo-init-workflow]]), or have a model draft it from a project summary (often after a deep-research chat). Checklist: stack matches reality, principles appropriate, standards enforceable, phases session-aware, no assumptions of continuous context. Rules grow as the project does — distill recurring corrections into new standards.

## Dean-Relevance

**Adoption path**: immediate
**Why**: SDD matches Dean's native working style (extensive planner, plans as source-of-truth, low tolerance for chaotic iteration) and governs his repos via CLAUDE.md/AGENTS.md — current daily practice, not aspiration.
**Watch for** (what upgrades to active): tooling that makes specs *executable/verifiable* (spec → tests / automated conformance) rather than static docs — that would turn SDD from discipline into infrastructure.
**Suggested next step**: —

## Related
- [[vibe-coding]]
- [[skills-rules-subagents]]
- [[starting-a-project-vibe-coding]]
- [[project-rules-example]]
- [[repo-init-workflow]]
- [[worktrees-parallel-agents]]
