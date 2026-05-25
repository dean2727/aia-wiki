# Coverage Booster Workflow

> A focused workflow for driving test coverage to ≥90% by attacking easy wins first, then documenting genuinely untestable code with rationale.

**Category**: tools
**Last updated**: 2026-05-25
**Status**: reference

## What it is

A fully-automated workflow (`auto_execution_mode: 3`) invoked when coverage drops below 90%, before major releases, or after big refactors. It baselines coverage with branch data, ranks under-90% modules into easy/moderate/hard buckets, and grinds the easy wins first (pure functions, utilities, things with existing mocks), re-running coverage after each batch. Truly untestable code (live hardware, fatal exits) gets an inline comment plus a documented rationale in `docs/coverage-notes.md` rather than a fake test.

It's the coverage-specialized subset of [[fix-tests-workflow]] — same uv/pytest commands, same ≥90% target, but scoped purely to raising the number.

## Why it matters

Coverage gains are highly non-linear: a few parametrized tests on pure functions move the number far more than wrestling an async integration path. By prioritizing easy wins and explicitly documenting (not faking) the hard parts, the workflow buys real confidence cheaply and avoids the false comfort of mocked tests that prove nothing.

## How it works

| Step | Action |
|---|---|
| 1. Baseline | `pytest --cov=src --cov-branch --cov-report=term-missing --cov-report=xml`; save dated snapshot |
| 2. Identify targets | Find <90% modules; bucket easy / moderate / hard; log prioritized plan |
| 3. Add focused tests | Cover missing branches; parametrize combinatorial paths; mock external deps aggressively; keep tests <1s |
| 4. Re-run often | Re-run coverage after each batch; update progress per module |
| 5. Hard-to-test code | Try DI/seams; else inline comment + rationale in `docs/coverage-notes.md`; log refactor TODOs |
| 6. Final verification | `make format`/`make test`/coverage/`make audit`/`make check`; confirm ≥90% and trending up |

Tips: small focused tests beat large integration suites for coverage; reuse fixtures; avoid `# pragma: no cover` unless documented.

## Dean-Relevance
**Fit score**: 7/10
**Adoption path**: experimental
**Why**: A targeted tool to call when a Crafted/Praxis module's coverage dips — narrower than the full fix-tests pass, useful pre-release.
**Analogy**: Triaging the ER waiting room — treat the quick cases first, chart the complicated ones for later.
**Suggested next step**: Set a 90% coverage gate in CI so this workflow has a clear, automatic trigger.
**Watch for**: If coverage repeatedly falls below threshold, fold this into [[phase-completion-workflow]] so each wave self-corrects.

## Related
- [[fix-tests-workflow]]
- [[phase-completion-workflow]]
- [[dependency-hygiene-workflow]]
- [[vibe-coding]]
- [[starting-a-project-vibe-coding]]
