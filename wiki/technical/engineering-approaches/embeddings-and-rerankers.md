# Owning Your Retrieval Stack: Open Embedders, Rerankers, and Fine-Tuning Them Yourself

> A 2026 snapshot of where retrieval quality is moving — small open Apache-2.0 embedders and rerankers that beat much larger models, plus the now-cheap recipes to fine-tune your own embedder/reranker on domain data in under a day.

**Category**: topics
**Last updated**: 2026-05-28
**Status**: active

## What it is

A cluster of spring-2026 Hugging Face releases that together change the economics of building a retrieval pipeline. Two threads:

1. **New open model families that punch above their parameter count.** The *Ettin reranker* family (six Sentence Transformers cross-encoders, 17M–1B, Apache 2.0) is state-of-the-art at every size and a drop-in upgrade over the legacy MiniLM rerankers. *Granite Embedding R2* (IBM, 97M + 311M multilingual, Apache 2.0) delivers the best sub-100M multilingual retrieval quality with a 32K context window.

2. **Fine-tuning your own embedder/reranker is no longer specialist work.** Sentence Transformers v5.4/5.5 added multimodal training and an AI-agent "train-sentence-transformers" skill; NVIDIA's NeMo recipe takes you from a folder of domain docs to a deployed, domain-adapted embedder in under a day — no manual labeling. PaddleOCR 3.5 covers the upstream document-ingestion step that feeds all of this.

The connecting insight: **retrieval quality is now something you architect and tune, not something you rent.** General-purpose embeddings understand the internet, not your contracts, your Jira tickets, or your growth-content taxonomy. The gap that used to require an ML team and weeks of work now closes with a single GPU and a recipe.

## Why it matters

The retrieve-then-rerank shape is the backbone of every modern search/RAG system: a cheap embedder pulls top-K candidates, an expensive cross-encoder re-orders just those K. What changed in 2026 is that **both halves got dramatically cheaper to own and customize.**

- **The reranker is the cheapest quality lever in RAG, and it just got cheaper still.** A reranker reads each `(query, document)` pair jointly through every transformer layer (vs. an embedder, which encodes query and doc independently and compares vectors). That joint attention is far more accurate but costs one forward pass *per pair*, so you only run it on the K survivors of retrieval. Ettin's 17M reranker beats every legacy MiniLM cross-encoder on quality *and* throughput — swapping it in is a one-line change that improves latency and search quality simultaneously.
- **Small open models now beat much larger ones on the tasks you actually run.** A 311M Granite model beats jina-v5-nano (212M active, but heavier) on retrieval at 5.5x the encoding throughput. A *fine-tuned* 2B multimodal embedder beat the 8B version of the same model. Specialization beats scale — see [[specialization-beats-scale]].
- **Domain fine-tuning produces large, real gains.** NVIDIA's recipe: +10% NDCG@10/Recall@10 on their own docs; Atlassian got Recall@60 from 0.751 → 0.951 (+26.7%) fine-tuning on a Jira dataset on a single A100.
- **Apache 2.0 + CPU/ONNX paths** mean these can run on-prem or at the edge with no API dependency — relevant any time data can't leave your premises.

## How it works

### 1. Ettin reranker family — small, fast, state-of-the-art cross-encoders

Six CrossEncoders (`cross-encoder/ettin-reranker-{17m,32m,68m,150m,400m,1b}-v1`), Apache 2.0, built on Johns Hopkins' ModernBERT-style **Ettin** encoders (unpadded attention, RoPE, GeGLU, 2T-token open pre-training, 8K context).

| Size | MTEB(eng,v2) NDCG@10 | H100 pairs/sec | Headline |
|---|---|---|---|
| 17M | 0.5576 | 7517 | Fastest reranker tested; beats *every* MiniLM variant on quality |
| 32M | 0.5779 | 6602 | Beats 568M `bge-reranker-v2-m3` (17x param gap) |
| 68M | 0.5915 | 4913 | Matches Qwen3-Reranker-0.6B at 1/9 the params |
| 150M | 0.5994 | 3237 | Strongest reranker under 600M tested; 2.3x faster than 150M peers |
| 400M | 0.6091 | 1738 | Within 0.0024 of the 1.54B teacher |
| 1B | 0.6114 | 928 | Within 0.0001 of teacher; 2.4x faster than it |

Two engineering choices drive the speed edge:

- **Modular `Transformer` with unpadded inputs.** The reranker uses a plain `AutoModel` + a 4-module head (Pooling-CLS → Dense+GELU → LayerNorm → Dense→1 score) instead of `AutoModelForSequenceClassification`. The wrapped class keeps inputs *padded*, so FA2's kernel runs but the rest of the model still burns compute on padding tokens. Ettin propagates unpadded inputs all the way through, which is why its 150M runs 2.3x faster than the architecturally identical `gte-reranker-modernbert-base` and `granite-embedding-reranker-english-r2`.
- **bf16 + FA2 together.** Enabling both yields 1.7x (17M) → 8.3x (1B) over fp32+SDPA. Counterintuitively, turning on FA2 *with padding* is slower than bf16+SDPA — the unpadding is the load-bearing part. Set `model_kwargs={"dtype":"bfloat16","attn_implementation":"flash_attention_2"}` and `pip install kernels`.

**Training recipe (the reusable part):** pointwise **MSE distillation** from a strong teacher (`mxbai-rerank-large-v2`, 1.54B) over ~143M `(query, doc, teacher_score)` triples. This sidesteps the usual problems with human-labeled triples — expensive labels, false negatives after hard-negative mining, and binary labels that don't capture *degrees* of relevance. A single ~150-line script trained all six sizes; only learning rate and batch size changed. Distillation closes the student-to-teacher gap almost completely, so the lesson is: **train a better teacher and the same script yields better students.**

```mermaid
flowchart LR
    Q[Query] --> E[Embedder: encode query + corpus separately]
    E -->|cosine sim, cheap, runs over millions| TK[Top-K candidates]
    TK --> R[Reranker: joint attention per query,doc pair]
    R -->|accurate, runs only over K| F[Final ordering]
```

### 2. Granite Embedding Multilingual R2 — best sub-100M multilingual retrieval

Two Apache-2.0 embedders, both a ground-up rebuild on **ModernBERT** (R1 was XLM-RoBERTa, 512-token context):

| Model | Params | Dim | Context | MTEB Multilingual Retrieval | Note |
|---|---|---|---|---|---|
| `granite-embedding-97m-multilingual-r2` | 97M | 384 | 32K | 60.3 | Best open sub-100M (next best, m-e5-small, is 50.9) |
| `granite-embedding-311m-multilingual-r2` | 311M | 768 | 32K | 65.2 (#2 under 500M) | Matryoshka, #1 on LongEmbed (71.7) |

What changed from R1 and why it matters:

- **ModernBERT backbone** → alternating attention lengths cut long-sequence compute, RoPE enables 32K context cleanly, FA2 support.
- **32K context (64x R1's 512)** is the biggest gain — LongEmbed jumped +31 to +34 points. R1's 512-token limit meant "your legal contract was judged by its first page."
- **Tokenizer is the unsung lever.** 311M uses the Gemma-3 tokenizer (262K); 97M prunes GPT-OSS down to 180K. "A 32K window sounds impressive until your tokenizer burns half of it encoding a paragraph of Thai."
- **311M built via** multi-teacher knowledge distillation → contrastive fine-tuning → model merging (combine checkpoints from different objectives, no extra compute) → Matryoshka. **97M built via** vocabulary selection (prune 262K→180K) + multi-teacher distillation.
- **Matryoshka (311M only):** truncate 768→256 dims (3x smaller storage *and* cheaper cosine) for only −0.5 NDCG; even 128 dims keeps 97% of quality. Notably, the 311M *truncated to 384* still beats the native-384 97M.
- **Enterprise framing:** trained on IBM-governed data, deliberately **without MS-MARCO** or non-commercial-licensed sets; ships ONNX/OpenVINO (CPU), vLLM embed endpoint, GGUF/Ollama. Drop-in for LangChain/LlamaIndex/Haystack/Milvus with a one-line model-name change, no instruction prefix needed. (English-only siblings `granite-embedding-english-r2` 149M / `-small-english-r2` 47M exist for English-heavy data.) Part of the wider [[open-model-releases-spring-2026]] wave.

### 3. Multimodal embedding & reranking in Sentence Transformers (inference)

Sentence Transformers v5.4 unified text/image/audio/video behind the *same* `encode()` / `CrossEncoder` API. Multimodal embedders map all modalities into one shared space; multimodal rerankers score mixed-modality `(query, document)` pairs.

- **Cross-modal retrieval just works:** `encode_query()` (text) vs `encode_document()` (image screenshots) — these wrappers auto-apply the model's query/document instruction prompts.
- **The modality gap:** cross-modal similarities (e.g. text↔image ~0.5–0.67 for true matches) sit lower than within-modal ones because modalities cluster in separate regions of the space. *Relative ordering is preserved*, so retrieval still works — but don't compare absolute scores across modality pairs.
- **Key use case: Visual Document Retrieval (VDR)** — retrieve relevant document *pages as images* (charts, tables, layout intact) for a text query, instead of OCR-then-embed-text. Supported embedders include Qwen3-VL-Embedding-2B/8B, nvidia llama-nemotron-embed-vl, nomic-embed-multimodal; rerankers include Qwen3-VL-Reranker, jina-reranker-m0. Older CLIP models remain supported for low-resource/CPU.
- **Compose your own with `Router`:** route inputs to per-modality encoders (e.g. MiniLM for text, SigLIP for images) — but separate encoders start *unaligned*, so a `Dense` projection + training is required to fuse the spaces.

### 4. Training/fine-tuning multimodal embedders & rerankers (the recipe)

Tom Aarsen's walkthrough fine-tunes `Qwen3-VL-Embedding-2B` for VDR. **NDCG@10 went 0.888 → 0.947 in one epoch — beating the 8B version and every VDR model tested.** This is the headline argument for fine-tuning over scaling up.

The multimodal training pipeline is *identical* to text-only Sentence Transformers training (same `SentenceTransformerTrainer`); only three things differ:

| Component | Choice | Why |
|---|---|---|
| Loss | `CachedMultipleNegativesRankingLoss(mini_batch_size=1)` | Pushes query↔positive up, query↔negatives down. Uses **in-batch negatives** (every other sample's docs, free) + supplied hard negatives. Gradient caching makes a large effective batch fit even at `mini_batch_size=1`, critical for a 2B VLM |
| `MatryoshkaLoss` wrapper | dims `[2048…64]` | One model usable at many sizes. Finetuned model holds within 0.3% of peak down to 512-dim (4x smaller), 92% at 64-dim (32x). Concentrates signal in early dims |
| Model loading | `model_kwargs` (bf16, FA2) + `processor_kwargs` (`max_pixels` = image resolution/memory tradeoff) | The only multimodal-specific config |

Larger batch = more in-batch negatives = stronger signal. `BatchSamplers.NO_DUPLICATES` ensures in-batch negatives are genuinely distinct. Multimodal **rerankers** train similarly via `CrossEncoderTrainer` with either *Any-to-Any + LogitScore* (model generates a token; score = log P("1") − log P("0")) or *Feature-Extraction + Pooling + Dense*.

**The AI-native bit:** Sentence Transformers v5.5 ships a `train-sentence-transformers` Agent Skill (`hf skills add train-sentence-transformers --claude`). You ask Claude Code / Cursor / Codex to "fine-tune a cross-encoder on my `(query, doc)` pairs, mine hard negatives, push to my Hub repo" and it emits a runnable, version-aware script (base-model selection, loss/evaluator choice, hard-negative mining, distillation, LoRA, Matryoshka). The Ettin recipe itself was bootstrapped this way.

### 5. NVIDIA NeMo: domain embedder in under a day, zero manual labels

A six-command CLI pipeline (`nemotron embed sdg|prep|finetune|eval|export|deploy`) fine-tuning `Llama-Nemotron-Embed-1B-v2`. The valuable, transferable ideas:

1. **Synthetic data generation (SDG)** — an LLM reads your docs and generates `(question, answer)` pairs, no human labels. Crucially it generates **multi-hop questions** (1–3 hops) that span multiple passages, plus a quality score per pair (relevance/accuracy/support/clarity) so only above-threshold pairs train.
2. **Hard-negative mining with a false-negative guard** — embed all queries/passages, find the most-similar non-positive passages, but **discard any scoring above 95% of the minimum positive score** (those are probably unlabeled true positives). This margin ceiling is the key trick: hard negatives must be confusing-but-wrong, not secretly-right.
3. **Multi-hop unrolling** — a 2-positive question becomes 2 training examples (same negatives, different positive) so contrastive loss sees each positive independently.
4. **Contrastive fine-tune** at temperature 0.02 (deliberately sharp — justified by high-quality hard negatives), ~1–2 epochs for real data (3 overfits).
5. **Eval on held-out BEIR**, then export to ONNX/TensorRT (+FP8) and deploy behind an OpenAI-compatible `/v1/embeddings` NIM endpoint — drop-in for an existing RAG pipeline.

Whole thing: under a day on one A100/H100 (most of it hands-off), ~2–3 hrs for ~500 docs.

### 6. PaddleOCR 3.5 — the ingestion step that feeds everything above (brief)

Retrieval quality is capped by ingestion quality: "the hard part often starts before the LLM." PaddleOCR 3.5 turns PDFs, scans, screenshots, tables, charts, formulas, and complex layouts into structured data — and now runs with **Hugging Face Transformers as an inference backend** (`engine="transformers"`), so its OCR (PP-OCRv5) and document-parsing (PaddleOCR-VL 1.5) models slot into a PyTorch/Transformers stack with less integration friction (`engine_config` for dtype/device/attention). For raw throughput, the default `paddle_static` backend is still recommended. Note the alternative for image-heavy docs: VDR (section 3) skips OCR entirely by embedding page *images* directly.

## Sources
- `hugging-face-blog-2026-05-28-introducing-the-ettin-reranker-family.md`
- `hugging-face-blog-2026-05-28-granite-embedding-multilingual-r2-open-apache-2-0-multilingu.md`
- `hugging-face-blog-2026-05-28-multimodal-embedding-reranker-models-with-sentence-transform.md`
- `hugging-face-blog-2026-05-28-training-and-finetuning-multimodal-embedding-reranker-models.md`
- `hugging-face-blog-2026-05-28-build-a-domain-specific-embedding-model-in-under-a-day.md`
- `hugging-face-blog-2026-05-28-paddleocr-3-5-running-ocr-and-document-parsing-tasks-with-a.md`

## Related
- [[advanced-rag-techniques]]
- [[pre-retrieval]]
- [[semantic-boundary-chunking]]
- [[agentic-rag]]
- [[graph-rag]]
- [[redis-for-rag]]
- [[llm-agent-evaluation]]
- [[model-compression]]
- [[specialization-beats-scale]]
- [[open-model-releases-spring-2026]]
- [[gemma-4]]
