# Project Rules Example (AGENTS.md)

> A real-world `AGENTS.md` from a colleague's TS + Python + Postgres project (the "ellie" repo, nick.reith) — kept as a reference artifact for the patterns worth stealing.

**Category**: tools
**Last updated**: 2026-05-25
**Status**: reference

## What it is

An annotated example of a mature `AGENTS.md` from someone else's codebase, used here purely to learn structure and conventions — not as Dean's own rules. It is the document an AI agent reads to understand how to build, lint, test, and behave inside that repo. The notable thing is how *comprehensive* and *operational* it is: it encodes not just style but the exact commands, the failure-mode playbooks, and the human-in-the-loop git etiquette.

It pairs naturally with the [[skills-rules-subagents]] taxonomy (this is the "rules" artifact) and with [[repo-init-workflow]], which generates a file like this automatically.

## Why it matters

It's a concrete template for what "good" looks like when codifying a project for agents. Several patterns are directly portable: a Makefile-target table as the single source of build/test commands, strict `mypy` + `ruff` + `deptry` gates wired into pre-commit, uv-only dependency management (never edit the lock manually), and explicit `AGENTS.md` placement scoring (root + highest-density dirs). The "never commit without showing a diff and getting approval" rule and the documented known-broken-test escape hatch are the kind of hard-won operational detail you only get from a lived-in repo.

## How it works

Sections worth lifting as patterns:

| Section | Pattern to steal |
|---|---|
| Build/Lint/Test table | One Makefile-target table = the canonical command reference for humans and agents |
| Code-style guidelines | Concrete rules (ruff format, 120-char soft limit, strict typing, Google docstrings) over vague "be clean" |
| Dependency management | uv-only; `uv add` updates the lock; never hand-edit; `make check` after adds |
| Git review workflow | No auto-commits; always show diff → explain → request approval → commit |
| Testing philosophy | "Don't claim functionality without tests"; every success metric must be test-verifiable |
| AGENTS.md locations | Score directories by code density; place rule files at root + hotspots |
| Mock-patching / known-broken notes | Document lazy-import patch targets, soft-delete sentinels, and tests to `--ignore` |
| Kubernetes ops rule | Trigger→action: if a rollout stalls >30s, immediately pull logs — don't wait |

## Related
- [[skills-rules-subagents]]
- [[repo-init-workflow]]
- [[starting-a-project-vibe-coding]]
- [[spec-driven-development]]
