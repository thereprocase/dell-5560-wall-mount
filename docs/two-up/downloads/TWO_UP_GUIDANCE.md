# Design Guidance Memo: Two-Laptop Stacked Variant (Precision 5560)

## 1. Verdict Up Front

**Verdict: Build the two-up variant on top of the Minimalist M1.1 part family with bolted cheek shrouds
and an inter-stage splitter dam, rather than starting a fresh Rev H-style ducted part family.**

M1.1’s open-frame arms, indexed 12.0 mm ladder (`dell-5560-wall-mount/minimalist/build.py:61`), and two-rung key
hardware (`dell-5560-wall-mount/minimalist/build.py:45-50`) already solve the Bambu P1S 256 × 256 × 256 mm bed limit
and print at 400.55 g in 15 h 42 m 30 s—66.2% less estimated filament than the full Rev H ducted set
(`dell-5560-wall-mount/README.md:59-61`). However, an unshrouded M1.1 frame cannot maintain a "shared pressurised
plenum" across a two-laptop stack because its sides and inter-stage gap are open
(`dell-5560-wall-mount/Airflow_Design_Decision.md:20-21`). Conversely, scaling Rev H’s monolithic ducts
(`174.5 × 131.7 × 109.6 mm`, `dell-5560-wall-mount/print_release/manifest.json:43-45`) to a two-up tilted stack
creates compound-angle loft splits and roughly triples filament mass. The practical engineering path is to
reuse M1.1’s side-printed arms (`dell-5560-wall-mount/minimalist/build.py:33,68`), 40.0 mm rear gap
(`dell-5560-wall-mount/minimalist/build.py:29`), and fan cradles (`dell-5560-wall-mount/minimalist/build.py:51-57`), while
adding flat-printed 1.6 mm side-cheek plates and a dual-outlet splitter dam
(`dell-5560-wall-mount/minimalist/build.py:64`) to close the plenum chamber.

---

## 2. Geometry Budget (15° Tilt vs. Upright Baseline)

All calculations derive from the ground-truth case envelope in `dell-5560-wall-mount/minimalist/build.py:26-31`:
width $W = 344.4\text{ mm}$, depth $D = 230.3\text{ mm}$, thickness $T = 20.0\text{ mm}$, wall gap
$G = 40.0\text{ mm}$, compliant pads $p = 2.0\text{ mm}$, and front retaining tine
$H_{\text{tine}} = 40.0\text{ mm}$ (`dell-5560-wall-mount/minimalist/build.py:36`, vs. 94.0 mm on Rev F/H in
`dell-5560-wall-mount/README.md:183`). For the 5560, `armHeight` resolves to
$\min(\max(230.3 - 22.0 + 2.0, 186.0), 220.0) = \mathbf{210.3\text{ mm}}$
(`dell-5560-wall-mount/minimalist/build.py:68`), and the full upright M1.1 arm spans $Z = -74.0\text{ mm}$ to
$+210.3\text{ mm}$, or **284.3 mm** total vertical height (`dell-5560-wall-mount/minimalist/build.py:500-504`).
Using $\sin 15^\circ = 0.2588$ and $\cos 15^\circ = 0.9659$:

* **Single tilted case vertical height (`ESTIMATE`):**
  $D \cos 15^\circ + T \sin 15^\circ = 230.3(0.9659) + 20.0(0.2588) = 222.45 + 5.18 = 227.6\text{ mm}$.
* **Single tilted case horizontal projection (`ESTIMATE`):**
  $D \sin 15^\circ + T \cos 15^\circ = 230.3(0.2588) + 20.0(0.9659) = 59.60 + 19.32 = 78.9\text{ mm}$.
* **Removal clearance along 15° axis (`ESTIMATE`):**
  Lifting past the 40.0 mm M1.1 front tine (`dell-5560-wall-mount/minimalist/build.py:36`) plus 10.0 mm finger/cable
  margin requires $50.0\text{ mm}$ travel ($\Delta Z = 50 \cos 15^\circ = 48.3\text{ mm}$,
  $\Delta Y = 50 \sin 15^\circ = 12.9\text{ mm}$). Because the upper laptop is shunted parallel to the
  lower laptop, the lower laptop extracts forward-and-up through the inter-tier gap with a **260.0 mm
  vertical pitch** (leaving $260.0 - 222.5 = 37.5\text{ mm}$ vertical clearance above the rear hinge).

| Metric | Single Upright (M1.1 Baseline) | Two-Up 15° Shingling Stack (`ESTIMATE`) | Two-Up 15° Non-Overlapping Stack (`ESTIMATE`) | Source / Arithmetic |
| :--- | :--- | :--- | :--- | :--- |
| **Case Width ($X$)** | 344.4 mm | 344.4 mm | 344.4 mm | `dell-5560-wall-mount/minimalist/build.py:26` |
| **Total Assembly Width ($X$)** | 376.4 mm (`ESTIMATE`) | 376.4 mm | 376.4 mm | $2 \times (\text{armOriginX } 176.2 + \text{armThickness } 12.0) = 376.4\text{ mm}$ (`dell-5560-wall-mount/minimalist/build.py:31,33,34,69`) |
| **Arm / Stack Vertical Pitch ($\Delta Z$)** | 210.3 mm (`armHeight`) | 260.0 mm | 276.0 mm | Upright: `dell-5560-wall-mount/minimalist/build.py:68`. 15°: $222.5 + 37.5\text{ mm}$ (shingled) or $227.6 + 48.3\text{ mm}$ (non-overlapped) |
| **Two-Case Vertical Span** | 230.3 mm (1 unit) | 487.6 mm | 503.6 mm | Pitch $+ 227.6\text{ mm}$ upper case height |
| **Total Assembly Height ($Z$)** | 354.3 mm (`ESTIMATE`) | 609.9 mm | 625.9 mm | Fan bottom $Z = -74.0\text{ mm}$ (`dell-5560-wall-mount/minimalist/build.py:500`) + case span + lift ($50.0\text{ mm}$ upright or $48.3\text{ mm}$ at 15°) |
| **Depth Off Wall ($Y$)** | 68.0 mm | 126.9 mm | 126.9 mm | Upright: $40 + 20 + 2 + 6 = 68\text{ mm}$ (`dell-5560-wall-mount/minimalist/build.py:28-30,35,71`). 15°: $40 + 78.9 + 2.0 + 6.0\text{ mm}$ |
| **Plenum Depth ($Y$, wall to case)** | 40.0 mm constant | 40.0 mm (base) to 99.6 mm (hinge) | 40.0 mm (base) to 99.6 mm (hinge) | Base: $40.0\text{ mm}$ (`dell-5560-wall-mount/minimalist/build.py:29`); Hinge: $40.0 + 230.3 \sin 15^\circ = 99.6\text{ mm}$ |
| **Plenum Cross-Section Area** | $13,936\text{ mm}^2$ (`ESTIMATE`) | $13,936\text{ mm}^2$ (inlet) to $34,699\text{ mm}^2$ (top) | $13,936\text{ mm}^2$ (inlet) to $34,699\text{ mm}^2$ (top) | Span between arms $348.4\text{ mm}$ (`dell-5560-wall-mount/minimalist/build.py:69`) $\times Y_{\text{gap}}$ |

**Wall-run fit check:** A $2 \times 230.3\text{ mm}$ tilted stack (**609.9 mm** total height including lower
fans and top extraction clearance) **fits on a standard open wall run** above a desk or in an equipment
closet. **Where it does not fit:** standard 450–600 mm vertical backsplashes between a desktop and upper
wall cabinets, beneath low shelves, or behind doors where a **126.9 mm** projection off the wall (vs.
68.0 mm upright) creates a strike hazard.

---

## 3. Plenum Strategy: Shared Chamber vs. Split Manifold

| Criterion | Option A: One Shared Plenum Chamber Behind Both Cradles | Option B: Two Independent Ducts Fed From One Lower Manifold |
| :--- | :--- | :--- |
| **Static Pressure Distribution** | Expanding wedge ($40.0\text{ mm}$ to $99.6\text{ mm}$ depth) decelerates upward flow and recovers static pressure toward the upper tier, when an internal baffle steps the chamber back to 40.0 mm above the Tier 1 hinge. | Equalized only if branch lengths and bends match; upper duct branch is ~260 mm longer (`ESTIMATE`), adding friction and turning losses that starve the upper laptop. |
| **Split-Joint Leakage** | Moderate perimeter length across 4 vertical arm/shroud splits, 2 dam seams (`0.6 mm` center seam, `dell-5560-wall-mount/minimalist/build.py:66`), and two tilted laptop perimeters. | Lower perimeter at the laptop interface if shrouds seal tightly, but doubles internal duct wall area and requires sealed slip-joints across the P1S bed split plane. |
| **One Laptop Absent or Idle** | **Critical vulnerability:** An empty cradle exposes a $344.4 \times 230.3\text{ mm}$ opening (`dell-5560-wall-mount/minimalist/build.py:26-27`), dumping >80% of plenum static pressure (`ESTIMATE`) and starving the active laptop. If both laptops are present and one is idle, the plenum pressurizes both undersides (`dell-5560-wall-mount/Airflow_Design_Decision.md:8-11`), providing passive bypass cooling without harm. | An empty upper or lower cradle still dumps its branch unless fitted with a manual shutoff damper at the manifold wye; idle-but-present behavior is identical to Option A. |
| **Print Mass & Complexity** | Low: uses flat side shrouds and two-piece angled dams on M1.1 arms. | High: requires multi-plate 3D tubular ducts exceeding Rev H’s ~1,185 g (`ESTIMATE` from `dell-5560-wall-mount/README.md:59-61`). |

**Recommendation:** Choose **Option A (Shared Plenum Chamber)** built by enclosing the rear and sides of the
M1.1 arm stack with flat cheek panels and an internal stepped baffle (resetting the rear gap from 99.6 mm at
Tier 1's top outlet slot back to 40.0 mm at Tier 2's base), paired with a snap-in **blanking cover** for
single-laptop operation.

**Falsification Measurement:** Measure static pressure ($\Delta P$ in Pa) at the Tier 1 and Tier 2 intake
window zones ($X = \pm 111\text{ mm}$, $Z \approx 151\text{–}191\text{ mm}$ along each base,
`dell-5560-wall-mount/Airflow_Design_Decision.md:8-9`) with both laptops installed. **Option A is falsified if**
upper-vs-lower intake static pressure differs by more than **35%** (`ESTIMATE`) or if whichever tier reads
lower fails to reach **+5 Pa** gauge (compared against the 2D RANS reference of 15.43–18.80 Pa at 20 Pa
supply in `dell-5560-wall-mount/README.md:253-260`) after adjusting the Tier 1 outlet slot width between 8 mm and
16 mm (`dell-5560-wall-mount/Airflow_Design_Decision.md:5-6`).

---

## 4. Print-Bed Partition (Bambu P1S: 256 × 256 × 256 mm)

In M1.1, `armHeight` is capped at **220.0 mm** and resolves to **210.3 mm** for the 5560
(`=min(max(laptopDepth - 22 mm + padThickness; 186 mm); 220 mm)`, `dell-5560-wall-mount/minimalist/build.py:68`),
yielding a **284.3 mm** total Z span ($Z = -74.0\text{ mm}$ to $210.3\text{ mm}$,
`dell-5560-wall-mount/minimalist/build.py:500-504`) that fits diagonally on the 256 × 256 mm P1S bed with an 8 mm
brim (`dell-5560-wall-mount/minimalist/reports/release.json:15`). A two-up arm spanning **544.3 mm** vertically
($Z = -74.0\text{ mm}$ to $470.3\text{ mm}$ at a 260.0 mm stack pitch) must split into two stages.

**Proposed Partition (reusing M1.1 vocabulary):**
1. **Lower Arms (Plates 01–02):** Retain M1.1 lower fan hanger geometry ($Z = -74.0\text{ mm}$ to $0\text{ mm}$,
   `dell-5560-wall-mount/minimalist/build.py:500`), tilt the cradle seat 15° forward ($Y_{\text{top}} = 126.9\text{ mm}$),
   and cap the upper split plane at **$Z = 160.0\text{ mm}$**. This produces a **234.0 mm** vertical part
   length that fits orthogonally on the 256 mm bed with an 8 mm brim on both ends
   ($234.0 + 16.0 = \mathbf{250.0\text{ mm}}$). Include two upper splice key slots at $Z = 130.0\text{ mm}$
   and $154.0\text{ mm}$ (24.0 mm pitch, `dell-5560-wall-mount/minimalist/build.py:61,73`).
2. **Upper Stacking Arms (Plates 09–10):** Span $Z = 160.0\text{ mm}$ to $395.0\text{ mm}$ (**235.0 mm**
   part length + 16.0 mm brim = **251.0 mm** $\times$ **126.9 mm** depth; fits orthogonally inside
   $256 \times 256\text{ mm}$). Mates to the Lower Arm via a double-rung splice key and carries its own two
   reinforced wall pads (`wallPadHeight = 32.0 mm`, `dell-5560-wall-mount/minimalist/build.py:39`).
3. **Fans & Caps (Plates 03–06):** Reuse M1.1 `03/04_fan_cage` and `05/06_fan_cap` unchanged
   (`dell-5560-wall-mount/minimalist/reports/release.json:65-119`).
4. **Tier 1 Inter-Stage Splitter Dams (Plates 07–08) & Tier 2 Upper Dams (Plates 11–12):** Split along $X$
   with a 0.6 mm center seam (`dell-5560-wall-mount/minimalist/build.py:66`), each half $173.9\text{ mm}$ wide
   (`dell-5560-wall-mount/minimalist/build.py:390-392`). Tier 1 dam contracts the lower gap to a 12.0 mm exhaust slot
   (`dell-5560-wall-mount/minimalist/build.py:65`) while its rear face channels bypass air into Tier 2’s 40.0 mm gap.
5. **Side Plenum Cheek Panels (Plate 13, L+R nested):** Flat 2.4 mm skins ($210.3 \times 75.0\text{ mm}$
   mean wedge `ESTIMATE`) clipping into the arm lightening windows
   (`dell-5560-wall-mount/minimalist/build.py:506-518`).
6. **Expanded All-Hardware Plate (Plate 14):** Doubles the dam keys/keepers and adds 4 splice keys/keepers
   (24 small parts on one plate).

| Component Group | M1.1 Baseline Plates | Two-Up Variant Plates (`ESTIMATE`) | M1.1 Mass (g) | Two-Up Mass (`ESTIMATE` g) | M1.1 Time (h:m:s) | Two-Up Time (`ESTIMATE` h:m) | Source / Scaling Arithmetic (vs. $210.3\text{ mm}$ `armHeight`) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Lower Arms (L+R)** | 2 (`01–02`) | 2 | 239.48 g | 282.6 g | 7:05:35 | 8:22 | `release.json:36-62` ($239.48\text{ g}$, $25,535\text{ s}$) $\times \frac{234.0}{284.3}\text{ Z-span} \times 1.43\text{ wedge width} = 1.18\times$ |
| **Upper Arms (L+R)** | 0 | 2 | 0 g | 285.0 g | 0:00:00 | 8:26 | `ESTIMATE`: $239.48\text{ g} \times \frac{235.0}{284.3}\text{ Z-span} \times 1.44\text{ wedge width} = 1.19\times$ |
| **Fan Cages & Caps** | 4 (`03–06`) | 4 | 115.64 g | 115.64 g | 4:57:43 | 4:58 | Unchanged (`release.json:65-119`: $2 \times 51.29 + 2 \times 6.53\text{ g}$, $17,863\text{ s}$) |
| **Airflow Dams** | 2 (`07–08`) | 4 (Tier 1 + Tier 2) | 31.34 g | 81.5 g | 2:38:18 | 6:52 | `release.json:121-147` ($31.34\text{ g}$, $9,498\text{ s}$) $\times 2.6\times$ for 15° span + splitter |
| **Side Cheek Panels** | 0 | 1 (4 panels nested) | 0 g | 66.2 g | 0:00:00 | 2:06 | `ESTIMATE`: $4 \times (210.3 \times 75.0 \times 2.0\text{ mm net}) \times 1.05\text{ g/cm}^3 \times 0.5\text{ window factor}$ |
| **Hardware Plate** | 1 (`21`) | 1 (24 pcs) | 14.09 g | 28.18 g | 1:00:54 | 1:55 | `release.json:149-161` ($14.09\text{ g}$, $3,654\text{ s}$) $\times 2.0\times$ |
| **Total Set** | **9 plates** | **14 plates** | **400.55 g** | **859.1 g** | **15:42:30** | **32:39** | **Delta: +5 plates, +458.6 g (+114.5%), +16 h 56 m (+107.8%) (`ESTIMATE`)** |

---

## 5. Strength: Anchors, Critical Joint, and First Failure Mode

* **Load Demand (`ESTIMATE`):** M1.1’s section review assumes a 3.0 kg case at $2g$
  (`dell-5560-wall-mount/minimalist/README.md:148`, or $29.4\text{ N}$ static $\times 2 = 58.8\text{ N}$ per laptop).
  Two laptops double vertical shear to **117.7 N** ($2g$). At a 15° tilt, the center of mass shifts outward
  from $Y = 50.0\text{ mm}$ (`40 mm gap + 10 mm half-thickness`) to:
  $$Y_{\text{CG}} = 40.0 + \frac{230.3}{2}\sin 15^\circ + \frac{20.0}{2}\cos 15^\circ = 40.0 + 29.8 + 9.7 = \mathbf{79.5\text{ mm}}\text{ (`ESTIMATE`)}$$
  Combined with 2x mass, total wall overturning moment increases by
  $2 \times (79.5 / 50.0) = \mathbf{3.18\times}$ (`ESTIMATE`: from $2.94\text{ N}\cdot\text{m}$ to
  $9.35\text{ N}\cdot\text{m}$ at $2g$).
* **Wall Anchor Count and Spacing:** For the 5560 (`armHeight = 210.3 mm`,
  `dell-5560-wall-mount/minimalist/build.py:68`), M1.1 places wall bolts at $z_1 = 18.0\text{ mm}$ and
  $z_2 = h - 16.0 = \mathbf{194.3\text{ mm}}$, giving **176.3 mm** vertical bolt spacing
  (`dell-5560-wall-mount/minimalist/build.py:521,548`). Use **8 wall anchors total (4 per side: 2 on each Lower Arm,
  2 on each Upper Arm)** through the Ø7.2 mm clearance bores (`wallBoltDiameter = 7.2 mm`,
  `dell-5560-wall-mount/minimalist/build.py:37`):
  * **Single-arm upright pull-out reaction (`ESTIMATE`):** At 176.3 mm bolt spacing, one 3.0 kg laptop at
    $2g$ ($M = 58.8\text{ N} \times 0.050\text{ m} = 2.94\text{ N}\cdot\text{m}$ total, or
    $1.47\text{ N}\cdot\text{m}$ per arm) produces
    $1.47\text{ N}\cdot\text{m} / 0.1763\text{ m} = \mathbf{8.3\text{ N}}$ pull-out per upper bolt.
  * **Two-up segmented-arm pull-out reaction (`ESTIMATE`):** On the 234.0 mm Lower Arm
    ($Z = -74\text{ to }160\text{ mm}$) and 235.0 mm Upper Arm ($Z = 160\text{ to }395\text{ mm}$), placing
    pads at $z_{\text{low}} = 18.0\text{ mm}$ and $z_{\text{high}} = 144.0\text{ mm}$ (local to each cradle)
    gives **126.0 mm** intra-arm bolt spacing and **386.0 mm** total span from bottom bolt
    ($Z = 18.0\text{ mm}$) to top bolt ($Z = 260.0 + 144.0 = 404.0\text{ mm}$). With each arm segment
    carrying its own laptop at $Y_{\text{CG}} = 79.5\text{ mm}$
    ($M_{\text{arm}} = 29.4\text{ N} \times 0.0795\text{ m} = 2.34\text{ N}\cdot\text{m}$ at $2g$), upper
    bolt pull-out per segment is $2.34\text{ N}\cdot\text{m} / 0.126\text{ m} = \mathbf{18.6\text{ N}}$
    (`ESTIMATE`). If spliced rigidly across the full 386.0 mm bolt span, top-bolt pull-out drops to
    $4.68\text{ N}\cdot\text{m} / 0.386\text{ m} = \mathbf{12.1\text{ N}}$ (`ESTIMATE`).
  * **Horizontal spacing:** Governed by laptop width at
    $2 \times (\text{armOriginX } 176.2 - 18.0) = \mathbf{316.4\text{ mm}}$
    (`dell-5560-wall-mount/minimalist/build.py:69,549`), which misses 406.4 mm (16 in) wood studs—mount a plywood
    backer board across studs first.
* **The One Joint That Actually Matters:** The **wall-pad-to-arm transition** at `print_height = 12.02 mm`
  (just above the 12.0 mm main arm thickness,
  `dell-5560-wall-mount/minimalist/reports/wall-transition-review.json:4,13`). Because the arm prints flat on its
  outer side (`dell-5560-wall-mount/README.md:81`), outward pull or lateral torque loads the transition between the
  12.0 mm arm web and the 30.0 mm-wide wall pad (`dell-5560-wall-mount/minimalist/build.py:522-525`) in **interlayer
  (Z-axis) tension and peel**. M1.1’s 32.0 mm pad height and paired 6.0 mm tapered gusset webs
  (`dell-5560-wall-mount/minimalist/build.py:39-41`) increase this section from $192.0\text{ mm}^2$ to
  $415.8\text{ mm}^2$ (`dell-5560-wall-mount/minimalist/reports/wall-transition-review.json:14,45`). Keep this exact
  M1.1 gusset on all 8 pads; scaling the 1.11–1.24 MPa upright baseline
  (`dell-5560-wall-mount/minimalist/README.md:150`) by the $18.6\text{ N} / 8.3\text{ N} = 2.24\times$ segmented
  moment ratio puts peak nominal pad stress at $\mathbf{2.49\text{–}2.78\text{ MPa}}$ (`ESTIMATE`).
* **The One Detail That Will Fail First:** **Long-term warm ASA creep and outward deflection of the
  15°-tilted lower retaining shelf and front tine** (`frontLip = 6.0 mm`, `tineHeight = 40.0 mm`,
  `dell-5560-wall-mount/minimalist/build.py:35-36`). Under a 15° tilt, $\sin 15^\circ = 25.9\%$ of the laptop's
  weight ($7.6\text{ N}$ static) pushes continuously against the front tine in warm exhaust air
  (`dell-5560-wall-mount/minimalist/README.md:154`). Widen `frontLip` from **6.0 mm to 10.0 mm** (`ESTIMATE`).

### What Would Make This Fail (3 Concrete Failure Modes & Revealing Measurements)

1. **Thermal Cascade Into Tier 2 Intake (Airflow Failure):** Hot exhaust exiting Tier 1’s hinge at
   $Z = 232\text{ mm}$ (`dell-5560-wall-mount/Airflow_Design_Decision.md:5`) gets entrained into Tier 2’s rear plenum
   wedge instead of ejecting into the room.
   * *Revealing Measurement:* Place a thermocouple at Tier 2’s intake window zone ($X = \pm 111\text{ mm}$,
     $Z = 170\text{ mm}$, `dell-5560-wall-mount/Airflow_Design_Decision.md:8-9`) with Tier 1 at 100% CPU+GPU load.
     If Tier 2 intake air temperature rises **$> 4.0^\circ\text{C}$ above ambient room air** (`ESTIMATE`),
     the inter-stage splitter dam is leaking exhaust into the upper supply.
2. **Lower-Tier Plenum Dumping / Upper-Tier Starvation (Fluidic Failure):** The expanding 15° wedge
   ($40.0\text{ mm}$ to $99.6\text{ mm}$) dumps supply air through Tier 1’s side gaps and 12.0 mm top slot,
   leaving zero static pressure for Tier 2.
   * *Revealing Measurement:* Differential manometer across the Tier 2 base cover intake grille with fans at
     100% PWM. If gauge static pressure at Tier 2 reads **$< +3.0\text{ Pa}$** (`ESTIMATE`, vs. 17.67 Pa
     modeled for a 12 mm slot in `dell-5560-wall-mount/README.md:258`), the shared chamber lacks sufficient flow
     restriction at Tier 1 and requires a mid-tier fan pair.
3. **Warm ASA Creep at the Front Retaining Tine or Upper Wall Pad Peel (Mechanical Failure):** Continuous
   outward thrust ($7.6\text{ N}$ static wedge force at 15°) or upper-pad peel ($18.6\text{ N}$ at $2g$)
   causes progressive plastic deformation or layer splitting at `print_height = 12.02 mm`.
   * *Revealing Measurement:* Dial indicator or calipers measuring front-tine-to-wall distance ($Y$) and
     feeler gauge checking the `12.02 mm` pad-to-arm layer seam under a **6.0 kg dead-load test ($2\times$
     nominal mass) at $45^\circ\text{C}$ for 24 hours**. Permanent set **$> 1.5\text{ mm}$** at the tine tip
     or any visible white craze line at the pad root fails the qualification.

---

## 6. Airflow Honesty and Minimum Bench Test

**What Is Unknown (per repository limits in `dell-5560-wall-mount/README.md:265,335-338` and
`dell-5560-wall-mount/Airflow_Design_Decision.md:13-21`):**
1. **Internal laptop flow resistance and fan curve:** The Dell 5560’s internal blowers and heatsink fin
   impedance are unmeasured; the 2D OpenFOAM study prescribed a $0.4\text{ m/s}$ intake velocity
   (`dell-5560-wall-mount/README.md:253,265`).
2. **Supply fan operating point:** The 2D CFD assumed a flat $20\text{ Pa}$ total inlet pressure
   (`dell-5560-wall-mount/README.md:253`), and the 3D trial used uncalibrated constant-force assumptions
   (`dell-5560-wall-mount/README.md:336`). Actual P-Q delivery of two 120 × 120 × 27 mm fans
   (`dell-5560-wall-mount/minimalist/build.py:52-53`) into a leaky wall gap is unmeasured.
3. **Plenum leakage and thermal plume carryover:** Side leakage past noncontact cheeks
   (`dell-5560-wall-mount/Airflow_Design_Decision.md:20-21`) and pre-heating of Tier 2’s intake air by Tier 1’s hinge
   exhaust (`Z = 232 mm`, `dell-5560-wall-mount/Airflow_Design_Decision.md:5`) have zero physical or converged CFD
   data (`dell-5560-wall-mount/README.md:39-40,335-338`).

**Minimum Bench Test to Settle Shared-Plenum Viability:**
Before modeling or printing a two-up mount, clamp two Precision 5560s (or one 5560 and one
$344.4 \times 230.3 \times 20.0\text{ mm}$ cardboard dummy with two $70 \times 40\text{ mm}$ cutouts at
$X = \pm 111\text{ mm}, Z = 151\text{–}191\text{ mm}$ per `dell-5560-wall-mount/Airflow_Design_Decision.md:8-9`) at a
15° tilt against a flat board using foamboard side cheeks and the two 120 mm fans at the bottom. Run a
20-minute CPU+GPU stress load comparing **(1) open tilted stack** vs. **(2) shrouded shared plenum with a
cardboard inter-stage baffle**. Log Dell EC thermistors and fan RPM. If the shrouded shared plenum does not
reduce steady-state CPU/GPU temperatures by **$\ge 3^\circ\text{C}$** or fan speed by **$\ge 300\text{ RPM}$**
(`ESTIMATE`) on **both** tiers, drop the shared plenum shrouds and build a pure open mechanical two-up rack.

---

## 7. Build Order

1. **Run the foamboard bench test (Section 6)** on a physical Precision 5560 to verify that 15°
   shared-plenum airflow does not feed Tier 1 hinge exhaust into Tier 2’s intake.
2. **Print the M1.1 fit coupon (`coupons/00_fit_coupon_plate`, `dell-5560-wall-mount/minimalist/README.md:62-63`)** in
   your target ASA spool to qualify the `0.30 mm` key clearance and `0.20 mm` split-crown interference
   (`dell-5560-wall-mount/minimalist/build.py:43,50`).
3. **Model only the Right Lower Tilted Arm ($234.0\text{ mm}$), Right Upper Tilted Arm ($235.0\text{ mm}$),
   and Arm-Splice Key** in FreeCAD (`dell-5560-wall-mount/minimalist/build.py`).
4. **Print a cropped 80 mm-tall coupon of the Lower-to-Upper Arm splice and 15° cradle hook** (1 plate,
   ~45 g `ESTIMATE`) to verify the 15° laptop insertion/removal path and splice rigidity.
5. **Print ONE side of the stack first** (`02_right_lower_arm`, `10_right_upper_arm`, `04_right_fan_cage`,
   `08_right_dam`) and test-fit on the wall with one laptop to measure hinge lift clearance, bolt tool
   access along the 15° angle, and tine deflection.
6. **Model and print the Left side, Tier 2 dams, and cheek panels** only after the single-side wall trial
   confirms the 260.0 mm vertical pitch and anchor alignment.

---

## 8. Open Questions for the Owner

1. **Single-laptop operation:** Will the mount frequently run with only one laptop installed?
   * *Default answer:* **No (both laptops normally docked).** If yes, add a printed snap-in blanking panel
     over the empty cradle so the open bay does not dump plenum pressure.
2. **Fan count and noise ceiling:** Do you want to keep M1.1’s **two** bottom 120 mm fans
   (`dell-5560-wall-mount/minimalist/build.py:51-53`) for the whole stack, or add a second pair at the mid-tier step?
   * *Default answer:* **Keep two 120 mm fans at the bottom first** and rely on the inter-stage contraction
     dam (`12.0 mm` outlet gap, `dell-5560-wall-mount/minimalist/build.py:65`), leaving ladder slots on the upper arms
     for a second fan pair if Tier 2 runs warm.
3. **Wall mounting substrate:** Are you bolting into drywall, masonry, or a wood backer board?
   * *Default answer:* **Mount a 12–18 mm plywood backer board across two wall studs first, then lag-screw
     all 8 arm pads (`wallBoltDiameter = 7.2 mm`, `dell-5560-wall-mount/minimalist/build.py:37`) into the plywood**,
     since the 316.4 mm horizontal bolt spacing (`dell-5560-wall-mount/minimalist/build.py:69,549`) misses 16-inch studs.
4. **Tilt angle vs. protrusion trade-off:** Is the **126.9 mm** wall protrusion at 15° acceptable, or would
   you prefer a **10° tilt** (`ESTIMATE`: reduces depth off wall to **107.7 mm**; see Appendix)?
   * *Default answer:* **Proceed with 15° (126.9 mm depth)** as requested, since it provides a 37.5 mm
     vertical clearance step at a 260.0 mm stack pitch for easy one-handed laptop extraction.
5. **Side port and cable clearance:** Which side ports stay plugged in while wall-mounted?
   * *Default answer:* **Stop the side plenum cheek panels 35 mm below the hinge and 25 mm behind the front
     case face** (`dell-5560-wall-mount/Airflow_Design_Decision.md:20`), leaving the upper side port zones open.

---

## Appendix: Parametric Tilt Trade-Off Table (0° / 10° / 15° / 20°)

All values use $D = 230.3\text{ mm}$, $T = 20.0\text{ mm}$, $G = 40.0\text{ mm}$, $p = 2.0\text{ mm}$,
$L_{\text{front}} = 6.0\text{ mm}$, $W_{\text{span}} = 348.4\text{ mm}$
(`dell-5560-wall-mount/minimalist/build.py:27-35,69`), and $50.0\text{ mm}$ extraction travel along the tilt axis
(`tineHeight = 40.0 mm` + 10.0 mm margin).

* **Case Vertical Height ($H_{\text{case}}$):** $230.3 \cos\theta + 20.0 \sin\theta$
* **Case Horizontal Projection ($Y_{\text{case}}$):** $230.3 \sin\theta + 20.0 \cos\theta$
* **Total Wall Projection ($Y_{\text{total}}$):** $40.0 + Y_{\text{case}} + 2.0 + 6.0 = 48.0 + Y_{\text{case}}$
* **Plenum Wedge Depth at Hinge ($Y_{\text{hinge}}$):** $40.0 + 230.3 \sin\theta$
* **Horizontal Step at Top of Case ($\Delta Y_{\text{step}}$):** $230.3 \sin\theta$ (forward offset of
  hinge relative to base; clears upper tier when $\Delta Y_{\text{step}} > T \cos\theta = 20.0 \cos\theta$)
* **Center of Mass Lever Arm ($Y_{\text{CG}}$):** $40.0 + 115.15 \sin\theta + 10.0 \cos\theta$

| Parameter (`ESTIMATE` for $\theta > 0^\circ$) | 0° Upright (M1.1 Baseline) | 10° Tilt Variant | 15° Tilt Variant (Target) | 20° Tilt Variant | Trade-Off Notes |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **$\sin\theta$ / $\cos\theta$** | 0.0000 / 1.0000 | 0.1736 / 0.9848 | 0.2588 / 0.9659 | 0.3420 / 0.9397 | Trigonometric factors |
| **Single Case Vertical Height ($H_{\text{case}}$)** | 230.3 mm | 230.3 mm | 227.6 mm | 223.2 mm | Peaks near $5^\circ$, then shortens |
| **Horizontal Step ($\Delta Y_{\text{step}} = D\sin\theta$)** | 0.0 mm | 40.0 mm | 59.6 mm | 78.8 mm | All $\ge 10^\circ$ clear $20\text{ mm}$ case thickness for shingled extraction |
| **Shingled Vertical Pitch ($\Delta Z_{\text{pitch}}$)** | 280.3 mm (non-overlapped) | 265.0 mm | 260.0 mm | 250.0 mm | $0^\circ$ must lift straight up ($230.3 + 50\text{ mm}$); $\ge 10^\circ$ extracts forward |
| **Two-Case Vertical Span** | 510.6 mm | 495.3 mm | 487.6 mm | 473.2 mm | $\Delta Z_{\text{pitch}} + H_{\text{case}}$ |
| **Total Assembly Height ($Z_{\text{total}}$)** | 634.6 mm | 618.5 mm | 609.9 mm | 594.2 mm | Includes $-74.0\text{ mm}$ fan tail + $50\cos\theta\text{ mm}$ top lift |
| **Total Wall Projection ($Y_{\text{total}}$)** | 68.0 mm | 107.7 mm | 126.9 mm | 145.6 mm | **+19.2 mm** deeper per $+5^\circ$ of tilt |
| **Plenum Wedge Depth (Base $\to$ Hinge)** | $40.0 \to 40.0\text{ mm}$ | $40.0 \to 80.0\text{ mm}$ | $40.0 \to 99.6\text{ mm}$ | $40.0 \to 118.8\text{ mm}$ | At $20^\circ$, top plenum area expands $2.97\times$, risking flow separation |
| **Plenum Top Cross-Section Area** | $13,936\text{ mm}^2$ | $27,869\text{ mm}^2$ | $34,699\text{ mm}^2$ | $41,378\text{ mm}^2$ | $348.4\text{ mm} \times Y_{\text{hinge}}$ |
| **CG Lever Arm from Wall ($Y_{\text{CG}}$)** | 50.0 mm | 69.8 mm | 79.5 mm | 88.8 mm | Drives wall-bolt overturning moment |
| **2-Up Overturning Moment ($2g$, $117.7\text{ N}$)** | $5.88\text{ N}\cdot\text{m}$ | $8.22\text{ N}\cdot\text{m}$ | $9.35\text{ N}\cdot\text{m}$ | $10.45\text{ N}\cdot\text{m}$ | Vs. $2.94\text{ N}\cdot\text{m}$ for single upright M1.1 |
| **Upper Bolt Pull-Out ($126\text{ mm}$ arm spacing)** | $11.7\text{ N}$ | $16.3\text{ N}$ | $18.6\text{ N}$ | $20.7\text{ N}$ | Per arm segment at $2g$ ($M_{\text{arm}} / 0.126\text{ m}$) |
| **Continuous Outward Tine Thrust ($1g$)** | $0.0\text{ N}$ | $5.1\text{ N}$ | $7.6\text{ N}$ | $10.1\text{ N}$ | $29.4\text{ N} \times \sin\theta$ per laptop into front lip |
