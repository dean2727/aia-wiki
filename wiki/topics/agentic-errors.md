# Agentic Errors

> Diagnosing and fixing looping, stalling, and incompletion in autonomous agents — the four root causes and a debugging method.

**Category**: topics
**Last updated**: 2026-05-25
**Status**: reference

## What it is

When an agent loops or never finishes, the symptom (repeated searches, endless summarizing, hitting a safety timeout) almost always traces to one of four root causes in its reasoning loop. The loop is just ReAct (reason → act → observe); a defect in any node manifests as non-termination. The discipline is to treat the agent like a buggy program: observe via traces, isolate the trigger, fix the policy (usually the prompt).

A subtle point worth holding: the *symptom* (looping) rarely points at the *cause*. The most common real cause is a flawed or unrecognized exit condition — the agent is "too cautious to ever be done" — even when memory and tools are fine. Default to inspecting stop-logic first.

## Why it matters

Non-termination is the defining reliability failure of autonomous agents and the one that burns tokens silently until a timeout. Knowing the four causes turns "the agent is stuck" from a vague complaint into a four-way differential diagnosis. Ties directly to [[llm-agent-evaluation]] (task completion rate, LLM-call error rate) and [[ai-guardrails]] (hard iteration caps).

## How it works

### The four root causes

| Cause | Software analogy | Tell-tale sign in traces |
|---|---|---|
| **Planning error** | Recursion with no base case | Same subtask revisited; "not done yet, try something else" where "else" ≈ same action |
| **Faulty tool use** | Exception thrown, never caught | Tool errors/zero results ignored; wrong tool retried with minor variations |
| **Memory leak** | State variable never updated | Re-finds a detail it already had; context overflow drops the original task/partial results |
| **Missing/flawed exit criteria** | `while` with no termination check | Searches forever; only stops at safety timeout; "never satisfied enough to finish" |

Causes compound: a planning error can drive repeated tool misuse; a memory lapse can make the agent think completed work is still pending.

### Debugging method

1. **Identify the pattern** — verbose logging / traces (LangSmith). Read the thought-action-observation sequence; spot the repeating cycle or ignored error. This is print-debugging for agents.
2. **Pinpoint the cause** — step-wise execution. Run one iteration at a time (framework step mode, or feed outputs back manually) to catch the exact bad decision point.
3. **Reproduce minimally** — strip to the simplest prompt/dummy tool that still triggers the loop, then incrementally add complexity. Isolates the variable and lets you test fixes fast.

### Fixes by cause

- **Planning** → tighten prompt instructions (e.g. "don't repeat identical searches," add a subgoal counter).
- **Tool** → real error handling; on failure, change strategy rather than retry.
- **Memory** → re-inject a recap of key prior results each iteration; trim/summarize context to stay in window.
- **Exit (critical)** → add an explicit completion check ("Have I answered the question? If so, finish"), define what "answered" looks like (few-shot examples of sufficient evidence), and a max-iteration backstop that forces an answer or graceful failure. Prefer refining the prompt-as-policy before code changes. Beware: overly strict criteria cause never-finishing; overly loose ("search no more than X times") risk premature/incomplete answers — balance is the whole game.

### Retryable vs. non-retryable exceptions

A robust agent runner distinguishes transient failures from terminal ones. **Retryable**: network/timeout classes (`httpx.TimeoutException`, `ConnectError`, `APIConnectionError`, `APITimeoutError`) and retryable HTTP statuses / rate limits — back off (`min(10, 2**attempt)`) and retry the same agent. **Non-retryable**: client/config errors (`BadRequestError` 400, `UnprocessableEntityError` 422, `AuthenticationError` 401, `PermissionDeniedError` 403, `NotFoundError` 404) — don't retry the same agent/model; move on. Always re-raise `asyncio.CancelledError`. Cap retries per agent (e.g. 3) and fall through to the next agent on exhaustion.

## Dean-Relevance

**Fit score**: 8/10
**Adoption path**: immediate
**Why**: His `generate_reply` already implements exactly this retryable/non-retryable split with per-agent retry caps and fallthrough — this page is the rationale behind code he runs in Crafted/Praxis.
**Analogy**: An agent loop with no exit check is a `while True` that forgot its `break` — and the prompt is the loop condition you actually edit.
**Suggested next step**: Add a per-iteration completion check + max-iter forced-answer to any agent that currently relies only on the network-level safety timeout.
**Watch for**: Models that self-report "stuck" / declare done reliably without prompt scaffolding — would shift exit-criteria work from engineering to model behavior.

## Related
- [[agentic-patterns]]
- [[building-agents-best-practices]]
- [[llm-agent-evaluation]]
- [[ai-guardrails]]
- [[agent-memory-learning-from-experience]]
- [[intro-to-agents]]
- [[context-engineering]]
