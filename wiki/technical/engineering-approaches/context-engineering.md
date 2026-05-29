# Context Engineering

> The deliberate, dynamic management of exactly what an agent sees at each step — framed as the alternative (or complement) to multi-agent complexity.

**Category**: topics
**Last updated**: 2026-05-25
**Status**: baseline

## What it is

Context engineering is the discipline of curating the agent's context window dynamically at every turn — system prompt, tool descriptions, history, retrieved knowledge — so the model always sees the right information, in the right form, at the right time. Karpathy's framing: "the delicate art and science of filling the context window with just the right information for the next step." It's the successor to prompt engineering (one-time instruction crafting); the unit of work is the *whole evolving context*, not the opening prompt.

It's a "battlefield" and not just a technique because it sits at the center of an architectural debate: Cognition (Devin) champions single-agent + rigorous context engineering, Anthropic defends multi-agent. Both are really arguing about *where to put the complexity*. See [[grok-4-20]] for the "fold it into the model" position on the same question.

## Why it matters

The case against naive multi-agent, stated in context-engineering terms:

| Multi-agent failure mode | Why it happens |
|---|---|
| Lost context | Subagents lack the big picture → misaligned goals |
| Compounding errors | A few bad agents jeopardize the whole result |
| ~15× token cost | Redundant context shared across agents |
| "Game of telephone" debugging | Errors hard to trace across hops |

Single-agent context engineering keeps one coherent thread of logic — more traceable, fewer tokens, more predictable. The practical upshot for any builder: before reaching for more agents, ask whether disciplined context management on *one* agent gets you there cheaper and more reliably.

## How it works

Core tools of the practice:
- **Workflows / orchestration** — design the step-by-step retrieval and prompt assembly.
- **Scenarios & test suites** — empirically compare "summary vs. full data in the prompt," strategy A vs. B for a use case.
- **Evaluation** — automate accuracy / hallucination / format checks (metrics, semantic similarity, LLM-as-judge). See [[llm-agent-evaluation]].

Efficiency heuristics: include only essential data (not whole docs); prefer dynamic/summarizing strategies over stuffing a giant static window. Memory splits into short-term (this run's window) and long-term (external, retrieved on demand) — see [[agent-memory-learning-from-experience]].

The synthesis position: it's not either/or. A "context engineer" agent can coordinate top-level work and spin up temporary sub-agents where parallelization genuinely helps — but meticulous context management underpins *every* agent, single or multi.

## Related
- [[grok-4-20]]
- [[harness-and-scaffolding]]
- [[agentic-patterns]]
- [[llm-agent-evaluation]]
- [[agent-memory-learning-from-experience]]
- [[building-agents-best-practices]]
