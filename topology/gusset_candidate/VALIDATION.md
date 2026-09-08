# What has and has not passed

## Geometry, editing and slicing

- Native nominal bracket: one valid solid, 40,273.37 mm³. Both STL meshes are closed; left mesh volume differs from CAD by about 0.06%.
- Circular Ø7 bolt and Ø16 tool gauges have zero exact CAD intersection volume. Sampled laptop insertion positions at 0, 1, 5, 20, 60, 120 and 130 mm have zero intersection. These are discrete samples with a simplified laptop envelope, not a complete contact-motion proof.
- FreeCAD reopen and hole diameter 7 → 7.4 → 7 mm regeneration pass. The native fit coupon is also one valid solid.
- Orca 2.4.2 slices both parts successfully, supports off, no slice warnings. Actual predicted pair consumption is **57.79 g**, based on PETG density 1.27 g/cm³.
- All 120 external layer transitions pass the 30° expansion audit with a 0.025 mm geometric allowance. Sample planes use a 0.0001 mm offset to avoid a mesh-section degeneracy at the bolt-hole tangency at Z=8.5 mm. Independent samples on both sides of the tangency also support the next layer. This fixes a numerical false flag, not the physical geometry.

The geometric shell/core accounting erodes each layer by 1.2 mm for walls and intersects neighboring slices across five layers above and below for skins. The remaining core is assigned 20% polymer. It estimates 58.50 g/pair, approximately 1.2% above Orca; **Orca's deposited material estimate is the quoted print mass**. This geometric method approximates ensure-shell-thickness behavior rather than reproducing Orca's exact toolpath logic.

## Structural screening — does not pass a strength-release gate

The actual perforated STEP geometry is tetrahedralized, including slot/seat/contact surfaces and tool openings. Supports are ideal clamps only at the washer-bearing annuli. The solver receives a print material orientation: print-plane Eₓ=Eᵧ=1800 MPa, interlayer E𝓏=900 MPa, Poisson ratios 0.3, Gₓᵧ=690 MPa and Gₓ𝓏=Gᵧ𝓏=345 MPa. These are **assumed screening properties, not measured values for this spool**.

Five interior samples per tetrahedron map shell/core coverage from the layer audit. Sparse core stiffness is assumed to be 0.04 times solid stiffness; this is an uncalibrated effective stiffness model for 20% infill, not explicitly meshed gyroid. Both material assumptions and layer mapping need calibration for a defensible strength prediction.

Each case loads one bracket; the two-bracket assembly/contact redistribution is not solved. The 2.5 kg mass assumption and concentrating a grab on one side provide explicit load scenarios, not a safety factor certification.

| Scenario | Previous, 1.2 mm mesh | Gusseted, 1.8 mm mesh | Gusseted, 1.2 mm mesh | Reduction at 1.2 mm |
|---|---:|---:|---:|---:|
| 73.6 N down, with lean moment | 0.922 mm | 0.480 mm | 0.574 mm | 38% |
| 24.5 N down + 30 N outward grab at 190 mm height | 3.201 mm | 2.133 mm | 2.639 mm | 18% |
| 24.5 N down + 20 N side force on cheek region | 2.315 mm | 1.143 mm | 1.380 mm | 40% |

Numbers are maximum displacement magnitude among monitored contact/support nodes. The new fine mesh has 31,335 nodes. The grab displacement still increases about 24% between the two new meshes, so convergence remains unresolved. Peak absolute grab stress rises from 38.2 to 66.3 MPa with refinement; the previous fine-mesh value was 66.5 MPa. **The gussets improve predicted stiffness but do not resolve the stress concentration or establish a strength margin.** No material failure criterion, wall-anchor rating, physical print strength or creep qualification is supplied.

The previous candidate remains in `../cad_candidate`; `results/comparison.json` records both mesh comparisons and the mass change.

The next structural step is to identify the grab-case compliance and stress concentrations, revise rib junction/section sizes, and use a better resolved/calibrated shell–infill/contact model. Simply polishing this shape further or quoting the earlier voxel model's smaller displacement would conceal the unresolved issue. PETG creep, layer failure, fastener preload, wall/anchor behavior and physical fit/load tests remain open.

Raw reports: `results/cad_validation.json`, `reopen_validation.json`, `layer_validation.json`, `layers.csv`, `structure_1.8.json`, `structure_1.2.json`, and `orca/result.json`. Exact load vectors and support/contact group sizes are recorded in the structural reports.
