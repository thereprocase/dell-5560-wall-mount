> Current designs: [Minimalist M1 guide](https://thereprocase.github.io/dell-5560-wall-mount/minimalist-guide.html) and [preserved ducted Rev H](print_release/). For both Rev H ducts, use the [corrected Orca cross-slot bridge settings](print_release_step/ORCA_BRIDGE_REVIEW.txt). This older guide retains the original design and material context.

# P1S / ASA — Revision F

Print the supplied oriented 3MF files with your **P1S, 0.4 mm nozzle, ASA,
0.20 mm layers, 6 walls, 6 top/bottom layers, 100% infill, 8 mm outer brim and
supports off**. The explicit hollow CAD sections remain empty at 100% infill.
These are standard model files, not sliced G-code or a native Bambu project.

## Print the coupons first

00_FIT_COUPONS.3mf contains a male/female joint and a split-pin/socket pair.
Check the keyed fit with hand pressure. The mortise has 0.30 mm nominal side
clearance and an open-mouth 45° roof. Try the CA bond on a second coupon set.
The pin has a 4.0 mm shaft, a 4.2 mm split crown and a 4.1 mm socket. Its small
interference is intentional; printing variation can dominate that allowance.
Adjust the socket/clearance parameter if needed. Do not scale the complete mount.

## Part set and orientations

Print one each of 01–14. Parts 11–14 are four identical push-pins supplied in
their assembly positions in STEP and button-down in the print files. The 8 mm
and 16 mm outlet rails are alternatives to the default 12 mm pair.

- Cradles: **outer side down**, diagonal on the plate. Do not place them on the wall back.
- Ducts: inclined fan inlet becomes the horizontal bed face. The open duct
  grows toward its narrow end; the joint buttress supports the mounting saddle.
- Fan trays: grille down, fan pocket open upward.
- Fan caps: broad front face down. Pins: button down, split tip up.
- Outlet rails: lip down at Z=232. The contraction and key roofs stay within
  45° from vertical; the air skin has no broad suspended ceiling.

| Representative part | Oriented size, mm |
|---|---|
| 02_right_cradle | 196.3 × 180.6 × 44.0 |
| 04_right_fan_duct | 174.5 × 132.0 × 109.9 |
| 06_right_fan_retainer | 139.0 × 49.0 × 13.0 |
| 08_right_outlet_rail | 183.8 × 39.0 × 78.0 |
| 10_right_fan_tray | 139.0 × 132.0 × 38.0 |
| 12_right_push_pin | 8.0 × 8.0 × 14.0 |

All individual parts and their 8 mm brims fit the 256 mm bed and avoid its stock
front-left cutter exclusion. Keep the supplied bracket rotation. Inspect the
slice preview for machine-generated extras. Use ordinary/off timelapse for
these plates rather than adding a separate smooth-timelapse tower.

Intentional bridges: 18 mm inside the closed cradle spine, 10 mm lower cradle
pockets and 6.6 mm dovetail roofs. Have the slicer span their short widths.
The geometric 0.20 mm audit finds no detached starts; maximum sampled reach
beyond the prior layer's 45° envelope is 8.8 mm inside the 18 mm bridge.
This is a geometry audit, not validated Bambu extrusion paths or a print test.

## Starting process settings

Use the filament manufacturer's ASA profile. Start outer/inner walls around
80/120 mm/s, first layer and bridges around 25 mm/s, and volumetric flow around
12 mm³/s. Retain the filament profile's bridge cooling; keep auxiliary cooling
off to avoid a strong draft across large ASA parts. Start elephant-foot
compensation at 0.15 mm and brim separation at 0.10 mm, then judge the coupon.

The inspected Bambu ASA profile in Studio 2.8.2.61 uses 270 °C nozzle and
100 °C PEI bed for the P1S-compatible 0.4 mm setup. These are Bambu-brand
settings; another ASA spool may need its own values. Dry to the filament
maker's instructions. Keep the enclosure closed, avoid cold drafts, use the
plate maker's adhesive guidance, and let the plate cool before removal.

## Assemble with CA and printed pins

1. Dry-fit each duct's two keys into its cradle from the room side. Dry-fit
   its outlet rail the same way. Select the outlet gap before gluing.
2. Remove the laptop and fans from the work area. Clean the mating surfaces.
   Apply a suitable gap-filling CA to the key/mortise contact surfaces and
   saddle/arm seating faces. Press each part fully against its shoulder and
   keep it seated for the adhesive maker's complete cure schedule. The keys
   support vertical load; the CA bond locks withdrawal and must pass the coupon test.
3. Form two mirrored half assemblies. Each half uses one cradle, one duct and
   one outlet rail. Their center seams are nominal clearances; no center screw
   or glued butt seam is needed to carry the laptop.
4. Slide each fan tray into the duct's dovetails. Keep this joint dry so the
   tray remains removable. Fit a 120 × 120 × 25–27 mm fan and suitable thin
   pads. The airflow arrow points **upward and toward the wall at 45°**.
5. Route the fan wire through the cap notch, seat the cap and press in its two
   split pins by hand. Do not glue pins, caps, fan frames or sliding trays.
6. Install the two half assemblies with four wall bolts and broad washers.
   Wall-hole centers are X=±162 and Z=−36/+174 mm: 324 mm between the two
   vertical bolt lines and 210 mm between each line's holes. Keep the halves
   level and parallel. All four bolts face the room through clear tool paths.
7. Add approximately 2 mm rear contact pads. Fit front pads to the actual closed
   case so it rests securely without being squeezed. Keep pads off vents and
   ports. The reference underside sits 40 mm from the wall; the bare slot is
   26 mm. Verify the rear foot and noncontact cheek-lip clearance.
8. Leave about 110 mm above the hinge. Lift the laptop 105 mm, then pull it
   forward for keyboard access. Remove two pins and the cap to service a fan.

No M3/M4 screws, nuts or heat-set inserts remain. The four toggle bolts and
washers are the only metal mounting hardware. The wall/anchor capacity, CA bond
strength, pin pullout, warm creep and physical printing remain unqualified.

Sources: [Bambu ASA](https://bambulab.com/en-us/filament/asa),
[Bambu print-volume limitations](https://wiki.bambulab.com/en/knowledge-sharing/print-volume-limitations),
[Bambu official profiles](https://github.com/bambulab/BambuStudio/tree/v02.08.02.61/resources/profiles/BBL),
[Prusa's adhesive guidance](https://blog.prusa3d.com/the-great-guide-to-gluing-and-assembling-3d-prints_44908/).
