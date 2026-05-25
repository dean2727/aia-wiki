# Agentic Patterns

> Reusable building blocks for structuring LLM-driven systems, spanning deterministic workflows and autonomous agents.

**Category**: topics
**Last updated**: 2026-05-25
**Status**: reference

## What it is

Patterns are the design vocabulary for agentic systems: proven templates for decomposing a goal, coordinating LLM calls, tools, and memory, and managing complexity. The key axis is **workflows vs. agents** — workflows follow predefined paths (predictable, consistent, cheaper), agents decide their own course at runtime (flexible, adaptive, costlier). Ng's observation holds: most business use cases are well-served by simple workflows, not full autonomy. Pick the least-autonomy pattern that solves the problem.

Real systems compose these. A planning agent's workers can use tool-use and reflection; a multi-agent system uses routing internally for task assignment. The patterns are flexible building blocks, not mutually exclusive architectures. This is the hub page — see siblings [[building-agents-best-practices]], [[agentic-errors]], [[agentic-mesh]], [[intro-to-agents]], and the eval/guardrail pages for depth.

## Why it matters

Patterns give a shared mental model that keeps systems modular, debuggable, and extensible. The recurring failure mode is over-engineering: reaching for multi-agent when a prompt chain would do. The only reliable selection method is empirical — define metrics, measure, find the bottleneck, iterate. See [[llm-agent-evaluation]].

## How it works

### Workflows (deterministic control flow)

| Pattern | Shape | When |
|---|---|---|
| **Prompt chaining** | Output of call N → input of call N+1; fixed sequence | Cleanly decomposable, predictable subtasks (outline → validate → write) |
| **Routing / handoff** | Classifier LLM dispatches to a specialized downstream task; that task owns completion | Separation of concerns; tiered model usage (cheap model for simple, capable for hard) |
| **Parallelization** | Independent subtasks run concurrently, an aggregator synthesizes | Latency wins; quality via voting/diverse perspectives; query decomposition for [[agentic-rag]] |

### Agentic patterns (model-driven control flow)

| Pattern | Shape | Notes |
|---|---|---|
| **ReAct** | Interleaved reason → act → observe loop | The base substrate; see [[intro-to-agents]] |
| **Reflection (Evaluator-Optimizer)** | Generator produces output; evaluator critiques against criteria; loop until pass or max iters | Mimics draft-review-revise. Lets you get a "juicy" first response, *then* impose constraints — avoids over-constraining up front. Costs latency/tokens; justified when downstream error cost is high |
| **Tool use (function calling)** | LLM emits structured call matching a tool schema; result fed back | The most widely recognized pattern; extends model beyond training data. See [[mcp-and-a2a]] |
| **Planning (Orchestrator-Workers)** | Planner generates a *multi-step* plan; workers execute (possibly parallel); synthesizer checks goal, may re-plan | Differs from routing: a full plan, not a single next step |
| **Multi-agent** | Independent agents with own tools/history/expertise; coordinated centrally or peer-to-peer | See below |

### Multi-agent coordination

- **Coordinator-manager (centralized)**: one agent holds global state, directs others — optimal allocation, conflict prevention, consistent/predictable; ideal for mission-critical. Think Google ADK, LangGraph. Planning is a hierarchical special case of this.
- **Swarm (distributed)**: peer-to-peer, decision authority dispersed; simple local rules → emergent collective behavior; agents added without reconfig. Think OpenAI Agents SDK handoffs.

Orchestrator routing strategies: LLM-based dynamic routing, rule-based, hierarchical clustering + intent detection, graph-based conditional edges, auction/bidding (agents self-select via confidence), load-balancing/performance-based, and multi-objective (Pareto: cost × latency × quality × resource).

The Microsoft "primary patterns" naming maps onto the above: Sequential (chaining), Concurrent (parallelization), Magentic (dynamic specialization routing), Group Chat (shared-context collaboration), Handoff (explicit control transfer).

## Dean-Relevance

**Fit score**: 7/10
**Adoption path**: experimental
**Why**: His Crafted/Praxis multi-agent build with `generate_reply` retry-across-agents is a coordinator-manager-with-handoff hybrid — this is the catalog his architecture instantiates.
**Analogy**: Patterns are to agents what GoF design patterns were to OOP — vocabulary, not religion.
**Suggested next step**: Audit his agent flow and tag each hop with its pattern; flag any multi-agent hop that's really just routing and could collapse to a workflow.
**Watch for**: Framework-native orchestration (LangGraph/ADK/Agents SDK) absorbing these patterns as first-class primitives, shifting the choice from "implement" to "configure."

## Related
- [[building-agents-best-practices]]
- [[agentic-errors]]
- [[intro-to-agents]]
- [[agentic-mesh]]
- [[llm-agent-evaluation]]
- [[ai-guardrails]]
- [[agent-frameworks]]
- [[agentic-rag]]
