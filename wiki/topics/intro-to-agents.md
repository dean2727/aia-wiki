# Intro to Agents

> The conceptual ladder from static models to compound systems to autonomous agents, and when agency is actually worth it.

**Category**: topics
**Last updated**: 2026-05-25
**Status**: reference

## What it is

The progression: traditional models are specialized tools, excellent at their training task, brittle outside it. **Compound systems** chain multiple specialized components (LLMs, image models, retrievers, DBs) — RAG is the canonical example, combining retrieval and generation — but follow predefined patterns. **Agents** are compound systems plus autonomy: instead of fixed rules, they use a foundation model's reasoning to decide actions dynamically, plan, and adapt to context. The venue-finder example: a compound system returns a list; an agent factors in recent preferences, live availability, and local events during your dates.

Three capabilities define an agent: **reasoning** (plan and decompose a goal), **acting** (invoke external tools to gather info and execute), and **memory** (recall prior interactions/preferences). ReAct is the popular configuration that interleaves these.

## Why it matters

This is the framing for the core build/skip decision. Collaborative agents communicate and coordinate toward a shared goal; a **multi-agent system** is the broader structural concept (agents may collaborate, compete, or run independently). The substrate the rest of the cluster builds on — see [[agentic-patterns]] for the templates, [[building-agents-best-practices]] for the lifecycle, [[agentic-errors]] for failure modes.

## How it works

### When to use agents vs. not

- **Always seek the simplest solution first.** If the exact steps are known, a fixed workflow or plain script is more efficient and reliable than an agent.
- Agency trades latency and compute cost for performance on complex, ambiguous, or dynamic tasks — confirm the benefit outweighs the cost.
- **Workflows** → predictability and consistency on well-defined tasks. **Agents** → flexibility, adaptability, model-driven decisions.
- Even when building agents, keep it simple — overly complex agents are hard to debug and manage.
- Agency introduces unpredictability; require robust error logging, exception handling, and retry mechanisms so the system can self-correct (see [[agentic-errors]]).

### Standing limitations

Data privacy (agents touch sensitive data), technical complexity, poor generalization to unforeseen scenarios without retraining, compute cost, and ethical/bias/transparency concerns. Human oversight remains important even as capability improves.

## Dean-Relevance

**Fit score**: 4/10
**Adoption path**: skip
**Why**: This is foundational framing he operates well past daily — the only live takeaway is the "simplest solution first" discipline against over-agenticizing Crafted/Praxis.
**Analogy**: Model → compound system → agent is like function → pipeline → autonomous worker that decides its own pipeline.
**Suggested next step**: —
**Watch for**: Nothing here moves toward active — it's settled substrate; the frontier lives in the sibling pages.

## Related
- [[agentic-patterns]]
- [[building-agents-best-practices]]
- [[agentic-errors]]
- [[agentic-rag]]
- [[agent-memory-learning-from-experience]]
- [[harness-and-scaffolding]]
- [[llm-agent-evaluation]]
