# Choosing a PEFT Technique (Beyond LoRA)

> LoRA is the default 98% of the time mostly because of momentum, not because it's always best — the durable move is to benchmark a few PEFT methods on *your* data along a Pareto frontier of accuracy vs. memory.

**Category**: topics
**Last updated**: 2026-06-28
**Status**: active

## What it is

Parameter-efficient fine-tuning (PEFT) — adapting a model by training a small number of added parameters while freezing the base — is known substrate for Dean (LoRA/QLoRA/adapters are in his baseline). What's new here is an *empirical, no-horse-in-the-race* finding from Hugging Face's PEFT team: LoRA's dominance is largely self-reinforcing, and for some tasks it's strictly beaten.

The usage numbers are stark: of 20,834 HF model cards mentioning exactly one PEFT technique, **98.4% are LoRA**; ~95% of image-gen PEFT checkpoints are LoRA; 71% of `from peft import` GitHub hits are LoRA. The plausible cause isn't "LoRA is best for everyone" — it's that LoRA was early, so it has the most tutorials, the best downstream support, and momentum that feeds on itself.

## Why it matters

For anyone who actually fine-tunes open models (Praxis, Dell work), this reframes a default decision:

- **Don't trust paper claims; benchmark on your own data.** Nearly every PEFT paper claims to beat LoRA, but results are biased by uneven hyperparameter tuning (one study matched "better" methods just by tuning LoRA's learning rate), inconsistent baselines, and non-reproducible code. The reliable signal is a controlled run on *your* dataset, same base model / hardware / eval — which the PEFT library makes a one-line config swap.
- **Think in tradeoffs (Pareto frontier), not a single "best."** Track test accuracy *and* VRAM (and runtime, checkpoint size, forgetting/drift). A method is only worth considering if it's on the frontier — i.e. nothing beats it on *both* accuracy and memory at once.
- **Even "use LoRA" should mean a LoRA variant.** Vanilla LoRA is often dominated by its own variants: rank-stabilized init (rs-LoRA) for accuracy, LoRA-FA for memory. On the math benchmark, plain LoRA hit 48.1% @ 22.5GB while rs-LoRA hit 53.2% and LoRA-FA needed only 20.2GB — so "just use LoRA" is leaving points or gigabytes on the table.

## How it works

The HF PEFT benchmark evaluates all techniques under identical conditions (same base, dataset, code, hardware) on two tasks — math chain-of-thought (Llama-3.2-3B → GSM8K) and image-gen concept learning (FLUX → "cat plushy") — reporting accuracy, VRAM, forgetting, runtime, and checkpoint size.

Representative findings:

| Task | LoRA | On the frontier with it |
|---|---|---|
| LLM math (acc vs VRAM) | rs-LoRA 53.2% @ 22.6GB (on frontier) | **BEFT** 32.9% @ 20.2GB (cheaper); **Lily** 54.9% @ 25.6GB (more accurate) |
| Image gen (DINO-sim vs VRAM) | 0.697 @ 9.97GB (**below** frontier) | **OFT** 0.708 @ 9.01GB (strictly dominates LoRA) |

Two practical escape hatches the post supplies:

- **Serving objection ("vLLM/llama.cpp only load LoRA"):** PEFT now **converts non-LoRA adapters into LoRA checkpoints** with near-identical scores (e.g. GraLoRA → LoRA, similarity 0.702 → 0.694), so you can train with a better method and still serve through LoRA-only stacks.
- **Switching cost is ~one line:** `LoraConfig(...)` → `OFTConfig(...)` with the same `target_modules`.

Caveats the authors are honest about: hyperparameter sweeps can't be exhaustive across 40+ methods (contribute a PR if you think a method is under-tuned); benchmarks can't capture every capability (e.g. Cartridges targets long-prompt compression, unmeasured here); and method choice is also constrained by which layer types are modifiable, quantization support, and whether the adapter can be merged.

**The takeaway:** LoRA is a fine default, not an automatic one. Run a short PEFT sweep on your own task before committing.

## Related
- [[rl-post-training-libraries]]
- [[model-compression]]
- [[specialization-beats-scale]]
- [[embeddings-and-rerankers]]
