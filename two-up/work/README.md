# Dell Precision 5560 Wall Mount — Two-Up Stacked Variant (`work/`)

Working FreeCAD parametric model, exported STEP/STL geometry, measured B-rep
verification (`measured.json`), and standalone `numpy`/`scipy` analytical checks
for the two-laptop, 15-degree tilted shared-plenum variant specified in
`../DESIGN_GUIDANCE.md`.

---

## Files in `two-up/work/`

| File / Directory | Purpose |
| :--- | :--- |
| `params.py` | Plain-Python dictionary (`PARAMS`) and ordered spreadsheet table (`PARAMETERS`) for the two-up stack. No FreeCAD imports; every parameter traces to `../../minimalist/build.py`, `../DESIGN_GUIDANCE.md`, or an explicit `ESTIMATE` comment with arithmetic. |
| `native.py` | Stock FreeCAD sketch and feature wrapper (`Native`, `E`, `bind`, `rectangle`) from `../../minimalist/native.py`. |
| `geometry.py` | Pure `numpy` / `scipy` analytical prism builder computing exact polygon areas via the shoelace formula and 2D bed footprints via `scipy.spatial.ConvexHull`. |
| `check.py` | Standalone verification runner (`python3 check.py`). Checks every part against the Bambu P1S `256 × 256 × 256 mm` build volume including an `8.0 mm` outer brim (`+16.0 mm` total XY allowance), compares analytical volumes/masses against `measured.json`, and exits nonzero on any failure. |
| `build_two_up.py` | Native FreeCAD builder creating `Laptop_Wall_Mount_TwoUp.FCStd` (`TwoUpParameters` spreadsheet + 39 valid single-solid parts), orienting every part onto the XY print bed, exporting `.step` and `.stl` files to `export/`, and recording exact B-rep properties in `measured.json`. |
| `Laptop_Wall_Mount_TwoUp.FCStd` | Generated FreeCAD 1.1.4 native document containing constrained sketches, feature history, `TwoUpParameters` spreadsheet, and 39 `App::Link` assembly instances. |
| `measured.json` | Exact FreeCAD B-rep volumes (`mm³`, `cm³`), ASA masses (`g` at `1.05 g/cm³`), oriented bounding boxes, and bed-fit statuses for all 39 parts. |
| `export/` | 39 `.step` files and 39 `.stl` meshes (`00_fit_coupon` plus `01` through `38` assembly parts) in their P1S build orientations. |

---

## What to Run and in What Order

### Step 1: Build the native `.FCStd` model and export STEP/STL + `measured.json`
```sh
flatpak run --command=freecadcmd org.freecad.FreeCAD two-up/work/build_two_up.py
```
*(Note: `freecadcmd` in FreeCAD 1.1.4 executes a `.py` script passed as its positional argument directly; passing unquoted `--stage` flags on the `freecadcmd` command line without `--pass` is rejected by FreeCAD's CLI parser, so `build_two_up.py` defaults to `stage='all'` automatically.)*

### Step 2: Run the analytical + B-rep comparison check
```sh
python3 two-up/work/check.py
```

---

## Parts Split to Fit the Bambu P1S Bed (256 × 256 × 256 mm)

With an `8.0 mm` outer brim around the part perimeter on the bed (`+16.0 mm` on
both X and Y axes, matching `../../minimalist/export.py:112`), every part
is kept within **240.0 × 240.0 mm** in XY (**256.0 × 256.0 mm** including brim):

1. **Vertical Arm Stack (`544.3 mm` total Z span from `Z = -74.0 mm` to `+470.3 mm`) $\to$ Split at `Z = 160.0 mm`:**
   * **Lower Tilted Arms (`01_left_lower_arm`, `02_right_lower_arm`):** `234.0 × 81.2 × 30.0 mm` (`250.0 × 97.2 mm` with `8 mm` brim), `128.99 g` B-rep mass each.
   * **Upper Stacking Arms (`09_left_upper_arm`, `10_right_upper_arm`):** `235.0 × 97.6 × 30.0 mm` (`251.0 × 113.6 mm` with `8 mm` brim), `135.37 g` B-rep mass each. Joined across `Z = 160.0 mm` by the 4-rung structural splice keys (`17/18_arm_splice_key`, `69.0 × 18.0 × 26.2 mm`, `11.53 g` each).
2. **Airflow Dams (`348.4 mm` span between arms) $\to$ Split along `X = 0` with a `0.6 mm` center seam:**
   * `07/08_tier1_splitter_dam` (`163.6 × 85.6 × 157.6 mm`, `58.77 g` each) and `11/12_tier2_dam` (`163.6 × 48.0 × 115.3 mm`, `26.93 g` each).
3. **Side Plenum Cheek Panels (`~470 mm` two-tier height) $\to$ Split by tier into 4 panels (`13–16`):**
   * `210.3 × 84.0 × 6.4 mm` (`226.3 × 100.0 mm` with `8 mm` brim), `33.01 g` each.

---

## Evidence Limits: What These Checks Prove and Do Not Prove

**What is proven:**
* FreeCAD 1.1.4 built and recomputed all 39 parts with zero invalid features, zero unconstrained sketches, and `len(Shape.Solids) == 1` on every part.
* Every exported `.step` and `.stl` part fits inside the `256.0 × 256.0 × 256.0 mm` P1S build volume with a full `8.0 mm` perimeter brim (`+16.0 mm` in X and Y).
* Analytical `geometry.py` estimates match measured FreeCAD B-rep volumes within `0.00%` to `2.89%` on every part (`983.03 g` analytical vs. `996.80 g` measured B-rep for the 38-part assembly, `-1.38%` overall; `35.28 g` vs. `35.28 g` for the fit coupon).

**What is NOT proven:**
* No OrcaSlicer toolpath/bridge audit has been run on the exported STLs.
* No physical print, mechanical load test, warm ASA creep test, or airflow/cooling measurement has been performed.
