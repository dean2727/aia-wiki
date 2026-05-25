# Agent Memory & Learning from Experience

> Approaches for agents that improve across sessions — long-term memory retrieval and learning from experience without fine-tuning.

**Category**: topics
**Last updated**: 2026-05-25
**Status**: baseline

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

## Dean-Relevance

**Fit score**: 6/10
**Adoption path**: watch
**Why**: Directly relevant to Crafted/Praxis, which is built on accumulating per-user context to "engineer how humans grow" — agents that learn from experience without retraining is nearly the thesis in infrastructure form.
**Analogy**: The difference between an employee who re-reads the same onboarding doc every morning and one who actually remembers yesterday's mistakes.
**Watch for** (what upgrades to active): a concrete, reproducible framework with benchmarks for experience-learning or learned memory retrieval that drops into an API-based stack (no training infra) — that would move this from watch to experimental fast.
**Suggested next step**: —

## Related
- [[context-engineering]]
- [[harness-and-scaffolding]]
- [[building-agents-best-practices]]
- [[agentic-errors]]
- [[llm-agent-evaluation]]
