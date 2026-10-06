# Rev H D4 socket hotpatch

D4 clears the four blind sockets for the fan-cover push pins. The earlier duct
construction cut the bosses, then fused in a sloping shell that crossed the
holes. D4 repeats the original parametric cuts after the completed union.

[Print and repair guide](../docs/revh-duct-d4.html) ·
[Download the hotpatch](../docs/downloads/Precision_5560_RevH_D4_Socket_Hotpatch.zip) ·
[Editable current FreeCAD model](Precision_5560_RevH_D4_Current.FCStd)

## What to use

Open the two projects under `slices/` as **OrcaSlicer projects**. They contain the
reviewed orientation, settings, support enforcer and G-code for a Bambu Lab P1S,
0.4 mm nozzle and Polymaker PolyLite ASA. Review them for the actual printer and
spool before printing. `print/` contains equivalent STL, STEP and geometry-only
3MF alternatives; those do not contain the complete process setup.

This download supplies **two replacement ducts**. The current native assembly
also includes the previously developed D3 duct reinforcement, T3 tray fit,
R2 retainers/keepers and two optional B1 rear baffles. Those surrounding fit
revisions are newer than the earlier public C1 native snapshot. The D4 change
itself is measured against the exact prepatch assembly in `baseline/`.
Existing duct-to-tray grooves and arm interfaces are preserved by the D4 cut.

For already printed ducts, read [REPAIR.md](REPAIR.md): a 4.1 mm hand bit with
maximum **6.0 mm tip depth from the duct socket face** can clear the modelled
obstruction while retaining the blind bottom. Physical cleanup success, pin
seating, retention and removal remain unconfirmed.

## Evidence and limits

- [Native comparison](build-report.json): 20 valid installed solids. Only the
  two ducts change, removing approximately 42.08 mm³ each inside the original
  bores. The other 18 installed solids match the bundled prepatch baseline.
- [Final native validation](final-validation.json): reopened and recomputed;
  both local bores are clear and all four pins pass nine sampled withdrawal
  positions. Only the actual split crown is allowed to overlap.
- [Parameter edits](parameter-validation.json): socket diameter and side-root
  radius change and restore successfully. Socket diameter intentionally sizes
  the matching pins too. Near-coincident root fillets exposed an OCC reverse-Cut
  inconsistency; the bounded Common-volume check and diagnostic records explain
  how that case was measured. Default restoration uses both directional Cuts.
- [Left](reports/03_left_fan_duct.json) and [right](reports/04_right_fan_duct.json)
  toolpath audits: exported/prepared/sliced meshes match; no floating model or
  support islands; maximum unsupported deposition span approximately 6.44 mm.
  The socket test detects the old obstruction and finds no model/support paths
  in the same four-layer passage samples in D4.
- [Printed-part repair envelope](printed-repair-validation.json): 90°, 118° and
  135° drill points pass nominal checks at the 6.0 mm tip limit.

The nominal bores remain 4.1 mm diameter and 7.7 mm blind depth. **7.7 mm is not
a drill-tip depth instruction.** These are geometry and toolpath checks, not
physical qualification of printed dimensions, strength or pin forces.

## Reproducing the correction

The construction uses stock FreeCAD features, so the saved model reopens
without project Python code. The original 897 object names are retained; D4
adds a group, compound of the original cutters and final Cut.

`build.py` runs in a FreeCAD Python environment. It reads the checked baseline,
refuses to replace an existing D4 candidate, then validates and exports. Preserve
or move the supplied candidate before rebuilding. `socket_fix.py` contains the
actual correction and checks. `validate_parameters.py` never saves its trial edits.

Headless `saveAs` omits GUI data in this FreeCAD build. `preserve_gui.py` restores
the original view providers, colors and camera, adds three hidden D4 providers,
and checks every geometry archive member is byte-identical. See
[gui-preservation.json](gui-preservation.json). The final model was also opened
and visually inspected in the real FreeCAD GUI.

`prepare.py` replaces only the mesh in the historical Orca templates. To slice:

```text
python revh_duct_r4/slice.py --orca /path/to/OrcaSlicer --orca-profiles /path/to/resources/profiles
```

The slicer wrapper uses the repository's `minimalist/slice_models.py`. Run
`python revh_duct_r4/audit.py` with NumPy, SciPy, Shapely and Matplotlib to audit
the checked projects directly. G-code is extracted to temporary files. The
`baseline/` projects are deliberately defective regression fixtures, not prints
to use. `package.py` builds the public ZIP and guide without local account paths.
