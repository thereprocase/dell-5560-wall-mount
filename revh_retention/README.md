# Rev H-R1 removable retainers

Four add-on parts for the preserved Precision 5560 Rev H geometry: two handed
side bars and two handed keepers. The existing fourteen Rev H parts, including
the already printed arms, are unchanged. The intended change is removable
withdrawal retention at the duct-to-arm and upper-rail-to-arm joints.

[Illustrated installation guide and interactive model](../docs/revh-retainers.html) ·
[Native FreeCAD model](Precision_5560_RevH_Removable_Retainers.FCStd) ·
[Print files](print/) · [CAD verification](validation.json)

Print `01_right_arm_fit_test.3mf` first. It contains a shortened right bar with
both window keys and the lower keeper. Test it directly on the printed right
arm. The coupon is not a substitute for the complete installed bar.

After the coupon passes, print `00_four_retainer_parts.3mf` once. It contains
15/16 left/right bars and 17/18 left/right keepers. The individual STEP, STL
and standard 3MF files are alternatives for replacements; do not also print
them. Keep the supplied orientations and 100% scale. Standard 3MF files contain
geometry, without slicer settings. Separate Orca review archives contain the
reviewed settings and G-code; re-slice for the actual ASA spool.

Orca starting process: P1S, 0.4 mm nozzle, 0.20 mm layer height, 6 walls,
6 top/bottom layers, 100% rectilinear infill of the deliberately open CAD,
Arachne walls, 8 mm outer brim, supports off. The bars print with their flat
outboard faces down. Keepers print with their catch feet down and split tips up.

## How the retention works

- The lower rounded key fits the existing triangular gusset opening. Its tab
  overlaps the front of the duct saddle with a nominal 0.30 mm gap.
- The second key enters the existing rounded guide opening above it. This
  limits rotation of the bar in its plane.
- The external heel extends below the lower key. It bears against the existing
  arm if the top of the bar tilts outward. The widened upper stop overlaps the
  upper rail's front lip.
- The square keeper stem keeps its eccentric catch foot oriented toward the
  arm. The foot overlaps the inner gusset face, preventing sideways loss. The
  split crown prevents ordinary downward withdrawal of the keeper.
- Removing one bar releases both the duct and rail on that side. Support both
  during service and remove the laptop before releasing retainers.

The stem is 3.0 mm square in a 3.6 mm socket. The 3.8 mm split crown needs
nominal 0.10 mm deflection per finger to pass. There is 0.60 mm total keeper
endplay and 0.50 mm catch-foot clearance to the inner arm. These are nominal
CAD dimensions; printer shrinkage, burrs and first-layer expansion need a test.

The existing shoulders and keys still carry the intended assembly loads.
These bars provide withdrawal retention, with running clearance; they are not
a clamping preload. They require no drilling of the arms, extra metal parts or
adhesive at the two retained joints. Original fan caps, trays and pins retain
their Rev H arrangement.

## Native construction and reproduction

`build.py` makes a Save As copy of `freecad/Precision_5560_Native.FCStd` and
adds constrained Sketcher profiles with stock Part extrusions, fillets,
booleans and mirrors. Native source features for the original fourteen parts
are preserved. The copy replaces the older assembly's fourteen invalid saved
joint references with fixed installed App::Links in an App::Part. The original
Rev H document is untouched. The completed file needs no custom geometry proxy.

This is a fixed-size add-on for the preserved Rev H snapshot. Editing the old
Rev H spreadsheet does not automatically resize or reposition the retainers.
Recheck any geometry edit, including the matching socket and keeper dimensions.

Run the builder in FreeCAD's GUI, then run `validate_export.py` with FreeCAD's
bundled Python against the saved file. The validator opens a separate snapshot,
forces native recomputation, compares all fourteen originals and frozen arms,
checks the new solids, sampled service/stop motions and combined outward-tilt
poses, and exports print-oriented STEP/STL/3MF. `render.py` captures actual native
views in a separate unsaved presentation document.

Slice the two combined 3MF plates with `minimalist/slice_models.py` and screen
both resulting G-codes with `minimalist/gcode_audit.py`. Then run `package.py` to
build the offline guide and download. The release report binds the native file,
exports, sliced input and audited G-code by SHA-256.

## Remaining physical checks

The coupon must seat by hand, latch fully, resist sideways removal while
latched, and release repeatedly without damage. Test the full retained assembly
while supported before loading it. Check bar movement, keeper seating and
warm ASA deformation. CAD does not establish a load rating, actual bar stiffness,
retention force, fatigue life, layer adhesion or creep resistance.

The new parts sit outside the existing arms. The original duct airways, fan
parts and laptop geometry are unchanged. This add-on has no new airflow result;
the existing CFD commissioning limitations remain in effect.
