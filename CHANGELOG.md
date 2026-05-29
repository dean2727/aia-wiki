# Changelog

## [2026-05-28] Nightly Run

315 staged RSS items triaged (the day's fetch: Anthropic, OpenAI, Google DeepMind, Hugging Face, Import AI, The Batch, Hacker News). The overwhelming majority were headline-only stubs (title + URL + one-line summary) with no synthesizable body. Wrote pages only for high-signal items that scored ≥7 **and** carried enough real content to synthesize without fabrication — quality over completeness, per the signal threshold.

### Created
- **Created**: `wiki/technical/models/deepseek-v4.md` — open MoE (1.6T/49B + 284B/13B) whose real advance is *cheap* 1M-token context for agents: hybrid CSA/HCA attention (~2% of GQA's KV cache), interleaved thinking across tool calls, XML/`|DSML|` tool schema, DSec RL sandbox. **Score 9.** Source: HF, 2026-04-24.
- **Created**: `wiki/technical/models/gemma-4.md` — truly-open (Apache 2) multimodal-incl-audio family from on-device (E2B/E4B) to 31B/26B-MoE; frontier arena scores via deliberate reuse (PLE, shared KV cache, alternating attention) rather than new tricks. **Score 8.** Source: HF, 2026-04-02.
- **Created**: `wiki/technical/algorithms/decoupled-diloco.md` — resilient distributed training across distant data centers via async "islands"; self-healing under injected failures, 12B trained across 4 US regions on 2–5 Gbps >20× faster than sync. **Score 8.** Source: Google DeepMind, 2026-04-23.
- **Created**: `wiki/technical/engineering-approaches/ai-native-open-source-contribution.md` — the maintainer-bottleneck inversion when everyone has a coding agent; Skill-as-encoded-judgment + deliberately non-agentic test harness for trust (HF `transformers-to-mlx`). **Score 8.** Source: HF, 2026-04-16.

### Skipped — high signal but not writeable from source
These cleared the signal bar but the staged item was a headline-only stub with no body to synthesize (writing a full page would mean fabricating post-cutoff specifics). Logged as seen; revisit if a substantive source lands.
- Frontier model launches (headline-only): `Introducing GPT-5.5`, `Introducing GPT-5.4` (+mini/nano), `Gemini 3.5: frontier intelligence with action`, Gemini 3.1 family (Flash-Lite / Flash-Live / Flash-TTS), `Introducing Claude Opus 4.7`, `GPT-Rosalind`, `ChatGPT Images 2.0`, `Lyria 3 Pro`, `Gemini Omni`, `Gemini Robotics-ER 1.6`.
- DeepMind science (headline-only): `AlphaEvolve` impact, `Co-Scientist` multi-agent partner (+ aging/ALS/liver/infectious-disease application stubs), `Gemini for Science`, `Measuring progress toward AGI: a cognitive framework`.
- Architecture explainers (Sebastian Raschka, stubs — substance folded into deepseek-v4 / gemma-4 pages): `Recent Developments in LLM Architectures: KV Sharing, mHC, Compressed Attention`, `A Visual Guide to Attention Variants`, `Components of a Coding Agent`, `My Workflow for Understanding LLM Architectures`.

### Skipped — already covered
- `Harness, Scaffold, and the AI Agent Terms Worth Getting Right` (HF) — already synthesized in `wiki/technical/engineering-approaches/harness-and-scaffolding.md` (2026-05-25); re-fetched, no new content.

### Skipped — below signal threshold (score ≤6)
- ~120 OpenAI items: Codex enterprise/customer stories (NVIDIA, Ramp, Cisco, Virgin Atlantic, Dell, Databricks…), ChatGPT Academy how-tos, enterprise/partnership/funding announcements, safety/policy/cyber posts, ads/commerce, education/health programs.
- ~30 Anthropic items: partnerships (KPMG, PwC, Gates Foundation, SpaceX), Korea/Glasswing, small-business/design product notes.
- ~15 Google DeepMind items: national partnerships, content provenance, WeatherNext, AI pointer, Project Genie.
- The Batch (Andrew Ng) issues 342–354 and Import AI (Jack Clark) 447–458 — newsletter digests, no single synthesizable advance.
- ~50 Hacker News items — general tech/news, off-topic for this wiki.
- Remaining substantial HF blogs (rerankers, embedding/multimodal-embedding training, RL libraries, vLLM/inference internals, robotics datasets, diffusers) — real content but incremental/niche relative to the ≥7 bar; not groundbreaking for Dean's current frontier zone.

- **Profile**: No changes

## [2026-05-25] Backfill Run — Wiki Seed

One-time backfill seeding the empty wiki from staged sources. Triaged 37 staged files; wrote a page for every file scoring ≥3 (34 pages). Three files scoring 1–2 were skipped (no extractable content). INDEX.md intentionally left untouched.

### Tier 1 — Score 7–8 (frontier, new signal · status: active)
- **Created**: `wiki/topics/grok-4-20.md` — Grok 4.20's in-model four-agent MoE architecture; the "experts inside vs. agents outside" framing for Dean's multi-agent work
- **Created**: `wiki/topics/harness-and-scaffolding.md` — emerging harness/scaffold/agent/policy vocabulary (HF, 2026-05-25); layer-level reasoning for agent builders

### Tier 2 — Score 5–6 (frontier-adjacent · status: baseline)
- **Created**: `wiki/topics/context-engineering.md` — single-agent context discipline vs. multi-agent complexity
- **Created**: `wiki/topics/mcp-and-a2a.md` — MCP (agent↔tool) + A2A (agent↔agent) interop protocols
- **Created**: `wiki/topics/agent-memory-learning-from-experience.md` — learned long-term memory / experience without fine-tuning (watch item)
- **Created**: `wiki/topics/agent-building-judgment.md` — Ng/Anthropic heuristics: agent vs. workflow, evals early, over/under-hyped
- **Created**: `wiki/topics/spec-driven-development.md` — spec-first + project-constitution discipline
- **Created**: `wiki/topics/vibe-coding.md` — vibe coder vs. real developer; ownership discipline
- **Created**: `wiki/tools/skills-rules-subagents.md` — the three context primitives of coding agents

### Tier 3 — Score 3–4 (known substrate / operational reference · status: reference)
- **Created**: `wiki/topics/advanced-rag-techniques.md` — advanced retrieval/ranking hub (RAG cluster)
- **Created**: `wiki/topics/pre-retrieval.md` — chunking, indexing, query optimization
- **Created**: `wiki/topics/graph-rag.md` — entity-graph + community-summary retrieval
- **Created**: `wiki/topics/agentic-rag.md` — agent-driven retrieval loops
- **Created**: `wiki/topics/semantic-boundary-chunking.md` — context-aware chunking with entity preservation
- **Created**: `wiki/topics/agentic-patterns.md` — workflow & agent patterns hub
- **Created**: `wiki/topics/agentic-errors.md` — debugging looping/stalled agents; retryable vs. non-retryable exceptions
- **Created**: `wiki/topics/agentic-mesh.md` — agent ecosystem / marketplace / registry concept
- **Created**: `wiki/topics/intro-to-agents.md` — traditional vs. compound vs. agentic systems
- **Created**: `wiki/topics/building-agents-best-practices.md` — agent lifecycle (data → scope → eval → scale)
- **Created**: `wiki/topics/ai-guardrails.md` — NeMo/Colang guardrail patterns
- **Created**: `wiki/topics/llm-agent-evaluation.md` — offline/online + agent/RAG evaluation metrics
- **Created**: `wiki/topics/model-compression.md` — knowledge distillation vs. pruning/quantization
- **Created**: `wiki/topics/synthetic-data.md` — SMOTE/CTGAN/GenAI synthetic data + evaluation
- **Created**: `wiki/topics/starting-a-project-vibe-coding.md` — project kickoff: scaffold → waves → evals → guardrails
- **Created**: `wiki/tools/redis-for-rag.md` — Redis as vector store / semantic cache / session memory
- **Created**: `wiki/tools/agent-frameworks.md` — LangGraph vs. autogen control spectrum (stub source)
- **Created**: `wiki/tools/project-rules-example.md` — example AGENTS.md artifact (colleague's "ellie" repo)
- **Created**: `wiki/tools/phase-completion-workflow.md` — dev-phase wrap-up workflow
- **Created**: `wiki/tools/docs-drift-workflow.md` — README/AGENTS/Makefile drift detector
- **Created**: `wiki/tools/dependency-hygiene-workflow.md` — audit / unused / upgrade-planning workflow
- **Created**: `wiki/tools/repo-init-workflow.md` — deep repo analysis → AGENTS.md generator
- **Created**: `wiki/tools/coverage-booster-workflow.md` — drive coverage to ≥90%
- **Created**: `wiki/tools/fix-tests-workflow.md` — fix tests/lint/coverage quality-gate workflow
- **Created**: `wiki/tools/worktrees-parallel-agents.md` — git worktrees for parallel agents

### Skipped — Score 1–2 (no extractable content)
- `notion-2026-05-25-common-rules-workflows-skills.md` — one-line stub
- `notion-2026-05-25-deep-research-systems.md` — only unavailable Notion images
- `notion-2026-05-25-agents.md` — trivial stub defining "agency"

- **Profile**: No changes

## [2026-05-25] Stanford "Self-Improving AI Agents" Course Ingest

Processed all 15 lecture PDFs from the Stanford self-improving-agents course (staged in `private/sources/staging/`), read in full, and synthesized into one synthesis page plus eight standalone topic pages. Every page carries a Dean-Relevance section. INDEX.md left untouched (matches the backfill-run convention; not maintained yet).

### Synthesis
- **Created**: `wiki/synthesis/self-improving-ai-agents.md` — the full course arc as one loop (generate → verify → train, human role shrinking); maps all 15 lectures + the four recap papers (Multiagent Finetuning, DeepSeekMath-V2, Absolute Zero, Intelligence-per-watt); five cross-cutting threads with verification as the master key

### Topics — Score 8 (frontier, rich, high Dean-fit · status: active)
- **Created**: `wiki/topics/verifiers-in-llm-reasoning.md` — Cobbe → Lightman PRM → Math-Shepherd → Weaver; the reliability bottleneck; application-layer relevance to his RAG/agent quality gates (fit 8)
- **Created**: `wiki/topics/evolutionary-search-self-improving-agents.md` — AlphaCode(2), AlphaEvolve, Darwin Gödel Machine, AI Scientist v1/v2; "director-not-operator" automation; OpenEvolve on-ramp (fit 8)

### Topics — Score 7–8 (frontier · status: active)
- **Created**: `wiki/topics/test-time-compute-scaling.md` — Large Language Monkeys, pass@k vs Maj@k, generation–verification gap, compute-optimal scaling, Archon/ITAS; all reachable via his OpenRouter stack (fit 7)
- **Created**: `wiki/topics/llm-memory-architectures.md` — MemGPT, Cartridges, LMCache, CacheBlend, MLA; KV cache as memory; maps to his self-updating-KB ✅ zone (fit 7)
- **Created**: `wiki/topics/agentic-evals-and-long-horizon-tasks.md` — METR time horizon, GDPval, DeepScholar-Bench; reliability gap calibration; closing reflection ≈ Praxis human-growth thesis (fit 7)
- **Created**: `wiki/topics/agentic-rl-exploration.md` — policy gradient as the fundamental equation, 3 unsolved problems, exploration ladder, RL²/AdA/Algorithm Distillation; zone-of-proximal-development ≈ Praxis thesis (fit 7)

### Topics — Score 5 (conceptual leverage · status: active)
- **Created**: `wiki/topics/train-time-rl-scaling.md` — STaR, GRPO vs PPO, DAPO's four fixes, DeepSeekMath unified gradient, "RL elicits not expands"; mostly conceptual since he's API-based, watch adoption (fit 5)

### Topics — Score 4 (out-of-zone domain, transferable methods · status: watching)
- **Created**: `wiki/topics/vision-language-action-models.md` — PaLM-E → RT-2 → action chunking/diffusion → π0/π0-FAST → Knowledge Insulation → π0.5; robotics is skip for Dean, but action-chunking / flow-matching / knowledge-insulation are dual-use (fit 4)

### Notes
- `llm-memory-architectures.md` chosen over the suggested `llm-memory-and-learning.md` to avoid duplicating the existing `agent-memory-learning-from-experience.md` (systems/architecture vs. learned-retrieval-policy); the two are cross-linked.
- Reasoning (Denny Zhou), post-training eras (Melvin Johnson), AI-for-math/neuro-symbolic (Thang Luong), and learning-from-feedback (ReAct/RLEF/Constitutional AI) were folded into the synthesis rather than given standalone pages — rich but best read as connective arc, not isolated topics.
- **Profile**: No changes

## [2026-05-27] Wiki Restructure — Understanding-First Taxonomy

Refactored the wiki from a **content-type filing system** to an **understanding-building structure**.

The previous layout was organized around *what a page is*:
- `topics/` = a concept
- `synthesis/` = multiple topics combined
- `tools/` = software
- (implicitly) workflows/patterns = “method pages”

That scheme is tidy for storage, but it doesn’t reflect how understanding compounds.

The new layout is organized around *how reality unfolds*:
- `wiki/technical/` = what researchers and engineers are discovering (methods, algorithms, architectures, engineering approaches)
- `wiki/world/` = how those discoveries are manifesting in shipped products, capabilities, and society
- `wiki/overview.md` = the connector: quarterly synthesis from technical breakthroughs → world-facing implications

In essence: **this structure optimizes for building understanding, not merely storing knowledge.**

### Updated
- **Updated**: `README.md` — documented the new `wiki/` tree
- **Updated**: `CLAUDE.md` — updated allowed wiki locations + index guidance to match the new taxonomy
- **Updated**: `.github/workflows/nightly.yml` — nightly prompt now targets `wiki/technical/` / `wiki/world/`
- **Updated**: `.github/workflows/weekly.yml` — weekly prompt now reviews `technical/synthesis.md`, `world/synthesis.md`, and `overview.md`
- **Updated**: `specs/notion_wiki_seeding.plan.md` — updated write targets to match the new wiki layout
- **Updated**: `.cursor/rules/wiki-pipelines.mcd` — updated wiki location conventions

### Created
- **Created**: `wiki/world/synthesis.md` — world-facing weekly synthesis placeholder
- **Created**: `wiki/overview.md` — quarterly connector placeholder

### Moved
- **Moved**: all wiki pages into `wiki/technical/...` and `wiki/world/...` (and removed the now-empty legacy directories)
