# FreeCAD continuation — Revision H

Worktree: F:/Code/dell-5560-wall-mount-standby, branch codex/parallel-standby. All completed FreeCAD, Fusion and Onshape work is merged into main in the original checkout. The GUI still uses this standby worktree.

Open freecad/Precision_5560_Native.FCStd. Read README.md for editing and evidence, RESEARCH_NOTES.md for workflow failures and corrections. The native model is the canonical editable artifact; STEP is exchange output. Recovery files are older evidence, not the current model.

The GUI runner polls local queue jobs. Always target the document by absolute FileName. Inspect app_report_log.txt and queue receipts. Never use global SendKeys. Headless checks run against ValidationSnapshot.FCStd, never against a GUI save target.

Current construction: 40 shared aliases, 176 fully constrained sketches, 14 installed solids. Rounded-profile replacements avoid unstable edge-filleting dependencies. Fan inlet width varies independently of the fixed cradle-side duct sections. Reports preserve original failures and separate successful regeneration from interface clearance.

No installed FreeCAD skill has been created yet. The notebook is the evidence for building that skill. No physical testing is implied by CAD acceptance.

PRINT FREEZE: User is printing both gray cradles/arms. No more geometry changes to either. frozen_print_arms/ records the exact current shapes. All subsequent outlet-rail fit changes must validate both against this baseline.

Latest completed work: teal rail dust roof and contoured arm relief, R2 rail tip, print-safe tray corner bevels, R4 cover-matched upper bosses. See FINISH_AUDIT.md and print_refinements/. Fusion-style grouped ribbon is fusion_ribbon.py, loaded by the personal StudioWorkspace module. Background #9EA6AD; Revit navigation. Runner now owns an OS lock; duplicate GUI was closed by the user. Latest validation: clearance_validation.json and rail_refinement_validation.json both pass.

Latest live pass: BossRunout and FanFitClearance, 0.30 mm dry-fit gaps, tangent rail lead-in, no microscopic finish slivers. See ADJACENT_FIT_REVIEW.md and complete_fit_review.json. Oriented revised P1S STL set is print_refinements_oriented/.


## Revision G release — 2026-09-07
Final model: 14 valid installed solids and 176 fully constrained sketches. Separate additive patches restore the original lofted duct wall; measured missing wall is zero. Six fan interface gaps remain 0.30 mm. Printed arms are unchanged. The complete P1S-oriented release is ../print_release/; public showcase is ../docs/. CFD figures describe the earlier baseline, not a new Revision G solve. A valid solid can still contain an unintended wall opening: check wall continuity against the original shell, not only isValid().

Airway review: audit_airway_continuity.py verifies zero patch intrusion into the original inner loft, zero missing wall, unchanged frozen arms and six 0.30 mm gaps. No geometry change was warranted. This is geometric acceptance, not measured airflow or thermal validation.

Revision H: three R12 internal tangent blends and two R14 exterior support blends per duct, native FlowInnerBlend/FlowOuterSupport. Broad smooth-loft trial was rejected because a downstream union became invalid. Final local blends pass native and independent STEP service checks, sampled wall thickness >1.60 mm and curved overhang <40 degrees. Arms and interfaces remain fixed. Revision H supersedes the earlier no-intrusion audit with explicit intentional blend accounting.
