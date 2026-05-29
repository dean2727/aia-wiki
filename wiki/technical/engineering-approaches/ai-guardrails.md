# AI Guardrails

> Constraints that keep agent behavior safe, predictable, and on-policy — from dialog scripting to LLM-native validators and hard stops.

**Category**: topics
**Last updated**: 2026-05-25
**Status**: reference

## What it is

Guardrails enforce what an agent must and must never do. NVIDIA **NeMo Guardrails** is the reference toolkit: a `config.yml` declares the engine/model and an `instructions` block (effectively the system prompt), while **Colang** (`.co` files) defines conversational flows — named flows that tie `define user`/`define bot` intents into structured dialogue paths.

The important shift is *how much* to script. The old approach hard-codes `define bot` strings for total control (still common in finance/healthcare/legal where predictability is mandatory). The **modern approach** is leaner: write a strong system prompt to govern behavior, use LLM-native guardrails (model built-in safety, output validators) instead of dialog scripting, and reserve NeMo rails for **hard stops** — things the bot should never do — not for scripting every response.

## Why it matters

Guardrails are where safety, compliance, and the agent's [[agentic-errors]] backstop (iteration caps, refusal paths) live. The practical takeaway: don't over-script. Dialog-scripting every turn is brittle and fights the model; the right division of labor is prompt-for-behavior, validators-for-output, hard-rails-for-the-forbidden. Pairs with [[building-agents-best-practices]] (responsible-AI section) and [[llm-agent-evaluation]] (bias/toxicity metrics).

## How it works

### Colang flow basics

A flow ties triggers to responses; the common pattern lets the LLM respond freely to a matched intent (`bot respond to ...`), while hard-controlled flows use fixed `define bot` strings. Flows can call other flows; `activate` runs a flow against dialogue turns and restarts it on re-trigger.

**Colang 2.0** is more Pythonic (one module = one `.co` file; packages hold modules; the Colang Standard Library cuts boilerplate). Note the tense convention — past tense for user (`user said "hi"`), present for bot (`bot say "hello"`) — and that flows loop back on completion (the "starter question reappears after your issue is resolved" effect).

```text
import core

flow main
    user said "hi"
    bot express greeting

flow bot express greeting
    bot say "hi there!"
```

### Timing rails

`import timing` controls response windows and follow-ups. A `wait` (~0.5s) before replying adds a human touch. If `bot was silent` past a "too long" threshold (~2s), reassure ("this is taking a bit longer than expected"). If `user was silent`, gently re-engage ("still there?" or a non-interrupting "how can I help?"). Same pattern automates periodic checks/reminders.

### Advanced flow management

As bots grow, control flow matters: `start_new_flow_instance` spins up a fresh instance even while another runs (handles overlapping/repeated user actions where plain `activate` would misbehave); `deactivate` stops a flow no longer needed (resource management, avoids unwanted responses); the `@override` decorator replaces or extends an existing flow without rewriting it — useful for customizing imported/standard-library flows.

## Related
- [[building-agents-best-practices]]
- [[agentic-errors]]
- [[llm-agent-evaluation]]
- [[agentic-patterns]]
- [[context-engineering]]
- [[agent-building-judgment]]
