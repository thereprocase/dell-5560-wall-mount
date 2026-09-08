# Rev H-C1 fan cable routing

Four replacement prints for the preserved Rev H mount: covers 05/06 and trays
09/10. The covers have an open groove in the rear/outboard mating edge. A cable
can be laid into that groove before the cover is fitted; the tray closes the
passage. The former closed front-face cable hole is filled. The connector stays
outside and does not pass through a hole.

Each tray gains two external zip-tie anchors, one near the cable exit and one
farther back along the outboard rail. Ties remain on the tray when the cover is
removed. The cable must be unplugged and freed from any off-tray attachment
before withdrawing the tray itself. Avoid tightening ties against the cable's
insulation or using these anchors to restrain the fan or another load.

[Illustrated guide and interactive model](../docs/revh-cables.html) ·
[Native FreeCAD](Precision_5560_RevH_Cable_Management_C1.FCStd) ·
[Print geometry](print/) · [Native validation](validation.json)

The native file is a Save As of the complete H-R1 assembly. Fourteen of its
eighteen installed parts are unchanged: both printed arms, ducts, rails, four
original cover pins, two H-R1 bars and two H-R1 keepers. The C1 replacement
covers and trays also work without the optional H-R1 retainers. Original Rev H
and H-R1 source files and downloads remain preserved. Minimalist M1.1 is a
separate design and is not changed by this release.

Print `00_cable_fit_coupon.3mf` first. It contains actual cropped cover/tray/duct
corners and one original pin. These reproduce the mating seam, open cable
groove, nearby tie anchor and original latch. Cover, tray and pin use their
full-part print directions. The short duct coupon prints front mating face down
to avoid a roof overhang created by cropping; it checks fit, not the original
duct's print orientation. The installed duct is unchanged.
After fitting the coupon, print `20_both_cable_covers.3mf` once and one each of
`09_left_fan_tray.3mf` and `10_right_fan_tray.3mf`: four replacements on three
plates. Individual covers 05/06 are alternatives to plate 20, not additional
parts. STEP, STL and geometry-only 3MF represent the same shapes.

Use OrcaSlicer, P1S, ASA, 0.4 mm nozzle, 0.20 mm layers, six walls, six top and
bottom layers, 100% rectilinear infill, Arachne walls, 8 mm outer brim and
supports off. Keep the supplied orientation and 100% scale. The coupon includes
the original duct interface: use 180 degrees for both bridge directions, with
Relative bridge angle and Align infill direction to model off. The full C1
cover/tray review uses automatic bridge direction. Use your actual spool's
temperature and drying instructions, then inspect the slice.

The checked wire is a 4 mm round envelope with 0.5 mm minimum installed gap to
the cover and tray. The outer wall groove is nominally 7 mm high and 5 mm deep
to its mating surface, with 1.2 mm corner radii. The opening is clearance for a
cable, not a clamp or a fluid seal. Check actual wire shape, jacket condition,
first-layer expansion and burrs. Larger bundles require a revised feature and
renewed clearance/print checks.

Each tie anchor projects 8 mm beyond the previous tray side, begins at the
grille-down print base and grows outward on a 45-degree underside. The local
fan-frame Y positions are 119 and 51 mm. A rounded 4 × 5.5 mm vertical slot
accepts the checked 1.5 × 3.6 mm tie-tail envelope with access to both ends.
Slot corner radius is 0.8 mm. This is a geometric fit, not a qualified tie-lug
force rating. Route wire outside the fan envelope and leave service slack.

`build.py` constructs the new features from constrained sketches, stock Part
extrusions, fillets, booleans and mirrors; the saved model needs no custom
feature proxy. The original native feature history remains present and hidden.
`validate_export.py` independently reopens and recomputes the saved model,
compares the preserved parts, checks cable capture and side-entry access,
samples cover/tray removal, checks fan/laptop envelopes, and exports/reimports
STEP and mesh files with P1S bed/brim checks. `render.py` captures actual native
geometry, with a separately labeled red cable reference.
`validate_service_animation.py` separately checks removed pins parked above
the cover path and cover travel through 35 mm; the viewer uses that sequence.

This is a fixed-size upgrade for the preserved Rev H snapshot. Editing the old
parameter sheet does not automatically adapt the cable features. Recheck
changes to groove, mating surfaces, anchor dimensions or fan envelope.

Physical cable fit, repeated service, cable abrasion, tie-lug strength and warm
ASA behavior remain untested. The original mount's retention, wall anchors,
load capacity and cooling still need physical qualification. The original
Rev H ducts and CFD records are unchanged; C1 adds no airflow or cooling result.
