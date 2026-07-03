# Agent Memory & Learning from Experience

> Approaches for agents that improve across sessions — long-term memory retrieval and learning from experience without fine-tuning.

**Category**: topics
**Last updated**: 2026-06-28
**Status**: active

## What it is

Two related frontier threads in giving agents durable improvement:

1. **Learning from experience without fine-tuning** — frameworks that let an LLM agent get better from its own interaction history (stored experience, distilled lessons, retrieved at the right moment) rather than weight updates.
2. **Long-term memory retrieval** — treating *what to remember and when to surface it* as a learned problem; recent work applies RL to retrieving long-term memories and answering from them, with promising results.

This sits one layer up from short-term context: short-term memory is what's in the window during a run; long-term memory persists across sessions, stored externally and retrieved on demand (see [[context-engineering]] and [[harness-and-scaffolding]]).

## Why it matters

It targets the ceiling on stateless agents: most production agents start every session cold. If experience can compound *without* a fine-tuning loop, agents get personalized and sharper cheaply — exactly the regime for a single-user system that accumulates context over time. It also reframes memory from a storage problem into a *retrieval-policy* problem, which is learnable.

## How it works

This is a watch item — the source is two pointers, not a synthesized method:
- A framework for LLM agents to learn from experience with no fine-tuning (VentureBeat coverage).
- An RL-based approach to long-term memory retrieval and answering (arXiv 2508.19828).

The shared shape: memory is captured as experience/lessons, and a learned (often RL-trained) policy decides what to retrieve and inject — closing a loop that prompt-only memory leaves open. Contrast with the failure mode in [[agentic-errors]], where an agent loses track of progress because working memory drops old information.

## Write policy and retrieval (the two hard halves)

Memory has two distinct hard problems, and most systems pick a point on each axis:

- **Who decides what to write?** Claude Code is *explicit*: it reads `CLAUDE.md` on start, and writes only when the user tells it to. ChatGPT is *autonomous*: it decides on its own when to save a memory and when to surface it — which adds a failure surface, since automatic retrieval produces false positives (pulling an irrelevant memory into context). Deciding *what's worth remembering* is genuinely difficult; over-writing pollutes future retrieval.
- **Retrieval is just RAG.** Surfacing the right long-term memory is the same problem as document retrieval (see [[advanced-rag-techniques]]). A naive system can "suck in" all memory every turn and lean on the context window; a sophisticated one is a **multi-step RAG pipeline** with its own relevance and ranking logic — and its own ways to go wrong.

## Human corrections as memory

A clean source of high-quality memory is the human-in-the-loop correction itself. In **ambient agent** setups, the user edits the agent's proposed tool calls in the loop; those edits get captured as memory. The correction *is* the lesson — no synthetic distillation needed, and it's grounded in what the user actually wanted. This pairs memory with oversight: the same interaction that keeps the agent safe also teaches it. See [[building-agents-best-practices]].

## Related
- [[context-engineering]]
- [[harness-and-scaffolding]]
- [[building-agents-best-practices]]
- [[agentic-errors]]
- [[llm-agent-evaluation]]
