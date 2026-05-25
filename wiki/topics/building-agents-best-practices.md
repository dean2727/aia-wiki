# Building Agents Best Practices

> The end-to-end lifecycle for shipping reliable production agents: data, scope, collaboration, eval, observability, and gradual scaling.

**Category**: topics
**Last updated**: 2026-05-25
**Status**: reference

## What it is

A production-agent playbook (framed around the Amazon Bedrock Agents stack but mostly portable). The throughline: agents are built on **ground-truth data**, kept reliable through **evaluation and observability**, and rolled out **gradually**. The foundation is high-quality ground truth — real, de-identified interactions covering diverse intents with inputs and expected outputs for simple and complex cases — refreshed from production over time. Without it there's nothing to benchmark against.

The architectural prior is divide-and-conquer: small, focused, collaborating agents beat one monolith on modularity, testability, scalability, and per-task model selection. The HR/payroll example — shared sub-agents (KB, meetings) plus permission-scoped specialists — shows why a single-agent setup forces redundant action groups.

## Why it matters

This is the checklist that separates a demo from a deployed agent. The two highest-leverage, most-portable ideas: **"Great LLM Evaluation = Quality of Dataset × Quality of Metrics"** (a product, so a weak factor caps the whole thing), and **crawl-walk-run** rollout. Everything else is risk reduction around those. Connects to [[llm-agent-evaluation]], [[ai-guardrails]], [[agentic-errors]], and [[agentic-patterns]].

## How it works

### Lifecycle stages

| Stage | Essentials |
|---|---|
| **Scope** | Define tasks, limitations, input/output formats; set explicit boundaries (HR assistant answers policy, never touches sensitive employee data) |
| **Collaborative design** | Small focused agents; shared sub-agents for common functions; permission-scoped specialists per role |
| **UX/personality** | Tone, greetings, brand voice, formality, cultural sensitivity — unified across sub-agents |
| **Instructions** | Unambiguous language; examples for complex concepts; clear boundaries between similar functions; confirmation on critical actions |
| **Knowledge bases** | Integrate enterprise KBs for accuracy, fresh data, citable sources, fewer model updates |
| **Evaluation** | Custom metrics per use case; automated quantitative scripts; A/B testing across versions; scheduled human eval; grow the test set from production |
| **Observability** | Model-invocation logging (prompts + responses), traces (orchestration steps, KB refs, generated code), production monitoring |
| **IaC** | Terraform/repeatable deploys; reusable action groups, guardrails, KBs; test pipeline |
| **Security** | Confirmation on data-modifying/sensitive ops; customer-managed encryption keys; least-privilege IAM; role/permission scoping |
| **Responsible AI** | Org-level reusable [[ai-guardrails]] for sensitive topics, harmful content, PII redaction |

### Human evaluation best practices

Diverse evaluator panel; clear rubrics; mix of SMEs and representative end-users; collect quantitative ratings + qualitative insight; analyze continuously for trends. Humans catch what's hard to quantify — NLU quality, response appropriateness, bias, overall UX.

### Test-case generation

Use an LLM to generate test cases from expected use cases — and use a *different* model than the one powering the agent, to avoid blind spots.

### Cost/performance

Right-size the model: cheap (Haiku-class) for simple agents, capable (Sonnet-class) for complex; experiment across FMs against cost/latency/accuracy with automated pipelines.

### Scaling: crawl-walk-run

Internal app (crawl) → limited external group (walk) → all customers (run) → eventually multi-agent collaboration. Reuse action groups/KBs/guardrails via IaC throughout. Minimizes rollout risk for mission-critical use.

### Metrics → outcomes (the healthcare-claims lesson)

Good metrics each surfaced a distinct real failure: **LLM-call error rate** → partial approvals on mid-analysis API failures (fix: state rollback); **task completion rate** → claims marked complete missing verifications (fix: mandatory checklists); **# human requests** → agent handling cases beyond its competence (fix: escalation protocols); **token usage per interaction** → unnecessary PHI in working memory (fix: data minimization). Metrics-driven optimization must align with business objectives.

## Dean-Relevance

**Fit score**: 7/10
**Adoption path**: experimental
**Why**: The eval-as-product framing, test-case generation with a separate model, and crawl-walk-run map directly onto how he'd harden Crafted/Praxis agents — even though the Bedrock specifics (SessionState, action groups) don't apply to his FastAPI/OpenRouter stack.
**Analogy**: Crawl-walk-run is canary deploys for behavior, not just traffic.
**Suggested next step**: Stand up a small ground-truth eval set for his agents and wire one automated metric (task completion via LLM-as-judge) into CI before the next prompt change.
**Watch for**: Eval tooling (DeepEval-style) that augments the eval set automatically from production traces — closes the loop without manual labeling.

## Related
- [[agentic-patterns]]
- [[llm-agent-evaluation]]
- [[ai-guardrails]]
- [[agentic-errors]]
- [[intro-to-agents]]
- [[agent-building-judgment]]
- [[synthetic-data]]
