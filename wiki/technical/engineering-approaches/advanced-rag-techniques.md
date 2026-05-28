# Advanced RAG Techniques

> The hub for techniques that turn naive vector-search RAG into a robust retrieval pipeline — pre-retrieval, retrieval, ranking, and graph/agentic extensions.

**Category**: topics
**Last updated**: 2026-05-25
**Status**: reference

## What it is

Naive RAG (chunk → embed → top-k cosine → stuff context) fails in predictable ways: it surfaces topically-near-but-wrong passages, drags in **distractors** (irrelevant context that falls inside the embedding "cloud" and silently degrades answers), and misses documents that phrase things differently than the query. The advanced-RAG body of work is the accumulated set of fixes layered across three stages: improving the index/query before retrieval ([[pre-retrieval]]), improving what comes back (hybrid + multi-representation retrieval), and improving the final ordering (reranking).

This page is the index for that cluster. The siblings go deep: [[pre-retrieval]] (chunking, cleaning, multi-representation indexing, query transforms), [[semantic-boundary-chunking]] (entity-preserving splits), [[graph-rag]] (global/QFS questions over a corpus), [[agentic-rag]] (an agent that decides whether/what/how to retrieve), and [[redis-for-rag]] (vector store + semantic cache + session memory in one engine).

## Why it matters

Most RAG quality problems are retrieval problems, not generation problems. Distractor-induced wrong answers are hard to debug because the LLM looks confident and the context looks plausible. Knowing the failure taxonomy and which lever fixes which failure is the difference between endlessly tweaking prompts and fixing the actual cause.

## How it works

| Stage | Technique | Fixes |
|---|---|---|
| Pre-retrieval | Chunking strategy, data cleaning, multi-representation indexing, query transforms (see [[pre-retrieval]]) | Bad granularity, noisy index, query/intent mismatch |
| Query transform | HyDE, multi-query, decomposition, step-back, semantic routing | Short/ambiguous queries, complex multi-aspect questions |
| Retrieval | Hypothetical-question embedding, sentence-window, auto-merging / parent-doc, **hybrid (dense + BM25)** | Dilution, lost surrounding context, OOV/rare-term misses |
| Ranking | **Reciprocal Rank Fusion (RRF)**, cross-encoder reranking, embedding adapters | Too many candidates, bi-encoder imprecision |

**Hybrid retrieval**: dense captures "what you meant," sparse (BM25) nails "what you said" — fuse for coverage on synonyms/typos/rare terms. Cost: two indexes, two pipelines, a fusion step.

**RRF**: rank-based fusion, score `1/(k+rank)` (k≈60), summed across lists. No score normalization needed — ideal default for hybrid.

**Cross-encoder reranking**: bi-encoder casts the wide net (fast, top-N candidates), cross-encoder scores each (query, doc) pair for precision (slow, applied only to the shortlist). The two-stage net-then-sort pattern is the standard production rerank.

**Bridge techniques** (between retrieval and ranking): *sentence-window* (embed per sentence, expand ±k on a hit), *auto-merging / parent-document* (retrieve small child chunks, return larger parents when enough children share one). These trade precision for context completeness.

**Evaluation — the RAG triad**: score query→context relevance, context→answer relevance, and answer groundedness. Build a small validation set (~10 queries to start, grow until conclusive) with ideal answers and a superset of expected source docs. Ragas / TruLens / MLflow.

## Dean-Relevance

**Adoption path**: experimental
**Why**: This is the substrate behind Praxis retrieval over Qdrant — hybrid + RRF + cross-encoder rerank is the most likely concrete upgrade to his current dual-collection setup.
**Analogy**: Bi-encoder = big net; cross-encoder = the fisherman sorting the catch. Cast wide, then sort precisely.
**Suggested next step**: Add a cross-encoder rerank stage over Qdrant top-N and measure the RAG triad on a 10-query validation set before/after.
**Watch for**: Long-context models eating the "stuff more context" rationale — but retrieval precision (distractor suppression) stays load-bearing regardless of window size.

## Related
- [[pre-retrieval]]
- [[semantic-boundary-chunking]]
- [[graph-rag]]
- [[agentic-rag]]
- [[redis-for-rag]]
- [[llm-agent-evaluation]]
- [[agentic-patterns]]
