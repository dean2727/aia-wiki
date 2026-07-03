# Computer-Use Agents

> Agents that operate software the way a person does — seeing the screen, reasoning, and clicking/typing across browser, desktop, and mobile — now arriving both as a native frontier-model tool and as small, locally-runnable open models.

**Category**: topics
**Last updated**: 2026-06-28
**Status**: active

## What it is

A computer-use agent perceives a GUI (usually screenshots), decides an action (click, type, scroll, navigate), executes it, and loops — automating work that has no API by driving the same interface a human would. Two June-2026 releases mark the capability maturing on opposite ends of the deployment spectrum:

- **Gemini 3.5 Flash — native computer use.** Google folded computer use into the *main* Flash model as a built-in tool, rather than shipping it as the separate Gemini 2.5 computer-use model it used to be. Developers build agents that see/reason/act across browser, mobile, and desktop via the Gemini API, aimed at long-horizon enterprise automation (continuous software testing, cross-application knowledge work).
- **Holo3.1 (H Company) — fast, local, open.** A Qwen-based open family (0.8B / 4B / 9B / 35B-A3B) built for *robustness across deployment reality*: web + desktop + mobile, multiple agent harnesses, and — for the first time in this lineage — quantized checkpoints (FP8, Q4 GGUF, NVFP4) for fully local, private inference on consumer hardware.

## Why it matters

- **It's the bridge to software without APIs.** The long tail of enterprise and personal workflows lives in apps that were never built to be automated. Computer use turns "is there an integration?" into "can a human do it on screen?" — a much larger surface. This is the practical face of the [[agentic-mesh]] for legacy software.
- **Local + private is now real, which changes the calculus for Dean's 🟡 zones.** Holo3.1 runs the agent on a Windows/Mac machine with the model on the same box (Apple Silicon) or a DGX Spark on the same network — *nothing leaves the user's network*. Quantization barely costs accuracy (FP8 and NVFP4 match each other, ~2 pts below BF16 on OSWorld) while NVFP4 W4A16 gives ~1.74× the throughput of BF16, and harness+quant optimizations compound to a ~2× end-to-end speedup (avg step time 6.8s → 3.3s). For someone cautious about cloud cost and privacy, local computer-use agents are crossing from "interesting" to "deployable."
- **The hard part is distribution shift, not peak benchmark.** Holo3.1's whole framing: strong performance in one setting (browser) doesn't transfer to another (mobile, a different harness). Their gains are about *robustness* — AndroidWorld 67%→79.3% on the 35B, near-parity between function-calling and structured-JSON execution, +25% inside their own product harness. The lesson for builders: evaluate computer-use agents in the exact environment *and harness* you'll ship in (see [[agentic-evals-and-long-horizon-tasks]]).

## How it works

The loop is screenshot → reason → action, but the engineering lives in two places:

**Interface robustness (Holo3.1).** Native support for *function-calling protocols* alongside structured JSON output lets the same model drop into third-party agent stacks without rewriting the action interface. Smaller sizes (0.8B–9B) exist specifically to trade peak capability for cost and on-device privacy.

**Safety against prompt injection (Gemini 3.5 Flash).** Operating in live environments means the screen itself is an attack surface — a malicious page can carry an *indirect prompt injection*. Google's mitigations, presented as defense-in-depth, are the pattern to copy:

- **Targeted adversarial training** for the computer-use behavior.
- **Explicit user confirmation** for sensitive/irreversible actions.
- **Auto-stop** the task when an indirect prompt injection is detected.
- Combine with sandboxing, human-in-the-loop verification, and strict access controls.

This is the [[ai-guardrails]] story applied to agents with hands: the more an agent can *do* in a real environment, the more its perception channel must be treated as untrusted input.

## Related
- [[agentic-mesh]]
- [[ai-guardrails]]
- [[agentic-evals-and-long-horizon-tasks]]
- [[harness-and-scaffolding]]
- [[gemma-4]]
- [[vision-language-action-models]]
