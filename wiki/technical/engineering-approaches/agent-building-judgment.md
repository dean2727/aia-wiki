# Agent-Building Judgment

> Field-tested heuristics from Andrew Ng and Anthropic on when to build agents, how to evaluate them, and what's over- vs. under-hyped.

**Category**: topics
**Last updated**: 2026-05-25
**Status**: baseline

## What it is

A distillation of practitioner judgment (Andrew Ng; Anthropic's building-agents talk) about the meta-skills of agent building — not the patterns themselves ([[agentic-patterns]]) but the decisions around them: granularity, evals, model empathy, and where agents actually pay off. The throughline: the tools are now commodity "lego bricks" (RAG, memory, evals, guardrails); the rare skill is assembling the right ones and knowing when to stop.

## Why it matters

Most teams' bottleneck isn't capability, it's judgment: they over-engineer, postpone evals too long, and chase blind alleys improving one component when the whole approach is wrong. These heuristics are the difference between shipping and spinning. And instincts decay — strategies that were right a year ago (some RAG tactics) are obsolete as context windows grow. This is the agent-side companion to [[vibe-coding]]'s "critical thinking is the edge."

## How it works

**Agent vs. workflow** — an *agent* lets the LLM decide how many steps and which actions, looping to resolution; a *workflow* is a fixed, pre-orchestrated sequence. Ng: simple workflows cover most business cases. Start simple; add agency only when flexibility is genuinely needed. (See [[intro-to-agents]].)

**Evals — start ugly, start now.** The common mistake is treating evals as a big formal project. Throw together 5 examples + LLM-as-judge in 20 minutes to catch regressions, then improve incrementally. Trace individual steps, not just end-to-end, to find the failing component. See [[llm-agent-evaluation]].

**Empathy for the model** — "see through the model's eyes": give it well-documented tools (a widely neglected lever) and make implicit knowledge explicit. Simulate being the model to find where it lacks clarity.

**Over- vs. under-hyped:**

| Overhyped | Underhyped |
|---|---|
| Consumer agents booking your vacation (specifying + verifying ≈ doing it yourself; high error cost) | Agents automating small repetitive tasks at scale |

**Sweet spot** — tasks that are valuable and complex but have *low cost of error or are easy to monitor*. Coding and search are canonical (coding gets verification via tests — a real feedback loop).

**Advice:** always have a way to measure results; never build in a vacuum. Design products that benefit *as models improve* rather than betting on current limitations.

## Dean-Relevance

**Adoption path**: experimental
**Why**: This is the judgment layer over everything Dean builds — especially "start evals ugly and early" and "agent vs. workflow," which directly shape how he scopes Praxis features.
**Watch for** (what upgrades to active): updated heuristics as the landscape shifts — e.g. long-context and [[grok-4-20]]-style in-model agency invalidating today's "just use a workflow" defaults. This is a living page; refresh it when the lego bricks change.
**Suggested next step**: —

## Related
- [[agentic-patterns]]
- [[building-agents-best-practices]]
- [[llm-agent-evaluation]]
- [[agentic-errors]]
- [[vibe-coding]]
- [[context-engineering]]
