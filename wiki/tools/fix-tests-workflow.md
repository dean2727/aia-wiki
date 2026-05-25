# Fix Tests, Lint & Coverage Workflow

> An end-to-end workflow for getting every quality gate green — lint, format, type-check, tests, and ≥90% coverage — with aggressive prioritization and watchdog timeouts.

**Category**: tools
**Last updated**: 2026-05-25
**Status**: reference

## What it is

A fully-automated workflow (`auto_execution_mode: 3`) triggered whenever `make check` or `make test` fails, lint/type-check regresses, or coverage dips below 90%. It runs the gates in a deliberate order — baseline check, fast lint/format pass, then tests under a 10-second watchdog to separate fast-failing files from slow/hanging suites — diagnoses each failure to root cause, and only then expands coverage. It's the superset workflow; [[coverage-booster-workflow]] is its coverage-only subset.

Two rules give it teeth: never delete or comment out a test without written approval (fix fixtures/mocks instead), and after three failed attempts on the same test, log it to `notes/test-triage.md` and escalate to a more powerful model.

## Why it matters

Failing gates are where vibe-coded velocity goes to die — flaky tests, hangs, and creeping lint debt compound until nobody trusts the suite. The watchdog pattern (10s timeout to classify fast vs slow) keeps a single hanging test from blocking the whole pass, and the three-strikes escalation rule prevents an agent from burning hours spinning on one stubborn failure.

## How it works

| Step | Action |
|---|---|
| 1. Baseline gate | Run `make check`; fix the `check` target itself if it skips format/test/audit; log failures |
| 2. Lint & format | `make format`, `uv run mypy`; repeat until clean |
| 3. Global test (watchdog) | `timeout 10 make test`; classify pass vs hang; log failing tests |
| 4. Fast-failing files | Per file: `timeout 10 pytest <file> -vv`, diagnose, minimal root-cause fix, re-run; **3-strike escalation** |
| 5. Slow/hanging suites | Run without timeout, instrument to isolate hang; mock external services; document unavoidable real deps |
| 6. Regression sweep | Re-run `timeout 10 make test`; repeat 4–5 until exit 0; `make check` green |
| 7. Coverage expansion | Drive to ≥90% (see [[coverage-booster-workflow]]); document untestable lines |
| 8. Final gate | `make format` + `make test` + coverage + `make audit` + `make check` + `make docs-test` |

Key rules: never remove tests without approval + justification; log stubborn issues after 3 tries; chase root causes, not refactors.

## Dean-Relevance
**Fit score**: 9/10
**Adoption path**: immediate
**Why**: This is the exact "get the suite green" procedure for the per-wave test passes in his FastAPI projects, and the 3-strike escalation matches his automation-first instinct.
**Analogy**: A pit crew checklist — fast tasks first, a stopwatch on every job, and a rule for when to call the head engineer.
**Suggested next step**: Adopt the 10s watchdog + 3-strike escalation as standing rules in his `AGENTS.md` so any agent fixing tests follows them.
**Watch for**: A test the agent can't fix in three tries is the signal to escalate to a stronger model rather than keep iterating.

## Related
- [[coverage-booster-workflow]]
- [[phase-completion-workflow]]
- [[dependency-hygiene-workflow]]
- [[project-rules-example]]
- [[vibe-coding]]
