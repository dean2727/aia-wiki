# Vision-Language-Action (VLA) Models

> Robotics' "GPT moment" — pulling robot control into the same token/representation space as vision-language models, and the methods (action chunking, flow matching, knowledge insulation) that let one generalist model do dexterous, long-horizon tasks.

**Category**: topics
**Last updated**: 2026-05-25
**Status**: watching

## What it is

A robot policy maps **observations + a goal** to **actions** (joint angles / degrees of freedom). Classically, robotics policies were narrow and brittle — limited tasks, poor transfer. LLMs/VLMs are the opposite: broad, generalizing, "work basically all the time." **Vision-Language-Action models** ask: can we bring robot actions into the *same model* as vision and language, and inherit that generalization?

The arc (per Danny Driess, Physical Intelligence): **PaLM-E** (first embodied VLM) → **RT-2** (first true VLA, actions-as-tokens) → diffusion/**action-chunking** policies → **π0 / π0-FAST** (generalist flow-matching VLAs) → **Knowledge Insulation** and **π0.5** (open-world generalization). Even at low relevance to Dean's work, several *methods* here are domain-transferable.

## Why it matters

The headline: robotics is having its foundation-model moment, but it's **earlier than language** — still effectively in the SFT stage, data-starved (the field's total data is dwarfed by an LLM's pretraining corpus), with little inference-time compute. For an AI engineer the value is in the *transferable ideas*, which keep reappearing across modalities:

- **Action chunking** = commit to a multi-step plan and execute open-loop, instead of replanning every step — a general agent-design principle.
- **Flow matching / diffusion** for **multimodal continuous** outputs — when there are many valid ways to act, model the whole distribution instead of averaging into mush.
- **Knowledge insulation** — protect a pretrained model's general capabilities while bolting on a new skill (a clean answer to catastrophic forgetting).
- **Co-training data mixtures** — the same mixture-weighting problem that shows up in any fine-tuning.

## How it works

### PaLM-E — embodied reasoning as vision-language modeling

Learn an **encoder that maps continuous observations (images, states) into the LM's token-embedding space** — treat sensor inputs "as if they were words." Trained jointly on robot data + general vision-language data, it showed **positive transfer**: training on multiple tasks beat training on any single task (new for robotics at the time). **Catastrophic forgetting** of language only hurt at *small* scale — large models retained language while gaining embodiment. Limitation: PaLM-E **outputs language commands** that rely on separate **low-level controllers** to actually move.

### RT-2 — the first VLA (actions as tokens)

RT-2 closes that gap: **discretize and bin robot actions, then tokenize them as text**, so the LM autoregressively *emits the actions themselves* (action tokenization ↔ de-tokenization). Co-trained on ~⅓ general vision-language + ⅔ robot-action data, it generalized semantically — e.g. "pick up the extinct animal" succeeded unseen. But it hit the **"dexterity wall"**: fine, practical manipulation (folding laundry) didn't come from more data — it needed new architectures.

### Action chunking + diffusion (the dexterity unlock)

Two insights got robotics past the wall:

- **Action chunking**: output a **trajectory of actions** at once, not one action of dimension *d*. The supervision signal is stronger (you predict T steps), robot data is **multimodal** (many valid paths A→B), and committing to one chunk avoids the averaging that kills autoregressive single-step prediction. Execution is **open-loop** over the chunk — like how humans commit to a motion rather than micro-correcting. **Real-time action chunking** conditions the current chunk on state + previous actions to stay reactive.
- **Diffusion policy**: instead of discretizing, **predict continuous action trajectories by denoising**, conditioned on history/observations/goals. Robots want **smooth, globally consistent** plans, and continuous action spaces are naturally multimodal — diffusion models multimodal continuous distributions well, avoiding the compounding errors of step-by-step prediction.

### π0 and π0-FAST

**π0**: a generalist VLA = a **pretrained VLM backbone (SigLIP 400M + Gemma 2.6B)** + an **action expert (~300M)** trained with **flow matching**. The two transformers interact through the **self-attention layers**, so the action expert can be small (good for inference speed). Multiple camera views in; still uses action chunking. Trained across many robots (~903M timesteps). Beats RT-2 on dexterous tasks precisely because of chunking + flow matching (autoregressively predicting ~700 tokens per chunk at 50 Hz is too slow *and* degenerates).

**π0-FAST**: a **FAST tokenizer** for action chunks — apply a **Discrete Cosine Transform** (like JPEG) to the action trajectory, quantize, flatten time-first, and **BPE-compress** (squashing the many zeros where the robot isn't moving). Big compression (up to ~13×) and better training targets (more information per token, PCA-like). Trains **~5× faster** (160k vs 1.2M steps) and fits dexterous data — but **autoregressive decoding is still too slow** for high-rate control.

### Knowledge Insulation & π0.5

**Knowledge Insulation (KI)** — best of both worlds: train the VLM backbone on **discrete FAST actions for representation learning** and **co-train on web data** for generalization, but use a **continuous action expert** for fast, high-quality generation, and **stop gradients** from the action expert flowing into the backbone (so RL-style action training doesn't *destroy* the backbone's knowledge). Adding language-prediction tasks alongside keeps the model attending to the prompt — fixing π0's failure of ignoring instructions (it would "pick up the rag" when told "pick up the spoon" because the scene looked like cleanup). Result: fast training, fast inference, better generalization and instruction-following.

**π0.5**: tests whether **scaling robot data + diversity → scaling performance**. With enough diverse environments (~100), it matches in-domain training and shows **open-world generalization**; web data + cross-embodiment + multi-environment data all contribute.

### What's still missing

Robotics is "in its infancy" on data; little inference-time compute is used; high-level→sub-task decomposition is underexplored; and there's a big disconnect between **computer-vision benchmarks** and what CV can actually do *in* robotics. The bottleneck is data diversity, not (yet) algorithms.

## Related
- [[evolutionary-search-self-improving-agents]]
- [[self-improving-ai-agents]]
- [[train-time-rl-scaling]]
- [[model-compression]]
- [[agentic-rl-exploration]]
