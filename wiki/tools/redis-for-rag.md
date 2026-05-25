# Redis for RAG

> An in-memory engine that can serve three RAG roles at once — vector store, semantic cache, and LLM session memory — with low latency and horizontal scale.

**Category**: tools
**Last updated**: 2026-05-25
**Status**: reference

## What it is

Redis used as the data layer for a RAG system. Beyond the obvious vector-index role, its value is consolidating three jobs that otherwise need three services: vector search, a semantic cache over past Q&A, and conversation/session memory for the LLM. RedisVL is the purpose-built library for managing vectors + metadata and similarity search; it integrates with LangChain, LlamaIndex, and Spring AI.

## Why it matters

The semantic-cache role is the differentiator: cache prior FAQ answers as vectors and serve a near-duplicate incoming query from cache instead of re-running retrieval + LLM inference — direct latency and cost reduction. The in-memory design means retrieval and cache lookups run at minimal latency, which matters for interactive agents and high-QPS endpoints.

## How it works

| Role | What it does |
|---|---|
| **Vector database** | Stores/indexes embeddings, ANN similarity search |
| **Semantic cache** | Vector-matches incoming query against past answered questions; cache hit skips the LLM call |
| **Session manager** | Stores chat history; fetches recent + relevant turns as context |

Build flow: stand up Redis configured for vectors → use RedisVL (or a framework integration) → embed and store data → wire retrieval into the generative model → query, retrieve relevant vectors, augment generation.

**Where it fits vs. Dean's stack**: Dean already runs Qdrant for vector search, so Redis-as-vector-DB is redundant. The non-overlapping wins are the *semantic cache* and *session memory* layers, which Qdrant doesn't cover and which complement any pipeline from [[advanced-rag-techniques]] / [[agentic-rag]].

## Dean-Relevance
**Fit score**: 6/10
**Adoption path**: experimental
**Why**: Qdrant already owns vector search, but a Redis semantic-cache + session layer in front of Crafted/Praxis would cut OpenRouter cost/latency on repeat queries without touching the retrieval stack.
**Analogy**: A semantic cache is a barista who remembers your order — near-identical request, instant answer, no re-brewing.
**Suggested next step**: Prototype a RedisVL semantic cache (cosine threshold for "close enough") in front of the existing Qdrant pipeline and measure cache-hit rate + cost delta on real query logs.
**Watch for**: Provider-side prompt/response caching (e.g. OpenRouter/Anthropic caching) maturing enough to make a self-hosted semantic cache unnecessary.

## Related
- [[advanced-rag-techniques]]
- [[pre-retrieval]]
- [[agentic-rag]]
- [[agent-memory-learning-from-experience]]
- [[agent-frameworks]]
