# Context Engineering

> The deliberate, dynamic management of exactly what an agent sees at each step — framed as the alternative (or complement) to multi-agent complexity.

**Category**: topics
**Last updated**: 2026-06-28
**Status**: active

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

## Why context grows out of control

The pressure is structural, not a bug. A single deep-research run can fire 50+ tool calls; Anthropic has noted a typical agent makes *hundreds*. Each call's raw output, naively plumbed back, drives the window toward its limit fast (a deep-research run can burn ~500k tokens, $1–2). And large contexts don't just hit a hard wall — they degrade *before* it, with idiosyncratic failure modes well short of the nominal limit. So the question is never "does it fit," it's "what does the model actually need to see right now."

## Offloading and compaction

The core move is to keep raw material **out** of the model and bring back only a pointer or a synthesis:

- **Offload to disk / state.** Write a tool call's full output to the file system (or an agent state object), and hand the model back a summary plus a URL/handle it can re-fetch on demand. The external file system is, in effect, free token budget.
- **Summarize at boundaries.** Compression can happen at offload time *or* at the tool-call boundary itself. Hugging Face's deep-research agent runs code in the environment, summarizes the result, and passes only the trimmed context to the LLM — the raw call stays in the environment. Anthropic's researcher similarly summarizes findings.
- **Compaction is the risky version.** Devin uses a *fine-tuned model* specifically for compaction. It works, but it is one of the trickiest parts of agent building: every pruning rule is more logic to maintain in the harness, and (see below) it can destroy information you needed.

The discipline: offload first (reversible), summarize/prune second (lossy), and keep the raw available so a prune is never a dead end.

## Context failure modes

- **Pruning is irreversible.** Once you drop history to save tokens, it's gone unless you offloaded it. Treat summarize/prune as lossy and always back it with an on-disk copy.
- **Context poisoning.** A hallucination that lands in the history *stays* in the history, steering every later step off track. The longer the run, the more a single bad token compounds.
- **Keep tool-call errors in.** Counterintuitively, don't scrub failed-call output — surfacing the error (as Claude Code does) lets the model correct course instead of repeating the mistake blind.

## Caching

Because every pass re-sends the whole context, prompt caching cuts latency and cost dramatically — but it doesn't solve growth: a cached context can still balloon past what the model handles well. Many providers cache for you transparently. The leverage case for running your **own** open models is that you control the cache directly, which can be a meaningful cost/latency win at scale.

## Multi-agent context isolation

Multi-agent is, in context terms, a way to *compress*: each sub-agent does token-heavy work and returns a compact result the orchestrator loads. That works cleanly when sub-agents only **read** — deep research parallelizes well because agents gather information and a single agent writes the final synthesis. It breaks down when sub-agents each **decide** or **write** part of the artifact: their implicit choices conflict, and reconciling them at compile time is the hard part (why multi-agent *coding* is much harder than multi-agent *research*). Rule of thumb: reach for multi-agent only when the task parallelizes into independent read/gather work. See [[mcp-and-a2a]] for moving that work off the agent entirely.

## Designing for improving models

The deepest lesson is temporal: **the structure is the product, not the model.** You add scaffolding (decomposition, fixed workflows, inductive biases) to get acceptable performance from *today's* model at *today's* compute — but that same structure becomes the bottleneck as models improve. The 2024 "split into sections, then compile a report" workflow beat the contemporaneous open-ended agent; once base models got dramatically better, the ranking flipped and the rigid workflow held the system back. The bitter-lesson corollary for builders: prefer letting the model think with more compute over hand-specifying how it should think, and constantly re-assess which assumptions you can now *remove*. Practical implications: keep harnesses general and thin (Claude Code ships deliberately under-scaffolded), avoid having to rip out and rebuild the agent, and note that shipping a product that *doesn't quite work yet* can pay off when model capability catches up to it.

## Timeline

- `2026-05` (wiki) Page created by a wiki run — single-agent context discipline vs. multi-agent complexity
- `2026-06` (wiki) Page updated by a wiki run — Notion Track A enrichment: offloading/compaction, context failure modes (poisoning, irreversible pruning, keep tool errors), caching, multi-agent context isolation tradeoffs, and…

## Related
- [[grok-4-20]]
- [[harness-and-scaffolding]]
- [[agentic-patterns]]
- [[llm-agent-evaluation]]
- [[agent-memory-learning-from-experience]]
- [[building-agents-best-practices]]
