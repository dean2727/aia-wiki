# Semantic Boundary Chunking

> Context-aware chunking that splits at natural semantic boundaries while keeping domain-critical entities intact within a single chunk.

**Category**: topics
**Last updated**: 2026-05-25
**Status**: reference

## What it is

A chunking strategy for RAG that does two things at once: split text at *meaningful* points (paragraph ends, topic shifts, complete thoughts) rather than arbitrary lengths, and ensure that domain-critical entities — chemical names, legal terms, patient/clinical data — are never split across or lost between chunks. Each resulting chunk is a self-contained, contextually coherent idea with its key entities preserved.

It's the high-end of the chunking spectrum in [[pre-retrieval]] — beyond fixed-size and recursive splitting, into semantic/agentic territory with an explicit entity-preservation constraint.

## Why it matters

Fragmented chunks produce fragmented retrieval: a chunk that cuts a drug name from its dosage, or a clause from its defined term, returns context that's technically relevant but semantically broken — exactly the kind of distractor that produces confident-wrong answers. In specialized domains the payoff is large: one cited medical use case moved RAG accuracy from ~40% to ~90% by preserving entities at chunk boundaries.

## How it works

1. Analyze text to identify semantic units (sentences, paragraphs, topic shifts).
2. Chunk at those boundaries so each segment is semantically complete.
3. Refine with domain awareness — detect key entities (NER or domain rules) and adjust boundaries so no critical entity is severed.

| | Fixed-size | Semantic-boundary + entity preservation |
|---|---|---|
| Split point | Arbitrary char/token count | Topic/semantic boundary |
| Entity integrity | Often broken | Preserved |
| Compute cost | Cheap | Higher (analysis + NER pass) |
| Best for | Exploratory, generic text | Legal, medical, technical corpora |

**Hard limit**: this keeps related info together *within* a source but cannot bridge facts distributed *across* multiple documents. When the answer requires cross-document synthesis, reach for [[graph-rag]] instead.

## Dean-Relevance
**Fit score**: 5/10
**Adoption path**: experimental
**Why**: Crafted/Praxis content (human-growth notes/journaling) is less entity-dense than legal/medical, but topic-shift-aware boundaries could still cut distractors in his Qdrant retrieval.
**Analogy**: Don't tear a recipe in half mid-ingredient — cut between recipes, never between an ingredient and its quantity.
**Suggested next step**: A/B a semantic chunker (topic-shift boundaries) against current fixed/recursive chunking on the RAG triad before committing the extra ingest cost.
**Watch for**: Cheap, fast LLM-based agentic chunkers that make entity-preserving boundary detection negligible-cost at ingest time.

## Related
- [[pre-retrieval]]
- [[advanced-rag-techniques]]
- [[graph-rag]]
- [[agentic-rag]]
- [[redis-for-rag]]
