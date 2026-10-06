# Adjacent-part fit review - P1S ASA

Completed live in FreeCAD, with interface and isolated-part views. Printed cradles
were checked against frozen BReps and were not changed.

| Interface | Final result | Action |
|---|---|---|
| Cap / duct, both sides | 0.30 mm minimum | Shortened backing ends, retaining cap position and pin geometry |
| Cap / tray, both sides | 0.30 mm minimum | Shortened tray ends |
| Tray / duct, both sides | 0.30 mm minimum | Relieved sliding rim and widened female dovetail for 0.30 mm normal flank clearance |
| Upper rail / printed arm, both sides | 0.30 mm minimum | Removed microscopic step by making rear lead-in tangent at Y6 |
| Duct keys / printed receivers, all four | At least 0.30 mm | Measured and retained |
| Fixed mounting shoulders | Intentional seating contact | Retained load-bearing surfaces |
| Pin retention | Original intentional interference | Retained shaft, crown, sockets and cap passages |

R4 duct relief now ends in a 45-degree runout, with coincident tool junctions.
No faces below 0.1 mm2 or edges shorter than 0.05 mm remain on unfrozen parts.
This screening is not a mathematical proof that every possible visual defect
has been eliminated. The two sides derive from mirrored native sources.

Native edit groups: BossRunout, FanFitClearance, RailRefinement. All profiles
are constrained. ManufacturingFitReview is a measurement/reference sheet;
it deliberately does not pretend to drive the geometry.

Print orientations follow the root P1S_ASA_Print_Guide.md and prepare_prints.py:
duct inlet down, tray grille down, cap front down, rail lip down, pin button down.
Use print_refinements_oriented/ for the six revised STL parts. Those meshes are
closed and their bounds plus an 8 mm brim fit the P1S bed/cutter exclusion.
The original print_ready/ files retain the older geometry. No replacement arms
were generated. Caps and pins retain their original oriented files.

Dovetail groove crown width increases from 6.60 to approximately 6.737 mm;
its roof remains a short bridge. Runouts use 45-degree relief; bed-facing
roundovers were avoided. P1S baseline: ASA, 0.4 mm nozzle, 0.20 mm layers,
6 walls, 6 top/bottom layers, 100% fill of explicit hollow CAD, supports off.
Slicer toolpaths and physical fit/retention remain unverified.

Evidence: complete_fit_review.json, fan_fit_clearance.json,
fixed_key_fit_audit.json, junction_cleanup.json, rail_tangent_cleanup.json,
clearance_validation.json, print_refinements_oriented/manifest.json.


## Final wall correction / Revision G
The earlier corner-only audit missed two unintended skin notches per duct.
Separate additive `LoftSkinPatch` features now restore the original native loft
wall at both corner regions. Native sketch boundaries make each patch editable.
OriginalWallSkin excludes the pre-existing socket intersection; zero additional
wall loss is checked directly against that reference. Approximately 73.96 mm3
of wall was restored per duct. See duct_blend_patches.json and
complete_fit_review.json. The unsuccessful free-form blend trial was rolled back.
This additive patch construction supersedes the earlier cut-only repair.


## Revision H airflow refinement
Three R12 tangent blends per duct soften the internal direction changes. Two R14 exterior blends support the thinned corners. Inlet/outlet profiles and keys remain fixed. Native features: FlowOuterSupport and FlowInnerBlend; edit their Edges radii. The sheet lists the radii as reference values. Sampled new curve wall thickness exceeds 1.60 mm and downward overhang stays below 40 degrees in the inlet-down orientation. Native and exported assembly clearance checks are rerun. This is geometric refinement; no new pressure-loss or thermal solve is claimed.
