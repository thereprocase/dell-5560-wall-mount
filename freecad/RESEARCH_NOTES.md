# FreeCAD native engineering notebook

Updated 2026-09-07. Evidence for a future FreeCAD skill; this is a project notebook, not an installed skill.

## Scope and preservation

- User requests the entire Revision F mount as editable native FreeCAD sketches and features, visible during construction, suitable for continued design work.
- Isolated worktree: F:/Code/dell-5560-wall-mount-standby; branch codex/parallel-standby; baseline 576da22.
- Parallel Onshape agent owns the original checkout. Do not modify its source, notes, request budget, or document.
- User authorized using the empty warmed-up FreeCAD document, saving in this worktree, and opening/closing FreeCAD as needed.
- Original CadQuery/STEP evidence remains unchanged. Native files and build scripts live in freecad/.

## Live-proven tooling

- C:/Program Files/FreeCAD 1.1/bin/python.exe: Python 3.11.14, FreeCAD 1.1.3, Qt 6.8.3.
- Embedded imports FreeCAD, Part, Sketcher work without another Python installation.
- Headless native sketch + PartDesign Pad test: one valid solid, expected cylinder volume.
- Launching freecad.exe with an absolute .FCMacro argument executes the macro in a visible new instance. This started successfully with PID 21056 (session-specific, do not reuse blindly).
- live_runner.FCMacro keeps a Qt timer alive on App._mount_runner. Timer processes one .ready file, stops during execution, writes .json status and .done/.failed receipts, then restarts.
- Scripts execute on the GUI thread. Gui.updateGui() periodically allows visible progress. Never modify a FreeCAD document from a worker thread.
- Queue paths must resolve inside this freecad/ directory. Files are local code, with no network listener. Execution is privileged only as much as the running user process.

## Important failure: keyboard focus

WScript.Shell.AppActivate + SendKeys did NOT reliably focus FreeCAD. The attempted macro path was typed into the user's chat. Do not use focus-dependent keystroke injection. Direct executable launch with a macro argument worked and does not consume keyboard focus. For future GUI interaction use in-process FreeCADGui/Qt APIs and verify results in files or screenshots.

Sandboxed process inspection hid the real window handle/title; elevated read-only inspection showed the actual desktop process. A zero MainWindowHandle in the sandbox did not prove there was no GUI.

## Native model strategy

- Push pin: PartDesign Body, five fully constrained sketches, two Pads, Chamfer, AdditiveLoft, Pocket. Spreadsheet expressions drive diameters, heights, clearance, interference, and split.
- Measured pin: one valid solid, volume 204.56030211057183 mm3; matches recorded source volume to numerical precision. Full transformed STEP comparison follows assembly placement.
- Larger source parts have fillets before fuses and cuts. Preserve this order using standard Sketcher + Part Extrusion/Fillet/Fuse/Cut/Loft/Mirroring and linked placements.
- native_ops.py implements only the small source construction vocabulary. It constructs persistent native features; it never assigns a final opaque BRep to a Part::Feature. Saved files do not need the adapter to recompute native operations.
- build_families.py reads selected source functions through AST, without importing CadQuery or executing the source exporters. SourceLocation properties retain original file and line provenance.
- Polygon sketches use coincident vertices and editable dimensional coordinates; zero coordinates use PointOnObject to the relevant sketch axis. These are constrained coordinate profiles, not claimed to be a fully refactored design-intent constraint graph.
- Outlet gap uses spreadsheet expressions through a symbolic numeric adapter. Pin parameters are expression-driven. Broader cross-family parameter dependency coverage still needs audit.
- Per-family checkpoints compare valid solid count, volume, bounding box, and symmetric BRep difference with the preserved STEP files. Matching volume alone is not acceptance.

## Current evidence / continued-work requirements

Read queue/*.json, pin_validation.json, native_validation.json, build_progress.json, and any build_failure.txt. Runtime files report what actually completed.

Still to verify as construction progresses: all five families, final 14-instance assembly, native assembly joints/service direction, symmetric shape differences, outlet alternatives, save/reopen, parameter perturbations, interference/service checks, and model-tree organization. Physical load, adhesive, thermal, print, and retention behavior are not established by a successful CAD rebuild.

## Future skill outline

1. Preflight/version/workspace and document inventory; preserve user changes.
2. Clarify mechanical function, load cases, materials, manufacture, interfaces, and acceptance evidence.
3. Choose stable skeleton, coordinates, datum planes, part boundaries, and dimensional dependencies.
4. Use named native sketches/features, geometric constraints, expressions, mirrors/patterns, and assembly links/joints.
5. Iterate in short transactions, recompute/inspect, save checkpoints, and maintain source provenance.
6. Validate shape/topology, mating clearances, parameter changes, service paths, and exports independently.
7. Separate geometric verification from physical engineering validation.
8. Hand off editable FCStd, scripts, evidence, tested parameter ranges, limitations, and next steps.

Avoid hard-coded session PIDs, desktop coordinates, silent topology changes, blanket Block constraints, imported-only final solids, invented API properties, and claims that CAD success proves structural safety.

## Parameter expansion and further verified fixes

The user explicitly requested more parameters and a well-organized spreadsheet. The parameter sheet now has 40 named values grouped into Layout, Structure, Wall mounting, Fan module, Duct, Outlet, Fits, Push pin, and Service. Inputs and derived formulas have different colors. Stable aliases, not row numbers, are the feature interface.

- `design_bindings.py` makes dimensional relationships explicit: fit allowance to bare slot; laptop height to contraction/throat/lip; symmetric module spacing; wall holes and tool corridors; pin sockets; dovetail/mortise clearances; fan plane and mating placement; duct insets. This is being validated, not assumed proven.
- FreeCAD `Placement.Rotation.Angle` expressions accept angle quantities in degrees correctly. The Python Rotation.Angle accessor itself is radians; do not confuse them.
- `App::Link` does not expose ShapeColor directly through its default ViewProviderLink. Set the source view color or inspect Link material override APIs.
- Display labels are auto-deduplicated by FreeCAD. Use `PartKey` and `InstanceKey` properties for identity, never infer filenames from labels.
- Assembly uses the stock `Assembly::AssemblyObject` and `Assembly::JointGroup`; `JointObject.Joint`, `ViewProviderJoint`, and `GroundedJoint` are installed workbench classes. Solver returned 0 with negligible placement changes for the initial assembly.
- Source-connected Part::Compound nodes preserve standard feature placements through downstream Part operations. The initial App::Link transform chain was not respected by Part::Mirroring.
- Native Part::Loft `Linearize=True` converts planar spline faces to actual planes. This corrected the right-duct symmetric difference from 0.04956 mm3 to zero. Do this at initial construction. Updating old lofts in place left an old mirrored result with invalid boolean differences; a freshly created native mirror of the updated source was valid and matched exactly.
- Never trust a difference volume without validating both boolean result shapes. The stale mirror produced negative volumes and nonsensical results; increasing fuzzy tolerance did not fix it and was rejected as a solution.
- Do not open the live FCStd in a separate process while the GUI saves it: the external read caused a Windows rename failure. Perform independent tests on a completed copy or exported STEP.
- Before deleting generated objects during a rebuild, snapshot their string names. Assembly observers may remove dependent objects automatically, invalidating cached Python object handles. Preserve a pre-rebuild FCStd checkpoint.

## Application log and spreadsheet QA

- Capture the actual Report view and notification widgets, not just caught Python exceptions. `capture_log.py` saves app_report_log.txt/json every three seconds using a retained GUI-thread Qt timer. Historical failures are preserved; inspect timestamps and queue receipts to distinguish old failures from current work.
- FreeCAD Spreadsheet stores `-36 mm` as text. Set `=-36 mm` for a negative quantity. getContents() may return a leading apostrophe for text and a leading equals sign even for ordinary numeric quantities. Preflight actual alias value types, not only input strings.
- Classify derived spreadsheet cells from the explicit dependency specification, not a leading equals sign: positive literal quantities can also normalize to formula strings.
- Active view can be the spreadsheet. Obtain `Gui.activeDocument().mdiViewsOfType('Gui::View3DInventor')[0]` for camera methods rather than assuming activeView() is 3D. This permits model building while the user keeps Parameters open.
- After organizing cells, preserve and reapply expression bindings. Alias names are the stable interface; hard-coded B12-style addresses are not suitable for validation or continued editing.
- Current parameter expansion uses `Parameters` as the same document object, with nine sections, descriptions, units, input/derived distinction, and per-input validation results. Some remaining local section dimensions intentionally live in their sketches.

## Export, restart, and performance

- The application's log revealed that `Part.export` silently ignored App::Link assembly components. `Import.export` on the 14 links was tested from an isolated FCStd snapshot and produced 14 valid STEP solids. Use the assembly-aware exporter and reimport the output; absence of a Python exception is not proof of export success.
- Native baseline acceptance for the expanded model: 128 fully constrained sketches, 14 valid solids, no invalid features, and valid symmetric-difference results of zero for all fourteen parts.
- Independent exported-STEP checks passed the original laptop/fan/driver and sampled assembly/service paths. Only intentional split-pin crown interference remained (about 0.13038 mm3 at each socket).
- Live parameter sweeps were too slow and monopolized the UI. Nominal FCStd and a validation snapshot had been saved first. The two agent-created GUI processes were stopped; the nominal model was reopened with a fresh runner and `--log-file`. Remaining sweeps moved to the bundled Python executable against the separate snapshot, skipping completed cases. Do not read/write the active GUI document from the worker.
- `--single-instance` only routes to an instance that was started with single-instance support; it did not attach to the earlier normal process. The attempted cooperative pause did not reach the running sweep and is not a proven cancellation method. Add explicit cancel-file checks to future job loops before launching them.

## Robust native rounded profiles

Parameter tests exposed `Missing edge link` errors on standard Part::Fillet features when profile dimensions changed. The nominal shape remained cached and valid, so checking only final solid validity would have missed the failed regeneration. Check each document object's state/status as well.

The accepted correction is native rounded Sketcher profiles followed by Part::Extrusion, with no Python feature proxy. `rounded_profiles.py` replaced 30 planar-profile fillets. Each replacement was independently compared with its old shape before reconnecting downstream links. All replacements matched within the nominal comparison gate. The previously failing laptop-thickness test then passed with no feature errors.

- Polygon profiles derive arc centers and tangent endpoints from the original constrained sharp profiles. Coincident arc/line endpoints close each wire.
- Rectangular source boxes use their native Shape.BoundBox expressions to define a rounded profile in the correct extrusion plane. Their original parametric box dimensions remain dependencies.
- Each arc uses center coordinates, radius and a well-conditioned endpoint coordinate for each end. This avoids the poor conditioning of short chord plus radius constraints.
- Preserve observed native results: the original front-tine fillet did not round one shallow corner. Rounding every mathematical corner changed volume by 0.005995 mm3. The replacement detects actual source circular arcs and retains the source's sharp corner; no tolerance was relaxed to accept that discrepancy.
- Zero DistanceX/DistanceY dimensions were locally tested and accepted by Sketcher 1.1.3. Do not assume zero dimensions require Block constraints.
- The resulting model has native feature dependencies and needs no project Python code to recompute geometry after opening. The builder/repair module is construction tooling only.
- Official source consulted to understand missing-edge behavior: https://github.com/FreeCAD/FreeCAD/blob/main/src/Mod/Part/App/FeatureFillet.cpp and https://github.com/FreeCAD/FreeCAD/blob/main/src/App/PropertyLinks.h. The final workaround is locally tested; it does not patch FreeCAD or disable topological naming globally.
- Write Python source explicitly as UTF-8 on Windows. Path.write_text() without encoding can emit cp1252 and break a subsequent import when labels contain Unicode.

## Final validation and interface correction

- Final construction has 158 fully constrained sketches, 14 valid installed solids and no invalid feature states. Nominal Boolean comparisons pass with valid difference shapes. Independent reopen and forced recompute pass, including 14 assembly joint/ground objects and intact joint references.
- The combined layout and fit cases pass regeneration and four cradle keyed-interface checks. The combined fan case initially regenerated but intersected each cradle by about 180.819 mm3. Validation originally aggregated only regeneration; corrected it to report regeneration_pass, clearance_pass and their conjunction all_pass. Preserve failing evidence rather than rewriting it as success.
- Isolating fan size from pose showed width/size changes reproduced the collision while pose-only changes did not. Inspection found fanFrameWidth incorrectly drove all duct cross sections. Keep the fan inlet variable and downstream cradle-side section width fixed. Twenty-four native sketch expressions changed; nominal shape is preserved. The full combined fan case then passed all four checked interfaces with zero overlap.
- A shape-valid solid is insufficient engineering acceptance. Check feature state, constraint state, intended interfaces, external component clearance and sampled service paths separately. Record which configurations each claim covers.
- GUI image capture: grabbing the whole Qt main window can corrupt OpenGL content or capture the wrong active subwindow. Use the 3D view's saveImage for model previews, explicitly activate the SpreadsheetGui::SheetView through QMdiArea, and capture that widget after a short Qt timer delay.
- Never depend on ActiveDocument after recovery or user tab changes. Resolve canonical FileName and set that document active. Earlier recovery log errors remain preserved and are not evidence against the later saved native document.
- Future skill scope: inspect intent and source geometry; establish datum/parameter contracts; build stock native dependencies; edit through stable aliases/object identifiers; keep UI responsive with short jobs and explicit cancellation; capture actual application errors; validate nominal and changed configurations separately; save checkpoints and clear evidence provenance. Do not imply professional certification or physical verification from CAD validity.

- Spreadsheet display titles may use the document Label after renaming, rather than its internal Name. Resolve the underlying document by filename, then accept either Name or Label when selecting its sheet window. A failed display selection can occur after a successful geometry validation/save; report these outcomes separately.

## Studio graphics preset

`studio_view.FCMacro` restores the model, backs up it and the View parameter group, applies MSAA 8x (enum value 4), VBO, automatic cache, three-point lighting, slate gradient, shaded satin materials, 0.05% deviation and 5-degree angular deflection. `studio_camera.py` uses 0.35-radian perspective for less distortion. Saved geometry remained 14 valid solids with no invalid features or broken joint references. Restore-time joint warnings were transient; post-restore references passed checks.

Source keys verified against FreeCAD 1.1.0: src/Gui/Multisample.{cpp,h}, View3DSettings.{cpp,h}, PreferencePages/DlgSettingsLightSources.cpp and DlgSettings3DView.ui at https://github.com/FreeCAD/FreeCAD/tree/1.1.0/src/Gui . Software OpenGL is in Preferences/OpenGL, while lights are in Preferences/View/LightSources. Directions use parenthesized vector strings. The requested AA setting is verified; effective GPU sample count and interactive navigation-cube behavior were not measured. The render preview was visually inspected.

The prior FreeCAD process was a fresh session without the runner. A --single-instance request exited without executing the macro. Direct executable-plus-macro launch succeeded. Preserve unrelated sessions; never use global SendKeys to recover automation.

## Matte illustration preset

`cel_view.py` adds Flat Lines with 1.3 px charcoal edges, low material specularity (0.06/0.07/0.08) and shininess 8, teal/graphite/gold source colors, and a lighter slate gradient. Key/fill/rim/ambient intensities are 95/14/48/10. The prior document and View preference group are backed up before changing appearance. Geometry and sketch data are untouched; preserve the user camera and clear selection for a clean preview. This is a cel-inspired live viewport treatment, not a quantized shader or modeled surface texture. `cel_preview.png` records visual QA.

User approved the matte illustration style and disliked gradient banding. Final preset uses a solid slate #52606D background; keep this preference for future model presentation.

Background refined at user request: 20% blend toward white from #52606D to #75808A. This is the current preferred solid background.

## Ribbon mapping, print freeze and batched finishing

The user asked for Fusion-style grouped commands, not just a workbench tab strip. `fusion_ribbon.py` follows Solid/Create/Modify/Assemble/Construct/Inspect/Insert/Select order and supplies a contextual Sketch tab. Reference: https://help.autodesk.com/cloudhelp/ENU/Fusion-Model/files/GUID-99E108D3-07E9-4FFA-AEF9-A97D3278ED91.htm and Autodesk's Fusion interface guide. Workbench differences are explicit; missing Sheet Metal is disabled, not impersonated. Pin buttons plus group dropdowns reduce native toolbar clutter. QTabBar requires scroll buttons disabled, no elision and sufficient minimum width to prevent the clipped-tab arrows the user rejected. Actual toolbar-widget grabs work; whole-window desktop capture returned a black pixel on this session.

The user froze both arms after starting prints. Preserve current BRep baselines and check valid symmetric differences before/after edits. Print-freeze properties document the boundary; they do not magically prevent all indirect edits through shared parameters. Do not change frozen dimensions or rebuild the cradles.

Repeated per-feature recomputes caused avoidable UI pauses. The final fan finishing operation creates both complete native chains, then recomputes once (18 seconds including save/checks versus many intermediate rebuilds). Parameter-sheet changes can dirty wide dependency graphs; avoid mixing decorative cell edits into a small geometry edit. Further validation and exports run on completed copies outside the GUI.

A second GUI session had also acquired the same queue, causing conflicting logs and file-rename receipts. A process-wide save/close proposal was rejected by automatic approval review. The safer alternative touched only our automation timers; the user closed the duplicate session themselves. The surviving process and saved XML were checked before continuing. `live_runner.FCMacro` now holds an OS file lock for its lifetime, records PID, and catches claim races. No global keystrokes or forced shutdown are used.

For cover-matched outlines, blindly applying an edge fillet failed on the duct bosses. Analytic R4 corner-cut profiles succeeded and preserved the R3.25 socket support envelope. Tray bed-side R4 fillets would create less favorable early-layer overhangs; 45-degree reliefs tuck the square backing behind the rounded cover while preserving the fan ledge and sliding features. See FINISH_AUDIT.md for all source-family decisions.


## P1S orientation re-review and open finish defect (2026-09-07)
Re-read root README.md, P1S_ASA_Print_Guide.md, TOLERANCES.md and prepare_prints.py.
Machine baseline: P1S, 0.4 mm nozzle, ASA, 0.20 mm layer, 6 walls, 6 top/bottom,
100% infill of explicit hollow geometry, 8 mm outer brim, supports off.
Orientations: cradles outer-side-down with the supplied 45-degree plate rotation;
ducts untilted, inlet-down; trays untilted, grille-down; caps untilted then X -90
(face-down); rails X 180 (lip Z232 down); pins button-down.
Preserve 0.30 mm dovetail side/crown and fixed-key nominal offsets, 0.20 mm
root allowance, and existing pin/socket diameters. No global shrink scaling.
The user's newest arrow identifies a remaining protruding teal corner behind a
fan cover. OPEN: exact live face identification requested; do not treat the previous
finish audit as exhaustive acceptance. Check opposite-side mirrored counterpart
and the full length of any proposed relief, especially the inlet-down first layers,
socket support, dovetails and duct wall thickness. Both arms remain PRINT FROZEN.
Latest refined STL exports are installed-coordinate exchange files; the original
print_ready files have the old revision. Do not pass these off as updated oriented
P1S print files. Regenerate a separate oriented set after the remaining finish fix.


Selected-face diagnosis: read SelectionEx and transform vertices back to the
construction coordinates. The earlier fixed-depth cosmetic cut ended at local
Y121, intersecting the sloped wall and creating a fin. Blending its termination
with an oblique extrusion from the same constrained R4 profile resolved the
abrupt corner without global fillets. Test against a saved snapshot first;
compare actual native result volume to the tested Boolean result and preserve
socket envelopes and frozen-part geometry. Native group: BossRunout.


Full adjacent-fit review: zero interference does not establish print clearance.
Measure distToShape for separate dry-fit parts, and isolate male keys from their
intentional load shoulders. Replaced coordinate-only dovetail allowance with
0.30 mm normal flank offset. Preserve intentional pin interference separately.
A 0.01 mm Boolean-tool overlap created microscopic faces and mismatched mesh
edge subdivisions. Making the tool junction exactly coincident removed these
faces; do not treat mesh welding as a substitute for fixing source geometry.
Animated ViewFitSelection could capture stale framing. Use camera-node position,
orientation and focal distance derived from a part bounding sphere for reliable
live review; restore visibility after isolated-part viewing.


HTML5 showcase: showcase/public contains a private, self-contained Three.js
before/after viewer, 14 pairs of installed-coordinate meshes, exploded/focus
controls, evidence summaries and 6 oriented STL downloads. Tailscale Serve route
/mount-showcase proxies localhost:8876; existing root and TCP services retained.
Serve only curated public/, not the repository. Tailnet HTTPS testing found 502s
from simultaneous mesh requests exhausting the default Python socket backlog;
limited loading to one part pair at a time and raised request_queue_size to128.
Desktop/mobile HTTPS browser checks now pass with zero script/resource errors,
WebGL ready, no mobile overflow and all six downloads available. Server is a
hidden Python process; route persists but process must be restarted after reboot.


## Revision G release — 2026-09-07
Final model: 14 valid installed solids and 176 fully constrained sketches. Separate additive patches restore the original lofted duct wall; measured missing wall is zero. Six fan interface gaps remain 0.30 mm. Printed arms are unchanged. The complete P1S-oriented release is ../print_release/; public showcase is ../docs/. CFD figures describe the earlier baseline, not a new Revision G solve. A valid solid can still contain an unintended wall opening: check wall continuity against the original shell, not only isValid().

Airway review: audit_airway_continuity.py verifies zero patch intrusion into the original inner loft, zero missing wall, unchanged frozen arms and six 0.30 mm gaps. No geometry change was warranted. This is geometric acceptance, not measured airflow or thermal validation.

Revision H: three R12 internal tangent blends and two R14 exterior support blends per duct, native FlowInnerBlend/FlowOuterSupport. Broad smooth-loft trial was rejected because a downstream union became invalid. Final local blends pass native and independent STEP service checks, sampled wall thickness >1.60 mm and curved overhang <40 degrees. Arms and interfaces remain fixed. Revision H supersedes the earlier no-intrusion audit with explicit intentional blend accounting.
