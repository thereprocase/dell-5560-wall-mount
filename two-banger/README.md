# Two-Banger 5560 Rack (2× Dell Precision 5560, 2× 140 mm Fans)

**Status:** CAD and automated fit checks only; no part has been printed or test-fitted. [3D viewer and downloads](https://thereprocase.github.io/dell-5560-wall-mount/two-banger/) · [wall-hung variant](wall/README.md).

Greenfield, desk-standing back-to-back A-frame rack built from scratch in FreeCAD 1.1.4.

---

## Layout Choice & Why

A **desk-standing back-to-back A-frame** with both `140 × 140 × 25 mm` fans lying flat at the
bottom is the simplest geometry that works: at the base (`Z = 47 mm`), the two laptops' undersides
sit `142 mm` apart—matching the 140 mm fan width with zero transition ducts—and lean inward at
`14°` so gravity rests both laptops against the inner rails while narrowing the top gap to `30.6 mm`
at the hinges. Splitting the rack left-and-right at `X = 0` keeps every part flat, support-free, and
well inside the Bambu P1S `256 × 256 × 256 mm` bed with an `8 mm` brim, using only **4 printed
parts** and **M4 screws**.

**Airflow split:** Both laptops and both 140 mm fans are mirror-symmetric about `X = 0` and `Y = 0`,
so each laptop's intake underside sees the exact same wedge plenum geometry and share of fan air.

---

## Judgment Calls Recorded

1. **Desk-standing A-frame (`14°` inward tilt) instead of wall-hung:** Eliminates wall anchors and
   heavy cantilevered arms, lets gravity hold the laptops against the inner plenum rails, and keeps
   the `228 mm` tall end frames comfortably under the `256 mm` bed limit.
2. **`16 mm` open under-fan desk clearance:** Raises the fan tray deck on integral end-frame feet
   with an open `110 × 15 mm` intake arch at each end (plus open front/back under the tray) so the
   140 mm fans can breathe freely on a flat desk.
3. **`12.5 mm` inboard support rails + `24 mm` outer bottom lip:** Supports the outer `12.5 mm` of
   each laptop's chassis edge (clearing the intake windows near `|X| ≈ 76–146 mm`) and leaves the
   entire side-port zone (`Z > 71 mm`) completely open so cables plug in and laptops lift out `24 mm`
   by hand.
4. **M4 heat-set inserts + screws instead of glue or printed pins:** Bolts the two fan trays
   together at `X = 0` and into the two end frames in under ten minutes, and lets you swap a fan or
   disassemble the rack with a single 3 mm hex key.
5. **No top tie bar:** Keeps the rack at 4 printed parts and leaves the hinge exhaust completely
   unobstructed; stiffness relies on the `149 mm` deep fan tray bolted at `Y = ±50 mm` to each end
   frame.

---

## Part List (PETG at 1.27 g/cm³)

| Part | Description | Print Pose | Footprint (mm) | With 8 mm Brim | Volume (cm³) | Mass (g) | Bed |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `01_left_end_frame` | Left A-frame end cheek | Outer flat face down | `228.0 × 201.4 × 18.5` | `244.0 × 217.4` | `212.64` | `270.06` | PASS |
| `02_right_end_frame` | Right A-frame end cheek | Outer flat face down | `228.0 × 201.4 × 18.5` | `244.0 × 217.4` | `212.64` | `270.06` | PASS |
| `03_left_fan_tray` | Left 140 mm fan tray half | Bottom deck flat down | `172.4 × 149.0 × 14.0` | `188.4 × 165.0` | `84.75` | `107.63` | PASS |
| `04_right_fan_tray` | Right 140 mm fan tray half | Bottom deck flat down | `172.4 × 149.0 × 14.0` | `188.4 × 165.0` | `84.75` | `107.63` | PASS |
| **TOTAL** | **4 printed parts** | **4 P1S plates** | — | **all ≤ 256 × 256** | **`594.79`** | **`755.38`** | **PASS** |

---

## Hardware List

* **6×** M4 × 12 mm socket-head cap screws (4× end-frame-to-tray, 2× center tray seam)
* **4×** M4 heat-set brass inserts (`Ø5.6 mm` pilot holes in the outer ends of the two fan trays)
* **2×** M4 hex nuts (or locknuts) for the center tray seam at `X = 0`
* **8×** M4 × 30 mm fan mounting screws + **8×** M4 nuts (4 per `140 × 140 × 25 mm` fan)
* *Optional:* **4×** stick-on silicone rubber bumpons under the end-frame feet

---

## Print Notes (Bambu P1S, PETG)

* **Material:** PETG, `0.4 mm` nozzle, `0.20 mm` layers, `4–6` walls, `25–40%` gyroid infill (or `100%` if maximum rigidity is preferred; masses above assume solid `1.27 g/cm³`).
* **Supports:** **None required.** All four parts print flat in their exported `work/export/*.stl` orientations.
* **Adhesion:** `8 mm` outer brim enabled; every part + brim fits inside `256 × 256 mm` with zero rotation required.

---

## 10-Minute Assembly

1. Press the **4× M4 heat-set inserts** into the outer `Ø5.6 mm` end bosses of `03_left_fan_tray` and `04_right_fan_tray`.
2. Bolt `03_left_fan_tray` and `04_right_fan_tray` together at the center flange (`X = 0`) using **2× M4×12 screws + 2× M4 nuts**.
3. Drop both `140 × 140 × 25 mm` fans onto the tray deck (airflow arrow pointing **UP**), routing their wires out the open under-tray arch, and fasten with **8× M4×30 screws + 8× M4 nuts**.
4. Bolt `01_left_end_frame` and `02_right_end_frame` onto the ends of the tray assembly using **4× M4×12 screws** from the outside into the heat-set inserts.
5. Slide both Dell Precision 5560s into the `14°` cradles, hinges up, undersides facing inward.

---

## Reproduce & Verify

```sh
# Rebuild TwoBanger.FCStd, STEP/STL exports, and page/models/ STLs
flatpak run --command=freecadcmd org.freecad.FreeCAD "$PWD"/two-banger/work/build_rack.py

# Run FreeCAD B-rep validity, bed-fit (with 8 mm brim), and 0.0 mm3 interference checks
flatpak run --command=freecadcmd org.freecad.FreeCAD "$PWD"/two-banger/work/check_rack.py
```

Check results are saved in `work/check_output.txt` and `work/check_results.json`.
