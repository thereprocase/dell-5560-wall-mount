# Clear the four fan-cover pin sockets

The D4 CAD and Orca projects correct the plastic wall crossing these sockets.
For existing printed ducts, try controlled cleanup before deciding
whether replacements are needed. Physical success has not yet been reported.

1. Work on a cooled duct on the bench, with its cover and pin removed. Use the
   existing round opening to guide a **4.1 mm drill bit in a hand pin vise**.
2. Set a firm depth stop so the **tip can enter at most 6.0 mm from the flat
   duct socket face**. Measure from the duct face, not through an installed cover.
   Keep the bit aligned with the existing hole; turn slowly by hand and clear chips.
3. Repeat for all four sockets, two per duct. These are **blind holes**: do not
   drill through. The CAD bottom is 7.7 mm deep, and that is not a drilling target.
4. Refit each cover and matching split pin. Confirm seating, retention and
   removal by hand. Stop if it binds; do not hammer the pin or deepen the hole
   past the stop. Record which socket and pin were checked.

The 6.0 mm limit includes the pointed tip. A nominal model check of 4.1 mm bits
with 90°, 118° and 135° points clears the unwanted pin obstruction while leaving
at least 1.7 mm to the original blind bottom and preserving the intended crown
contact. Material may remain farther behind the pin tip; complete excavation of
the nominal bore is unnecessary for this repair. The check cannot account for
actual print shrinkage, drilling angle or the condition of the printed wall.

[Modelled repair check](printed-repair-validation.json) ·
[Original diagnosis and section](evidence/pin-hole-obstruction.json)

Replacement projects are `slices/03_left_fan_duct/03_left_fan_duct.gcode.3mf` and
`slices/04_right_fan_duct/04_right_fan_duct.gcode.3mf`. Open them as OrcaSlicer
projects; keep the supplied orientation and review settings for the actual printer.
