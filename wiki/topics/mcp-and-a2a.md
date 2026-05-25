# MCP and A2A

> Two protocol layers for agent interoperability — MCP connects agents to tools/data, A2A connects agents to each other.

**Category**: topics
**Last updated**: 2026-05-25
**Status**: baseline

## What it is

**MCP (Model Context Protocol)** — Anthropic's open standard for connecting AI systems to data sources and tools through one standardized interface, replacing N bespoke integrations. MCP servers (plugins / data connectors) expose capabilities to clients (Cursor, Claude, etc.).

**A2A (Agent-to-Agent)** — Google's protocol for agents to discover each other and collaborate across vendors and frameworks, built on HTTP / SSE / JSON-RPC. It complements MCP: MCP is agent↔tool, A2A is agent↔agent.

Together they're the substrate of the [[agentic-mesh]] vision — a standardized way for agents to find tools, find each other, and transact.

## Why it matters

Protocol standardization is what turns a pile of custom integrations into an ecosystem. The leverage shows up at scale: an org with strong internal APIs gets agent capability almost for free by layering MCP on top. The lesson from early adopters is **strong internal APIs + MCP = powerful agents at low friction** — and it drives bottom-up innovation, since any team can wire an agent into the shared toolset without reinventing integration logic.

## How it works

**MCP** — client connects to servers; servers expose tools/data. The hard part is governance and security, not the protocol:

| Security area | Practice |
|---|---|
| Credentials | Never share integration tokens; env vars / secrets managers; rotate ~30d |
| Least privilege | Minimal scopes; connect only the pages/DBs needed |
| Isolation | Run servers in containers; network segmentation |
| Auth | OAuth 2.1 + external IdP; identity-aware proxies keep upstream tokens off clients |
| Monitoring | Log all tool calls; watch for anomalous data volume |
| Input handling | Treat all tool params as untrusted; parameterized queries; no arbitrary code exec |
| Human-in-loop | Show tool descriptions; confirm sensitive actions; emergency disconnect |

**A2A** — five principles: embrace agentic capabilities (collaborate in natural modalities, not as mere tools), build on existing standards, secure by default, support long-running tasks (live status/feedback), modality-agnostic. Mechanics: agents advertise an **Agent Card** (JSON capabilities) for discovery; a client agent formulates tasks, a remote agent acts; "task" objects have a lifecycle and emit **artifacts**; messages carry typed "parts" for UX negotiation.

**Enterprise patterns:** Block built "Goose" on in-house MCP servers for end-to-end control (~75% time saved on routine tasks); Amazon layered MCP over its API-first ecosystem, using MCP as a universal translator over thousands of existing endpoints.

**Tradeoff:** whether to adopt MCP/A2A depends on mission-criticality, desired user control, and how much bespoke integration you'd otherwise carry — user-centered design drives the call.

## Dean-Relevance

**Fit score**: 6/10
**Adoption path**: experimental
**Why**: MCP is directly usable in Dean's tooling (Cursor/Claude) and relevant to wiring Crafted into data sources; A2A matters as the multi-agent interop story — but these are established protocols he already understands, not new signal.
**Watch for** (what upgrades to active): A2A reaching real adoption beyond Google's orbit (interop across the frameworks Dean uses), or an MCP capability that meaningfully changes how he connects Crafted/Praxis to Supabase/Qdrant.
**Suggested next step**: —

## Related
- [[agentic-mesh]]
- [[skills-rules-subagents]]
- [[harness-and-scaffolding]]
- [[building-agents-best-practices]]
- [[agentic-patterns]]
