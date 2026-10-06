# Onshape modeling workflow

## Current checkpoint (2026-09-07)

**Superseded connection-only checkpoint:** the MCP tools are now visible. The direct-API research pilot built a native pin and four assembly instances; see [EFFICIENT_NATIVE_WORKFLOW.md](EFFICIENT_NATIVE_WORKFLOW.md) and [RESEARCH_NOTES.md](RESEARCH_NOTES.md). No MCP modeling tools were executed. The current allowance is 40 total direct-request attempts, 34 used.

- Public target document: `c452b7f3224726ea2f11cdda`.
- Workspace: `3231ffbfcf00782c1dba2494`.
- Creation returned HTTP 200 from exactly one POST; no follow-up verification call was made.
- Credentials and returned target IDs are in local Git-ignored `.env`.
- Codex global MCP name: `onshape_featurescript`.
- HTTP endpoint: `https://fs-mcp.labs.onshape.app/mcp`.
- Server registration succeeded; OAuth was initiated but completion is not yet confirmed.
- No MCP modeling pilot ran. A direct native pin reconstruction subsequently ran as documented above.

## Quota correction

The App Store listing supplied by the user explicitly states:

> API calls made by this MCP server count toward your overall Onshape API allocation.

Treat this MCP as metered. The general public App Store OAuth exemption is not a basis for assuming this app is exempt. A model-facing MCP call can cause multiple underlying API calls; do not equate the two counts. Use the account's Developer usage counter before and after a small pilot to measure consumption, not to assume an exemption. Record timestamps and allow for counter update delays; an immediate unchanged counter is inconclusive.

## Connection

Subscribe to [Onshape Labs FeatureScript MCP](https://cad.onshape.com/appstore/apps/Onshape%20Labs/6a29aea7c03f8bf659841734), then complete browser OAuth. If the current login expires, run `codex.cmd mcp login onshape_featurescript` on Windows. Restart/reload the client to expose the newly configured tools, then inspect their actual capabilities before planning mutations.

The app listing says the service creates `FeatureScript MCP Workspace` and `FeatureScript MCP Notes` documents, writes persistent `FS Notes.md`, and can delete workspaces inside its sandbox document. Do not assume it edits our target directly. Inspect the destination behavior after connection and keep sandbox results separate from accepted target geometry. The OAuth flow requested read, write, delete and read-PII scopes; review these in the browser consent screen.

## Modeling and handoff

Keep dimensions, equations, manufacturing constraints, feature order and acceptance checks in this repository. `design_parameters.json`, the source geometry and `revision_f_baseline.json` remain the design inputs; generated MCP notes are supporting context.

Prepare coherent changes locally. Use modular FeatureScript stages for cradle supports, duct/plenum geometry, fan interfaces and outlet rails, sharing layout dimensions. Compile, inspect errors and evaluate geometry through the official MCP once connected. Cache returned IDs and unchanged definitions; avoid idle polling and rediscovery. Record source revisions and measured usage at checkpoints.

Custom feature operations do not automatically become separate sketch/extrude/loft/fillet entries. Explicitly build conventional features where ordinary editing is required by README.md. Track that work separately from working custom generators; passing a custom-feature pilot does not satisfy the native feature-tree acceptance criteria.

First pilot: a small isolated parameterized feature with a known expected solid count and dimensions, followed by one parameter change and inspection. Record before/after account usage, MCP actions, errors, dimensions and result. Do not launch the full rebuild until the measured cost and tool behavior are understood.

If the conventional-feature handoff requires the personal API key, prepare a deterministic plan with cached definitions, a hard request budget and durable checkpoints before executing. Include setup and verification in that budget. Do not automatically retry ambiguous creation failures. No additional personal-key calls are budgeted by the one-call document-creation instruction.

## References

- [Official MCP setup](https://www.onshape.com/en/blog/get-started-featurescript-mcp-server)
- [Official endpoint announcement](https://www.onshape.com/en/blog/featurescript-mcp-server-enables-text-code-cad)
- [General API accounting policy](https://onshape-public.github.io/docs/auth/limits/)
- [Codex MCP configuration](https://developers.openai.com/codex/mcp)
