# Revision H GPU assessment - 8 September 2026

Keep the CPU backend for the next CFD run. The tested CUDA pressure solver
took **219.86 seconds versus 178.31 seconds on CPU** for the same ten steps on
the 3,193,565-cell duct mesh: 23.3% longer. All five field RMS comparisons pass,
but maximum local pressure and velocity differences exceed the preset
comparison tolerance. The tested GPU backend is not accepted for production.

The four-frame startup movie remains an archived commissioning record. No
replacement long sequence, sustained shedding result or settled lip-suction
result has been completed. Hundreds of actual samples and a longer physical
window are still needed; repeated or interpolated frames do not supply them.

## Measured comparison

Both duct runs use WSL OpenFOAM 2412 patch 260127, four MPI ranks, identical
mesh/decomposition/initial fields, quiescent initial velocity, the same SST
model, four fan sources, 10 microsecond fixed steps and 120 pressure solves.
Only the pressure solver changes: CPU GAMG versus CUDA GKOCG with block Jacobi.
Full fields are written at the 0.1 ms endpoint.

| Measurement | CPU | GPU |
|---|---:|---:|
| Solver process wall time | 178.31 s | 219.86 s |
| Mean step after first three | 16.29 s | 19.86 s |
| Total pressure iterations | 474 | 18,907 |
| Maximum iterations in one pressure call | 16 | 730 |
| Maximum logged Courant number | 0.00213 | 0.00213 |
| Turbulence bounding events | 5 | 5 |
| Final relative mass imbalance | 1.89e-7 | 3.04e-7 |

This is one sequential trial per backend on a shared desktop, not a repeated
performance study. Timing includes solver startup, function objects and the
endpoint field write; it excludes meshing, decomposition and reconstruction.
A 1.4-second geometry render ran near GPU-case setup; other desktop work was
also active. Sampled total-device memory peaked at 3,643 MiB during the GPU
run, including other applications. This is not an isolated solver allocation.

`compare_cfd_fields.py` reads the original OpenFOAM scalar64 binary values,
avoiding VTK's possible float32 cell-field conversion. It hashes geometry,
cell zones, initial fields, properties, forcing and spatial schemes. The
criterion, set before the large comparison, is RMS and maximum field error
at most `1e-7 + 1e-4 * reference` using the corresponding reference magnitude.

Maximum U-component difference: 6.25e-5 m/s. Maximum kinematic-pressure
difference: 0.00838 m2/s2, or 0.0101 Pa at the assumed density of 1.2 kg/m3.
Both exceed the strict maximum-error rule. This does not quantify error
against hardware. The tolerance was not relaxed after seeing the result.
Compact logs, inputs, hashes and comparisons are in
`docs/simulation/revh-transient/gpu-benchmark/`; original fields stay local.
Published text uses LF line endings; the artifact checksums cover those bytes.
Original logs remain in their source cases.

## Functional trials

- RTX 3080 Ti, compute capability 8.6, 12,884,377,600 reported device bytes.
  A compiled CUDA 12.4 double-precision kernel checked 1,048,576 values with
  zero maximum error. This is a runtime check, not a CFD speedup.
- A 4,800-cell momentum-source fixture runs ten 0.2 ms steps. CUDA block
  Jacobi with default `scaling 1` passes all five field comparisons against
  the CPU, including maximum errors. The larger case still needs its own check.
- Block Jacobi with `scaling -1` exits zero but gives grossly wrong fields.
  Source inspection finds RHS scaling without corresponding use of the stored
  matrix-wrapper scaling member. No adapter-source patch was made.
- Experimental multigrid crashes with CUDA illegal memory access at both
  scaling signs; `ranksPerGPU 1` also fails. The crash cause remains unresolved.

## Isolated runtime

The [OpenFOAM Ginkgo Layer](https://github.com/hpsim/OGL) supplies CUDA linear
solvers while retaining OpenFOAM models and function objects. It does not
move mesh generation or the whole CFD solver to the GPU.

- OGL commit: `d3e80f4651ebe8b7383af4b746a6c3a43f87bc3e`.
- Ginkgo requested ref `ogl_0600_gko190`, resolved commit
  `ac44187f33ed1aa0c0fe9436dc86b25a860374ba`, reported version 1.10.0.
- Isolated root: `/home/repro/code/dell5560-cfd-gpu-20260908`.
- Matching OpenFOAM source 2412.260127-1 and libopenmpi-dev 4.1.6-7ubuntu2
  packages were unpacked locally. No system packages or Windows BARAM solver
  were changed. Build and install completed beneath the isolated root.
- CUDA architecture 86; CUDA/OpenMP/reference enabled; HIP/SYCL, GPU-aware MPI
  and mixed precision disabled. Transfers use host staging.
- Configure recipe: `gpu/configure_ogl.sh`.
- MPI initially hung contacting X11 at localhost port 6001. The child-process
  environment `HWLOC_COMPONENTS=linux,stop`, with DISPLAY, WAYLAND_DISPLAY and
  XAUTHORITY unset, permits workers to start. No desktop setting was changed.

`benchmark_revh_backend.py` creates fresh cases and enforces timeouts that stop
only their own process groups. Source OpenFOAM's `etc/bashrc` before enabling
shell `set -e`; add the isolated `install/lib` and CUDA `lib64` to the child's
`LD_LIBRARY_PATH`. `export_revh_backend_evidence.py` creates compact evidence;
it does not push or deploy it.

## Mesh candidates remain provisional

`generate_revh_sequence.py` preserves Revision H geometry and the original
18.2M-cell case. It requests 0.25 mm targets in 16 mm-wide lip strips at
X=+/-111 mm, 0.5 mm selected full-span edges, 1 mm selected passages and 2 mm
general surfaces. These are changed meshes, not grid-convergence evidence.

- **05: 3,193,565 cells.** Standard checks pass. Four low-determinant cells
  (minimum 0.0002218), 71,820 concave cells; minimum face weight 0.05272.
  Poor wall-layer coverage. Used only for the bounded backend benchmark.
- **06: 3,405,599 cells.** Absolute 0.1 mm first layers plus refinement at
  05's four defects. Rejected: 765 low-determinant cells, 514 low-weight faces,
  eight low-volume-ratio faces, one bad decomposition tet and 88,041 concave
  cells. Improved layer coverage did not justify the quality regression.
- **07: 3,868,774 cells.** Smaller relative layers with less erosion give
  average layer counts 2.09/4 printed, 3.19/4 laptop and 0.995/2 fan housings.
  Rejected: 975 low-determinant cells (minimum 0.0001396), 11 low-weight faces
  (minimum 0.03290) and 130,554 concave cells. Expanded checks fail three.

No quality threshold was lowered to call these candidates validated. A long
production solve has not been launched on them.
