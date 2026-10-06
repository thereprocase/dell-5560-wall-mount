# Revision F — limited structural screen

The printed sections meet the stated bending, bearing and shear screen.
Minimum ratio to an assumed stress limit: **1.19**.
The CA bonds and printed-pin pullout have not been qualified; this is not a
complete assembly load rating or FEA.

## Assumptions and method

2.5 kg laptop; 6 kg installed assembly; 1 kg per fan module; 3× gravity;
50 N outward hinge pull. Normal/bearing limit 5 MPa; shear limit 2 MPa;
effective modulus 1,000 MPa; local multiplier 1.5. These are chosen screening
values, not measured warm ASA strengths. Print on the supplied faces with
100% infill in the remaining solid sections. Designed cavities remain empty.

The exported cradle geometry supplies net section properties every 0.5 mm,
including hollow sections and unsymmetric bending. A 10% section allowance
remains. The rear-section extraction ignores added cheek stiffness. The check
does not resolve torsion, buckling, fatigue, impact or long-term creep.

The duct uses two 8 × 40 mm keys with 12.6 mm engagement, 21 mm apart. Their
lower shoulders carry vertical load and the moment from the sideways fan
offset. The saddle retains a 10 mm root with at least 40 mm net height. The
rail keys are 9 mm wide, 25 mm apart. Their sloped leading faces print without
unsupported ledges. The four split pins retain fan caps and carry no laptop load.

| Case | Stress MPa | Assumed limit MPa | Ratio |
|---|---:|---:|---:|
| shelf 3g | 3.12 | 5.0 | 1.60 |
| tines 50N hinge pull | 3.88 | 5.0 | 1.29 |
| rear rail combined | 4.19 | 5.0 | 1.19 |
| rear rail upper tail | 2.60 | 5.0 | 1.93 |
| duct key lower shoulder bearing | 1.41 | 5.0 | 3.54 |
| duct key root shear | 0.67 | 2.0 | 3.00 |
| duct saddle root bending | 1.51 | 5.0 | 3.32 |
| fan support ledge | 0.34 | 5.0 | 14.80 |
| rail key lower shoulder bearing | 0.47 | 5.0 | 10.70 |
| split pin shear | 1.17 | 2.0 | 1.71 |
| tray dovetail bearing | 0.25 | 5.0 | 20.39 |
| tray dovetail root shear | 0.12 | 2.0 | 16.31 |
| wall hole bearing | 1.27 | 5.0 | 3.92 |
| wall washer punching | 0.13 | 2.0 | 15.84 |

## Joint demands that still need physical qualification

- Each duct: 47.8 N outward couple demand for the stated 3g fan-module case.
  CA locks the keyed lap against withdrawal. The plastic shoulder calculation
  establishes neither adhesive peel resistance nor warm bond durability.
- Each printed pin: 7.4 N retention demand. The shear check passes;
  frictional pullout, repeated use and creep remain untested. Test the coupon.
- Each upper wall anchor: 63.5 N tension; conservative carrying-anchor shear
  89.2 N. Select toggle bolts for the actual wall and those loads.

Four Ø7 mm wall holes remain at X=±162, Z=−36/+174 mm. All four bolt axes remain
normal to the wall, with clear Ø16 mm room-side tool corridors. No other metal
fasteners or heat-set inserts are required.

Estimated installed mass, including conservative laptop/fan/hardware allowances:
4.41 kg. No service temperature or physical load rating is claimed.

Regenerate with build_mount.py, section_properties.py, then strength_check.py.
