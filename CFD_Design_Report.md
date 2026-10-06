# Plenum and outlet CFD — Revision F

**Keep a 12 mm nominal slot as the starting configuration.** The 8 mm slot
retains more intake pressure, while 16 mm passes more bypass flow. At fixed
inlet total pressure, narrowing the slot does not automatically create the
fastest outlet jet. These are comparative model results, not predictions for
the user's uncharacterized fans or laptop.

The gentler lower turn improves mean intake pressure by only
0.11 Pa
on the common mesh. That small difference does not justify calling it an
optimized shape. Retain its printable transition and use the larger slot-width
tradeoff to guide the first prototype. The contraction starts at Z=198 mm,
after the estimated intake band, reaches its throat at Z=226 mm, and guides
the outlet upward to Z=232 mm. All three variants keep the skin within 45° for
lip-down printing.

## Model and boundary conditions

OpenFOAM v1912 (Ubuntu package 1912.200626-2build3), simpleFoam, incompressible
steady RANS, k-omega SST. Density 1.2 kg/m³; kinematic viscosity 1.5e-5 m²/s.
Two-dimensional block mesh with a 1 mm empty span. No-slip smooth walls,
20 Pa inlet total pressure (10 Pa sensitivity), zero-gauge static pressure at
the slot exit, prescribed 0.4 m/s suction through the intake band (0.8 m/s
sensitivity). Inlet k=0.015 m²/s² and omega=50 s⁻¹. Wall functions use the
solver's standard SST setup. This is not a transition-resolving calculation.

The inlet line slopes 45° and has wallward/upward normal. The mesh idealizes
the center section of a fan band with sealed cheeks; it omits the grille,
fan hub/swirl, structural ribs, three-dimensional spreading and leakage at
noncontact joints. The CAD skins sit around a similar ruled flow path;
2 mm wall thickness and small transitions are simplified in the CFD geometry.
The CFD intake patch is Z=156–192 mm, a simplified band within the image-derived
layout. The rear foot projects 2 mm at Z≈218–222 mm; its true height is unmeasured.

Laptop intake flow is a prescribed demand, not a pressure-coupled internal
resistance or laptop-blower model. The supplied fan pressure is an assumption,
not a measured operating point or an adopted fan curve. Do not multiply a
representative slice across the entire laptop to claim total CFM.

## Results

Pressure is gauge pressure relative to the slot outlet. Mean and minimum
values sample the intake patch; velocity is area-mean at the slot exit.

| Case | Mean intake Pa | Minimum intake Pa | Exit m/s | Flow imbalance % | Strict residual target met |
|---|---:|---:|---:|---:|---|
| curved_12 | 17.67 | 15.80 | 4.42 | 0.00000 | no |
| curved_12_fine | 17.72 | 15.62 | 4.29 | 0.00000 | no |
| curved_12_high_draw | 16.44 | 11.51 | 4.63 | 0.00000 | yes |
| curved_12_low_pressure | 8.53 | 7.01 | 3.16 | 0.00000 | no |
| curved_12_medium | 17.68 | 15.65 | 4.34 | 0.00004 | no |
| curved_16 | 15.43 | 12.87 | 5.16 | 0.00000 | yes |
| curved_8 | 18.80 | 17.42 | 4.01 | 0.00000 | yes |
| straight_12 | 17.56 | 15.75 | 4.39 | 0.00000 | yes |

## Numerical checks

All eight block meshes pass checkMesh; positive volumes and acceptable
nonorthogonality/skewness. Pressure-velocity coupling uses SIMPLE with one
nonorthogonal correction and under-relaxation. Momentum uses bounded
linear-upwind convection; turbulence uses upwind convection.

The nominal cell-size sequence is 2.0, 1.3, 0.85 mm. Coarse-to-fine mean intake
pressure changes by0.31%;
exit velocity changes by2.95%.
Medium-to-fine pressure changes by0.24%.
Mass imbalance remains below 0.001%. Four cases do not satisfy the strict
1e-6 residual stop before 1600 iterations. Their final monitored mean pressures
change by less than 0.01% between saved states. Treat them as stabilized
screening results, with unresolved residual/flow unsteadiness, not fully
converged high-accuracy solutions. Raw logs preserve this limitation.

## What this does not establish

No conjugate heat transfer, laptop temperature, exhaust entrainment distance,
room recirculation, noise, buoyancy or fan-off cooling prediction. Side leakage
can lower real plenum pressure. The unheated domain ends at the hinge height;
it does not model how far the hot plume travels. No topology or generative
optimization solve is represented by this study.

A useful next calibration is the exact 120 mm fan model and RPM/PWM setting,
plus intake static pressure and laptop temperature at a repeatable workload.
Those allow a fan-curve/internal-resistance model and a meaningful 3D study.

## Reproduce and inspect

Run unpack_cfd_evidence.py to inspect the recorded fields and logs. To generate new results, run run_cfd_sweep.py with OpenFOAM available, then analyze_cfd.py and render_cfd.py.
Each cfd/ case contains its mesh dictionaries, initial conditions, parameters,
checkMesh and solver logs, and the final field state. VTK output for the
comparison cases opens in ParaView. The included foam_environment.md explains
the runtime setup and the -noFunctionObjects option used to avoid an old
function-object hashing incompatibility; postprocessing reads written fields.

Sources: [OpenFOAM SST model](https://doc.openfoam.com/2306/tools/processing/models/turbulence/ras/linear-evm/rtm/kOmegaSST/),
[OpenFOAM boundary conditions](https://www.openfoam.com/documentation/user-guide/a-reference/a.4-standard-boundary-conditions),
[Dell service manual](https://dl.dell.com/content/manual44781765-precision-5560-service-manual.pdf?language=en-us).
