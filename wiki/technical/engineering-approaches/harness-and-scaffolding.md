# Harness and Scaffolding

> The emerging vocabulary for the layers around an LLM that turn it into an agent — and why "harness" and "scaffold" keep getting conflated.

**Category**: topics
**Last updated**: 2026-05-25
**Status**: active

## What it is

The agent field moved faster than its vocabulary — the terms blurred badly enough that practitioners at ICLR 2026 couldn't converge on definitions of "harness" and "scaffold." A small set of words became load-bearing anyway: **model, scaffolding, harness, agent, policy**. This page pins them down with a practical mental model rather than a dictionary.

The one-line version the community converged on: **Agent = Model + Harness**. If you're not the model, you're the harness — everything that isn't the raw LLM (the loop, the tools, the parsing, the memory, the stop logic) is harness.

Source: Hugging Face, *"Harness, Scaffold, and the AI Agent Terms Worth Getting Right"* (2026-05-25).

## Why it matters

Dean works inside harnesses daily — Claude Code's own docs say it "serves as the agentic harness around Claude." Two products on the *same* model can feel completely different because their harnesses make different choices; swapping a better model into the same harness also changes everything. Being able to separate model / harness / scaffold / product cleanly is what lets you reason about *which layer* a behavior — or a bug, or an improvement — actually lives in. That's the difference between "the model is dumb" and "my context management is dropping the relevant tool result."

It also names a discipline — **harness engineering** — that's quietly where a lot of real agent quality now comes from: deciding when to stop, how errors get handled, what guardrails keep the loop on track.

## How it works

The core split (the distinction that causes most of the confusion):

| Term | What it is | One-liner |
|---|---|---|
| **Model** | The LLM itself | Text in, text out; no loop, no memory between calls |
| **Scaffolding** | The behavior-defining layer | What the model *works from*: system prompt, tool descriptions, response parsing, context management |
| **Harness** | The execution layer | What *makes it run*: calls the model, executes tool calls, decides when to stop |
| **Agent** | Model + Harness | A model wrapped so it can act in a loop, not just respond |
| **Policy** | The behavior itself | Given a situation, the distribution over actions; partly in weights, partly in scaffold/harness |

Broad vs. narrow usage matters: products like Claude Code and Codex call the *whole thing* the harness ("everything that isn't the model"). The scaffold/harness split matters most when you reason about them separately — e.g. in a training pipeline, where the harness runs many loops in parallel and feeds results back to update weights.

**Supporting vocabulary:**
- **Context engineering** — designing what's in the window at each step (system prompt, tool descriptions, history, retrieved knowledge); continuous, harness-managed throughout the run. Short-term memory = in the window this run; long-term = stored externally, retrieved on demand. See [[context-engineering]] and [[agent-memory-learning-from-experience]].
- **Tool use** — the model emits a structured call, the harness routes it, the result feeds back. Underpins [[mcp-and-a2a]].
- **Skills** — reusable, on-demand packages of *knowledge* for a multi-step goal ("investigate this bug, form a hypothesis, fix it"), vs. a tool which is a single *action*. See [[skills-rules-subagents]].
- **Sub-agents** — an agent called by another: own model + scaffold, reasons independently, returns a result. Distinct from a tool (function) or skill (knowledge) because it can itself reason and call further sub-agents.

**Training-side terms** (relevant if you train, not just deploy): **RL environment** (stateful thing actions mutate), **trainer** (runs episodes, scores, updates weights — e.g. TRL's GRPOTrainer), **rollout / trajectory / trace** (one full run start to finish — the raw data RL learns from), **reward** (verifiable vs. learned; sparse vs. dense; rubrics break it into weighted dimensions). An **eval harness** is the same loop pattern but records metrics at a checkpoint instead of updating weights.

## Related
- [[context-engineering]]
- [[skills-rules-subagents]]
- [[mcp-and-a2a]]
- [[agentic-patterns]]
- [[grok-4-20]]
- [[agent-building-judgment]]
