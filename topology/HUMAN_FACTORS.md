# Human contact and handling requirements

Research date: 2026-09-08. Scope: a personal, bare-handed, closed-laptop wall
mount. These references inform the design; aerospace, industrial-handle and
building-accessibility dimensions are not laptop-mount certification rules.

## Published guidance worth using

| Source | Guidance | Relevance and limit |
|---|---|---|
| NASA Human Integration Design Handbook, Rev 1, Fig. 9.7-4, printed p. 833 (PDF p. 838) | Bare-hand fingertip recess: 19 mm opening, 13 mm depth. Two-finger bar: 32 mm clearance and 65 mm clear span. One-hand bar: 48 mm clearance and 111 mm span. | These are distinct geometries. A fingertip hole is not a lifting grip, and a flat laptop edge is not a cylindrical handle. |
| FAA HF-STD-001B (2016), §§5.2.2.5.3.3, 5.2.2.5.4.4, 5.2.2.6, 5.2.2.8 | Handle geometry should permit at least 120° finger curl; handles need 50 mm obstruction clearance in its equipment context. Grasp areas above the centre of gravity aid stability; guides and stops aid installation. | Use the handling principles; do not blindly apply the industrial handle clearance to a thin laptop. |
| U.S. Access Board, door/gate hardware guide | Recommends at least 1½ inches (38.1 mm) knuckle clearance for bars and pulls; prefers loose-grip operation and fewer simultaneous actions. | A useful comparison for generous grip space, not a legal requirement for this hobby mount. |
| CCOHS, Hand Tool Ergonomics — Tool Design | Prefer a strong whole-hand grip for forceful tasks, neutral wrists, and sufficient surface friction. Typical power-tool handles are 30–50 mm in diameter and over 100 mm long. | Those are handle sizes, NOT wall-gap dimensions. Apply the posture and contact principles to retrieval. |
| NASA-STD-3001 Vol. 2, §9.3 | Make grasping provisions deliberate; avoid exposed sharp edges, burrs, entrapment and pinch points. | Inspect contact regions and the full insertion/removal path, rather than only the seated state. |

Sources:

- https://www.nasa.gov/wp-content/uploads/2015/03/human_integration_design_handbook_revision_1.pdf#page=838
- https://hf.tc.faa.gov/publications/2016-12-human-factors-design-standard/full_text.pdf
- https://www.access-board.gov/ada/guides/chapter-4-entrances-doors-and-gates/
- https://www.ccohs.ca/oshanswers/ergonomics/handtools/tooldesign.html
- https://www.nasa.gov/reference/9-0-hardware-and-equipment-vol-2/

The NASA dimension illustration was inspected, not inferred from extracted
table numbers alone. FAA text was read from the official downloadable PDF.

## Translation into this design — provisional engineering choices

1. **Selected target: at least 32 mm behind the upper 80 mm grasp regions.** The
   proposed 20 mm trial is a compact comparison, not a validated comfort target.
   The earlier 8 mm gap is rejected for a fingers-behind retrieval grip. Measure
   the actual nearest obstruction: wall texture, pads, rails and screws count.
2. **Expose both upper side edges above the laptop centre of gravity.** Preserve
   enough unobstructed edge for multiple fingers and permit a two-handed lift.
   Do not force the user to lift the whole laptop by a small pinch on its lid.
3. **Reserve the hand approach and lifting path as empty design space.** Topology
   optimization may remove material but must not grow ribs into those regions.
   The hand envelope must move with the laptop through the whole retrieval path.
4. **Use an upward lift along the slightly tilted slot, with clear guides and a positive bottom seat.** The current
   96 mm bracket and 6 mm seat imply approximately 90 mm of upward travel before
   the laptop bottom clears the rails. Allow additional handling margin above
   the laptop when selecting the installation location.
5. **Chamfer the slot mouth and touched edges.** Start with 1–2 mm edge breaks
   where geometry permits, keep new edges from becoming sharp ridges, and feel
   an actual PETG print. This dimension is our prototype choice, not a sourced
   ergonomic standard. Preserve the requested print slopes.
6. **Keep fingers away from the closing seat gap.** The chosen side grip should
   remain above the bracket while lowering the laptop. Smooth protected laptop
   contact areas and avoid a tight wedge fit that demands extra squeezing.

Because the wall is flat, merely deleting bracket material cannot create more
than the wall-to-laptop gap behind it. Achieving more finger space requires more
rear clearance, a deliberately tilted laptop/slot, or a different grip route.
Any such geometry change must also change the structural load lever arms.

## Cheap personal fit check before choosing a final clearance

With the laptop continuously supported on a desk, compare temporary 20, 32 and
38 mm spacers against a vertical board. Check finger approach and withdrawal,
comfortable grasp at both side edges, and neutral wrists. Do not use an untested
print to suspend the laptop for this check. A later printed coupon should check
PETG edge feel, pads and slot fit. Final retrieval testing must cover approach,
grasp, upward lift, withdrawal and reseating, including cables if connected.

No percentile coverage, one-handed suitability or comfortable lifting claim has
yet been established for the modeled mount.

## Selected tilted trial

The user accepted the NASA-informed 32 mm target and suggested a slight outward lean. The current tilted model provides 32 mm minimum across the upper 80 mm of the 230.3 mm laptop envelope, approximately 21 mm rear clearance at its bottom and 37.9 mm at its top. The slot and seat rotate together by about 4.2 degrees. A 22 mm slot surrounds the repository's 20 mm reference thickness with 1 mm nominal clearance per face. This allowance is still subject to an actual laptop/pad fit check. The wall attachment pads remain against the wall. This geometry is implemented in `slot_up/tilted_grip/study.py`; the reserved hand zone is above its 96 mm design envelope.
