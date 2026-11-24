# Tight Wall-Mount Stacked Two-Banger 5560 Rack

**Status:** CAD and automated fit checks only; no part has been printed or test-fitted. [3D viewer and downloads](https://thereprocase.github.io/dell-5560-wall-mount/two-banger/wall/).

Tight-to-the-wall stacked edition: both Dell Precision 5560s sit in the **same
orientation** (undersides facing the `Y = 0` wall, hinges up), tilted `10°`
forward and stacked vertically at a **`212.0 mm` pitch** (tucked `15 mm` below
Tier 1's hinge so Tier 1's hot exhaust vents outboard), fed from below by two
`140 × 140 × 25 mm` fans angled at `50°`.

---

## Layout Choice & Why

Leaning both laptops `10°` forward from a `35.0 mm` base wall gap keeps the
rack within **`108 mm`** of the wall (`127 mm` at the bottom fan corner)
while giving Tier 1 a `40.0 mm` horizontal step and `23.2 mm` vertical gap to
slide out below Tier 2. Full-height `18 mm` outer cheeks and `26 mm` gusseted
inboard seats capture both laptops laterally, while splitting each side arm at
`Z = 133.0 mm` into Lower (`Z = -105..133`) and Upper (`Z = 133..371`) Arms keeps
all plates inside the Bambu P1S `256 × 256 × 256 mm` bed with an `8 mm` brim.
Four `1.0 mm` flush 2-color inlay bodies with `1 × 1 mm` `45°` V-grooves print
flat on the arm bed faces with zero bridging. The two `12 mm` solid fan-plate
halves glue at `X = 0` into one rigid fan plate and bolt from the outside of
the lower wall panels via M4 heat-set inserts in the plate ends.

**Airflow split:** Both `140 mm` fans sit side-by-side at `55°` centered on
the `344.4 mm` laptop width, blowing symmetrically up the enclosed wall plenum
behind both stacked laptops.

---

## Part List (PETG at 1.27 g/cm³)

| Part | Description | Print Pose | Footprint (mm) | With 8 mm Brim | Volume (cm³) | Mass (g) | Bed |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `01_left_lower_arm` | Left lower wall arm (`Z = -105..133`) | Outer flat face down | `238.0 × 107.9 × 34.1` | `254.0 × 123.9` | `179.36` | `227.78` | PASS |
| `02_right_lower_arm` | Right lower wall arm (`Z = -105..133`) | Outer flat face down | `238.0 × 107.9 × 34.1` | `254.0 × 123.9` | `179.36` | `227.78` | PASS |
| `03_left_upper_arm` | Left upper stacking arm (`Z = 133..371`) | Outer flat face down | `238.0 × 88.2 × 34.1` | `254.0 × 104.2` | `197.68` | `251.05` | PASS |
| `04_right_upper_arm` | Right upper stacking arm (`Z = 133..371`) | Outer flat face down | `238.0 × 88.2 × 34.1` | `254.0 × 104.2` | `197.68` | `251.05` | PASS |
| `05_left_fan_tray` | Left 50° solid 12 mm fan plate half | Fan plate flat down | `172.4 × 149.0 × 12.0` | `188.4 × 165.0` | `142.98` | `181.58` | PASS |
| `06_right_fan_tray` | Right 50° solid 12 mm fan plate half | Fan plate flat down | `172.4 × 149.0 × 12.0` | `188.4 × 165.0` | `142.98` | `181.58` | PASS |
| `07_left_lower_inlay` | Left lower 2-color bed-face inlay | Outer flat face down | `104.0 × 33.5 × 1.0` | `120.0 × 49.5` | `2.57` | `3.27` | PASS |
| `08_right_lower_inlay` | Right lower 2-color bed-face inlay | Outer flat face down | `104.0 × 33.5 × 1.0` | `120.0 × 49.5` | `2.57` | `3.27` | PASS |
| `09_left_upper_inlay` | Left upper 2-color bed-face inlay | Outer flat face down | `130.0 × 38.0 × 1.0` | `146.0 × 54.0` | `3.51` | `4.46` | PASS |
| `10_right_upper_inlay` | Right upper 2-color bed-face inlay | Outer flat face down | `130.0 × 38.0 × 1.0` | `146.0 × 54.0` | `3.51` | `4.46` | PASS |
| **TOTAL** | **10 bodies** | **6 P1S plates** | — | **all ≤ 256 × 256** | **`1052.20`** | **`1336.29`** | **PASS** |

---

## Hardware List

* **8×** `1/4-in` or `M6` wall anchors / lag bolts with washers (`Ø7.2 mm` bores at `X = ±168.7 mm`, `Z = -28, 114, 240, 356 mm`; `337.4 mm` horizontal spacing—use a plywood backer board across 16-in studs or rated hollow-wall toggles)
* **12×** `M4` heat-set brass inserts (`Ø5.6 mm` pilot holes: 8× in solid fan plate at `124.5 mm` fan pitch, 4× in the outer ends of the solid fan plate)
* **4×** `M4 × 12 mm` socket-head cap screws driven from the outside of the lower wall panels through flush `Ø8.0 mm` counterbores into the fan-plate end inserts (zero loose nuts)
* **8×** `M4 × 30 mm` fan mounting screws (4 per `140 × 140 × 25 mm` fan into solid-plate M4 heat-set inserts)

---

## Reproduce & Verify

```sh
flatpak run --command=freecadcmd org.freecad.FreeCAD "$PWD"/two-banger/wall/work/build_wall_rack.py
flatpak run --command=freecadcmd org.freecad.FreeCAD "$PWD"/two-banger/wall/work/check_wall_rack.py
```

Check results are saved in `wall/work/check_output.txt` and `wall/work/check_results.json`.
