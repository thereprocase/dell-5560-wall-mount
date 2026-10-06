REVISION H PROTOTYPE - PRINT-ORIENTED STEP FILES

14 parts, one of each numbered file. Parts 11-14 are four identical pins.
The arms (01-02) are included for completeness; yours are already printed.
This is the same geometry as the Revision H STL print release, not the
experimental 0.8 mm wall trial or the forthcoming minimalist design.

Open one STEP at a time in OrcaSlicer. Keep the baked orientation, use mm,
and do not auto-orient or scale. Each part sits at Z=0 centered on a 256 mm
P1S plate. Inspect the preview after importing because slicers can arrange
parts automatically. Do not print the whole folder together on one plate.

P1S / ASA starting setup: 0.4 mm nozzle, 0.20 mm layers, 6 walls,
6 top/bottom layers, 100% infill of the intentionally hollow CAD,
8 mm outer brim, supports off. Use the actual spool's ASA temperature and
drying instructions. Review bridges and the first layer before printing.
Both ducts need the corrected bridge direction described in
ORCA_BRIDGE_REVIEW.txt. Automatic bridge direction is unsuitable at the
long slots. The corrected paths pass the geometric screen; physical ASA
bridge quality still requires a print check.

Orientations: arms outer-side-down and diagonal; ducts inlet-down;
trays grille-down; caps broad front face down; rails lip-down; pins button-down.
Fit clearance is nominally 0.30 mm at the revised joints. Pin retention has
intentional interference. The existing fit coupons remain useful.

All 14 STEP files were reimported and checked for one valid solid, source
shape agreement, print-bed/brim clearance and matching Rev H STL bounds.
See manifest.json for per-file checks and hashes. STEP files are editable
exchange solids; the full native feature history remains in the FCStd model.
