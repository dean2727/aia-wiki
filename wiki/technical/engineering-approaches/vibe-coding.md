# Vibe Coding

> Relying on AI-generated code you only superficially understand — and the discipline that separates an accelerated developer from one accruing silent technical debt.

**Category**: topics
**Last updated**: 2026-05-25
**Status**: baseline

## What it is

Vibe coding (Karpathy's term) = throwing a vague prompt at an AI, pasting the output, shipping code you don't truly own. It works short-term and creates fragile, poorly-understood systems long-term. The distinction that matters isn't "use AI or not" — it's **vibe coder** (treats AI as a magic generator) vs. **real developer** (uses AI as an accelerator while keeping ownership of problem framing, trade-offs, and final calls). The gap shows the moment bugs appear, requirements shift, or someone has to explain the system.

## Why it matters

Critical thinking is the durable edge: AI handles syntax, boilerplate, and simple patterns, but not domain nuance, trade-off evaluation (performance vs. maintainability, cost vs. scale), architecture with long-term impact, or compliance. The risk of vibe coding isn't a bad first draft — it's unpredictable behavior, hidden bugs, inability to adapt, and team-wide drag from debt. This is the coding-side companion to [[agent-building-judgment]].

## How it works

Treat AI like an eager but inexperienced junior developer you manage. Core principles:

| Principle | In practice |
|---|---|
| Outsource the repetitive | Boilerplate, CRUD, scaffolding, basic tests |
| Own the complex parts | Business logic, critical integrations, perf-sensitive code, architecture |
| AI for exploration, not decisions | Ask for options; you choose |
| Sparring partner | Explain your reasoning; challenge its suggestions |
| Always verify | Review, test, debug, refactor before shipping |

Workflow: start from a strong template; plan in Markdown before coding; keep plans in-repo (`plans/implementation-plan.md`); distill patterns/frustrations into rules (AGENTS.md); separate planning from execution (cheap models draft, strong models review). Recovery: when a section goes off the rails, redo it with proper planning rather than patching messy code. See [[spec-driven-development]] and [[starting-a-project-vibe-coding]] for the structured form, and treat repeated frustrations as inputs to a workflow/rule you can reuse.

## Dean-Relevance

**Adoption path**: immediate
**Why**: This is the philosophy underneath Dean's whole AI-assisted workflow (own the complex, automate the rote, plan-first) — he already operates this way; the page is a crisp statement of the standard.
**Watch for** (what upgrades to active): as models get strong enough to reliably own larger slices, the "own the complex parts" line moves — worth revisiting when frontier coding agents change what's safe to delegate.
**Suggested next step**: —

## Related
- [[spec-driven-development]]
- [[starting-a-project-vibe-coding]]
- [[skills-rules-subagents]]
- [[agent-building-judgment]]
- [[worktrees-parallel-agents]]
