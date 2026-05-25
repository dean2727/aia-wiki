# Pre-Retrieval

> Everything you do to the index and the query *before* a search runs — chunking, cleaning, multi-representation indexing, and query transformation.

**Category**: topics
**Last updated**: 2026-05-25
**Status**: reference

## What it is

Pre-retrieval is the half of [[advanced-rag-techniques]] that happens before any vector lookup: how documents are split and stored (indexing) and how the incoming query is reshaped (query optimization). It's where most recall is won or lost — a well-structured index plus a well-formed query means the retrieval step rarely has to compensate.

Two axes: **optimizing indexing** (chunking strategy, data cleaning, multi-representation indexing, self-querying/parent-doc retrieval setup) and **optimizing query** (multi-query, decomposition, step-back, HyDE, semantic routing).

## Why it matters

Garbage index → garbage retrieval, no matter how good the embedding model. Likewise a raw one-line user query often sits in a sparse, badly-placed region of embedding space. The query transforms here exist to move the query (or its hypothetical answer) into a denser, more relevant neighborhood, and to fan a complex question into sub-questions the index can actually answer.

## How it works

### Chunking strategies

| Strategy | What | When |
|---|---|---|
| Fixed-size + overlap | Char-count windows, overlap so sentences aren't cut | Exploratory; context not critical |
| Recursive structure-aware | Split on `\n\n`→`\n`→… respecting hierarchy | Default general-purpose |
| Structure-aware (sentence/para/section) | Split on natural units | Clean, well-formatted docs |
| Content-aware | Markdown / code splitters (by heading, function/class) | Docs, source code |
| Semantic | Embed sentences, break on similarity drop | Topic/sentiment tasks needing coherence |
| Agentic | LLM extracts propositions, decides chunk boundaries | Highest quality, highest cost |

Size depends on content type, embedding-model token limit, expected query length, and downstream use (QA → small precise chunks; summarization → larger). A **non-homogeneous index** (mixed granularities) accommodates both short factoid and broad thematic queries. See also [[semantic-boundary-chunking]] for entity-preserving variants.

### Data granularity / cleaning
Stop-word removal, special-char/HTML stripping, normalization (lowercasing, stemming/lemmatization), fact-checking/refresh routines. Balance: aggressive cleaning boosts efficiency but can strip domain-relevant terms — be domain-aware.

### Multi-representation indexing (MRI)
Index the same document under multiple representations (summary embeddings + raw chunks, separate inverted indexes for free-text vs. entity/structured fields, visual features). At query time, route each query part to the best representation and fuse (intersection / union / RRF). Embed summaries, store full docs in a KV store keyed by ID. Elasticsearch shines for the keyword/entity index (fuzzy matching via edit distance).

### Retrieval-setup patterns
- **Self-querying**: LLM reads the query + a metadata schema (`AttributeInfo`) and emits a semantic-search component + metadata filters.
- **Parent-document retrieval (PDR)**: embed small child chunks, retrieve, then return larger parents (or whole docs) for reasoning context. Store parents in Redis/Mongo/in-memory keyed by ID. Often hybridized with dynamic routing (factoid → child chunk; explain → parent).
- **Hypothetical-question indexing**: generate a question per chunk, embed the questions, match query→question for tighter semantic alignment.

### Query optimization

| Technique | Mechanism | Best for |
|---|---|---|
| Multi-query | LLM generates N rephrasings, parallel search, dedupe-union | Clear query, varied doc phrasing |
| Decomposition | Break into independent sub-questions | Complex, multi-aspect questions |
| Step-back | Abstract to a more general question first | Poorly-phrased / principle-based |
| HyDE | Embed an LLM-generated hypothetical answer, not the query | Unseen domains, noisy/incomplete docs |
| Semantic routing | Route query to domain-specific prompt/sub-model | Multi-domain systems |

**Routing — vector vs. LLM classifier**: semantic routers (embedding similarity to synthetic queries) win on latency, cost, determinism, locality. LLM classifiers win on ambiguous/overlapping intents, novel phrasing, and explainability. Production verdict: hybrid — fast vector first pass (route if cosine > ~0.85), fall back to LLM classifier only for low-confidence cases.

## Dean-Relevance
**Fit score**: 7/10
**Adoption path**: experimental
**Why**: MRI (separate semantic + entity indexes) and HyDE/multi-query map directly onto Crafted/Praxis's Qdrant + dual-collection setup and his Jinja2 prompt builders for query rewriting.
**Analogy**: A well-optimized query is a laser pointer; a raw query is a flashlight — same light, wildly different precision.
**Suggested next step**: Try HyDE (generate hypothetical answer with Sonnet, embed via text-embedding-3-large) on his hardest ambiguous queries and compare retrieval against the raw query.
**Watch for**: Embedding models trained natively for query/answer asymmetry that close the gap HyDE exploits, making the extra LLM call unnecessary.

## Related
- [[advanced-rag-techniques]]
- [[semantic-boundary-chunking]]
- [[graph-rag]]
- [[agentic-rag]]
- [[redis-for-rag]]
- [[synthetic-data]]
