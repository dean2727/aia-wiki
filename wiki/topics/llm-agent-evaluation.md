# LLM/Agent Evaluation

> The layered metric stack for LLMs and agents: offline quality, online behavior, system performance, and agent/conversation/RAG-specific judges.

**Category**: topics
**Last updated**: 2026-05-25
**Status**: reference

## What it is

Evaluating an LLM or agent in production needs multiple layers: **offline** (pre-deployment quality/efficiency), **online** (real-world behavior), **system-level** (latency/throughput/SLAs), and **task/quality** judges. Agent eval needs a broader lens than system metrics — it spans four categories: System (efficiency/latency/throughput/uptime), Task Completion, Quality Control, and Tool Interaction.

Most quality metrics are **LLM-as-a-judge** (G-Eval generalizes this with chain-of-thought to any custom criterion; DAG builds deterministic decision trees). Anthropic's framing: combine **code-based, model-based, and human** graders, each scoring part of the transcript or outcome; pick the right grader per job, and weight/threshold (binary all-pass, weighted-sum, or hybrid).

## Why it matters

Evals are leverage. Early on they force teams to *define success*; later they hold a quality bar and serve as regression tests. The sharpest payoff: **model adoption speed** — teams with evals tune prompts and upgrade to a new model in days while competitors spend weeks. Evals also become the highest-bandwidth channel between product and research (metrics researchers can optimize against). Directly informs [[building-agents-best-practices]] and catching [[agentic-errors]].

## How it works

### Offline vs. online

| Offline (controlled / labeled / simulated) | Online (real traffic / user behavior) |
|---|---|
| Response accuracy (ground-truth) | Task completion rate (input, tools_called, output) |
| Bias & toxicity (also online via drift) | Latency / response time |
| Summarization correctness | Tool correctness (did it call expected tools in prod?) |
| Hallucination vs. context | Conversational metrics (below) |
| Prompt alignment, JSON correctness | User feedback (implicit drop-offs, explicit 👍/👎) |
| G-Eval / DAG, all RAG metrics | Drop-off rate, conversational turn length |
| Role adherence (scripted) | User satisfaction, uptime |

**Hybrid** metrics bridge both — start with test sets, evolve with production data. Continuous improvement: A/B testing, canary deployments, drift detection (Evidently AI), error analysis, retraining pipeline.

### System performance

| Metric | Target / formula |
|---|---|
| TTFT (time to first token) | ≤ ~2s |
| TPOT (time per output token) | ≤ ~0.1s (10 tok/s) |
| Latency | `TTFT + TPOT × tokens` (benchmark at 100 tokens) |
| Throughput | max tok/s across users per 1-GPU-equiv, valid only while TTFT<2s, TPOT<0.1s |
| Requests/sec | 100-token requests/sec under the same constraints |

### Agent quality metrics

- **Response accuracy** — match to ground truth.
- **Task completion (alignment score)** — LLM extracts Task + Outcome from input/output/tools_called, judges alignment.
- **Tool correctness** — was every expected tool actually called.
- **Bias / toxicity** — LLM-judge, esp. after RLHF/fine-tuning.
- **Summarization / hallucination** — factual correctness vs. source/context.
- **Prompt alignment / JSON correctness** — follows instructions / matches schema.

### Conversational metrics

Conversational G-Eval, conversation efficiency (info-gathering), engagement (intent + relevance + flow), coherence (logical progression), role adherence (stays in role across turns), knowledge retention (retains facts presented mid-conversation), conversation completeness (extracts user intentions across turns, checks each was met), conversation relevancy (sliding-window relevance per turn).

### RAG metrics

| Metric | Measures | Component |
|---|---|---|
| Faithfulness | Output factually aligns with retrieval_context | Generator |
| Answer relevancy | Output statements relevant to input | Generator |
| Contextual precision | Relevant nodes ranked above irrelevant (weighted cumulative) | Retriever |
| Contextual recall | retrieval_context covers expected_output statements | Retriever |
| Contextual relevancy | retrieval_context statements relevant to input | Retriever |

See [[advanced-rag-techniques]] and [[agentic-rag]] for the pipelines these score.

## Dean-Relevance

**Fit score**: 8/10
**Adoption path**: experimental
**Why**: His Qdrant + OpenRouter RAG and multi-agent Crafted/Praxis build are exactly what the RAG-component and task-completion/tool-correctness metrics target — and the eval-driven fast-model-upgrade payoff matters given he swaps Claude/Gemini via OpenRouter.
**Analogy**: Contextual precision vs. recall = "are the big fish ranked first" vs. "did we catch all the fish in the pool."
**Suggested next step**: Wire faithfulness + contextual precision/recall (DeepEval or hand-rolled LLM-judge) onto his Qdrant retrieval, and a task-completion judge on the agent layer, so model swaps are decided by numbers not vibes.
**Watch for**: Cheap, reliable LLM-judge models making continuous online eval affordable per-request rather than sampled — would let him score production traffic, not just test sets.

## Related
- [[building-agents-best-practices]]
- [[agentic-errors]]
- [[agentic-patterns]]
- [[agentic-rag]]
- [[advanced-rag-techniques]]
- [[ai-guardrails]]
- [[agent-building-judgment]]
- [[synthetic-data]]
