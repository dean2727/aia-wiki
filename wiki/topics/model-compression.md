# Model Compression

> Shrinking large models for deployment via distillation, pruning, quantization, and architecture choices while preserving most of the accuracy.

**Category**: topics
**Last updated**: 2026-05-25
**Status**: reference

## What it is

The family of techniques that take an oversized model and produce something deployable under real-world latency/memory/cost constraints. Knowledge distillation is the headline method: a pretrained teacher transfers behavior to a smaller student trained from scratch to mimic its outputs (not its weights). The student learns from *soft targets* — full probability distributions / logits — which carry richer signal ("dark knowledge", inter-class confidences) than hard labels, yielding better generalization than training the small model directly on raw data.

Distillation is one option alongside pruning (drop weights/neurons), quantization (lower numeric precision), weight factorization, and efficient base architectures (MobileNet-class). These compose — KD is frequently the *final* step that produces the released checkpoint. The canonical LLM example: train a frontier giant, then distill down to deployable sizes (e.g. a 2T teacher distilled into the released Llama 4 Scout/Maverick siblings). DistilBERT is the reference data point: ~97% of BERT accuracy, 40% fewer params, 60% faster.

## Why it matters

Frontier capability and deployable form factor diverge. Compression is what lets a lab ship a usable model after spending the training budget on something too large to serve. For an engineer the practical reading is: the small open model you actually run was probably distilled from a giant you'll never see, which is why these punch above their parameter count.

## How it works

Distillation loop: feed each example to both teacher (frozen) and student; minimize distillation loss (KL / cross-entropy) between their output distributions. Softmax **temperature > 1** during training softens the teacher's peaks so relative confidences survive as signal; reset to T=1 at student inference.

Three knowledge types (often combined, multi-term loss):

| Type | What's matched | Best for |
|---|---|---|
| Response-based | Teacher output probabilities (soft targets) | Classification, LM, general compression |
| Feature-based | Internal activations / feature maps (e.g. FitNets, L2) | Vision, speech, where intermediate structure matters |
| Relation-based | Pairwise input similarities / attention patterns | Metric learning, face recognition, ranking |

When to reach for distillation over (or with) other compression:

| Situation | Why KD |
|---|---|
| Need small **and** accurate | Better accuracy/efficiency tradeoff than aggressive prune/quant alone |
| Compressing an ensemble | Only KD can fold many models' predictions into one student |
| Cross-architecture transfer | Student architecture is free — deep transformer teacher → shallow CNN student for edge |
| Semi-supervised | Teacher pseudo-labels unlabeled data; student trains on soft labels |
| Hardware / privacy limits | Sometimes only a smaller architecture meets memory/latency; distilled student avoids exposing teacher weights (not a guarantee — students can still leak) |

The tradeoff is an extra training pass for cheap, durable inference. Prune/quantize for incremental wins on an existing architecture; distill when you need a fundamentally smaller model that keeps most of the accuracy. [[grok-4-20]] is the local MoE landmark here — sparse activation as a complementary "compression" lever (serve a fraction of params per token).

## Dean-Relevance

**Fit score**: 4/10
**Adoption path**: watch
**Why**: Dean consumes frontier models via OpenRouter and doesn't self-host or train, so this is landscape literacy — useful for reasoning about *why* a given open model behaves as it does, not a daily lever.
**Analogy**: A mentor distilling the gist of each step to you so you can execute at the right level without carrying all the underlying detail.
**Suggested next step**: —
**Watch for**: Practical on-device / distilled-small-model tooling good enough to run a personalization model for Crafted/Praxis locally — that would flip this to experimental.

## Related
- [[grok-4-20]]
- [[synthetic-data]]
- [[agent-frameworks]]
