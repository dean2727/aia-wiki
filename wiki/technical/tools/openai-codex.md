# OpenAI Codex

> OpenAI's coding agent that has outgrown coding — a persistent, plugin-extensible workspace now used by 5M+ people/week, ~20% of them non-developers, for long-running knowledge work as well as software.

**Category**: tools
**Last updated**: 2026-06-28
**Status**: active

## What it is

Codex is OpenAI's agentic coding product (CLI + app + IDE + cloud), positioned by mid-2026 as a general "agent for getting work done." Two shifts define its current state:

- **Beyond code.** 5M+ weekly users; non-developers (analysts, marketers, operators, designers, researchers, investors, bankers) are ~20% of users and growing >3× faster than developers. OpenAI now ships **role-specific plugins** (data analytics, creative production, sales, product design, public-equity investing, investment banking — bundling 62 apps and 110 skills), **Sites** (Codex generates interactive hosted dashboards/planners/boards shareable by URL and kept live as details change), and **annotations** (point at an exact part of a doc/spreadsheet/slide/site and tell Codex what to change — iterative refinement after the first draft).
- **Beyond a single prompt.** OpenAI's "Codex-maxxing" guidance frames Codex as a *persistent workspace* that preserves context across long-running projects: break ambitious goals into verifiable steps, maintain continuity across workstreams, and deliberately decide when to delegate execution vs. keep human oversight.

## Why it matters

For Dean specifically, two things are worth tracking:

- **The "verifiable steps + delegation boundary" framing is the durable lesson**, not the product. It's the same discipline as [[spec-driven-development]] and [[harness-and-scaffolding]]: long-horizon agent work succeeds when the goal is decomposed into independently checkable units and the human owns the judgment calls. This maps directly onto how Dean already works (extensive planning before acting, plans as source of truth) — Codex is productizing that workflow.
- **Plugins + Sites are a bet on an agent-native work surface.** Instead of adapting work to a fixed tool/file, the agent generates a fit-to-purpose artifact (a live site, a dashboard) and maintains it. That's the "things around the model are the product" thesis (see [[context-engineering]]) showing up as a consumer surface — and a competitor framing to building your own harness.

The caution flag from Dean's profile applies: much of the value here requires connecting Codex to your tools and trusting delegation, which is friction/lock-in to weigh against a self-built [[harness-and-scaffolding]] approach. Codex pairs with the [[frontier-model-launches-summer-2026]] models (GPT-5.6 Sol/Terra/Luna ship to Codex first).

## How it works

- **Plugins** bundle apps + skills + instructions + workflows per role; they work out of the box, can be adapted, and custom plugins can be built and shared (OpenAI is building toward an open plugin ecosystem across Codex and ChatGPT). Enterprise admins control underlying app permissions.
- **Sites** turn analysis/plans into interactive hosted webpages (dashboards, planners, review workspaces, galleries) shareable in-workspace by URL, kept up to date on request. Partner ecosystem in progress (Vercel, Wix, Replit, Lovable, Figma, Webflow, etc.).
- **Annotations** extend the developer "point and refine" loop to documents, spreadsheets, and slides — Codex focuses edits on the selected region without reworking the rest.
- **Long-running work**: used as a persistent context store across workstreams; the operative skill is decomposition into verifiable steps plus an explicit delegate-vs-oversee decision per step.

## Related
- [[harness-and-scaffolding]]
- [[spec-driven-development]]
- [[frontier-model-launches-summer-2026]]
- [[skills-rules-subagents]]
- [[building-agents-best-practices]]
