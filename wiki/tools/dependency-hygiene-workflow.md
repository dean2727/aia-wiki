# Dependency Hygiene Workflow

> A periodic workflow that keeps dependencies used, secure, and correctly pinned via automated audits, unused-dep checks, and upgrade planning — all through uv.

**Category**: tools
**Last updated**: 2026-05-25
**Status**: reference

## What it is

A workflow (`auto_execution_mode: 2`) run monthly or whenever audit tools flag something. It snapshots the dependency tree, runs security and unused-dependency checks, then works through findings: removing or regrouping unused packages, resolving CVEs by upgrade/patch/justified-ignore, and parking larger upgrades as tracked TODOs. Everything routes through `uv` — `uv tree`, `uv add <pkg>@<ver>`, `uv lock` — never manual lock edits or legacy pip.

It's the dependency-focused sibling of [[docs-drift-workflow]] and [[fix-tests-workflow]], all built on the same `make check` quality gate.

## Why it matters

Vibe-coded projects accrue dependency cruft fast — packages added mid-wave and never removed, transitive CVEs, drifted pins. Left alone this becomes a security and reproducibility liability. A monthly pass with `deptry` + `pip-audit` keeps the tree lean and auditable, with every removal and CVE fix logged for trail.

## How it works

| Step | Action |
|---|---|
| 1. Inventory & baseline | `uv tree` snapshot; `make audit` (pip-audit + tree) + `uv run deptry src`; log findings dated |
| 2. Unused/misplaced | Remove unused deps; move dev-only deps to correct group; `uv lock`; re-run `make check` |
| 3. Security CVEs | Per pip-audit finding: check advisories, choose upgrade/patch/justified-ignore; `uv add <pkg>@latest` + `uv lock` + `make check`; record before/after |
| 4. Upgrade planning | Check newer versions of critical runtime deps; backlog TODOs describing required testing |
| 5. Final validation | `make format`, `make check`, `make docs-test`; ensure `uv tree` + `make audit` are clean |
| 6. Commit | `chore: dependency hygiene [date]` listing removed/upgraded/CVEs |

## Dean-Relevance
**Fit score**: 8/10
**Adoption path**: immediate
**Why**: It's uv-native and matches his exact tooling preference (uv over pip/requirements.txt) plus his bloat-zero stance — directly applicable to the FastAPI side of Crafted/Praxis.
**Analogy**: Flossing for the dependency tree — cheap if monthly, painful if you skip it for a year.
**Suggested next step**: Schedule the monthly pass and wire `deptry` + `pip-audit` into CI so new cruft fails fast.
**Watch for**: A recurring CVE in a core runtime dep is the signal to fast-track the parked upgrade rather than re-ignoring it.

## Related
- [[docs-drift-workflow]]
- [[fix-tests-workflow]]
- [[coverage-booster-workflow]]
- [[project-rules-example]]
- [[vibe-coding]]
