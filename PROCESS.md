# Design process and reproduction

Revision F combines parametric CAD, scaled manufacturer imagery, print checks, structural screening and comparative CFD. This page records the decisions and reproduction steps. Physical measurement and coupon testing come next.

## Decisions that shaped the design

| Stage | Question | Decision and evidence |
|---|---|---|
| Layout | How can a server laptop remain easy to remove? | Hinge up, underside toward wall, tall front tines and a vertical lift-out path. Retain four room-facing wall bolts. |
| Vent identification | Where does the underside actually admit air? | Scale Dell side and inside-cover images. The covered center of the exterior grille leads to two inferred intake windows, with explicit uncertainty. |
| Plenum | How can the fans feed pressure at the intake? | Contain the rear gap with cheeks and place the contraction above the estimated intake band. Keep the laptop vertical. |
| Flow comparison | Does the smallest slot create the fastest exit? | Run eight OpenFOAM cases. Under assumed fixed supply pressure, the smaller slot retains more pressure but gives lower exit speed. Start with 12 mm. |
| Material reduction | Where can solid plastic be removed? | Use hollow box cradles, thin duct skins, framed trays and pocketed caps. Check actual net sections. Revision F uses 35.0% less CAD volume than D. |
| Manufacturing | How can the brackets print on their sides? | Orient each family around its load path and support geometry; use sloping roofs and short bridges. Audit every 0.20 mm layer. |
| Assembly | Can all hardware except wall bolts disappear? | Use keyed CA joints for fixed parts and printed split pins for removable fan caps. Keep tray joints dry. |
| Fit | What clearance should the printer reproduce? | Record coordinate, radial and diametral allowances separately. Supply coupons; no global ASA shrink correction. |

Figures show CAD geometry, scaled reference images or calculated flow fields. The laptop and fan envelopes are simplified. Physical testing, topology optimization and 3D thermal analysis remain outside this checkpoint.

## Repository map

| Location | Contents |
|---|---|
| Root STEP files | Printable assembly and explicitly named reference assemblies |
| `parts/` | Fourteen individual exact solids |
| `print_ready/` | Oriented 3MF/STL parts, alternate rails and fit coupons |
| `outlet_gap_variants/` | 8 and 16 mm outlet STEP alternatives |
| `reference/` | Attributed reference images and measurement evidence |
| `cfd/` | Case dictionaries, parameters, result summary and per-case raw-evidence ZIPs |
| Root Python files | CAD generation, analysis, validation, rendering and packaging |
| Root JSON files | Machine-readable geometry, fit, print and structural results |

The repository begins at Revision F. Earlier volume comparisons are recorded in `material_comparison.json` and `reference/Revision_D_Geometry.json`.

## Python setup and CAD regeneration

Use Python 3.12 and CadQuery 2.8.0. `requirements.txt` records the dependencies; packages specified by lower bounds may change on future installations.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python build_mount.py
python reconstruct_profile.py
python section_properties.py
python strength_check.py
python prepare_prints.py
python audit_layers.py
python validate_assembly.py
python render_preview.py
python render_fdm_guide.py
python vent_layout.py
```

Run from the repository root. Regeneration overwrites the corresponding exports. CAD dimensions are in millimeters. `build_mount.py` defines Revision F using primitives from `base_geometry.py`; make assembly changes through those active functions.

Reference images are included and attributed in [SOURCES.md](SOURCES.md). Available fonts can affect the layout of regenerated figures.

## CFD reproduction

The study used OpenFOAM v1912, Ubuntu package `1912.200626-2build3`. Install a compatible runtime and load its shell environment. The scripts use that environment when the optional local runtime is absent. Newer releases may require dictionary changes.

To inspect or reanalyze the recorded study, first unpack its per-case evidence:

```bash
python unpack_cfd_evidence.py
python analyze_cfd.py
python render_cfd.py
```

To perform new runs, use a separate checkout or copy of the case evidence so the original results remain available:

```bash
python run_cfd_sweep.py
python analyze_cfd.py
for case in cfd/*/; do
  if [ -f "$case/system/controlDict" ]; then
    foamToVTK -case "$case" -latestTime -ascii
  fi
done
python render_cfd.py
```

Each run executes `blockMesh`, `checkMesh` and `simpleFoam -noFunctionObjects`. The flag avoids a function-object compatibility failure in the older binary. The solver writes normal field output for postprocessing. [foam_environment.md](foam_environment.md) and [CFD_Design_Report.md](CFD_Design_Report.md) give the environment, boundary conditions and numerical limits.

Case ZIPs contain meshes, saved states, logs and VTK files. The finest-mesh archive uses numbered 4 MiB pieces; the unpack script joins them automatically. Dictionaries and `results.json` are directly browsable. Four cases missed the strict residual target; their logs retain that record.

## Package and check

```bash
python create_package.py
```

This creates a portable ZIP with validation results and a SHA-256 manifest. It excludes local environments, git metadata and generated archives. Physical print, bond, retention, thermal and anchor tests remain pending.

Before printing, follow [P1S_ASA_Print_Guide.md](P1S_ASA_Print_Guide.md). Before adjusting a fit, read [TOLERANCES.md](TOLERANCES.md). The ordered prototype evaluation appears in [ENGINEERING_REPORT.md](ENGINEERING_REPORT.md).
