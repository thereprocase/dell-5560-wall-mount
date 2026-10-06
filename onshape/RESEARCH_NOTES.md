# Native Onshape automation research notebook

Updated 2026-09-07. Intended as evidence for a future skill; not yet a proven workflow.

## User requirements and current boundary

- Move toward a fully native, human-editable model: actual sketches, constraints and ordinary features.
- Each distinct part gets its own Part Studio tab in the existing document; use an Assembly for instances.
- Preserve the existing Revision F source and baseline exports.
- User raised the total exploratory allowance from 20 to 40 requests, including failed attempts and verification.
- At authorization increase: 14 counted attempts (13 HTTP responses plus one sandbox-blocked connection). 26 remain.
- Latest checkpoint: 34/40 counted attempts; six remain. Research includes live tests documented below. No MCP calls have been used.
- Do not treat parallel tool calls as request savings. One MCP invocation may consume multiple requests.

## Exact checkpoint

The following initial pin/assembly state is historical; later dated sections record the constrained, variable-driven pin and populated assembly. Canonical current summary: `EFFICIENT_NATIVE_WORKFLOW.md`.

Document `c452b7f3224726ea2f11cdda`, workspace `3231ffbfcf00782c1dba2494`.
Pin Part Studio `cf9a24a5d90f7bf7ae0d3004`, still named `Part Studio 1`.
Assembly `959913d7c8696541b603dc65`, still named `Assembly 1`, empty at attempt 14.

Pin features, all OK at attempt 12:

| ID | Native type | Name |
|---|---|---|
| FsccNllSqSt2GtL_0 | newSketch | Pin - axial profile (mm) |
| F6eJcmPlBqWoX2y_0 | revolve | Pin - revolve 360 degrees |
| FqmwXx7eYeJWJUo_1 | newSketch | Pin - 1 mm split from z=4 |
| FGkQYbmYK6DR0na_1 | extrude REMOVE | Pin - split cut symmetric 6 mm |

At attempt 10: one solid, part ID `JHD`, bounds (-4,-4,0) to (4,4,14) mm.
Volume 204.56030071178648 mm3; source pin volume 204.56030211054718 mm3.
Volume/bounds agreement is preliminary, not full shape equivalence. No native export or visual QA yet.
Both sketches remain unconstrained; the constraint update was rejected, and attempt 12 confirmed no constraints were added.

## Proven payloads and failures

All exact requests/responses are in `exploration_20/`; ledger is `requests.jsonl`.
`explore_native.py` reserves an attempt before network I/O, uses no redirects/retries, and stops at 40. The directory retains its original `exploration_20` name for continuity.
Credentials are read from ignored `.env` and never included in request artifacts.

- Native polygon sketch creation succeeded: `BTMSketch-151`, `BTMSketchCurveSegment-155`, `BTCurveGeometryLine-117`; geometric coordinates and parameters are meters.
- Profile includes the head chamfer and retaining taper, allowing one native revolve rather than multiple extrudes/chamfer/loft features.
- A query selecting the axial edge returned both wire and region-edge representations. Revolve failed until restricted to one edge with `qNthElement(..., 0)`.
- Native symmetric REMOVE extrude succeeded with `symmetric=true`, depth `6 mm`, `defaultScope=true` in this single-solid studio.
- `box` is reserved in FeatureScript. Read-only measurement failed to parse until renamed `bounds`.
- Batch `features/updates` with newly invented sketch constraints returned 404: "Sketch constraint with nodeId ... not found in sketch ...". Do not repeat this payload; investigate constraint insertion semantics versus updating existing constraints.
- POST `/elements/d/.../w/.../e/...` returned 405 for rename. Do not guess endpoints: inspect official metadata API schema first.
- Sandbox sockets are blocked (WinError 10013); the approved executor works with network escalation.

## Efficiency research, documented but not yet tested here

1. Official SDK documents POST `/assemblies/d/{did}/w/{wid}/e/{eid}/transformedinstances` for creating instances with transforms. Inspect its nested payload models before use; this may insert all four pins in one request.
2. Official feature API documents one feature creation and batch updates of existing features. No bulk native feature creation shortcut established yet.
3. One native sketch can carry many curves/constraints, and one operation can select multiple regions. Group by engineering intent and shared extrusion direction/depth, while preserving useful editing boundaries.
4. Read-only FeatureScript evaluation can return solid counts, bounds, volumes and additional checks together. Avoid separate read requests for each scalar.
5. Metadata API, not the guessed elements endpoint, exposes element/part metadata updates. Investigate document-level batching for names.

## Source index

- Feature API guide: https://onshape-public.github.io/docs/api-adv/featureaccess/
- Assembly API guide: https://onshape-public.github.io/docs/api-adv/assemblies/
- Official SDK endpoint index: https://github.com/onshape-public/go-client/blob/master/onshape/README.md
- Assembly SDK API: https://github.com/onshape-public/go-client/blob/master/onshape/docs/AssemblyApi.md
- Transformed instances schema: https://github.com/onshape-public/go-client/blob/master/onshape/docs/BTAssemblyTransformedInstancesDefinitionParams.md
- Standard library: https://cad.onshape.com/FsDoc/library.html

The SDK index advertises API v16; successful exploration used v9. Public SDK documentation is schema evidence, not proof that every field works in the current target.

## Questions to resolve before the next execution

- Exact transformed-instance request structure, result mapping, same-document references and fixed-state behavior.
- Correct insertion of new sketch constraints; full-feature replacement versus incremental batch updates.
- Shared Variable Studio creation/import and bulk variable definitions; dependencies across separately modeled parts.
- Native derive/mirror strategy for handed parts in separate tabs without duplicated source feature trees.
- Native feature creation lower bound and whether any documented endpoint accepts multiple new ordinary features.
- Export/validation batching, synchronous Parasolid versus asynchronous STEP overhead.
- Stable native selection references after dimensional edits, without coordinate-dependent selections.

## Future skill structure

- Preflight: current user scope/budget, inspect cached IDs and source versions, preserve manual edits.
- Offline planning: dimension dependency graph, per-tab feature manifest, payload/schema validation, cost accounting.
- Execution: one durable request reservation, inspect each mutation result, stop on ambiguity, no hidden retries.
- Verification: geometry and topology, parameter perturbations, assembly instances and mates, source comparisons.
- Recovery: checkpoint IDs, microversions, remaining budget, known-good payloads and unresolved errors.
- Promotion rule: label techniques documented, locally checked, or live proven; never turn hypotheses into skill guarantees.

## Research update: constraint semantics resolved (attempts 15-16)

- Downloaded official SDK OpenAPI from `https://raw.githubusercontent.com/onshape-public/go-client/master/onshape/api/openapi.yaml` into `research_sources/openapi.yaml`; `inspect_schema.py` makes it locally searchable.
- SDK describes `updatePartStudioFeature` as replacing an existing feature in its existing location.
- Applied the SAME prepared constraints using single-feature replacement, one request per sketch. Both returned HTTP 200 and `featureStatus=OK`.
- Profile and split now have connected polygons with orientation/length constraints and a fixed anchor point. Solver degrees of freedom and robust parameter behavior are not yet verified.
- Supported rule: create entities and constraints together initially; use full single-feature replacement for adding/removing sketch structure; reserve batch updates for existing nodes/parameters and preserve returned node IDs.
- Documented batching: `transformGroups` contains `{instances: [BTAssemblyInstanceDefinitionParams], transform: [16 numbers]}`; `setVariables` accepts an array of `BTVariableParams`.
- User has a separate agent migrating to local FreeCAD in a worktree (terminal 9:0.2). Research reuse of its feature/sketch definitions; do not edit that agent's worktree or equate STEP transfer with native feature-history transfer.

## Research update: live batching and parameter evidence (attempts 17-30)

- Attempt 17 inserted all four pins with Revision F rigid transforms in ONE `/transformedinstances` request. Attempt 30 verified four occurrences and exact requested transforms. They are positioned, not fixed or mated; no other components exist yet.
- Attempts 18/21 created a Variable Studio and assigned 38 nominal variables in bulk. ID `3d2282e9c3a6bc48e89ce5fd`, named `Design variables - Revision F`.
- Attempt 19 failed because derived expressions referred to variables not yet established in that new studio. Attempt 21 seeded all literals; attempt 22 assigned the full table with derived expressions successfully. Thus seed then relate is live proven; same-request creation with dependent expressions is not.
- Attempt 20 batch-updated EXISTING sketch constraint dimensions, preserving cached node IDs. It temporarily warned because the variable creation prerequisite had failed. Do not chain dependent calls without checking the first result: this was an avoidable mistake.
- Attempt 23 showed automatic Variable Studio visibility in the pin studio without explicit per-tab imports, crown diameter 4.2 mm, and nominal pin volume unchanged.
- Attempt 25 renamed BOTH tabs in one document metadata POST, using `{items:[{href,properties:[{propertyId,value}]}]}` and the href/property IDs from attempt 24. Both per-item statuses SUCCEEDED.
- Attempts 26/27 changed head radius to 4.5 mm and measured bounds +/-4.5 mm, height 14 mm, volume 230.69835158965364 mm3, one solid. This proves shared variables drive the native sketch/revolve, not merely a disconnected table.
- Attempt 28 restored the full nominal variable table. Attempt 29 verified all four native features OK, 26 profile constraints, 11 slot constraints. Assembly references the restored document microversion in attempt 30.
- The split sketch's anchor is fixed at nominal (-0.5,4) mm: split width/root are not yet robustly centered/driven under arbitrary edits. Only the head-radius perturbation was tested. Record this before claiming complete parameterization.
- At this checkpoint: 30/40 counted attempts used. Four native features, one modeled pin, four positioned assembly instances, 38 shared variables.

## Parallel public research

User explicitly authorized fan-out. Three research agents used zero authenticated calls:

- `research_sources/NATIVE_BULK_RESEARCH.md`: native tree limits, template copy, map variables, community examples.
- `research_sources/FREECAD_BRIDGE_RESEARCH.md`: FreeCAD bridge and Morphe constrained-sketch JSON/adapters.
- `research_sources/MCP_EFFICIENCY_RESEARCH.md`: hidden MCP operations, target restrictions, dense evaluation.

## Export/validation checkpoint (attempts 31-34)

- STEP export completed with three requests: export start, one status, download. Saved `33-native-pin-download.step`.
- Used existing FreeCAD bundled Python locally; no GUI launch or other worktree edit.
- Both STEP solids valid; bounds match. Both Boolean directional differences empty, but direct OCCT volume disagrees by 0.05231513305921 mm3. Fine tessellated volume agrees within about 0.00000163 mm3 and converges toward Onshape/source volume. Numerical integration discrepancy is suspected, not proven. Preserve conflicting evidence.
- Corrected the comparison script so Boolean emptiness alone does not imply acceptance when volume checks disagree.
- Attempt 34 obtained native shaded PNG, inspected visually; pin split/crown/chamfer present.
- Final request count 34/40. Six unspent. No more API calls needed to write research/handoff.
- Full current report and practical execution plan: `EFFICIENT_NATIVE_WORKFLOW.md`.
