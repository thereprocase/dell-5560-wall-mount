# Traced-laptop airflow exploration

User authorized surface repair and an actual run, then requested the README's
Dell side-profile/intake traces and an internal duct with a simulated fan.

## Native model

`native/cfd_helpers_traced.py` replaces only the prior analysis helper component
in the single native production document. The 14 printed occurrences and their
13 joints remain. The helper has a traced silhouette, two traced intake openings,
two assumed internal passages to the hinge, two Dell actuator markers and two
porous-interface markers. The wall is a separate helper body. The six helper
bodies are all present in `output/native/cfd_helpers_traced.step`; role metadata
and the reconstruction JSON hash are preserved beside it. Native sketches are
fully constrained and features healthy. The pre-update archive is retained.

## Surface repair

The original OCCT triangulation had 672 open edges. A STEP topology reload
closed them. `repair_surface.py` paired all 1,208 original/reloaded faces and
checked bidirectional vertex/interior samples, centroid, area, validity and
volume. Maximum sampled distance was 1.22e-10 mm, maximum face-centroid difference
0.000479 mm, and volume difference 0.017325 mm3. This is a bounded geometric
comparison, not a successful exact coincident Boolean comparison.

OpenFOAM still reported near-coplanar intersections. Rounding and an independent
Gmsh triangulation did not resolve them. The accepted mesh uses a deterministic
seed-5560 perturbation bounded at 1.710e-8 m (0.0000171 mm), keeping domain-plane
vertices fixed. No facets flipped. OpenCFD v2412's **default** surfaceCheck then
reported a closed surface, no illegal triangles and no self-intersections. Its
four separate closed surface components are the outer fluid boundary and inner
obstacle boundaries; the subsequent volume mesh has one connected fluid region.
Rejected trials and displacement/hash evidence are retained. No manufacturing
CAD was modified by the numerical perturbation.

## Runtime and volume mesh

WSL OpenCFD passed its serial smoke test, but its MPI launcher stalled before
worker creation. Actual meshing/solving uses BARAM's bundled Windows
OpenFOAM-v2412 build `6467f461-20260821` with Microsoft MPI 10.1.12498.18, eight
processes. The case directory retains the earlier `OpenCFD_v2412` naming;
`run_provenance.json` records the actual runtime.

The v2/v3 mesh has 836,278 cells in one fluid region. Standard checkMesh reports
Mesh OK: maximum skewness 2.496 and non-orthogonality 64.69 degrees, positive
volumes and valid face interpolation weights. The expanded diagnostic still
flags one cell with determinant 0.000683 and concave polyhedral cells/warped
faces. Those diagnostics are retained, not represented as a completely clean
expanded check. There are no prism layers in this coarse exploratory mesh;
wall resolution and mesh independence remain unverified.

## Fan and solver assumptions

All four fan sources apply nominal 10 Pa times disk area as a total force,
divided by assumed density 1.2 kg/m3 for the incompressible momentum equation.
These are constant-force actuators, not measured manufacturer P/Q curves. The
two Dell source zones contain 2,438 and 2,443 cells. The initial 2 mm Noctua zones
were under-resolved; v3 broadens them to 10 mm within the fan housings while
preserving total force, selecting 2,033 and 2,032 cells. Native marker geometry
remains 2 mm; numerical source thickness is recorded in the case assumptions.

The v3 run starts from v2's saved iteration-300 fields, uses steady incompressible
kOmegaSST and first-order bounded-upwind momentum for this coarse exploration.
The old warm-start time metadata is archived separately. Grille resistance is
unset; the trace specifies gross active openings, not their porosity. There is
no heat transfer, CPU load, fin-stack resistance, measured blower curve or
validated hardware operating point.

Current case: `cases/OpenCFD_v2412/installed_pressure10_v3`. Solver logs, monitors,
assumptions and input hashes are retained there. `render_installed_result.py`
reads the reconstructed result to sample fan/intake flow and render streamlines.
Iteration numbering is SIMPLE convergence progress, not physical elapsed time.

## Completed exploratory run and GUI

The v3 solver ended normally at its 1200-iteration limit after 1166 seconds;
reconstruction completed. It did not satisfy the 1e-5 SIMPLE convergence target.
Final initial residuals: Ux 4.797e-5, Uy 6.977e-5, Uz 6.449e-5,
p 2.955e-5, k 1.974e-4, omega 5.490e-6. Maximum speed was 4.935 m/s;
net ambient flux was 3.456e-8 m3/s. Small net flux does not establish convergence.

Final preview and sampled flows are in `results/iteration_1200/` within v3.
Sampled intake flows were 3.520 and 3.546 CFM, versus 3.498 and 3.522 at
iteration 400 (less than 0.7% change). This is stability evidence for these
two integral quantities only, not calibrated hardware performance or complete
field convergence. Noctua disk samples have 98.7% valid sample coverage.

`Watch-Run.ps1` provides a visible WPF monitor with residuals, log tail and
folder/image buttons. Child GUI and VTK processes need WINDIR/SystemRoot and
USERPROFILE restored from Windows known folders in this agent environment;
without them WPF raises a FontCache URI error and VTK may exit silently.

## Technical drawing package

`output/pdf/Precision_5560_CFD_Technical_Review.pdf` is a seven-sheet A3
landscape review set: system isometric, independent orthographic views,
left/right longitudinal cuts, internal speed/pressure plane, transverse intake
section with reverse view, mesh details and residual history. A companion ZIP
contains the PDF, 150 dpi sheets and provenance manifests.

Builders: `drawing_assets.py` (FreeCAD Python / VTK / matplotlib) and
`build_drawing_package.py` (system Python with workspace-local PDF libraries).
Use VTK_SMP_MAX_THREADS=1: the parallel runtime caused silent exits/stalls in
this environment. Final field sections use actual cut-cell triangulations;
regular-grid probe trials produced invalid-sample stripes and were rejected.
VTK reports some non-contourable polyhedra on the Y=45 mm cut; omitted cells
are not filled. Rendered mesh diagonals are explicitly distinguished from
original polyhedral cell faces. Pressure is kinematic p multiplied by 1.2.
All seven pages are rendered with MuPDF and visually reviewed; source hashes
and PDF hash are in drawing_package_manifest.json. No new solve was run.
