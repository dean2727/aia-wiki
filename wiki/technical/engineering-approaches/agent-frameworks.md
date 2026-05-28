# Agent Frameworks

> The landscape of agent-building libraries arranged on a spectrum from maximal LLM agency to maximal developer control.

**Category**: tools
**Last updated**: 2026-05-25
**Status**: reference

## What it is

Agent frameworks sit on a spectrum. At one end, high-agency systems (AutoGen-style) let the LLM drive control flow and decide what to do next. At the other, structured systems (LangGraph-style) impose an explicit graph so behavior is repeatable and scalable. They were each designed around a different paradigm, so the right pick is use-case dependent. By now, all the major libraries implement or support the standard [[agentic-patterns]].

## Why it matters

The core tradeoff: high-agency frameworks are fast to stand up but hard to steer when the agent doesn't behave as expected; graph-based frameworks cost more dev effort but buy controllable, repeatable outcomes. Most teams that need reliability lean toward the structured end — which is why LangGraph sees heavy adoption.

## How it works

| Need | Reach for |
|---|---|
| Maximal LLM autonomy, fast prototype | AutoGen-style (high agency) |
| Repeatable, scalable, controllable flows | LangGraph-style (explicit graph) |
| Standard patterns (routing, reflection, tools) | Any major framework now supports them |

## Dean-Relevance

**Adoption path**: watch
**Why**: Useful framing for picking an orchestration layer in Praxis agent features, but his current work leans on the [[harness-and-scaffolding]] of coding agents rather than a heavyweight framework.
**Analogy**: AutoGen vs LangGraph is improv vs a score — both make music, one is reproducible.
**Suggested next step**: —
**Watch for**: A concrete need for repeatable multi-step agent flows in Praxis would make LangGraph-style structure worth adopting.

## Related
- [[agentic-patterns]]
- [[agentic-rag]]
- [[grok-4-20]]
- [[building-agents-best-practices]]
