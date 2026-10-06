# Airflow setup: sealed mount benchmark

**Benchmark prepared, not meshed or solved.** OpenCFD v2412 is installed and passed an isolated 400-cell official cavity mesh/solver smoke test. Benchmark dictionaries parse, but its surface reports two self-intersections; benchmark meshing is withheld pending repair. See [verification evidence](verification/README.md). These scripts install nothing. This is an isothermal benchmark of prescribed delivered flow through both ducts and a rear plenum with **artificially sealed sides** and a nominal 12 mm outlet gap. It excludes ambient leakage, upstream fan/guard losses, true fan operating-point prediction, laptop internals and CPU temperature.

The confirmed fan assumption is the standard original-generation **Noctua NF-A12x25 PWM**. Its official endpoints are 2000 RPM, 102.1 m3/h (60.09 CFM) free flow and 2.34 mm H2O maximum static pressure. Those endpoints do not occur simultaneously. The actual installed RPM and numerical pressure-flow curve remain unknown. `fan_curve_template.csv` intentionally contains only headers; no interpolated manufacturer curve is fabricated. See [Noctua specifications](https://www.noctua.at/en/products/nf-a12x25-pwm/specifications) and its [official P/Q discussion](https://www.noctua.at/en/expertise/tech/nf-a12x25-performance-comparison-to-nf-f12-and-nf-s12a).

## Files and provenance

- `prepare_geometry.py` and `geometry/geometry_manifest.json` document geometry generation and simplifications. The seven named patch STLs are in **metres** and jointly form the closed fluid boundary; do not scale them by 0.001 again. The individual patches are intentionally open surfaces.
- `inputs.json` records scope, fan identification, assumed air/turbulence properties, the 20/35/50 CFM **per-fan** sweep, and coarse/medium/fine mesh settings.
- `generate_case.py` combines named STL regions and writes a standalone OpenCFD v2412 case, including field boundary conditions, mesh/numerical dictionaries, monitors, an explicit `Allrun`, and `case_manifest.json` containing hashes and geometry checks.
- `cases/OpenCFD_v2412/` contains the current generated cases. The earlier `cases/q*_coarse` artifacts are retained historical v2312 preparation, with their original version guards/manifests; do not use them with the new environment. Generation alone is not OpenFOAM validation.

The generator refuses missing/empty patches, inconsistent triangle-edge closure/winding, reversed overall orientation, geometry outside the background box, and existing output directories. It checks the region seed against the bounding box; the geometry-prep manifest and later mesher must establish actual interior placement. OpenFOAM surface/intersection and mesh checks remain required.

The `q20_coarse`, `q35_coarse`, and `q50_coarse` v2412 cases were generated locally from the 6104-triangle, seven-patch surface. Python syntax, closed-edge/winding checks, unit conversions and installed OpenFOAM dictionary parsing passed. There are no benchmark `polyMesh` or solver logs. **Surface self-intersections remain unresolved; benchmark mesh generation and convergence are unverified.**

## Generate cases without running CFD

From the repository root, with ordinary Python 3.10+:

```powershell
python fusion/cfd/generate_case.py --cfm 20 --level coarse
python fusion/cfd/generate_case.py --cfm 35 --level coarse
python fusion/cfd/generate_case.py --cfm 50 --level coarse
```

The first case uses `0.009438948864 m3/s` at **each** fan. The others use `0.016518160512` and `0.023597372160 m3/s` per fan. These are conditional flow demands, not measured/predicted delivered flows. For mesh sensitivity, generate the same flow with `--level medium` and `--level fine`. `--geometry`, `--inputs`, and `--output` permit explicit alternate inputs and a **new** output directory. Existing cases are never erased or overwritten.

Coarse targets roughly 1 mm surface cells, medium 0.75 mm, and fine 0.5 mm with 0.25 mm outlet-region refinement. Cell limits are approximately 1.5/3/6 million; these are configuration limits, not measured cell counts or memory predictions. The coarse mesh is principally a setup check. Narrow passages, 2 mm details, boundary layers and achieved wall resolution need actual inspection and refinement evidence.

## OpenFOAM automation reference

The generated case is pinned to **OpenCFD OpenFOAM v2412**, package `2412.260127-1`, `simpleFoam`, incompressible steady RANS and `kOmegaSST`. It is not an OpenFOAM Foundation case and not a BARAM project. The [OpenCFD simpleFoam documentation](https://doc.openfoam.com/2312/tools/processing/solvers/rtm/incompressible/simpleFoam/) specifies kinematic pressure and velocity/turbulence fields; the generator uses `constant/turbulenceProperties`. The [v2412 boundary-condition API](https://api.openfoam.com/2412/pageBoundaryConditions.html) confirms the pressure/velocity combinations below. Installed v2412 dictionary parsing and comparison against its motorBike SST tutorial are complete; this still does not establish successful benchmark meshing or solving.

Boundary conditions:

| Patch | U | p | Other fields |
| --- | --- | --- | --- |
| `fan_left`, `fan_right` | `flowRateInletVelocity`, positive incoming volume flow | `zeroGradient` | Prescribed k/omega from assumed 5% intensity and 8 mm length scale |
| `outlet` | `pressureInletOutletVelocity` | Zero-gauge `fixedValue` | Backflow-safe `inletOutlet` k/omega with documented assumed values |
| Four wall groups | `noSlip` | `zeroGradient` | `kqRWallFunction`, `omegaWallFunction`, `nutkWallFunction` |

OpenCFD documents [flow-rate inlet syntax](https://doc.openfoam.com/2306/tools/processing/boundary-conditions/rtm/derived/inlet/flowRateInletVelocity/); the referenced page is v2306, while the solver/model and wall-function example were checked against v2312. The [v2312 rotating-fan tutorial](https://doc.openfoam.com/2312/examples/tutorials/incompressible/pimpleFoam/ami-rotating-fan/) confirms these wall-function families and a pressure/backflow outlet. The [SST documentation](https://doc.openfoam.com/2312/tools/processing/models/turbulence/ras/linear-evm/rtm/kOmegaSST/) supplies the k/omega initialization formulas. No rotating fan is modeled in this benchmark.

Only after choosing to run and sourcing the OpenCFD v2412 environment, the explicit future command from a generated case is:

```sh
sh Allrun
```

**This command has not been executed.** `Allrun` refuses another environment/executable version and refuses to reuse an existing mesh/run. It checks the combined surface, generates a background mesh, runs `snappyHexMesh`, checks mesh quality and the seven nonempty named boundaries, confirms one connected region, then invokes `simpleFoam`. It creates logs without cleanup scripts. A stopped or failed case should be preserved; generate a new case to retry.

Six [surfaceFieldValue monitors](https://doc.openfoam.com/2312/tools/post-processing/function-objects/field/surfaceFieldValue/) record per-patch volume flux and mean kinematic static pressure at the two fans and outlet; `yPlus` reports wall resolution. Multiply a kinematic-pressure difference by the assumed density (1.2 kg/m3) for Pa. These static-pressure monitors alone are not a total-pressure-loss calculation when section velocities differ. Check signed flux balance, solver residuals, stable monitors, separation/backflow and mesh sensitivity before drawing conclusions. A converged fixed-flow solution does not establish that the fan can deliver that flow.

## BARAM standalone GUI path

BARAM is a separate GUI workflow recommended for interactive setup. Current [BARAM documentation](https://baramcfd.org/en/manual-en/manual-baramflow-en/introduction-en/) identifies BARAM v26's solver stack as NextFOAM v25, derived from OpenFOAM v2412. The selected OpenCFD release shares that upstream release family, but **OpenCFD v2412 is not the NextFOAM binary or a native BARAM project**. Carry over geometry, patch roles and numerical input values, then create a native BARAM project; dictionary/project compatibility is unverified. No installation is performed by these scripts.

1. In BaramMesh, import the seven `geometry/*.stl` patches, or the generated `constant/triSurface/fluid_boundary.stl` containing named SOLID regions. Check that all seven names and metre dimensions survive import. [BaramMesh geometry documentation](https://baramcfd.org/en/manual-en/manual-barammesh-en/geometry-barammesh-en/) explains the separate display of STL SOLID regions.
2. Define one fluid region using seed `(0, 0.02, 0.10)` m and verify that it lies inside the intended connected plenum. Follow BaramMesh's background-grid, castellation, snapping and boundary-layer steps, using `inputs.json` refinement settings as starting assumptions. [Region selection](https://baramcfd.org/en/manual-en/manual-barammesh-en/region-barammesh-en/) uses an interior point to choose the enclosed volume.
3. Export the mesh as a BaramFlow project or load its OpenFOAM mesh into a new BaramFlow case. The [BaramMesh workflow](https://baramcfd.org/en/manual-en/manual-barammesh-en/introduction-barammesh-en/) provides mesh export; [BaramFlow mesh import](https://baramcfd.org/en/manual-en/manual-baramflow-en/installation-en/) accepts a `constant` or `polyMesh` directory. This is mesh transfer, not an assertion that the generated OpenCFD solver dictionaries import correctly.
4. Recreate the steady incompressible, energy-disabled flow study in BaramFlow. Assign the same per-fan volume flows, zero-gauge pressure outlet and no-slip wall groups, keeping `assumed_side_seals` visibly labeled as artificial. Set room-air and turbulence assumptions explicitly. If the GUI requests mass flow instead, convert using the chosen density and record the conversion.
5. Save the BARAM project before any mesh/solver run. No fan-curve or thermal inputs should be inferred from the fan's endpoint ratings. Use BARAM's own supported solver settings and the same conservation/mesh-sensitivity checks.

For physical interpretation and the later ambient/thermal path, see [CFD preparation research](../CFD_PREP_RESEARCH.md). The production Fusion laptop and wall helper bodies supply visual/geometry references; the sealed fluid benchmark remains a separate simplified analysis model.
