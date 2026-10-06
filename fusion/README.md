# Fusion native mount and CFD preparation

**Manufacturing release:** the selected Revision G print model is the FreeCAD
release in [print_release](../print_release/). This Fusion port and its CFD
helpers retain the Revision F baseline geometry.


## Revision F native port

The complete manufacturing port is in one Fusion document:
**Precision 5560 | Rev F | Native Engineering**. It contains 14 printed
occurrences, 13 native rigid assembly joints, 113 fully constrained manufacturing
sketches and 45 manufacturing parameters. The timeline is grouped by component
and construction stage, with component-family colors and associative mirrors.
The live checks reported no unhealthy features.

The six authored part families and all 14 placed parts passed source-geometry
comparisons. Every directional Boolean difference was empty; the assembly
introduced no new part intersections. Live parameter edit/restore checks passed,
including checks through the assembled mirrors. Evidence is under
`output/native/geometry_validation.json`, `assembly_geometry_validation.json`,
`parameter_checks.json`, and `assembly_parameter_checks.json`.

- Manufacturing archive: `output/native/Precision_5560_RevF_native.f3d`.
- Manufacturing-only exchange geometry: `output/native/assembly.step`.
- Extended archive: `output/native/Precision_5560_RevF_native_with_CFD_helpers.f3d`.
- Current traced-profile archive: `output/native/Precision_5560_RevF_traced_CFD_helpers.f3d`.
- Native helper recipe and roles: `native/cfd_helpers.py` and
  `output/native/cfd_helpers.json`.

The CFD helper component adds a vented laptop surrogate, wall, two Dell blower
actuator markers, and an intake porous-interface marker. Its sketches are fully
constrained and features healthy. These are editable analysis assumptions, not
measured Dell internal geometry. Hidden markers are omitted from the current
helper STEP export; their explicit recipe and role metadata remain authoritative.
Do not treat actuator/porous markers as solid flow obstructions.

Local archive export is verified; reopening those archives is not yet verified.
No cloud-save success is claimed. `native/finalize.py` predates the helper
component: do not rerun it blindly and overwrite the manufacturing-only exchange
export with analysis bodies included.

The latest helper replaces the generic envelope with the 14-point Dell side
trace from `profile_reconstruction.json`. Two traced active intake openings
replace the former full-width opening. Two assumed internal duct passages connect
these intakes to hinge discharge slots, each with a separate blower actuator
zone. `native/cfd_helpers_traced.py` builds this in the existing production
document; its sketches are fully constrained and features healthy. The traced
helper STEP includes all six bodies, including the two fan and two porous marker
bodies. See `output/native/cfd_helpers_traced.json` for roles and provenance.

The side-profile estimate retains its +/-2 mm uncertainty and the intake trace
its +/-4 mm uncertainty. Internal duct shape, fan curves and grille resistance
remain assumptions. The simulation records numerical fan forcing separately
from the visible native actuator markers.

## CFD software and trust evidence

See [vendor audit index](cfd/vendor/README.md) for download provenance, SHA256
manifests, installation status and repeatable integrity checks. BARAM 26.3.0's
per-user MSI installation completed; Microsoft MPI subsequently installed after
renewed approval. Both BARAM GUIs open and its bundled Windows solver passed a
400-cell cavity smoke test. `cfd/Launch-BARAM.ps1` supplies missing child-process
profile/MPI environment variables when launching from this automation host.
OpenCFD v2412 is installed in WSL Ubuntu and
passed an isolated official cavity smoke test. Fusion's Simulation workspace
showed an upgrade requirement; no upgraded subscription or simulation study was
created.

See [CFD preparation](cfd/README.md) for benchmark scope and current geometry
checks. No mount/laptop flow or thermal result has been established. Dell blower
curves, vent measurements, internal resistance and heat loads remain unknown.

## Historical pilot evidence

The following records the initial pin experiment, before the full native port.
Its remaining-work statements describe that earlier checkpoint.

User authorized launching Fusion, creating a new model, and experimenting within it on 2026-09-07. No additional Onshape requests are authorized by this work.

`FusionPinPilot/` contains a one-shot Python add-in. It creates a NEW document with a native pin component, sketch constraints and dimensions, revolve and split cut; exercises the head radius; restores nominal dimensions; then creates four positioned occurrences. It exports local STEP, PNG and F3D artifacts to `output/` and records either `result.json` or `error.json`.

## Verified result

The add-in ran automatically after the user launched Fusion. Fusion version `2704.1.36`; `output/result.json` reports success. Created a new model with four positioned pin occurrences and eight timeline entries (component/feature/occurrence history). Both solid features report healthy state 0.

- Axial profile fully constrained; split sketch NOT fully constrained. Split anchor/centering parameter behavior still needs refinement.
- Native nominal volume 204.56030211132358 mm3, bounds (-4,-4,0) to (4,4,14) mm.
- Head radius 4 -> 4.5 mm changed X/Y bounds to +/-4.5 mm and volume to 230.6983529891896 mm3. Radius restored to 4 mm; nominal volume recovered.
- Exported `output/Fusion_native_pin_assembly.f3d`, `output/Fusion_native_pin.step`, and `output/Fusion_native_pin.png`. PNG visually inspected.
- Existing FreeCAD/OCCT imported Fusion STEP as one valid solid. Volume 204.5603021147502 mm3 vs source 204.56030211045663 mm3; both directional Boolean differences empty after transforming original pin into local coordinates. See `output/geometry_comparison.json`.
- No Onshape calls. No existing Fusion model modified. Positioned occurrences are not assembly joints. The full mount and a human-edit preservation test remain future work.

The pilot is live verified, not just syntactically valid. Native archive is a local saved artifact; no cloud-save success is claimed.

Installed add-in location: `%APPDATA%/Autodesk/Autodesk Fusion 360/API/AddIns/FusionPinPilot`.

Installed Fusion executable found at `C:/Users/USER/AppData/Local/Autodesk/webdeploy/production/9c5312dfff2e4569cd1d269973ddf11cb999f782/Fusion360.exe`. Initial direct launch did not remain running; user offered to launch Fusion interactively. Do not repeatedly restart Fusion or disturb other documents.

If automatic loading does not occur, run **Utilities -> Add-Ins -> Scripts and Add-Ins**, find `FusionPinPilot` under Add-Ins and Run. `started.json` confirms add-in entry, not successful CAD construction. A custom event executes the work on the Fusion main thread after a short startup delay.

The script uses the installed Autodesk `adsk` Python API; it cannot run in ordinary system Python. `python -m py_compile` checks syntax only. Native Fusion regeneration, dimensions, exports and rendering must be verified inside Fusion.
