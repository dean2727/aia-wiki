# Skills, Rules, Subagents

> The three context primitives of modern coding agents — dynamic on-demand knowledge (skills), always-on guidelines (rules), and delegated context-isolated workers (subagents).

**Category**: tools
**Last updated**: 2026-05-25
**Status**: baseline

## What it is

Three distinct mechanisms for steering coding agents, often conflated:
- **Skills** — folders of instructions/scripts/resources an agent discovers and loads *only when relevant*. A superset over MCP tools: a distilled way-of-doing-something, lazy-loaded to avoid context bloat. (agentskills.io, skills.sh)
- **Rules** — static, authoritative guidelines *always applied* (or scoped by file globs): coding standards, architecture constraints, forbidden patterns, canonical-example pointers.
- **Subagents** — delegated workers in their own context window that handle a subtask and return a result.

See [[harness-and-scaffolding]] for where these sit in the agent stack, and their relationship to [[spec-driven-development]] (rules ≈ the project constitution).

## Why it matters

These are the levers for the real bottleneck in agent coding: context. Skills give narrow-and-deep knowledge without bloating every conversation (lazy loading, agent-decided). Rules encode the corrections you'd otherwise repeat. Subagents isolate long/parallel work so the main thread stays clean. Used well, they're how you make an agent reliably follow *your* patterns instead of generic ones.

## How it works

| Primitive | Loading | Best for | Lives in |
|---|---|---|---|
| **Skill** | Dynamic, agent-chosen when relevant | Multi-step tasks, test generation, framework nuances, company-specific style | `.agent/skills/` (name + description + body; can bundle resources) |
| **Rule** | Static, always on (or glob-scoped) | Build/test commands, conventions, guardrails (files not to touch) | Rules file / constitution |
| **Subagent** | Delegated, own context window | Long research, parallel workstreams, independent verification | Spawned by parent agent |

**Skill heuristics:** great for new knowledge/frameworks even the best LLMs lack from training data; turn frequently-used skills into `/`-invokable workflows (e.g. `/fix-issue`, `/review`, `/update-deps`).

**Rule heuristics:** don't copy whole style guides (use a linter — rules complement tooling); document only project-specific commands; add a rule when the agent repeats a mistake; keep them lean (rules ride in every conversation). When an agent ignores rules: make them specific/actionable, add "IMPORTANT:", resolve contradictions, prune.

**Subagent heuristics:** use for context isolation, parallelism, specialized multi-step work, or independent verification; overkill for a simple single-purpose task (use a skill). Foreground for sequential output you need; background for long/parallel work. Cursor's built-in Explore subagent runs many parallel searches in its own context with a faster model.

## Dean-Relevance

**Fit score**: 7/10
**Adoption path**: immediate
**Why**: Dean uses Cursor/Claude Code daily and is formalizing AI-assisted dev into discipline — skills/rules/subagents are the concrete mechanisms for the rules-and-workflows habit he already maintains.
**Watch for** (what upgrades to active): cross-tool standardization of skills (portable packages via skills.sh / agentskills.io) maturing into a real ecosystem — that would make skills a durable asset rather than per-tool config.
**Suggested next step**: —

## Related
- [[spec-driven-development]]
- [[harness-and-scaffolding]]
- [[mcp-and-a2a]]
- [[vibe-coding]]
- [[worktrees-parallel-agents]]
- [[project-rules-example]]
