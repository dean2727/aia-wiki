# Agentic RAG

> RAG where an LLM agent — not a fixed pipeline — decides whether to retrieve, what tools/sources to use, and whether the results are good enough to answer.

**Category**: topics
**Last updated**: 2026-05-25
**Status**: reference

## What it is

Agentic RAG moves the retrieval logic out of a static chain and into an agent's reasoning loop. The "agent-ness" lives mainly in the retrieval stage: instead of always running the same top-k search, the agent decides *whether* to search, *which* source/tool to use, evaluates the returned context, and re-searches or reformulates if it's insufficient. It can decompose a complex question, plan a multi-step retrieval strategy, and call non-retrieval tools (calculator, code interpreter, web, domain APIs/MCP) to turn a partial answer into a complete one.

It's the convergence of [[advanced-rag-techniques]] with [[intro-to-agents]] — query transforms like multi-query/decomposition/HyDE from [[pre-retrieval]] become *decisions the agent makes dynamically* rather than fixed pipeline stages.

## Why it matters

Static RAG retrieves even when it shouldn't, can't recover from a bad first retrieval, and can't combine retrieval with computation. Agentic RAG fixes all three, and its modular agent-based design scales naturally — add a tool or data source without rewriting the pipeline, hand specialized sub-domains to specialized (possibly fine-tuned) sub-agents. The cost is the usual agent tax: latency, token spend, and the failure modes in [[agentic-errors]].

## How it works

Three ingredients:

| Ingredient | Role |
|---|---|
| **LLM with function calling** | The reasoning core. Native function calling >> prompt-engineered/constrained-decoding emulation. Emits actions like "search for X," ingests results into context, continues reasoning. |
| **Tools** | Vector DB is the primary tool; plus calculators, code interpreters, web browsers, calendars, domain APIs / [[mcp-and-a2a]] servers. |
| **Agent** | LLM + memory + role + planning/decomposition + tool access. Architectures from [[agentic-patterns]]: ReAct, Plan-and-Execute. |

Agentic-specific retrieval capabilities vs. vanilla RAG:
- Decide whether retrieval is even necessary (skip it for things the model knows).
- Choose which search engine/source to query (autonomous planning).
- Evaluate retrieved context and self-trigger a re-search (self-correction).
- Decide whether to invoke an external tool (e.g. run Python to chart or compute a statistic over retrieved data).

Frameworks: LangChain/LangGraph, LlamaIndex, DSPy, Letta, CrewAI — see [[agent-frameworks]].

## Related
- [[advanced-rag-techniques]]
- [[pre-retrieval]]
- [[graph-rag]]
- [[agentic-patterns]]
- [[agent-frameworks]]
- [[mcp-and-a2a]]
- [[llm-agent-evaluation]]
- [[intro-to-agents]]
