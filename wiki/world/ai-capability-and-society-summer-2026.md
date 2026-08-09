# AI Capability and Society — Summer 2026

> Three mid-2026 signals that capability is now crossing thresholds with direct societal stakes: AI reliably out-persuades expert humans, AI-enabled cyberattacks are becoming autonomous, and serious researchers are openly modeling the path from AGI to superintelligence.

**Category**: synthesis
**Last updated**: 2026-06-28
**Status**: active

## What it is

A grouped read of three findings that aren't product launches but reset the backdrop against which everything else (the [[frontier-model-launches-summer-2026]], agent tooling) should be judged. The connective tissue: capabilities that used to be hypothetical risks now have measured, real-world effect sizes.

- **Superpersuasion.** A large study (Oxford / UK AISI / Stanford / LSE; 18,978 conversations, 6,923 people) found AI systems "reliably more persuasive than expert humans" on real policy attitudes and real money.
- **Autonomous cyber.** Anthropic's Frontier Red Team mapped 832 banned malicious accounts (Mar 2025–Mar 2026) onto MITRE ATT&CK and found AI use shifting from initial access to deep, post-compromise, semi-autonomous operations.
- **Paths to ASI.** A DeepMind paper and an Asterisk interview (METR's Ajeya Cotra) treat the AGI→superintelligence transition as a forecasting problem worth taking seriously now, alongside early "symptoms" of recursive self-improvement.

## Why it matters

This is the part of the wiki closest to Dean's animating concern — how AI interfaces with human judgment, growth, and society — so the implications matter more than the headlines.

**Persuasion is the one to internalize.** The effect sizes are not marginal:

| Finding | Result |
|---|---|
| AI vs. every class of human persuader (laypeople, tournament-selected, elite debaters) | AI exceeded **all** of them |
| Coaching humans with the very AI that beat them | Narrowed but **did not close** the gap |
| AI vs. professional canvassers, real Save the Children donations | AI **~3×** more effective; +10.8 pp of the £1 bonus |

Crucially, the *source* of AI's edge was identified: **throughput of information**, not some ineffable rhetorical magic. When the AI was constrained to human message length and human typing speed, its advantage over coached elite debaters collapsed from +4.1 pp to ~0. The persuasive power lives in how fast it can marshal and deliver relevant information — which is exactly the lever that scales with deployment. The societal fork the authors pose: persuasion this cheap could *consolidate* influence among the already-powerful (better advertising, state messaging) **or** *democratize* it (pro se litigants, small charities, grassroots advocates). "Not voting is voting" — the allocation choice is itself a choice.

**The cyber finding reframes "who is dangerous."** Anthropic's data shows the old risk signals breaking down:

- Threat actors increasingly apply AI *deep* in the attack lifecycle — AI-assisted account discovery rose 8.9% while AI phishing fell 8.6%; post-compromise techniques that once required real skill are now available to less-sophisticated actors.
- Medium-or-higher-risk actors jumped from **33% → 56%** across the two six-month halves (~1.7×).
- Neither the number of techniques (least-skilled used ~16, most-skilled ~20) nor the interface (Claude Code vs. API vs. chat) correlates with risk anymore. **The durable differentiator is the scaffolding** — whether the actor built an architecture that lets the model *chain* attack stages with minimal human input. That's the same "the structure is the product" thesis from [[context-engineering]], turned to offense.
- MITRE ATT&CK has *no ID* for agentic orchestration (a model autonomously doing recon → exploit → credential theft → tactical decisions). The framework the whole security industry uses doesn't yet name the most dangerous behavior — which is why both labs are gating cyber capability (see [[frontier-model-launches-summer-2026]]).

**The ASI discussion matters because it's no longer fringe.** DeepMind enumerates concrete pathways (scaling; an algorithmic paradigm shift like the next Transformer/MoE; recursive self-improvement; group-agent emergence) and argues for preparing across *many* scenarios rather than betting one timeline. Jack Clark's honest read: a "co-creation RSI" loop has plausibly already started (AI is measurably speeding up AI research — cf. the [[frontier-model-launches-summer-2026]] genomics result and Jalapeño's AI-accelerated chip design in [[llm-inference-serving-internals]]), but today's systems still lack paradigm-shifting creativity, so whether it compounds or tapers is genuinely open. A useful reframing from the same issue: "self-sustaining AI" (systems that need no human cognitive *or physical* input, gated on humanoid robotics) is effectively a measure of *declining human leverage* — a cleaner thing to track than doom narratives.

## How it works

The throughline for a builder/thinker like Dean:

1. **Measure effect sizes, then design.** Persuasion shows why: the actionable insight (constrain throughput → erase the edge) only appeared because the study isolated the mechanism. Treat "is this capability dangerous/useful?" as an empirical question with a measurable answer, not a vibe.
2. **Scaffolding is the risk and the product.** Offensive cyber, agent products, and persuasion all concentrate their power in the *structure around the model*, not the raw weights. Governance that targets only model capability (and not orchestration) will keep missing the real differentiator.
3. **Forecast in scenarios, monitor continuously.** DeepMind's prescription — hold a diverse set of forecasts, benchmark and update their relative plausibility over time — is itself a systems-thinking discipline, and the right posture for a fast-moving frontier.

## Timeline

- `2026-06` (wiki) Page created by a wiki run — grouped: superpersuasion study, AI-enabled cyber threats (MITRE ATT&CK gaps), paths to ASI/RSI

## Sources

- Import AI 462 (Jack Clark), *"Superpersuasion; self-sustaining AI; paths to ASI"* (2026-06-22) — covering the Oxford/AISI persuasion study, the Cotra/Lee Asterisk interview, DeepMind's *From AGI to ASI*, and Recursive's automated-research results
- Anthropic Frontier Red Team, *"What we learned mapping a year's worth of AI-enabled cyber threats"* (2026-06-03)

## Related
- [[frontier-model-launches-summer-2026]]
- [[ai-guardrails]]
- [[computer-use-agents]]
- [[context-engineering]]
- [[llm-inference-serving-internals]]
