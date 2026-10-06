# Revision H transient airflow study

This study uses Revision H's installed-coordinate `freecad/Precision_5560_Native.step`, starting from commit `f47a03f`. It retains the traced laptop silhouette, surrogate internal passages and four nominal 10 Pa constant-force actuators from the earlier study. It does not reuse the earlier Revision F printed obstacle as Revision H geometry.

The laptop profile has an estimated +/-2 mm image-trace uncertainty and the intake locations +/-4 mm. Finer CFD cells resolve this assumed geometry; they do not establish the real laptop lip shape or remove that uncertainty.

The objective is to investigate coherent vortex shedding at duct edges and pressure depression near the laptop lips. A steady streamline plot cannot demonstrate shedding. Negative gauge pressure alone does not identify a Bernoulli mechanism: examine velocity, static pressure, total pressure and the surrounding flow together. Fan forcing, viscous loss and separated flow all matter.

The earlier Revision F solution differs in geometry, mesh and numerical method. Comparing it with this case is not a mesh-independence test. That requires multiple Revision H meshes using the same physical model and solver protocol.

## Requested mesh and numerics

- 16 mm background cells; 1 mm printed/laptop surfaces and 2 mm fan housings.
- 0.5 mm cells in selected internal passages and wakes; 0.25 mm cells at selected duct edges and front/hinge lips.
- Five layers on printed/laptop walls, three on fan housings; requested first layer thickness 0.06 mm with 1.2 growth. Achieved coverage and y+ must be measured.
- Transient `pimpleFoam`, SST URANS, second-order backward time differentiation and linear-upwind momentum convection, three outer/two pressure correctors.
- Adaptive Courant limit 0.5, maximum time step 25 microseconds. The initial 2 ms run is a commissioning pilot, too short to establish mature flow or shedding.
- Every-step p/U probes, ambient signed and absolute flux, y+, vorticity and Q outputs. Kinematic pressure converts to Pa using the assumed 1.2 kg/m3 density.

These are requested settings, not measured mesh acceptance. Coherent URANS shedding may be captured; a lack of oscillations is not proof that the hardware lacks turbulent shedding. This is not DNS or a resolved-LES claim.

## Reproduction

Use the installed FreeCAD Python to run `prepare_installed_domain.py --printed-assembly ../../freecad/Precision_5560_Native.step --output geometry_revh --deflection-mm 0.025` from `fusion/cfd/`. The 0.025 mm deflection resolves the Revision H curves more finely than the earlier 0.1 mm tessellation. This reads the exported STEP without touching the live CAD document.

From the repository root, `python fusion/cfd/generate_revh_transient.py --case fusion/cfd/runs/NEW_CASE --perturb-m 1e-8` creates a new case and records hashes. Existing cases are refused. The bounded seed-5560 surface stabilization preserves domain planes and normal orientation; its measured displacement is recorded. It only addresses numerical tessellation coincidences, and does not modify native CAD. Unmodified and failed surface trials remain under `runs/`.

`python fusion/cfd/run_revh.py PHASE --case fusion/cfd/runs/NEW_CASE` runs `surface`, `mesh`, `zones`, then `pilot` as separate gated phases. It uses the previously installed BARAM Windows OpenFOAM-v2412 executables and eight MS-MPI workers. Each phase refuses to overwrite its own logs. The generated case dictionaries, logs and manifests are the execution evidence; this note is not a passed-test report.

Before the first solve, `python fusion/cfd/add_transient_sections.py --case fusion/cfd/runs/NEW_CASE` adds four bounded section outputs every 0.1 ms. The optional `initialize` phase requires `--source-case PATH_TO_OLD_CASE`; it maps saved iteration-1200 fields solely to shorten startup, preserving the original zero-time fields. The installed mapFields accepts `interpolate`, not `cellVolumeWeight`. A local source snapshot contains only U, p, k, omega and nut, avoiding derived-field patch mismatches. Existing target printed-wall boundary values are retained for the changed Revision H geometry. This initialization is not a Revision H solution.

## Acceptance and publication

Before interpretation: surface closure/intersections, one fluid region, mesh quality, achieved local resolution/layers, valid probes, positive turbulence fields, bounded Courant number, continuity relative to throughflow, and converged time-step correctors. Discard startup before calculating means, RMS and shedding spectra; observe at least 20 measured periods. Compare a halved time step and a further-refined mesh before claiming numerical independence. Experimental validation also requires measured geometry, fan operating points and pressure/flow data. See [NASA's verification and validation tutorial](https://www.grc.nasa.gov/www/wind/valid/tutorial/tutorial.html).

The collaborator owns the main GitHub Pages layout. CFD artifacts will be self-contained under `docs/simulation/revh-transient/`, with the actual completion status attached. No thermal prediction or hardware validation is implied.

## GPU assessment, 8 September 2026

The following records the initial inventory. A later isolated CUDA build and
duct-mesh comparison are documented in [GPU_ACCELERATION.md](GPU_ACCELERATION.md).
The tested GPU backend was 23.3% slower and failed the preset maximum-field-error
criterion; CPU remains selected. The original study below remains historical evidence.

Live inventory: NVIDIA RTX 3080 Ti, 12,288 MiB VRAM; the installed BARAM OpenFOAM library directory has no PETSc, AmgX or CUDA backend. WSL's compiler reports CUDA 12.4.131, but no installed OpenFOAM PETSc/AmgX bridge was found in the queried library paths. The queried OpenFOAM installation has the runtime library directory but no `src` or `wmake` directories. These observations do not establish a working GPU CFD runtime.

A new two-process WSL `hostname` MPI smoke test reproduced the previously recorded pre-worker launch hang. Its eight-second timeout did not terminate cleanly; the exact new test process group was identified and stopped after roughly one minute. The Windows mesher was unaffected. No unrelated MPI sessions were stopped. A GPU deployment would need to resolve that runtime path as well as installing and verifying the solver bridge.

GPU acceleration is possible through [OpenFOAM's external-solver interface](https://www.openfoam.com/news/main-news/openfoam-v20-06/numerics) and [GPU-enabled PETSc](https://petsc.org/release/overview/gpu_roadmap/). This offloads algebraic solves, not automatically the mesh generator or all CFD operations. A separate installation and comparison on this case are needed before asserting a speedup, fit in VRAM, or equivalent numerical results. The current mesh/solver run uses the established CPU runtime.

## Candidate 04 mesh disposition

The completed mesh has 18,219,444 cells (21.8 times the prior baseline count). Its requested edge spacing is 0.25 mm; the completed refinement level 6 contains 7,607,226 cells. The mesher reports 3,598,723 added layer cells and 86.648% coverage of selected faces after 60 layer passes. Coverage is aggregate and does not establish local y+ or full coverage at each lip.

The standard mesh check passes: one connected region, positive volumes, maximum nonorthogonality 64.998 degrees and skewness 2.944. Expanded checks find 2,998 cells with determinant below 0.001, 78 faces with interpolation weight below 0.05, and 396,528 concave cells. Additional diagnostics include 194 warped faces, 10,298 concave faces and 64 points on short edges. Minimum determinant is 7.746e-5 and minimum interpolation weight 0.03009. These are unresolved quality limitations, including defects near the lips. No thresholds were changed to label the mesh accepted.

This candidate is permitted only for a monitored commissioning solve to measure stability, sampling and throughput. It is not an accepted validation mesh. The positive volumes, positive determinants and standard quality bounds support attempting this short test, but do not remove the expanded defects. Local repair or a justified quality disposition, a longer settled-flow record, and same-geometry spatial/time-step comparisons remain required before quantitative conclusions. Actual cut-cell outlines and all defect centroids are published with the checks.

## Commissioning checkpoint and runtime

The mapped initial field produced a pre-adjustment Courant number of 1.111. The adaptive step reduced to 4.50 microseconds; the initial loop reports 0.500525 before the next adjustment. The first completed step consumed 230 wall seconds including startup, and the next consumed 192 seconds for 4.95 microseconds of physical time. Extrapolating that one step gives about 21.5 hours for the originally planned 2 ms endpoint; it is a startup estimate, not a long-run performance guarantee.

The run was asked to checkpoint cleanly with `stopAt writeNow` after startup turbulence bounding grew and the mesh defects remained unresolved. The original 2 ms endpoint was not completed. Output-only changes requested extrema, flux and local sections at every step for the final checkpoint; the pre-change dictionary and change record are retained. Pressure during this rapid adjustment of the old field can greatly exceed the nominal fan forcing and must not be interpreted as settled lip suction.

The low-determinant cells are closest to printed (2,243) and laptop (755) CAD patches. Their median approximate centroid-to-CAD distance is 0.0259 mm. This locates most defects near the first wall layer and supports revisiting layer insertion/thickness and local mesh geometry before a long solve. It does not prove that a particular defect caused the observed turbulence clipping.

A bounded follow-up WSL MPI probe forced control and TCP traffic onto loopback; it still timed out after eight seconds, and its isolated process group was cleaned up. No GPU solve was run. The newer [Brae transient solver](https://github.com/simd-ai/brae/blob/main/docs/solvers/pimplefoam.md) was also screened: its documented lack of transient `fvOptions`, adaptive stepping and runtime function objects excludes it as a direct replacement for this fan-actuator case. No speedup or compatibility claim is inferred from its benchmarks.

The first attempt completed four steps through 20.3206 microseconds, then aborted while re-reading the updated control dictionary: `ITstream::readRaw: Not implemented` on several MPI ranks. Its log and four probe records are retained separately; no volume checkpoint was written. The diagnostic restart begins again from the same mapped zero-time fields, disables runtime modification, and writes all fields and local sections every step through a target of 20 microseconds. Changing output scheduling slightly changes the adaptive timestep, so trajectories must not be joined. A 600-cell parallel IO test with eight workers passed field writing, section sampling and reconstruction before this restart. This tests IO, not the CFD geometry or physics.

New generated cases disable runtime dictionary modification to avoid this observed BARAM parallel re-read failure. Make configuration changes between runs. Before `pilot`, provide a reviewed `quality-disposition.json` matching the new case name, based on that case's actual standard and expanded checks. `commissioning_only` permits a monitored diagnostic run and carries no validation acceptance. `--attempt N` preserves phase logs for a distinct retry; preserve previous `postProcessing` records before restarting at the same physical time. The initial 2 ms plan in generation-time manifests remains distinct from the shorter diagnostic execution recorded in runtime dictionaries and status.

## Final diagnostic outcome

Attempt 2 completed four steps through 0.00002030843184 s (0.0203084 ms) in 787.9 wall seconds, followed by reconstruction of the final fields. The 20 microsecond target was slightly exceeded by the last adaptive step. Timestep range was 4.4998 to 5.5571 microseconds; maximum logged Courant after loop startup was 0.5. All 22 probes were found and finite. The final net ambient flux was 4.651e-12 m3/s against summed absolute flux 0.224637 m3/s, giving a relative net/one-way-throughflow imbalance of 4.14e-11. This checks algebraic mass balance, not the validity of the predicted flow rate.

Twelve k/omega bounding events remain recorded. Final startup y+ averages/maxima were printed 1.797/29.31, laptop 1.586/22.72, fan housings 3.084/18.74 and wall plane 6.072/46.74. These early values are not a settled layer-acceptance test. Four actual section frames are published with their timestamps and fixed colour scales; the MP4 provides play, pause and seeking controls, with the physical intervals uniformly slowed to about nine seconds of viewing time (rounded to 30 fps, final sample held for three seconds). No intermediate flow samples are invented. Rebuild it from the preserved GIF frames using `python fusion/cfd/export_revh_video.py --ffmpeg /path/to/ffmpeg`; the exact timing and hashes are in `animation-provenance.json`. Large initial pressure swings diminish rapidly during projection of the mapped field. Neither that swing nor the visible wall-vorticity sheets establish periodic shedding or Bernoulli suction.

The compact sample archive contains raw probes, all four section planes at each saved step, extrema, y+ and ambient flux records. Full three-dimensional fields at every restart step, failed trials and original logs remain local. The validation outcome is unsuccessful: the mesh is substantially finer, but its expanded quality failures, short flow history and missing spatial/time-step convergence still prohibit a released validation claim. GPU acceleration remains assessed but unimplemented.
