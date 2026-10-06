# Precision 5560 airflow: primary evidence and model gaps

Research date: 2026-09-07. This note separates manufacturer statements, visual observations, and proposed unmeasured geometry. The existing sealed CFD geometry is only an initial baseline; it does not yet contain laptop vents or internal Dell blowers and does not satisfy the expanded installed-model request.

## Manufacturer sources inspected

- [Dell Service Manual, October 2024, Rev. A05](https://dl.dell.com/content/manual44781765-precision-5560-service-manual.pdf?language=en-us), 75 pages. Downloaded from Dell and visually inspected. SHA256 `64dd6f4a2dc559da6db8ab5f17c85f7dfc98d209748bb4c6826156fc67b0df33`. Printed page numbers below equal PDF page numbers; subtract one for zero-based viewers.
- [Dell Setup and Specifications, March 2022, Rev. A02](https://dl.dell.com/content/manual34721296-precision-5560-setup-and-specifications.pdf?language=en-us), 24 pages. Underside image on page 9 visually inspected; dimensions on page 10. SHA256 `273e04997e7c186430257ec1f553c5c79812f0094779044f0447a0b4cb7c45ef`.
- [Dell-authored Precision 5560 Spec Sheet, distributor-hosted copy](https://media.bechtle.com/asrc/180712/1c4b3d4ee288fc9434f5175bf56070570/c3/-/8af281ab55e54f638e8d6a3c2b874bf0/dell-precision-5560-i9-a2000-32gb-1tb-data-sheet-1), page 1, Advanced Thermal Design. Manufacturer document, not a reseller's technical interpretation. [Original Dell URL](https://www.delltechnologies.com/asset/en-us/products/workstations/technical-support/precision-5560-spec-sheet.pdf) returned HTTP 404 during direct opening; the search index still exposes the same text, and the linked Dell-authored copy was successfully opened.

## What is confirmed

The Dell spec sheet states that the 5560 has two liquid-crystal-polymer fans, two heat pipes, and exhaust venting through the hinge. This establishes rear/hinge exhaust, not side-port exhaust. It provides no fan pressure-flow curve. [Spec sheet, page 1](https://media.bechtle.com/asrc/180712/1c4b3d4ee288fc9434f5175bf56070570/c3/-/8af281ab55e54f638e8d6a3c2b874bf0/dell-precision-5560-i9-a2000-32gb-1tb-data-sheet-1).

The service-manual visuals support these geometric facts:

| Page | Observation |
|---|---|
| 12 | Exploded assembly identifies separate left/right fans and heat sink. |
| 13 | Base-cover underside has a long transverse slotted grille near the hinge edge. |
| 27 | Left-fan removal diagram shows a circular impeller inlet and surrounding blower housing. |
| 29 | Right-fan removal diagram shows the other blower near the opposite side. |
| 31 | Heat-sink removal image shows the heat-pipe assembly connecting to fin regions alongside the hinge. |

The service instructions state that each fan slides out of the heat sink. Blue curved arrows in these pictures indicate removal/installation motion, **not airflow or operating rotation**. No calibrated scale or vent dimensions appear in these diagrams. Names should follow this A05 edition: older mirrors can reverse left/right labels relative to the viewed underside. [Service Manual](https://dl.dell.com/content/manual44781765-precision-5560-service-manual.pdf?language=en-us).

The setup guide confirms a 344.4 mm width and 230.3 mm depth; its bottom illustration also shows the transverse grille. Its side-view labels identify speakers. The project’s 20 mm closed-laptop envelope is a clearance representation, not a measured internal air cavity. [Setup guide, pages 6–10](https://dl.dell.com/content/manual34721296-precision-5560-setup-and-specifications.pdf?language=en-us).

## Air path: supported inference, not a measured map

The reasonable working topology is underside grille → internal intake space → two blower inlets → heat-exchanger fins → hinge exhaust. The underside grille's role as the principal intake is inferred from its position, the exposed blower inlets, and the confirmed hinge exhaust; the inspected Dell manuals do not label the entire underside grille with flow arrows. Additional keyboard, perimeter, or hinge leakage is unquantified. Do not force every square millimetre of the grille to carry equal flow.

The two internal blowers are different physical fans from the mount's two 120 mm external fans. Their pressure rises and operating points must be represented separately. Exhaust discharge direction in the installed global frame depends on hinge orientation and lid position; an image's upward direction is not automatically global +Z.

## Proposed editable geometry stub

Use a laptop-local frame before placement: X across width, D toward the hinge, N inward from the underside. Register this frame to the actual installed laptop. Keep the intake, blower, and exhaust topology connected; merely adding circles to the solid laptop envelope does not create a fluid path.

Suggested geometry-only seeds below are **unmeasured modeling assumptions**, not Dell specifications or dimensions extracted from an image. Their purpose is to make an editable, connected preliminary model while measurements are collected.

| Parameter | Optional initial seed | Meaning / evidence status |
|---|---:|---|
| `ventBandWidth` | 290 mm | Placeholder continuous intake band; real open area still unknown. |
| `ventBandDepth` | 30 mm | Placeholder span toward hinge. |
| `ventBandHingeSetback` | 35 mm | Placeholder distance of band centre from hinge edge. |
| `blowerCenterOffsetX` | ±110 mm | Approximate symmetric layout seed; actual left/right offsets may differ. |
| `blowerHingeSetback` | 45 mm | Placeholder inlet-centre setback. |
| `blowerInletDiameter` | 50 mm | Surrogate circular inlet, not a replacement-fan specification. |
| `internalAirDepth` | 8 mm | Simplified internal passage depth; must be clipped by measured interior obstructions. |
| `exhaustWidthPerSide` | 65 mm | Two separate hinge-exhaust stubs. |
| `exhaustHeight` | 5 mm | Placeholder opening height. |

Represent the visible underside grille initially as one parameterized open band with a separate adjustable resistance/open-area model; optionally divide it into left, centre and right zones. Add two short inlet passages normal to the underside, compact turning chambers, and two shallow passages leading to the hinge-exhaust patches. Use separate blower interfaces within these connected passages. A centrifugal blower surrogate should admit air normal to its inlet and discharge toward its tangential outlet; a straight axial cylinder with no downstream turning path is not the observed housing topology.

Keep each uncertain dimension tagged `assumed_unmeasured` and expose it in the geometry manifest. Preserve left/right independence even if starting symmetrically. Leave fan flow, pressure curve, RPM, vent resistance, fin resistance and heat loads unset rather than silently selecting a plausible value. An arbitrary flowrate would produce a scenario, not a simulation of the user's Dell fans.

## Measurements still needed for an installed prediction

- Register underside and hinge geometry to the mount: vent-band footprint, slot size/pitch/open fraction, underside-to-wall orientation, and lid angle.
- Identify exact left/right blower parts and acquire pressure-versus-flow data at relevant RPM, or measure them; free-air flow alone cannot define operation against duct resistance.
- Measure hinge exhaust cross sections and fin-stack resistance; record whether external mount airflow feeds or recirculates exhaust around that region.
- Bound heat dissipation and thermal-control state from the actual machine/workload. Processor rated power is not a measured thermal boundary condition.
- Extend the external fluid domain to allow the ambient leakage and recirculation suppressed in the sealed benchmark.

No installed cooling improvement or temperature prediction follows from the current geometry checks.

## Initial sealed-baseline geometry results

`prepare_geometry.py` completed gaps 8, 12 and 16 mm with actual nominal native assembly obstacles; nonnominal gaps replace the two rails with the corresponding source variant STEPs. Each result has one valid closed connected fluid solid, 229 boundary faces partitioned exactly once, and seven nonempty ASCII STL patches in metres. Ten disconnected enclosed pockets were excluded and listed individually in each manifest.

| Gap | Output directory | Fluid volume | Outlet area | Surface triangles |
|---|---|---:|---:|---:|
| 8 mm | `geometry_gap8/` | 4.612028 L | 0.0028536 m² | 6108 |
| 12 mm | `geometry/` | 4.640557 L | 0.0042936 m² | 6104 |
| 16 mm | `geometry_gap16/` | 4.669281 L | 0.0057336 m² | 6100 |

All full-surface meshes have zero boundary edges, nonmanifold edges and degenerate triangles. Patches are `fan_left`, `fan_right`, `outlet`, `laptop_shell`, `wall_plane`, `assumed_side_seals`, and `printed_or_model_walls`. The existing `laptop_shell` patch is the benchmark's whole planar Y=40 boundary, including its assumed continuation; it is not the actual vented laptop shell. These are geometry/mesh preparation results only, retained as a baseline for the expanded model.
