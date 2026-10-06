# OpenFOAM setup verification, 2026-09-07

WSL Ubuntu has `openfoam2412`, `openfoam2412-tools`, and `openfoam2412-tutorials` version **2412.260127-1**. The sourced environment is `/usr/lib/openfoam/openfoam2412/etc/bashrc`; `simpleFoam -help` identifies OpenFOAM 2412 build `_b8cf4d35-20260127`, patch 260127. See `environment.txt`.

## Completed checks

- All generated field, transport/turbulence and mesh/numerical dictionaries in the three current v2412 coarse cases were parsed by installed `foamDictionary FILE -keywords`. Evidence: `dictionary_q20_coarse.txt`, `dictionary_q35_coarse.txt`, `dictionary_q50_coarse.txt`.
- The installed `simpleFoam/motorBike` tutorial uses the same `RASModel kOmegaSST`, Newtonian transport, required k/omega/nut fields and wall-function families. Read-only excerpts are in `installed_motorBike_reference.txt`. Different numerics/relaxation settings in our case are explicit setup choices, not an exact tutorial copy.
- The installed official `icoFoam/cavity/cavity` tutorial was copied into `tutorial_cavity_v2412`. Only that local copy's endTime (0.05 s) and writeInterval (10) were changed. `blockMesh` generated 400 cells, `checkMesh -allGeometry -allTopology` reported **Mesh OK**, and `icoFoam` completed ten steps to 0.05 s. Its reported CPU execution time was 0.03 s. Logs and vendor-original controlDict are retained. This is a tiny **laminar installation smoke test**, not a validation of SST, the mount, or laptop cooling.

## Benchmark surface issue

The combined source boundary contains 6104 triangles in seven regions, 3050 vertices, one connected part and one consistently oriented zone. `surfaceCheck -checkSelfIntersection` reports a closed surface with no illegal triangles, **but two self-intersection locations**. The minimum triangle quality is `1.62449e-09`. See `surfaceCheck.txt` and `selfInterPoints.obj`:

```text
(0.131, 0.103959, -0.047041) m
(-0.0002, 0.002, 0.197) m
```

The geometry author has been notified. **Benchmark meshing is withheld pending resolution.** Closure alone is insufficient. `surfaceCheck` returned success despite the diagnostic, so the generator and current `Allrun` scripts now reject the self-intersection text explicitly. Current case manifests record this setup patch and retain the previous generator hash.

## Commands actually executed

From PowerShell:

```powershell
wsl -d Ubuntu -- bash /mnt/f/Code/dell-5560-wall-mount/fusion/cfd/verification/inspect_setup.sh
wsl -d Ubuntu -- bash /mnt/f/Code/dell-5560-wall-mount/fusion/cfd/verification/smoke_cavity.sh
```

The first script sources the installed environment, records selected package/executable versions, parses dictionaries and runs only `surfaceCheck` on benchmark geometry. The second makes a new isolated official tutorial copy, adjusts its local run limits, and runs `timeout 30s blockMesh`, `timeout 30s checkMesh -allGeometry -allTopology`, and `timeout 30s icoFoam`. It refuses to overwrite an existing verification directory.

Initial probe attempts stopped because strict shell error handling was enabled before sourcing OpenFOAM and because the optional `openfoam2412-default` meta-package was absent. The script now sources OpenFOAM first and queries the three actual installed packages. These were verification-script corrections; vendor installation files were not edited.

No mount/laptop flow solve or full production CFD run was performed. The current benchmark remains stationary, isothermal, deliberately sealed, and distinct from the later vented-laptop/external-flow preparation.
