# Minimalist M1.1 native fork

M1 is an independent open-frame prototype derived through a FreeCAD Save As of
the preserved Rev H document. Its arms, fan cradles, caps, dam and hardware are
new. No prototype arm freeze applies to this fork or to future ducted designs.

[Illustrated print and assembly guide](https://thereprocase.github.io/dell-5560-wall-mount/minimalist-guide.html) ·
[Interactive dimensioned examples](https://thereprocase.github.io/dell-5560-wall-mount/#m1-model) ·
[Nominal package](../docs/downloads/Minimalist_M1_5560.zip) ·
[Fit coupon package](../docs/downloads/Minimalist_M1_Fit_Coupons.zip)

## Reinforced wall transition (M1.1)

Each wall pad is now 32 mm tall with two 6 mm webs tapering 16 mm forward.
The webs reach the flat print face through the arm’s full thickness, filling
the adjacent window roots. Existing arm material, bolt centers, bores and
print orientation are preserved. The dam has a matching tapered clearance
notch; all six sizes pass all nine indexed positions.

When upgrading, replace arms 01/02 and optional dams 07/08 together. The other
sixteen parts are geometrically unchanged. The nominal full set is 400.55 g /
15 h 42 m 30 s in Orca, adding 12.50 g / 17 m 36 s compared with M1.0.
See the [illustrated comparison](../README.md#m11-carry-the-wall-pad-into-the-arm)
and `reports/wall-transition-review.json` for native layer sections and limits.
The 192 to 416 mm² section increase is not a tested strength multiplier.
To reproduce that comparison, extract `minimalist/presets/` from commit
`64fc1aa` to a separate directory, then run `wall_transition_review.py` with
`--baseline-dir` pointing to its six original preset directories. The current
native files stay untouched. `plot_wall_transition.py` renders the report.

## Open and edit

Open `Laptop_Wall_Mount_Minimalist.FCStd` in FreeCAD 1.1. The model contains
55 fully constrained sketches, stock Part construction features, a shared
Spreadsheet and 20 installed App::Links. It has no custom feature proxy that
must be installed to reopen or recompute it. Construction history is grouped by
part family; the installed assembly is separate from the hidden source features.

Open **M1 / Design parameters**, edit the blue measured case inputs, recompute,
and Save As a new file. Gray cells are derived. The parameter sheet documents
the 0.30 mm printed fit clearance and intentional split-crown interference.
The reference uses a 344.4 × 230.3 × 20 mm closed case, a 40 mm wall gap and
separate 2 mm compliant pads. The two cradles accept the modeled 120 × 120 ×
27 mm fan envelope and point it 45° up the rear gap.

The six checked examples in `presets/` span 304–400 mm case width, 210–275 mm
depth and 16–28 mm thickness. They are specific dimensioned examples, not a
continuous certified compatibility range. Screen diagonals are labels only.
Each preset has nine checked dam positions, indexed 0–8 on a 12 mm ladder.
All six delivered files also passed a live GUI open check with the installed
assembly visible and the source construction hidden.
The key engages two rungs 24 mm apart; both sides must use the same index.

## Files and plates

- `presets/<name>/M1.FCStd`: saved/reopened native preset.
- `presets/<name>/print/01–20`: individual oriented STEP, STL and standard 3MF.
- `21_all_hardware`: one plate containing all twelve parts numbered 09–20.
- `22_hardware_without_dam`: eight hardware parts; use with 01–06 for seven
  plates when omitting the optional dam.
- `M1_assembled.step`: installed assembly for inspection, not a print plate.
- `coupons/00_fit_coupon_plate`: compact samples of the actual key, keeper,
  arm/carriage, fan-hanger and cap-pin interfaces in their full-part build directions.
- `reports/release.json`: settings, slice estimates, source hashes and checks.
- `reports/toolpaths/`: deposited-path measurements and source G-code hashes.
- `section-review.json`: explicit load assumptions and nominal stress demand.

Print one each of 01–08 plus 21, for nine plates. Files 09–20 are replacement
alternatives; do not also print them. STEP, STL and geometry-only 3MF represent
the same part. The standard 3MFs have no slicer settings or G-code.

Each delivery ZIP includes an offline illustrated guide, native model, print
files, separately labeled Orca previews, settings and verified SHA256SUMS.
Nothing has been sent to a printer. Start with the coupon and your actual
ASA spool profile in OrcaSlicer; see the guide for orientation and assembly.

## Reproduce the checks

FreeCAD-side scripts use the application's bundled Python/modules. On Windows,
for example, use `"C:\Program Files\FreeCAD 1.1\bin\python.exe"` in place of
`FREECAD_PYTHON` below. Run from the repository root. Python paths are examples;
use the installation path on your machine.

```text
FREECAD_PYTHON minimalist/validate.py
FREECAD_PYTHON minimalist/presets.py
FREECAD_PYTHON minimalist/coupons.py
FREECAD_PYTHON minimalist/section_review.py
FREECAD_PYTHON minimalist/export_scene.py
```

Headless preset saves preserve the original GUI payload order through
`preserve_gui.py`, leaving geometry and parameter streams intact. Run
`gui_presets.py` from FreeCAD’s GUI Python environment to repeat the display
check before packaging regenerated files.

The construction builder is incremental and preserves existing part families.
For a clean reconstruction that leaves the delivered model untouched:

```text
FREECAD_PYTHON minimalist/build.py all --target minimalist/scratch/Rebuilt_M1.FCStd
FREECAD_PYTHON minimalist/validate.py --source minimalist/scratch/Rebuilt_M1.FCStd --output minimalist/rebuild-validation.json
FREECAD_PYTHON minimalist/compare_rebuild.py
```

`slice_models.py` uses the official Orca CLI and flattens its bundled P1S,
0.20 mm and ASA profiles. It preserves orientation/placement and never sends
a print. Example for the nominal set, with paths to your Orca installation:

```sh
python3 minimalist/slice_models.py --orca /path/to/OrcaSlicer \
  --profiles /path/to/resources/profiles/BBL \
  --output minimalist/slices/5560 \
  minimalist/presets/5560/print/0[1-8]*.stl \
  minimalist/presets/5560/print/21_all_hardware.stl
```

Repeat for each preset and the coupon. `audit_plates.py` requires Shapely and
Matplotlib. It analyzes all deposited path types, and reuses a result only when
the parsed path geometry, feature types, layer heights and widths are identical.
The package builder requires all six sets and the Rev H comparison slices:

```text
python3 minimalist/audit_plates.py
python3 minimalist/package_release.py --revh-slices /path/to/revh/comparison/slices
```

`browser_review.cjs` uses Playwright from `freecad/showcase/tooling` and Windows
Edge to check both interactive models, all presets, dam movement, mobile layout
and downloads. Install that folder's lockfile dependencies if needed, serve
`docs/` locally, then run it with the preview URL and `--full`.

## Evidence limits

Native validation checks valid one-solid parts, constrained sketches, unintended
part overlap, minimum intended interface gaps, rectangular case/fan envelopes,
wall intrusion and sampled removal motions. All nine dam indices are checked;
case and fan removal samples are run at the two end indices. A clean CAD result
does not prove a continuous insertion path with cables or real protrusions.

Orca's Bridge label excludes some slot roofs generated as Overhang wall. The
expanded toolpath report therefore includes every deposited feature type and
retains bridge-tagged and all-feature maxima separately. Prior-layer support is
estimated from reported line width with at least 0.05 mm overlap. Same-layer
anchoring order, adhesion and physical sag are not proven. Use the fit coupon
to check the key-slot roofs and the fan hanger before the full print.

The section review assumes a 3 kg case, twice gravity and equal arm loading.
It calculates net upright areas and section moments from native solid slices.
The peak nominal axial-plus-bending demand is about 1.11–1.24 MPa across the
examples. This excludes local stress concentration, shelf/fastener FEA, ASA
allowables, creep, temperature and layer adhesion; it is not a load rating.

Physical fit, printed retention, wall anchors, long-term deformation and cooling
performance remain unqualified. M1 has no CFD or cooling benchmark. Rev F's
exploratory CFD must not be presented as a result for M1 or Rev H.
