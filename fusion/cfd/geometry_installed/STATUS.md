# Installed ambient domain: geometry checkpoint

The exported CAD fluid is a valid, closed, single connected solid of 0.28534812883859545 m³. Its bounds are X ±400 mm, Y 0–450 mm, Z −300–500 mm. The laptop cavity probe (0,45,100) mm lies in this connected ambient component. Twelve disconnected closed pockets were excluded and are individually recorded in `geometry_manifest.json`.

The fluid subtracts the 14 printed assembly solids, vented laptop shell, and two simplified Noctua housing rings. It does not subtract actuator or grille markers. All four fan-zone volumes and the grille-marker volume are inside the selected fluid (each directional outside-fluid Boolean volume is zero).

The laptop internal layout is an explicitly unmeasured surrogate. Only its shell was included in the native helper STEP export. Hidden Dell actuator and grille markers were reconstructed from the exact native helper recipe and exported parameter metadata; provenance is recorded in the manifest. No fan pressure-flow curves or resistance values were invented.

## Failed surface gate

The five named ASCII STL patches use metres and partition every surface triangle exactly once. Their union has 24,428 triangles, 12,354 vertices, **672 open edges**, zero nonmanifold edges, and zero self-intersections detected by FreeCAD. It is **not watertight and is not ready for CFD meshing**. Removing the original BRep's triangulation cache did not resolve the open edges. Coordinate rounding from 1e-12 through 1e-6 metres did not merge these seams, so this is not merely a tiny duplicate-coordinate issue.

A diagnostic STEP export/reimport produced a mesh with zero open edges. However, equivalence is unproven: coincident Boolean comparison returned near-whole-domain residual volumes of 285,463,059.11833507 and 285,348,316.5141635 mm³, despite a raw volume difference of only 0.01776677370071411 mm³. That result was rejected. The delivered patches are from the original BRep, with their failed seam check preserved; no displacement, hole filling, or silent tolerance relaxation was applied.

Next geometry work should diagnose the original BRep's shared-edge tessellation or establish independent, sufficiently strong surface equivalence for the STEP roundtrip. An OpenFOAM surfaceCheck and subsequent volume-mesh quality check are still required. The earlier sealed baseline separately has two reported OpenFOAM self-intersection locations; it remains an initial baseline, not a substitute for this installed model.

No production solver case or flow/thermal result was produced. Dell blower pressure-flow curves/RPM, grille and fin resistance, and geometric dimensions remain unresolved physical inputs. `geometry_ready` and `solver_case_ready` are both false.
