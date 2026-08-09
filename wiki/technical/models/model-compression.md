# Model Compression

> Shrinking large models for deployment via distillation, pruning, quantization, and architecture choices while preserving most of the accuracy.

**Category**: topics
**Last updated**: 2026-08-09
**Status**: reference

## What it is

The family of techniques that take an oversized model and produce something deployable under real-world latency/memory/cost constraints. Knowledge distillation is the headline method: a pretrained teacher transfers behavior to a smaller student trained from scratch to mimic its outputs (not its weights). The student learns from *soft targets* — full probability distributions / logits — which carry richer signal ("dark knowledge", inter-class confidences) than hard labels, yielding better generalization than training the small model directly on raw data. Teacher-student compression dates to 2006 and was aimed at ensembles; the temperature-softmax formulation and the "dark knowledge" framing arrived with Hinton, Vinyals and Dean in 2015.

Distillation is one option alongside pruning (drop weights/neurons — the oldest branch, back to 1989), quantization (lower numeric precision), weight factorization, and efficient base architectures (MobileNet-class). These compose — KD is frequently the *final* step that produces the released checkpoint. The canonical LLM example: train a frontier giant, then distill down to deployable sizes (e.g. a 2T teacher distilled into the released Llama 4 Scout/Maverick siblings). DistilBERT (2019) is the reference data point: ~97% of BERT accuracy, 40% fewer params, 60% faster. [The announcement blog reported 95% and was later amended to the paper's 97%; both figures still circulate.]

## Why it matters

Frontier capability and deployable form factor diverge. Compression is what lets a lab ship a usable model after spending the training budget on something too large to serve. For an engineer the practical reading is: the small open model you actually run was probably distilled from a giant you'll never see, which is why these punch above their parameter count.

The motive has shifted, though, and it is worth being precise about. In the clearest first-party account — Gemma 2 (2024) — distillation is used less to *shrink* a large model than to escape the data budget: replacing the one-hot next-token target with the teacher's full distribution gives a richer gradient per token, which let the 2B and 9B train productively on more than 50× the compute-optimal token count and land competitive with models 2–3× bigger. The giant is a source of training signal no dataset can supply, not just a thing being compressed.

The same inversion happened on the quantization side. Reducing precision started as a deployment step and became a training technique once QLoRA (2023) showed gradients could flow through a frozen 4-bit base model.

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

## Timeline

_Each technique here arrived as a concession to deployment and ended up as a decision about training._

- `1989` (paper) LeCun, Denker and Solla present Optimal Brain Damage at NeurIPS, pruning weights by second-derivative saliency instead of magnitude. — First principled pruning, and the first demonstration that half a trained network's weights can be deleted with no loss; framed as a generalization tool, not a deployment one. [source](https://proceedings.neurips.cc/paper_files/paper/1989/hash/6c9882bbac1c7093bd25041881277658-Abstract.html)
- `2006-08` (paper) Buciluă, Caruana and Niculescu-Mizil publish Model Compression at KDD, training a compact network on ensemble-labeled data. — Established teacher-student compression nine years before distillation was named, and identified the transfer-data bottleneck that still governs it. [source](https://doi.org/10.1145/1150402.1150464)
- `2014-12` (paper) Romero et al. publish FitNets, supervising a student with the teacher's intermediate representations as hints. — Extended teacher-student training beyond outputs, so a student could be thinner and deeper than its teacher rather than merely smaller. [source](https://doi.org/10.48550/arxiv.1412.6550)
- `2015-03` (method) Hinton, Vinyals and Dean publish Distilling the Knowledge in a Neural Network, introducing the temperature-softmax formulation. — Replaced Caruana's logit matching with softened output distributions, naming the inter-class signal dark knowledge and giving the field its vocabulary. [source](https://arxiv.org/pdf/1503.02531)
- `2018-03` (paper) Frankle and Carbin publish the Lottery Ticket Hypothesis, finding sparse subnetworks that train to full accuracy when reset to their original initialization. — Turned pruning from a post-hoc trick into a claim about what over-parameterized training is for, since a randomly reinitialized subnetwork fails where the original initialization succeeds. [source](https://arxiv.org/pdf/1803.03635)
- `2019-10` (release) Hugging Face release DistilBERT, distilling BERT during pre-training with a combined language-modeling, distillation and cosine-distance loss. — Moved distillation from task-specific models to pre-training and from vision to NLP: 40% fewer parameters, 60% faster, 97% of BERT's GLUE score. [source](https://arxiv.org/abs/1910.01108v1)
- `2022-08` (method) Dettmers et al. publish LLM.int8(), isolating roughly 0.1% of outlier feature dimensions in 16-bit while quantizing the rest to 8-bit. — Made int8 inference lossless at 175B by working around emergent outlier features, halving memory and putting BLOOM-scale models on a single consumer-GPU server. [source](https://papers.nips.cc/paper_files/paper/2022/file/c3ba4962c05c49636d4c6206a97e9c8a-Paper-Conference.pdf)
- `2022-10` (method) Frantar et al. publish GPTQ, one-shot post-training quantization to 3 or 4 bits using approximate second-order information. — Put a 175B model on one GPU for generative inference for the first time, quantizing it in about four GPU hours with negligible degradation. [source](https://doi.org/10.48550/arxiv.2210.17323)
- `2023-05` (method) Dettmers et al. publish QLoRA, backpropagating through a frozen 4-bit base model into LoRA adapters with NF4, double quantization and paged optimizers. — Crossed quantization over from a serving step to a training technique, cutting 65B finetuning from over 780GB to under 48GB with no loss against 16-bit. [source](https://doi.org/10.48550/arxiv.2305.14314)
- `2024-08` (release) Google DeepMind publish the Gemma 2 report, training the 2B and 9B models by distillation from a larger teacher instead of next-token prediction. — Reframed distillation from compression to data-budget escape: the small models trained on over 50 times the compute-optimal token count and matched models two to three times their size. [source](https://doi.org/10.48550/arxiv.2408.00118)
- `2026-05` (wiki) Page created by a wiki run — knowledge distillation vs. pruning/quantization
- `2026-08` (wiki) Backfilled the compression lineage from a deep-research run, adding ten sourced events from 1989 onward

## Sources

- Buciluă, Caruana, Niculescu-Mizil, *Model compression*, KDD 2006 — https://doi.org/10.1145/1150402.1150464
- Hinton, Vinyals, Dean, *Distilling the Knowledge in a Neural Network*, 2015 — https://arxiv.org/pdf/1503.02531
- Romero et al., *FitNets: Hints for Thin Deep Nets*, 2014 — https://doi.org/10.48550/arxiv.1412.6550
- LeCun, Denker, Solla, *Optimal Brain Damage*, NeurIPS 1989 — https://proceedings.neurips.cc/paper_files/paper/1989/hash/6c9882bbac1c7093bd25041881277658-Abstract.html
- Frankle, Carbin, *The Lottery Ticket Hypothesis*, 2018 — https://arxiv.org/pdf/1803.03635
- Sanh et al., *DistilBERT*, 2019 — https://arxiv.org/abs/1910.01108v1
- Dettmers et al., *LLM.int8()*, 2022 — https://papers.nips.cc/paper_files/paper/2022/file/c3ba4962c05c49636d4c6206a97e9c8a-Paper-Conference.pdf
- Frantar et al., *GPTQ*, 2022 — https://doi.org/10.48550/arxiv.2210.17323
- Dettmers et al., *QLoRA*, 2023 — https://doi.org/10.48550/arxiv.2305.14314
- Gemma Team, *Gemma 2 technical report*, 2024 — https://doi.org/10.48550/arxiv.2408.00118

## Related
- [[grok-4-20]]
- [[synthetic-data]]
- [[agent-frameworks]]
