# Fit allowances — Revision F

Dimensions below are **nominal CAD allowances**, before printer error, shrinkage, surface roughness or elephant foot. No global ASA shrink correction is built into the geometry. Validate the coupons using the same filament, settings and orientation as the final parts.

| Interface | Nominal geometry | Intended behavior |
|---|---|---|
| Tray dovetail width | 0.30 mm horizontal allowance on each side; 0.60 mm total width difference | Removable sliding fit |
| Dovetail crown | 0.30 mm vertical roof clearance | Avoid rubbing on the groove roof |
| Dovetail root | Tongue root at −110.1 mm; groove bottom at −110.3 mm in the unrotated construction | 0.20 mm vertical allowance |
| Fixed duct / outlet keys | Mortise offsets nominal mating boundaries by 0.30 mm per side; printable roof adds asymmetric relief | Hand fit, followed by CA retention |
| Pin shaft and duct socket | Ø4.00 / Ø4.10 mm | 0.10 mm diametral clearance |
| Split-pin crown and socket | Ø4.20 / Ø4.10 mm | 0.10 mm diametral interference, or 0.05 mm radially |
| Cap pin passage | Ø4.50 mm | Clearance passage; retention occurs in the duct socket |
| Laptop thickness | 20 mm reference envelope in 26 mm bare slot | Fit pads to the actual closed laptop |

The dovetail groove is defined by coordinate offsets, not a constant normal offset of the sloping flank. Its nominal 0.30 mm horizontal allowance therefore gives less than 0.30 mm clearance normal to that slope. The generated geometry, rather than the shorthand source comment, is authoritative.

Fixed key clearances are not a uniform adhesive bondline: shoulders seat against the assembly, and the roof has deliberate relief. Choose and qualify an adhesive for the actual gap and surface preparation. The printed split pin's very small allowance is particularly sensitive to extrusion and hole-size error.

## Adjust the interface, not the whole assembly

1. Print `print_ready/00_FIT_COUPONS.3mf` and check fit by hand after cooling and removing brim artifacts.
2. Check the sliding interface over its full engagement length; a short coupon cannot reveal full-length warping. Check that the tray and cap both fully seat.
3. If a fit binds, inspect elephant foot and the slice before changing geometry. Modify the specific groove, mortise or socket allowance and regenerate the affected parts. Do not scale the whole mount and change its laptop fit and bolt spacing.
4. Test repeated pin insertion/removal and CA coupon retention. A geometrically valid fit does not establish pullout capacity or durability at operating temperature.

The source defines dovetails in `base_geometry.py: tongue()`, key pockets in `build_mount.py: tenons()`, and pin/socket geometry in `build_mount.py: pin()` and `right_duct()`. The nominal mortise allowance is passed as `0.3` in `right_cradle()`.
