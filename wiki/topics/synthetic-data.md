# Synthetic Data

> Artificially generated data that mimics the statistical properties of real data, used to fix class imbalance, sidestep privacy limits, cover rare cases, and accelerate iteration.

**Category**: topics
**Last updated**: 2026-05-25
**Status**: reference

## What it is

Generated data standing in for real data when collection is impractical, restricted, or too slow. Four canonical drivers: class imbalance (fraud, credit — minority class rare but critical), privacy/regulation (HIPAA, GDPR — simulate without exposing real records), rare/hazardous scenarios (crashes, failures in robotics/AV), and dev velocity (generate on demand instead of waiting on collection/labeling).

Methods span a complexity ladder. Sampling from declared distributions (NumPy/pandas: age ~ Normal(35), salary correlated with age) is fast and intuitive but breaks on nonlinear, high-dimensional relationships. Above that sit SMOTE (interpolation-based oversampling) and CTGAN (GAN for mixed-type tabular). GenAI generation (LLM text, StyleGAN images, audio pitch/noise/tempo augmentation) covers unstructured modalities.

The persistent trap: synthetic ≠ automatically safe. GANs can overfit and memorize training rows, so a "synthetic" record can be a near-verbatim real one — a genuine privacy leak. Synthetic data always needs a privacy audit before sharing.

## Why it matters

For engineers, synthetic data is the lever for evaluation and edge-case coverage when real labeled data is scarce or sensitive. But it carries failure modes (mode collapse, memorization, bias amplification) that don't show up in a single similarity score — so the engineering value is as much in *validating* generated data as in generating it.

## How it works

| Method | Mechanism | Strength | Weakness |
|---|---|---|---|
| Distribution sampling | Draw from declared marginals/relations | Trivial, fast, controllable | No realism for nonlinear/high-dim structure |
| SMOTE | Interpolate new minority points between nearest neighbors | Smooths decision boundaries for numeric data | Poor on categorical; bad hybrids in noisy/overlapping or high-dim space; ignores feature interactions |
| CTGAN | Conditional GAN on discrete columns; learns joint distribution of mixed types | Captures dependencies ("under 10 ⇏ manager"); privacy-safer generation | Slow, needs tuning, prone to mode collapse |
| GenAI (LLM/StyleGAN/audio aug) | Model-generated samples or transformations | Covers text/vision/audio, low-resource domains | Can inject bias/artifacts; needs realism+privacy eval |

**Evaluation is three-dimensional — no single metric suffices:**

| Axis | Check |
|---|---|
| Realism | KS test (numeric marginals), chi-square (categorical counts) |
| Utility | Train on synthetic, score on held-out **real**; t-SNE/PCA overlap as visual sanity check |
| Privacy | Nearest-neighbor / distance-to-nearest-real scan; membership inference tests for memorization |

**Limitations to flag:**
- **Mode collapse** — generator emits a narrow slice of the distribution (e.g. only common age groups, dropping infants/elderly); worse on small/imbalanced data or over-regularized models.
- **Memorization** — verbatim training samples leak; membership inference can confirm a record was in training.
- **Bias amplification** — synthetic generation faithfully reproduces *and often exaggerates* skews in the source (underrepresented group gets even rarer). Audit the generation process, not just downstream models.

This is where synthetic data meets [[llm-agent-evaluation]] — generated eval sets need the same realism/utility/privacy scrutiny — and [[advanced-rag-techniques]], where synthetic query/doc pairs power HyDE and embedding-adapter training.

## Dean-Relevance

**Fit score**: 6/10
**Adoption path**: experimental
**Why**: Generating synthetic eval sets and seed personalization data for Crafted/Praxis is plausibly useful, and the privacy/bias audit discipline maps directly to building on user growth data.
**Analogy**: Building a dataset from a recipe — declare the ingredients (distributions) and ratios (mean/variance), combine into repeatable structured data.
**Suggested next step**: When building eval sets for Crafted/Praxis, generate synthetic user scenarios with an LLM and validate utility by scoring a model on held-out real interactions before trusting them.
**Watch for**: LLM-based synthetic data pipelines with built-in privacy/distance auditing maturing into a standard tool — that turns the audit step from manual to default.

## Related
- [[llm-agent-evaluation]]
- [[advanced-rag-techniques]]
- [[model-compression]]
