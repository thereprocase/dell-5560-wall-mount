# FreeCAD to Onshape: native-history bridge research

Research date: 2026-09-07. Public documentation/repository research only. **Zero authenticated Onshape or MCP requests made by this research branch.** Nothing installed, no CAD document modified, and no other worktree edited.

## Recommendation

Use the independent FreeCAD migration as an offline reference and share the design recipe, rather than routing the native Onshape rebuild through STEP. A narrow common manifest containing parameters, sketch geometry/constraints, ordered solid operations, and assembly placements is the practical bridge. Emit a native FreeCAD tree and native Onshape feature payloads from that manifest. This is an engineering recommendation, not a verified existing translator.

No ready-made FreeCAD-to-Onshape feature-history translator was evidenced by this search. That is a bounded research result, not proof none exists.

## What imports preserve

- [Onshape supported formats](https://cad.onshape.com/help/Content/File/supported_file_formats.htm) explicitly labels STEP AP203/AP214/AP242 import as geometry and face color only. FCStd is absent from the translated CAD format list. Uploading an FCStd archive as a blob would not create a native feature tree.
- [Onshape imported-CAD guidance](https://cad.onshape.com/help/Content/Document/working_with_imported_cad.htm) discusses missing parametric history and continuing through direct edits and new features. This can deliver useful editable solids but does not restore the source sketches, constraints, pads, and pockets.
- [FreeCAD FCStd specification](https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/File_Format_FCStd.md): FCStd is a ZIP archive; Document.xml stores the object/parameter graph, while individual BREP files retain computed shapes. This provides an offline extraction path with no cloud requests. Prefer the generating Python script or FreeCAD Python API when available, because custom objects and binary property payloads make a general XML translator more complex.

## Useful existing projects and community techniques

### Morphe / SketchBridge: strongest reusable precedent

[Morphe repository](https://github.com/CodeReclaimers/morphe) advertises a CAD-independent constrained-sketch JSON representation, FreeCAD/Fusion/SolidWorks/Inventor adapters, solver status/DOF reporting, and FreeCAD roundtrip tests. Its FreeCAD RPC example exports and imports sketches. It is MIT licensed. **No Onshape adapter is listed.** This is a candidate source of schema and adapter patterns, not a drop-in solution or a dependency validated in this workspace. Its README links a SketchBridge desktop UI.

[Morphe specification](https://github.com/CodeReclaimers/morphe/blob/main/SPECIFICATION.md) makes stable element IDs, explicit point references, explicit geometric relations, and adapter-boundary coordinate conversion central. It separates schema validity, geometric validity, and solver satisfiability. These are valuable design rules for a future Onshape bridge. It covers sketch interchange, not a complete solid-feature/assembly migration. An Onshape emitter and an operation/placement layer would still be required.

### Onshape employee's compact custom-sketch recipe

[Onshape forum: Best way to use Onshape via Python](https://forum.onshape.com/discussion/20534/best-way-to-use-onshape-via-python) contains an Onshape employee's example of defining sketch creation in FeatureScript and posting a short custom-feature envelope with its namespace. This moves geometric complexity into one reusable definition and reduces payload authoring. It does **not** by itself prove reduced underlying request count or convert the custom feature into a conventional editable sketch feature. Choose this when a parameterized custom feature is acceptable; for conventional sketch/extrude history emit native feature records.

### JSketcher FCStd import: real lead, insufficient history evidence

[Author's July 2022 demo](https://www.youtube.com/watch?v=VjoP9uSRSYs) demonstrates direct FCStd import and says the implementation was in a development branch. [JSketcher repository](https://github.com/xibyte/jsketcher/blob/main/README.md) implements constrained sketches, feature history and an OpenCascade geometry backend. The specific importer code and its preservation of source constraints/history were not recovered in this pass. **Do not infer that native-file import means parametric-history conversion.** It also supplies no evidenced Onshape backend. Keep as a follow-up lead, not the critical path.

### cadmpeg: semantic interchange research, not an Onshape shortcut

[cadmpeg format-support matrix](https://github.com/cadmpeg/cadmpeg/blob/main/docs/format-support.md) distinguishes geometry, design records, complete design semantics, assemblies and native writeback. It reports FreeCAD semantic read/write coverage inside a declared envelope, and expressly says every native format remains incomplete. No Onshape codec appears in the inspected matrix. Its [architecture](https://github.com/cadmpeg/cadmpeg/blob/main/docs/architecture.md) makes losses explicit in a shared intermediate representation. Useful taxonomy for reporting conversion fidelity; its claims were not independently tested here. Installing a broad codec framework would not remove the need to generate Onshape feature API payloads.

### CodeToCAD: verify current implementation before adoption

[CodeToCAD](https://github.com/CodeToCAD/CodeToCAD) appears in Onshape-related searches, but the inspected current README demonstrates a build123d model and does not establish a functioning native-history Onshape bridge. Topic tags and old mentions are insufficient evidence. No installation recommended for this experiment.

## Proposed narrow bridge contract

The following is a proposed workspace-specific design, not a claim about a third-party library:

1. Shared dimensions: stable names, numeric baseline values, units, and expression dependencies. Keep existing source formulas authoritative.
2. Sketches: stable sketch/entity/point IDs; explicit plane origin and orthonormal basis; analytic line/arc/circle geometry; construction flags; driving versus reference constraints; dimensional expressions.
3. Operations: ordered extrude/revolve/add/remove/fillet/chamfer/pattern records referencing semantic sketch IDs. Record extent, direction, operation scope, and ordering explicitly.
4. Topology: prefer sketch-origin and semantic feature queries. Never transfer FreeCAD face/edge indices directly to Onshape IDs.
5. Assemblies: part-family IDs plus full placement matrices and intended joint/mate semantics. Placement import alone is not evidence of solved mates.
6. Verification: expected part counts, volumes, bounds, key sections/hole centers, and expected degrees of freedom. FreeCAD checks happen locally; Onshape regeneration/solver checks remain essential.

Start with the pin and one predominantly planar part, implementing only the feature and constraint families actually present. Round-trip a parameter change locally and on Onshape before broadening the adapter. Share the small recipe and measurements with the other migration agent rather than asking it to abandon its independent implementation.

## Call-density implications

- Extracting FCStd/script design information and running FreeCAD recomputes costs zero Onshape requests.
- A shared manifest eliminates duplicate geometric reasoning and permits full request bodies to be prepared before publishing. It does not change documented endpoint request granularity.
- Separate part tabs still require Onshape element creation. Native features, assembly instances, and mates still need their relevant cloud mutations. Batch only where the endpoint explicitly supports it; do not equate one Python helper or one MCP call with one API request.
- STEP can be a compact comparison artifact or fallback geometry delivery, but treating it as native migration would overstate completion.
- Cross-kernel validation matters: [FreeCAD issue 20889](https://github.com/FreeCAD/FreeCAD/issues/20889) records a fillet STEP-export discrepancy observed in Onshape. It is evidence that a local reimport alone is insufficient, not a claim all current exports are broken.

## Read-only local inventory

`git worktree list` returned `F:/Code/dell-5560-wall-mount` on `onshape-native-rebuild` and `F:/Code/dell-5560-wall-mount-standby` on `codex/parallel-standby`, both at 576da22 during this check. No FreeCAD-named files appeared in the bounded filename search of the standby worktree. This does not identify or exclude the user's independently running 9:0.2 agent, which may be working elsewhere or may not yet have saved files. No existing root AGENTS.md was found in this checkout.

A follow-up read-only installation check found `C:/Program Files/FreeCAD 1.1/bin/freecadcmd.exe`, `freecad.exe`, `python.exe`, `python311.dll`, and `FreeCAD.pyd`. No FreeCAD executable was discovered on PATH. No application was launched by this branch. The existing bundled environment is a candidate for offline STEP comparison without installing another kernel.

## Skill notes to retain

Always report geometry, editable parameters, native conventional history, constrained sketches and assembly mates as separate achieved capabilities. Prefer a narrow intermediate representation over an unproven universal converter. Preserve raw source and reference solids. Record every actual authenticated request centrally, including failures, hidden validation calls and polling. Local schema checks, a different CAD solver, and a generated payload are preparation, not proof of Onshape success.
