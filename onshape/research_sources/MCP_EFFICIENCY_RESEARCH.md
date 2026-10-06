# Onshape MCP and per-request density research

Date: 2026-09-07. Public web and loaded tool-description inspection only. This research made zero authenticated Onshape REST or MCP calls. No remote models changed. Cost estimates below are not measured API consumption.

## Findings that change the plan

1. **Separate orchestration from geometry.** FeatureScript can create geometry and properties within one Part Studio, but cannot create tabs, change other feature definitions, or edit assemblies. A giant FeatureScript cannot orchestrate the entire requested document. Onshape employee explanation: [FeatureScript/API boundary](https://forum.onshape.com/discussion/11476/access-to-api-methods-from-feature-script).
2. **The official MCP is a custom-feature authoring server, not a general document API wrapper.** Its launch was August 11, 2026. Custom features are native, reusable and parametric, including systems of related parts. That does not imply an expanded ordinary sketch/extrude tree. [Official launch and scope](https://www.onshape.com/en/blog/featurescript-mcp-server-enables-text-code-cad).
3. **Avoid discovery calls whose answer can be returned with useful work.** A rich feature-list read returns geometry, parameters, feature status, default planes and library version. Feature-add responses already return feature IDs, feature state and resulting microversion. Persist those locally instead of immediately GETting them again. `queryString` can reference known features/planes without preliminary topology-ID fetches. The `features/updates` endpoint updates an array of existing feature parameters; it is not evidence of batch feature creation. [Official feature guide](https://onshape-public.github.io/docs/api-adv/featureaccess/).
4. **Use a single evaluation for many geometric questions.** The evaluation endpoint accepts a lambda. Within one Part Studio context, return an array of maps with per-body names, bounds, volumes, counts and chosen interface measurements. This is an inference from the lambda API and library functions, not a measured benchmark. [Evaluation API](https://onshape-public.github.io/docs/api-adv/fs/).
5. **Evaluation is not persistence.** Temporary construction during evaluation can validate a shape, but cannot replace inserting a persistent feature. An Onshape employee explicitly confirms evaluation has no persistent side effects. [Official employee answer](https://forum.onshape.com/discussion/5382/whats-a-complete-api-call-to-partstudios-featurescript-look-like).

## Loaded official MCP metadata: hidden work and restrictions

These facts were read from the tool descriptions supplied to this session, without invoking those tools. Exact server implementation and request counts were not available in public source during this pass.

| Tool | What the description reveals | Budget consequence |
|---|---|---|
| `get_api_usage` | Returns used, limit, remaining, allocation cycle and allocation account. | A meter call itself consumes allocation according to the shared tool notice. Avoid repeated polling. |
| `test_featurescript` | Executes a lambda against a configured Part Studio; response includes live `libraryVersion`. No document selector argument. | Bundle useful construction/measurement with version discovery where appropriate. Hidden setup cost unknown. |
| `test_feature` | Writes a Feature Studio, appends a no-op helper, adds that helper to a Part Studio, then invokes the production code through evaluation. | At least three described operations; actual HTTP request count and cleanup/setup overhead unknown. Never count this as one REST call. |
| `create_geometry` | Branches a configured document version, writes code, adds a feature. No did/wid/eid arguments. Defaults to cleaning the new branch unless persistence requested. Does not return FeatureScript code errors. | Poor match for constructing exact tabs in the user's existing workspace. Do not use as the final publishing path without resolving its target semantics. |
| `create_feature_studio` | Accepts did, wid, name and optional initial contents. | Can combine element creation and initial code submission; actual request count unknown. Description additionally recommends reading latest contents before later writing. |
| `put_featurescript` | Overwrites entire studio and returns errors. Description says use once at session end, after tests. | Do not plan repeated production-studio MCP writes as a debugging loop. |
| notes/search tools | Shared notice says every server call consumes one or more REST calls. Notes tool asks to read before writing FeatureScript. | Prefer public documentation/local notes for this research; do not assume documentation searches are free. Account for any required notes read before MCP authoring. |

All production features should provide explicit defaults in the second `defineFeature` argument, per the tool metadata. Bundle a self-contained empty-precondition test feature beside the production exports, so it invokes them directly without extra import/setup transactions. Preserve an existing studio's version; discover the current version for new code. These reduce avoidable compile/test cycles, but do not prove correctness.

## Dense verification payload

The standard library documents `evBox3d` with `topology` and `tight:true`; bounds contain `minCorner` and `maxCorner`. `evVolume` accepts `entities` and returns zero when no 3D bodies match. `allSolidsAndClosedComposites` plus `getProperty(... PropertyType.NAME)` supports per-part iteration. Normalize quantities to explicit mm and mm^3 before returning machine-comparable scalars. [Official library](https://cad.onshape.com/FsDoc/library.html).

Recommended payload (design, not executed): model revision/hash; expected-versus-actual solid count; per-body stable label, volume_mm3 and tight world bounds_mm; hole/interface measurements selected from known queries; explicit error records. Catch independent checks separately so one measurement failure does not erase all other results. Avoid returning every face or tessellation when bounds and interface checks answer the current question. Cross-tab checks still require separate contexts or another documented mechanism.

## Assembly batching: useful but bounded

**Parent live-test update:** the separate `/transformedinstances` endpoint solved grouped insertion. `exploration_20/17-insert-four-pins.json` records four insertions in one POST; `30-final-assembly.json` verifies their transforms. Its schema accepts `transformGroups`, each with an `instances` array and one transform. Multi-source entries are documented by that schema but were not separately tested here; this pilot reused one pin source. The cautions below apply to `/modify`, not to `/transformedinstances`.

The assembly API can insert a Part Studio as well as a single part. Its definition endpoint returns instances and occurrence transforms; enable relevant mate information in that same read. `modify` accepts multiple transform definitions, so all placements can be submitted together after instance IDs are known. This does not establish a multi-source instance-creation batch. Separate part tabs imply separate sources. [Official assembly guide](https://onshape-public.github.io/docs/api-adv/assemblies/).

Actual generated Onshape client code confirms `BTAssemblyModificationParams` contains arrays for transforms/deletions and a suppression-state map. It does **not** contain an insertion array. Do not send guessed `insertInstances`/`addInstances` fields to `/modify` based on its broad name. [Official generated request model](https://raw.githubusercontent.com/onshape-public/go-client/master/onshape/model_bt_assembly_modification_params.go).

## Community leads and caveats

The [Mbvjdev MCP implementation](https://github.com/Mbvjdev/onshape-mcp) explicitly identifies hidden `onpy` HTTP calls and adds caching and rate limiting. Its current README says rectangles use four line operations and tests are mocked. This is a useful warning to instrument the underlying HTTP client, not an established optimal modeling route. Search snippets advertised an older 17-call bolt-pattern comparison, but the current inspected README no longer contains it; do not repeat that number as verified evidence.

An [Onshape forum thread about native feature parameters](https://forum.onshape.com/discussion/23719/is-there-any-way-to-fetch-all-parameters-can-be-used-to-create-a-feature) captures the same distinction: custom-feature internals do not appear as independent Part Studio tree features, motivating direct REST feature construction. The linked official feature guide, not the user's complaint, is authoritative for payloads.

## Practical recipe for the 40-call exploration

Prepare all source, defaults, stable feature IDs, full sketch entity/constraint arrays, expected dimensions and assertions locally. Use public docs or cached payloads to settle schema first. Publish one shared Feature Studio containing modular exports if custom-feature modeling is accepted, then insert a chosen export into each requested Part Studio. If ordinary feature-tree editability is required, batch all sketch entities inside each sketch POST and minimize feature count through meaningful combined profiles/patterns. Never call a client library per line without checking its HTTP behavior.

Maintain a local ledger of every attempted REST request, including failures and redirects/retries, separately from MCP invocations. Record response IDs and hashes. For opaque MCP work, meter before/after an isolated call only when budget headroom covers its unknown overhead; allocation deltas can include other active clients and may have reporting latency. Do not promise an exact remaining budget from unmetered MCP tool count.

Unresolved: exact official MCP per-tool HTTP costs; current server setup/cleanup reuse; generic batch feature creation; live multi-source testing of the documented transformed-instances schema; evaluation runtime/response-size ceilings; whether account usage reporting is immediate. No undocumented batching experiment is justified solely by an optimistic endpoint name.
