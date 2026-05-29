# Open Model Releases — Spring 2026

> Four open-weight releases that, taken together, show where open models are heading: efficiency over raw scale, hybrid Mamba/MoE architectures, on-device multimodal, and perception models that read scenes instead of just labeling them.

**Category**: topics
**Last updated**: 2026-05-28
**Status**: active

## What it is

A catalog of four open-weight releases that landed on Hugging Face in spring 2026, all under permissive licenses and all sharing one theme: **the open-model frontier moved away from "bigger" and toward "tighter, more specialized, more multimodal."**

- **IBM Granite 4.1** — a dense 3B/8B/30B LLM family where the 8B *dense* model matches the previous-gen 32B-A9B *MoE*; a case study in data-quality-over-scale and a fully-documented training pipeline.
- **IBM Granite 4.0 3B Vision** — a compact VLM shipped as a *LoRA adapter* on a 3B base, purpose-built for enterprise document/table/chart/form extraction.
- **NVIDIA Nemotron 3 Nano Omni (30B-A3B)** — a long-context omni model (text + image + video + *native audio*) on a hybrid Mamba-Transformer-MoE backbone, with NVFP4 checkpoints aimed at consumer GPUs.
- **Falcon Perception (0.6B) + Falcon OCR (0.3B)** — a sub-billion-param early-fusion Transformer for open-vocabulary grounding/segmentation that beats SAM 3, plus a 0.3B OCR sibling competitive with models 3-10× its size.

None of these is a frontier-chasing flagship. Each is a bet that the next open-model wins come from architecture and training discipline, not parameter count.

## Why it matters

The throughline across all four — read them as one signal, not four:

- **Efficiency is the headline, not a footnote.** Granite 4.1-8B dense beating a 32B-A9B MoE, Falcon OCR at 0.3B beating GPT-5.2-class OCR, Nemotron Omni shipping NVFP4 to fit a 24GB card — the competitive axis has shifted from "what scores highest" to "what scores this high *per parameter / per dollar / per watt*." This is the same lesson [[deepseek-v4]] teaches from the inference-cost side, arriving here from the model-size side. See [[specialization-beats-scale]].
- **Hybrid architectures are going mainstream.** Nemotron Omni interleaves Mamba state-space layers, MoE layers, and a few GQA attention layers in one backbone — using each where it's cheapest. Pure-transformer-everywhere is no longer the default assumption for an open release.
- **On-device multimodal is becoming real.** A 0.3B OCR model with MLX/Apple-Silicon integration, a 0.6B segmentation model, NVFP4 omni checkpoints — these are sized to run *locally*, not just in a datacenter. This is exactly the local/on-device frontier Dean tracks cautiously.
- **Perception is shifting from "label" to "read."** Falcon Perception resolves *"the third window from the left"* or *"the bottle labeled 168"* — compositional, OCR-aware, relational grounding that SAM-style fixed-query decoders can't do. Granite Vision and Nemotron Omni push the same way on documents. Perception models are starting to *understand* scenes, not just segment object classes.

For an AI engineer: the open option is no longer "cheaper but falls over on the hard stuff." For document/extraction/perception workloads specifically, open models in this batch are at or above the closed frontier — and small enough to self-host. See [[open-source-ai-state-spring-2026]].

## How it works

### Comparison table

| Model | Params | Context | Modalities | License | Notable architecture |
|---|---|---|---|---|---|
| **Granite 4.1** | 3B / 8B / 30B (dense) | up to 512K | text | Apache 2.0 | Dense decoder-only; GQA + RoPE + SwiGLU + RMSNorm; 5-phase pretrain → SFT → multi-stage RL; FP8 variants |
| **Granite 4.0 3B Vision** | 3B (+ LoRA adapter) | [Needs Verification] | text + image | Apache 2.0 | LoRA adapter on Granite 4.0 Micro; DeepStack injection (semantic features early, spatial features late) |
| **Nemotron 3 Nano Omni** | 30B total / 3B active (MoE) | LLM 5+ hours; audio in ≤20 min | text + image + video + audio | NVIDIA open (BF16/FP8/NVFP4) | Hybrid Mamba(23) + MoE(23, 128 experts top-6) + GQA(6); C-RADIOv4-H vision + Parakeet audio encoders; Conv3D + EVS video compression |
| **Falcon Perception** | 0.6B | long-context (dense scenes, 600 inst/expr) | text + image (grounding/seg) | [Needs Verification] (TII) | Early-fusion single Transformer; hybrid attention mask (image bidirectional, text/task causal); Chain-of-Perception `<coord>→<size>→<seg>` |
| **Falcon OCR** | 0.3B | — | text + image (OCR) | [Needs Verification] (TII) | Same early-fusion backbone as Perception, trained from scratch for OCR; FlexAttention serving, MLX support |

### Granite 4.1 — data discipline beats MoE complexity

A family of **dense, decoder-only** LLMs (3B/8B/30B), trained from scratch on ~15T tokens. The standout result: the **8B dense model matches or beats the previous-gen Granite 4.0-H-Small (32B-A9B MoE)** on IFEval, AlpacaEval, MMLU-Pro, BBH, GSM8K, BFCL v3, and more — a simpler architecture with far fewer params winning on training rigor.

How it was built (the actual point of the release — IBM published the full recipe):

- **5-phase pretraining**, progressively annealing the data mix from web-heavy → quality/instruction/reasoning-heavy: (1) general 10T tokens, (2) math/code 2T, (3) high-quality annealing 2T (chain-of-thought + synthetic instructions blended in), (4) refinement 0.5T, (5) **long-context extension 4K→512K** in staged 32K/128K/512K steps with a model-merge after each stage to avoid degrading short-context performance.
- **SFT on ~4.1M curated samples** gated by an **LLM-as-Judge** scoring six weighted dimensions (instruction-following, correctness, completeness, conciseness, naturalness, calibration), with hard-reject rules for hallucination/false-premise/bad-computation, plus deterministic rule-based filtering and global dedup.
- **Multi-stage RL** (on-policy GRPO with DAPO loss): Multi-domain RL → RLHF → Identity/Knowledge-calibration RL → Math RL, sequenced specifically to minimize catastrophic forgetting (RLHF dropped math scores; a dedicated Math RL stage recovers and surpasses them).

Deliberately ships **no long chain-of-thought** for predictable latency, stable token usage, and lower cost — an explicit production/enterprise posture. FP8 quantized variants (~50% memory/disk reduction, vLLM-optimized) released alongside. Trained on a GB200 NVL72 cluster (see [[training-at-scale-infrastructure]]).

### Granite 4.0 3B Vision — modular document intelligence

A compact VLM for **enterprise document understanding**: table extraction, chart→CSV/code/summary, and semantic key-value-pair extraction from forms. Three design bets:

- **Shipped as a LoRA adapter on Granite 4.0 Micro**, not a standalone model — so one deployment serves both multimodal and text-only workloads, falling back to the base LM automatically when vision isn't needed. Clean modularity for mixed pipelines.
- **DeepStack injection**: instead of injecting visual features at a single point, abstract/semantic features route into *earlier* layers and high-resolution *spatial* features into *later* layers — so the model captures both *what* is in a document and *where*, which matters for tables and forms where layout is meaning.
- **ChartNet** training data: a 1.7M-sample code-guided synthesis pipeline (24 chart types, 6 plotting libraries) where each sample aligns five views — plotting code, rendered image, data table, NL summary, QA pairs — teaching the model what a chart *encodes*, not just what it looks like.

Results: top Chart2Summary (86.4%) beating much larger models; strongest table extraction (TEDS) across PubTables-v2 / OmniDocBench / TableVQA; 85.5% exact-match zero-shot on the VAREX form-extraction benchmark. Pairs with **Docling** for end-to-end multi-page PDF pipelines.

### Nemotron 3 Nano Omni — hybrid backbone, native audio, long multimodal context

An **omni-modal** model (text + image + video + audio) extending NVIDIA's Nemotron line. Unified **encoder-projector-decoder** design: a Nemotron 3 Nano **30B-A3B** language backbone, **C-RADIOv4-H** vision encoder, **Parakeet-TDT-0.6B** audio encoder, each wired in via a lightweight 2-layer MLP projector, after which **vision/audio/text tokens are interleaved and processed jointly**.

The backbone is the interesting part — a **hybrid Mamba-Transformer-MoE** stack: 23 Mamba selective-state-space layers (cheap long-context), 23 MoE layers (128 experts, top-6 routing, plus a shared expert), and 6 GQA attention layers (global interaction). Mamba for length, MoE for capacity, attention for expressivity — each used where it pays. (Mamba/SSM context with [[llm-memory-architectures]].)

Multimodal-specific efficiency:

- **Dynamic resolution at native aspect ratio** — 1,024 to 13,312 patches/image (≈512×512 up to 1840×1840), replacing v2's tiling; critical for OCR-heavy docs, tables, slides, GUIs.
- **Conv3D tubelet embedding** for video — fuses each consecutive frame *pair* into one tubelet before the ViT, halving vision tokens (double the frames at the same budget, or halve tokens at the same frames).
- **EVS (Efficient Video Sampling)** at inference — keeps the first frame fully, then for each later frame keeps only "dynamic" (changed) tokens and drops static ones; stacks with Conv3D for compounding compression.
- **Native audio** (16 kHz, trained to 20-min inputs, LLM context supports 5+ hours) — audio enters the shared sequence as tokens, not as a pre-transcribed text string, enabling genuine cross-modal reasoning (e.g., matching what's *shown* to what's *said*).

Claimed up to **9× system throughput / 2.9× single-stream reasoning speed** vs alternatives; best-in-class on MMLongBench-Doc, OCRBenchV2, WorldSense, DailyOmni, VoiceBench. Trained for **agentic computer use** (screenshot grounding, GUI action selection). RL stage intentionally includes *unanswerable* cases to teach abstention over hallucination. Ships **BF16 / FP8 / NVFP4** — NVFP4 is the only one realistic on a 24GB consumer card (FP8 ≈30GB, BF16 ≈60GB).

### Falcon Perception — early fusion replaces the perception pipeline

A **0.6B** open-vocabulary grounding/segmentation model from TII. The thesis: most perception systems are modular pipelines (frozen vision backbone → fusion/decoder → matching → post-processing) that are hard to scale and accumulate complexity. Falcon Perception asks whether **one early-fusion Transformer** can do it all — and largely answers yes.

- **Single backbone, hybrid attention mask**: image patches and text/task tokens share parameters from layer one. Image tokens attend **bidirectionally** (like a vision encoder); text/task tokens attend **causally** (autoregressive prediction). One model behaves as both.
- **Chain-of-Perception** output interface: each instance is emitted as `<coord> → <size> → <seg>` — center first (which object?), then extent (how big?), then a single segmentation embedding that dot-products with upsampled image features to produce a full-res mask. Geometry-first ordering reduces ambiguity and avoids the Hungarian-matching machinery of decoder-based segmentation.
- **Variable-length, autoregressive** instance output — handles zero to hundreds of instances, where fixed-query decoders (SAM 3) run out of query tokens past ~200.
- Initialized via **multi-teacher distillation** (DINOv3 for local features, SigLIP2 for language alignment); trained on 54M images / 195M positive expressions / 488M hard negatives at a strict 1:1 positive:negative ratio (making *presence calibration* a first-class target).

Results: **68.0 Macro-F1 on SA-Co vs 62.3 for SAM 3.** The gap *widens with prompt complexity* on its own **PBench** diagnostic (which isolates capabilities): L2 OCR-guided +13.4, L3 spatial +21.9, L4 relational +15.8, Dense +14.2 over SAM 3. Remaining weakness: presence calibration (MCC 0.64 vs 0.82). The framing is explicitly a "bitter lesson" for perception — gains from data/compute/training signal, not from bolting on modules.

**Falcon OCR (0.3B)**: the same early-fusion backbone trained *from scratch* (no distillation — glyph-level features differ too much from object-level ones) purely for OCR. Scores 80.3 on olmOCR (within 1.7 pts of the top system) and 88.64 on OmniDocBench (ahead of DeepSeek OCR v2, GPT 5.2, Mistral OCR 3), leading on multi-column and tables — at ~3× smaller than 0.9B-class OCR VLMs, with the highest open-source OCR throughput. Ships with a paged-inference engine (FlexAttention, paged KV cache, continuous batching, CUDA graph capture) plus a **vLLM Docker server and MLX integration for Apple Silicon**.

## Dean-Relevance

**Adoption path**: experimental
**Why**: This batch is the clearest signal yet that open models have caught — and on document/perception/extraction workloads, passed — the closed frontier, while shrinking to sizes you can self-host. Praxis currently leans on hosted OpenRouter Claude/Gemini and OpenAI embeddings; nothing here replaces a reasoning agent. But two are *directly* slot-in evaluable: Granite 4.0 3B Vision / Falcon OCR for any document or chart ingestion path (cheaper, self-hostable, no per-token API bill, no data leaving your infra), and Granite 4.1's published training recipe is a reference for *how* a disciplined small-model pipeline is built. The MLX/NVFP4 sizing makes the local/on-device frontier you track cautiously suddenly practical rather than hypothetical.
**Analogy**: Think of the closed frontier as ordering from a Michelin kitchen — superb, but you pay per plate and the recipe stays secret. This batch is more like four chefs publishing their cookbooks *and* selling you a countertop appliance that makes the dish at home: Granite 4.1 hands you the full recipe (every pretraining phase, every RL stage), and Falcon/Granite-Vision hand you a 0.3-0.6B appliance small enough to run on your own counter (Apple Silicon, a single 24GB card). The win isn't a better dish — it's owning the kitchen.
**Suggested next step**: If any Praxis pipeline ingests PDFs, forms, or charts (content prerequisites, source documents), spin up **Falcon OCR (0.3B)** via its vLLM/MLX path or **Granite 4.0 3B Vision + Docling** on a single GPU and benchmark extraction accuracy + cost against your current hosted-model call. That's a low-risk, self-contained experiment that tests the whole "open + local for narrow tasks" thesis on a real workload.

## Sources

- Hugging Face / IBM Granite, *"Granite 4.1 LLMs: How They're Built"* (2026-04-29)
- Hugging Face / IBM Granite, *"Granite 4.0 3B Vision: Compact Multimodal Intelligence for Enterprise Documents"* (2026-03-31)
- Hugging Face / NVIDIA, *"Introducing NVIDIA Nemotron 3 Nano Omni: Long-Context Multimodal Intelligence for Documents, Audio and Video Agents"* (2026-04-28)
- Hugging Face / TII, *"Falcon Perception"* (2026-04-01)

## Related

- [[deepseek-v4]]
- [[gemma-4]]
- [[open-source-ai-state-spring-2026]]
- [[specialization-beats-scale]]
- [[training-at-scale-infrastructure]]
- [[model-compression]]
- [[llm-memory-architectures]]
- [[vision-language-action-models]]
