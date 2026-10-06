# Native FreeCAD wall mount

Open `Precision_5560_Native.FCStd` in FreeCAD 1.1.3. The source recipes and Revision F STEP files in the repository remain unchanged.

## Editing

- Double-click **Design parameters (mm)** to open the shared spreadsheet. Sections cover layout, structure, wall mounting, fan module, duct, outlet, fits, push pin and service.
- Edit blue input values in column B. Gray values derive from other inputs; overriding a formula deliberately breaks that relationship. Column D describes the actual dependency; column E records tests, not guaranteed continuous design ranges.
- **Installed assembly** contains fourteen links, grounded cradles, fixed joints and tray sliders. Part families have their own native construction groups. Expand the feature dependencies to edit constrained sketches, extrusions, lofts, rounded profiles, cuts and mirrors.
- SourceLocation on generated features identifies the preserved source recipe. PartKey and InstanceKey are stable identifiers; display labels are not identifiers.
- Geometry is in millimeters: X across laptop, Y outward from wall, Z up. Mirroring uses X=0. The native push pin uses Part Design; larger parts use standard Sketcher and Part features to preserve fillet-before-boolean construction.

## Evidence

- `final_native_validation.json`: original migration acceptance before the later user-requested finishing revisions.
- `FINISH_AUDIT.md`: current print freeze, six refined components, edit points, and validation evidence.
- `rail_refinement_validation.json`, `fan_finish_build.json`, `finish_cut_validation.json`: current finishing acceptance.
- `parameter_scenarios.json`: layout and fit cases pass; its fan-width failure predates the interface correction.
- `interface_scenarios.json`: corrected combined fan case passes regeneration and the four checked cradle interfaces.
- `fan_scenarios.json`: diagnostic isolation of the original fan-width binding failure.
- `parametric_validation.json`: historical individual sweep before rounded-profile repairs; not current acceptance. A successful nominal rebuild does not establish arbitrary parameter ranges.
- `clearance_validation.json`: independent exported STEP checks, including the original service-path samples.
- `reopen_validation.json`: independent FCStd reopen/recompute evidence, when present.
- `assembly_preview.png`, `parameter_sheet.png`: visual checks.
- `RESEARCH_NOTES.md`: working methods, failures, corrections and future-skill notes.

Earlier `native_validation.json` and `assembly_native_validation.json` are build-stage measurements. Queue receipts and recovery models retain the session's failures; they are not final acceptance evidence.

## Automation

`live_runner.FCMacro` runs a local queue on the GUI thread. A `.ready` file in `queue/` contains an absolute project-local Python path; completion produces a `.json` receipt and `.done` or `.failed`. No server or remote listener is installed. The runner and report-log timer can be stopped from the Python console with `App._mount_runner.stop()` and `App._mount_log_timer.stop()`.

Use `build_pin.py`, `build_families.py`, and `build_assembly.py` for construction. `native_ops.py` creates persistent stock FreeCAD features, and `design_bindings.py` adds dimensional dependencies to selected source recipes. The FCStd does not require these project modules to recompute its native geometry. Stock Assembly workbench Python modules are required for assembly joints, and ship with this FreeCAD installation.

Preserve a checkpoint before destructive rebuilds. Do not rerun the recovery scripts on a document with manual edits. All automated recovery in this session targets only this build's generated objects.

Do not send global keystrokes to control the GUI. Launch FreeCAD with the macro path or use its in-process GUI API. Do not read the live FCStd from another process while it is saving; use a completed snapshot for independent validation.

## Engineering boundary

This is a reconstruction and parametric CAD handoff. Existing structural, print and CFD evidence applies to the checked nominal Revision F geometry and assumptions. Edits require revalidation. Discrete geometric clearance checks do not prove uninterrupted collision-free motion, physical pin retention, adhesive strength, thermal performance or load capacity.

## Current checkpoint (2026-09-07)

The saved native document contains 40 shared aliases, 158 fully constrained sketches and 14 valid installed solids (11 modeled sources). Thirty fragile edge fillets were replaced with equivalent constrained rounded profiles and native extrusions. The assembly contains two grounded components, ten fixed joints and two tray sliders.

The tested layout case changes laptop dimensions to 346.4 x 231.3 x 20.5 mm, wall gap to 40.5 mm, tine height to 95 mm and wall-hole dimensions/positions. The fit case increases key/tray clearances and changes pin socket, cap passage and split width. Both regenerate without invalid features and preserve the four checked keyed interfaces. Exact inputs are in the reports.

The corrected fan case changes frame width to 120.5 mm, thickness to 25.5 mm, angle to 46 degrees, pivot to Y=67.5/Z=-83.5 mm, duct skin to 2.2 mm and grille bars to 2.6 mm. Fan width now changes the inlet while downstream sections retain the fixed cradle-interface width. The original binding widened all sections and caused about 180.819 mm3 interference per side. `fix_duct_interface.py` records the correction; `design_bindings.py` constructs it correctly for future builds.

Changed-case acceptance covers regeneration and the reported interfaces only. Full nominal clearance and sampled service checks are separate. These examples do not establish continuous safe parameter ranges or full clearance for every altered configuration.

The recovered Build_Recovery document is an older checkpoint. Continue editing `Precision_5560_Native.FCStd`. Automation must resolve the document by its absolute filename because the active document can change when the user selects another tab.

## Personal workspace and latest finish

The live GUI uses `fusion_ribbon.py`: Solid/Surface/Mesh/Sketch/Tools tabs, with Fusion-style Create, Modify, Assemble, Construct, Inspect, Insert and Select group order. Every mapped core command was checked against this installation. FreeCAD operation distinctions remain explicit in the menus: Part extrusion, Part Design Pad and Pocket are separate tools. Sheet Metal is disabled because its add-on is absent. This is a mapped native-command ribbon, not an exact reproduction of all Fusion workspaces or its timeline.

Navigation is Revit: middle-drag pans, Shift+middle-drag orbits, wheel zooms. `workspace_ui.py` supplies the coordinated UI styling and dock layout. `FUSION_GUIDE.html` is available in the ribbon. A small personal bootstrap is installed at `%APPDATA%/FreeCAD/v1-1/Mod/StudioWorkspace/InitGui.py`; rename that file to disable startup customization. Settings/layout backups are retained alongside the model. Latest solid background: #9EA6AD.

The local runner now holds an OS file lock so two FreeCAD processes cannot claim this project's queue. The user closed the duplicate session; the remaining session was verified to hold the latest saved rail refinement. The arms remain frozen. Revised component STEP/STL exports are in `print_refinements/`; these use installed assembly coordinates, so orient them for printing according to the source and finish-audit notes.


Latest adjacent-part review: [ADJACENT_FIT_REVIEW.md](ADJACENT_FIT_REVIEW.md). Revised, oriented P1S STLs: [print_refinements_oriented](print_refinements_oriented/). Original print_ready files are older geometry. Arms remain frozen.
