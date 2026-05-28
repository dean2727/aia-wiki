# Repository Initialization Workflow

> A deep-dive `/init` workflow that analyzes a repo's structure, stack, patterns, and config, then synthesizes a comprehensive `AGENTS.md` to bootstrap AI-assisted development.

**Category**: tools
**Last updated**: 2026-05-25
**Status**: reference

## What it is

A fully-automated workflow (`auto_execution_mode: 3`) that scans a repository across ten dimensions — structure, stack, code patterns, tooling/config, dev workflow, security/perf, docs, integrations — and synthesizes everything into a single `AGENTS.md` that gives any future agent deep contextual grounding. The analysis steps are marked `// turbo` so they run unattended. The output is the rule artifact every other workflow then reads: an `AGENTS.md` like the [[project-rules-example]].

Run it when initializing a new repo for AI-assisted development, onboarding a new agent or teammate, or when a complex project needs a knowledge base its agents can rely on.

## Why it matters

A coding agent is only as good as the context it starts with. Hand-writing a complete `AGENTS.md` for an existing codebase is tedious and error-prone; this workflow front-loads that discovery automatically, so the agent inherits conventions, gotchas, and architecture instead of rediscovering them every session. It's the entry point of the whole workflow family — [[starting-a-project-vibe-coding]] generates per-part `AGENTS.md` files exactly this way.

## How it works

Ten `// turbo` analysis passes → one synthesized doc:

| Pass | Looks for |
|---|---|
| 1. Structure | Directory tree, project type, key dirs |
| 2. Stack | Package managers, languages, frameworks, build/test/deploy tooling |
| 3. Code patterns | Conventions, design patterns, module/dependency relationships |
| 4. Tooling/config | gitignore, eslint/prettier, CI/CD, env configs |
| 5. Dev workflow | Branching, commit conventions, testing strategy |
| 6. Security/perf | Security config, perf patterns, error handling, observability |
| 7. Docs | Existing doc quality, gaps, README/API-doc patterns |
| 8. Integrations | External APIs, DB connections, system boundaries |
| 9. Generate | Synthesize findings into structured `AGENTS.md` |
| 10. Validate | Check completeness, format for usability, summarize |

Output `AGENTS.md` covers: overview, dev guidelines, tooling/workflow, agent-specific instructions, quick reference, troubleshooting, integration points, perf/security.

## Dean-Relevance

**Adoption path**: immediate
**Why**: It's the one-shot way to produce the project context doc he writes by hand when kicking off Praxis work, and it matches his plan-first, low-friction style.
**Analogy**: A codebase MRI — one scan and you get the full chart instead of poking around for symptoms.
**Suggested next step**: Run it against an existing Praxis repo and diff the generated `AGENTS.md` against the hand-written one to find blind spots.
**Watch for**: If a coding agent's built-in `/init` produces an `AGENTS.md` this thorough, the custom workflow becomes redundant.

## Related
- [[project-rules-example]]
- [[starting-a-project-vibe-coding]]
- [[skills-rules-subagents]]
- [[spec-driven-development]]
