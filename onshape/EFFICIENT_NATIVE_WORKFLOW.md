# Efficient native Onshape migration: researched and tested workflow

2026-09-07. This is an exploration checkpoint, not a completed mount migration.

## Result

34 counted attempts out of the user-authorized 40; six remain. One attempt was blocked by the local sandbox before an HTTP response; 33 received HTTP responses. This is an executor ledger, not a measured account billing-counter delta. All authenticated calls were direct REST; public research and three research agents made no authenticated calls. MCP tool descriptions were inspected without executing MCP tools.

The target now contains:

- **Push pin - native**: two ordinary constrained sketches, a revolve and a symmetric remove extrusion. Four native features, all status OK. The chamfer and crown taper live in the editable axial profile.
- **Design variables - Revision F**: 38 shared variables, including the mount parameter inventory and pin dimensions. The crown/socket diameter relationships are expressions.
- **Installed assembly - native WIP**: four occurrences of the pin in their intended installed positions. Transforms verified; no mates or fixed occurrences yet.

Links: [pin](https://cad.onshape.com/documents/c452b7f3224726ea2f11cdda/w/3231ffbfcf00782c1dba2494/e/cf9a24a5d90f7bf7ae0d3004), [variables](https://cad.onshape.com/documents/c452b7f3224726ea2f11cdda/w/3231ffbfcf00782c1dba2494/e/3d2282e9c3a6bc48e89ce5fd), [assembly](https://cad.onshape.com/documents/c452b7f3224726ea2f11cdda/w/3231ffbfcf00782c1dba2494/e/959913d7c8696541b603dc65).

## Proven ways to put more work in a request

| Technique | Live evidence | Practical cost |
|---|---|---|
| Complete native sketch payload | 9 profile segments + 26 constraints accepted together by full replacement | One sketch mutation, not one per curve/dimension |
| Full-profile revolve | Head, chamfer, shaft and tapered crown captured in one axial profile | Sketch + revolve, rather than separate operations for every axial section |
| Bulk Variable Studio assignment | All 38 variables accepted | One assignment; initial studio creation is another call |
| Dependent variable initialization | Seed literals, then assign relationships | Two assignments for this fresh table; same-request dependent initialization failed |
| Existing dimension batch updates | Both sketches changed to shared-variable expressions in one update | One POST for existing constraints with cached node IDs |
| New constraint insertion | Full single-feature replacement succeeds; batch update failed | One replacement per structurally changed sketch; include constraints at initial creation to avoid this |
| Assembly insertion with transforms | All four occurrences inserted together; matrices verified | One POST for all four, one GET for verification |
| Metadata batch | Both pin and assembly tabs renamed successfully | One workspace metadata POST after IDs/property metadata are known |
| Dense geometry evaluation | Counts, volume, bounds, part IDs and variable values returned together | One read-only FeatureScript evaluation per studio/checkpoint |
| Consume mutation response | Feature ID, regeneration status and microversion returned with creation | No extra lookup just to retrieve those fields |
| Cache public API schema | Official SDK OpenAPI downloaded from GitHub | Zero Onshape allocation for repeated schema research |

These are request counts observed in this experiment, not claims of API-allocation exemptions. Parallel requests do not reduce the count.

## Real limits

The official native feature creation endpoint takes one feature. Its batch-update endpoint explicitly requires existing features. We found no supported bulk creation of an arbitrary conventional feature tree. Custom FeatureScript can run many internal geometry operations, but those do not become separate editable sketch/extrude/loft entries. [Feature API](https://onshape-public.github.io/docs/api-adv/featureaccess/), [official API schema](https://github.com/onshape-public/go-client/blob/master/onshape/api/openapi.yaml).

The official MCP's geometry tool branches its configured sandbox and does not take our target document/workspace/element IDs. Its testing tools describe multiple underlying operations. Until request costs and destination behavior are measured, direct REST is the predictable route for this specific document and hard cap. This does not make the MCP useless for custom-feature development; it makes it a separate budgeted activity. See [MCP research](research_sources/MCP_EFFICIENCY_RESEARCH.md).

## Plan for the remaining mount

1. Keep a separate Part Studio for each distinct printed part, as requested. Build right-hand source parts first. For opposite-handed parts, prefer a linked native Derive + Mirror in its own tab if its dependency behavior is verified; ordinary edits then happen in the source tab. Copying a full native tree is an alternative when independent editing is intentional. These are proposed strategies, not live-tested in this exploration.
2. Use the shared Variable Studio for mating dimensions. Automatic visibility worked here, avoiding separate imports into every tab. Configured Variable Studios have different auto-insertion restrictions; research those before implementing the 8/12/16 mm outlet configurations.
3. Compile a feature manifest before spending calls: all sketch entities and constraints, then grouped operations by plane, extent and intent. Do not combine features merely to reduce count if that obscures a useful human editing boundary.
4. For each family, preserve the original operation order where fillets precede cuts. Group repeated holes/pockets into sketches, use native patterns, and preserve ruled duct transitions rather than silently substituting a smooth loft.
5. Build complete native constraint payloads at initial creation. For later edits, preserve server node IDs for partial batch updates; use single-feature replacement for structural sketch changes. Guard updates using source microversion when working alongside manual edits.
6. Insert all completed parts/occurrences using grouped transformed instances. Record the mapping from returned occurrence paths to part roles. Positioning is not mating: add and verify intended fixed/slider/fastened semantics separately.
7. Bundle per-studio verification into one evaluation. Obtain a final assembly definition once to check instance count, placements and references. Export the completed assembly once for local part matching and interference checks where that is cheaper than many individual exports.
8. Reserve a correction and verification allowance. Do not allocate the entire budget to feature creation or poll exports repeatedly while doing no other work.

A defensible full-build budget is `new tabs + native features + variable setup + assembly mutations + verification/export + correction reserve`. The exact feature count for the complex parts still requires the compiled manifest. This experiment does not justify another blanket 20/50/100-call promise.

### Remaining-work estimate after source reinspection

Planning allowance: approximately **200 additional API requests**, with a realistic range of **160-240** for the full conventional native deliverable. This is not a counted executable manifest or a guaranteed cap.

| Remaining work | Estimated requests |
|---|---:|
| Five source part families: cradle, duct, tray, cap, rail | 100-145 |
| Separate tabs and opposite-handed derived/mirrored parts | 20-25 |
| Assembly mates, outlet configurations and pin parameter completion | 10-20 |
| Geometry/parameter/fit verification, export and corrections | 25-45 |

The component ranges sum to 155-235; 160-240 is a rounded planning range. The existing 34 attempts are already spent, not included. Six of the current 40-call authorization remain. Main uncertainty: preserving cradle pre-Boolean fillets, ruled duct topology and stable mating references. The measured batching gains reduce overhead and repetitive work but do not eliminate creation of roughly a hundred ordinary native features. A hybrid custom-feature deliverable would be a different scope and is not this estimate.

## FreeCAD collaboration

There is no evidenced ready-made FreeCAD-to-Onshape history importer in the research. STEP transfers geometry, not the source constrained feature tree. A useful bridge is a common recipe of dimensions, sketches/constraints, operations and placements, emitted separately into each CAD system. FreeCAD can validate geometry and constraint behavior locally before cloud execution; it cannot prove Onshape regeneration without testing that backend.

[Morphe](https://github.com/CodeReclaimers/morphe) provides a CAD-independent constrained-sketch representation and FreeCAD adapter. It is a promising precedent, not an installed or tested dependency here; no Onshape adapter was found. Reuse its ideas or a narrow adapter only if it reduces work over the existing source. Do not turn this mount migration into a universal CAD converter. See [bridge research](research_sources/FREECAD_BRIDGE_RESEARCH.md).

## Validation actually performed

- Shared head radius changed 4 -> 4.5 mm: pin width/depth changed 8 -> 9 mm, height stayed 14 mm, one solid remained. Nominal values restored; final native features all OK.
- Nominal Onshape volume: 204.56030071178654 mm3, source approximately 204.56030211054718 mm3. Nominal bounds: (-4,-4,0) to (4,4,14) mm.
- Native STEP export used three requests: start export, one status read, one download.
- Existing FreeCAD 1.1.3 / OCCT 7.8.1 loaded the native export and original installed pin STEP, transformed the original back to pin-local coordinates, and checked both directional Boolean differences. Both were empty.
- **Numerical discrepancy retained:** direct OCCT volume of the native export is 204.50798697739742 mm3, while the source is 204.56030211045663 mm3. At 0.0001 mm tessellation deflection, their mesh volumes are 204.55988150407416 and 204.55988312993784 mm3 (difference about 0.00000163 mm3). Combined with Onshape's matching mass property and empty Boolean differences, this supports close shape agreement and suggests an integration discrepancy; its precise cause is unproven. No unconditional exact-conversion claim.
- Onshape shaded view inspected: head chamfer, shaft, split and crown visible. Image: [native pin](exploration_20/pin_native.png).

Only the head-radius parameter was exercised. The split sketch has a fixed nominal anchor (-0.5,4) mm; changing split width/root is not yet a robust centered/height-driven operation. Solver degrees of freedom have not been queried. The other ten distinct parts, mates, outlet configurations and full assembly fit checks remain unfinished.

## Reusable evidence and scripts

- [Running notebook](RESEARCH_NOTES.md): chronological discoveries and failures.
- [Request ledger](exploration_20/requests.jsonl): exact attempts; matching request and response files retain evidence.
- [Executor](explore_native.py): cap 40, no automatic retries or redirects, durable attempt reservation. Use sequentially; not designed for concurrent writers.
- [Pin payload builder](prepare_pin.py), [constraint builder](prepare_constraints.py), [variables](prepare_variables.py), [assembly payload](prepare_assembly.py).
- [Geometry comparison](compare_pin_freecad.py) and [results](exploration_20/pin_geometry_comparison.json).
- [Native API research](research_sources/NATIVE_BULK_RESEARCH.md), [MCP research](research_sources/MCP_EFFICIENCY_RESEARCH.md), [FreeCAD bridge research](research_sources/FREECAD_BRIDGE_RESEARCH.md).

These preparation scripts preserve the historical experiment; they are not yet a safe general migration command. A future skill should use vetted payload templates, explicit dependency checks, one central ledger, microversion protection, and separate labels for documented, live-tested and unresolved behavior.
