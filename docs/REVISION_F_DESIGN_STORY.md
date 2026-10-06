# A wall mount optimized for airflow synergy

A Dell Precision 5560 server mount designed to work with the laptop's cooling system. Two 120 mm fans feed a shrouded gap behind the underside. An upper restriction aims to retain pressure at the intake vents and direct bypass air upward, past the hinge exhaust. The laptop lifts out for keyboard access.

The assembly uses side-printed ASA brackets, 45° fan modules, keyed CA joints and removable fan trays. Four wall bolts are the only metal mounting fasteners.

![Revision F installed and empty, rendered from CAD](../Precision_5560_Wall_Mount_Preview.png)

**Revision F — prototype design.** CAD checks, structural screening and eight CFD cases are complete. Printing, joint strength and cooling performance still need physical validation.

[STEP assembly](../Precision_5560_Wall_Mount.step) · [Print files](../print_ready/) · [Assembly guide](../P1S_ASA_Print_Guide.md) · [Engineering report](../ENGINEERING_REPORT.md) · [Reproduction steps](../PROCESS.md)

## 1. Define fit and access

> “The hinge will go up so that the hot air escapes up and the fans can go on the bottom…”

The laptop sits vertically, underside toward the wall, with a 40 mm rear gap. A 344.4 × 230.3 × 20 mm envelope controls fit. The 26 mm bare slot allows for contact pads.

> “…make the tines on the front a little bit taller…”

The front tines are 94 mm tall. Four Ø7 mm wall holes face the room through clear Ø16 mm tool paths. We checked bolt access and laptop removal with the assembly in place. The laptop needs a 105 mm lift before moving forward; allow 110 mm overhead.

## 2. Support the laptop's intake

> “…doesn't have to seal, just has to be high pressure at vent high velocity beyond.”

The airflow goal became a plenum with a controlled outlet. Side cheeks limit leakage. A separate upper rail contracts the gap above the intake band, keeping the laptop vertical and the outlet width interchangeable.

Restricting the outlet can raise upstream pressure while reducing flow. The useful question was how much pressure each slot retained at the intake, and what exit velocity remained.

## 3. Locate the active vents

> “…download and scale images and cross sections of the machine to estimate its profile geometry?”

We scaled Dell side views and an inside-base-cover image against the published width and depth. The inside view revealed a covered center behind the broad exterior grille, leaving two estimated 70 × 40 mm intake regions near X = ±111 mm.

![Scaled Dell references and estimated profile](../Laptop_Profile_References.png)

The estimated intake band ends near Z = 191 mm, with ±4 mm location uncertainty. The contraction starts at 198 mm, reaches its throat at 226 mm and exits at 232 mm, near the hinge. No dimensioned factory section was found; the reconstructed profile has an estimated ±2 mm uncertainty. Check the actual machine before assembly.

## 4. Design for the print orientation

> “I would like to print the brackets on their side for strength, and not on their back.”

> “Also bridges are just fine, they're usually printable. Unsupported overhangs are bad.”

The brackets print on their outer sides. Ducts print inlet down; outlet rails print lip down. Sloped roofs support the next layer, while short bridges close box sections and dovetail grooves.

![Supplied print orientations](../FDM_Print_Orientations.png)

The 0.20 mm layer audit found no floating starts. The longest intentional bridge spans 18 mm. Each part and its 8 mm brim fits the P1S bed and avoids the cutter exclusion. Bambu Studio could not run in the environment, so toolpaths and ASA bridge quality remain to be checked.

## 5. Reduce material along the load path

> “I feel like we could get really creative and save a ton of plastic here.”

We hollowed the brackets, thinned the duct skins and pocketed the trays and caps. Material remains at bearing shoulders, bracket roots and wall holes. This used explicit geometry and section calculations; no topology or generative solver was run.

We extracted net section properties every 0.5 mm, including voids and unsymmetric bending. The structural screen uses a 2.5 kg laptop, 6 kg installation, 3g acceleration and a 50 N outward hinge pull. The minimum ratio of assumed stress limit to calculated stress is 1.19. This is a screening result; bonds, anchors and warm ASA creep remain unqualified.

Revision F uses **1,177.3 cm³ of solid CAD, 35.0% less than Revision D** at equal fill policy. The latest containment and assembly changes add 13.1 cm³ to the lightweight Revision E.

## 6. Keep service parts removable

> “Can we also make it tool free / ca glue assembly, except for the four wall bolts?”

Keyed lap joints connect the fixed ducts and outlet rails. Their shoulders carry vertical load; CA resists withdrawal. Fan trays slide in dry, and two split pins retain each cap.

> “…have the fans angle down so they're blowing at a 45 to the gap instead of straight in?”

The fan intakes face down and outward. Air flows upward and wallward at 45°. Cheeks contain the rear flow while leaving side ports accessible.

![Fixed joints and removable fan assemblies](../Tool_Free_Assembly.png)

The screened loads require 47.8 N of outward retention per duct and 7.4 N per pin. Adhesive and pin tests must establish that retention before service.

## 7. Compare the outlet slots

> “And do some cfd to design the plenum and slot?”

Eight OpenFOAM v1912 cases compare slot width, lower-turn geometry, mesh size, supply pressure and intake demand. The model uses steady incompressible RANS with k–omega SST in a sealed 2D section.

![Calculated pressure and velocity fields](../CFD_Plenum_Study.png)

At an assumed 20 Pa inlet total pressure and prescribed 0.4 m/s intake demand:

| Outlet | Mean intake pressure | Mean exit speed |
|---|---:|---:|
| 8 mm | 18.80 Pa | 4.01 m/s |
| **12 mm** | **17.67 Pa** | **4.42 m/s** |
| 16 mm | 15.43 Pa | 5.16 m/s |

The narrow slot retained more pressure; the wide slot produced a faster exit. We kept **12 mm** as the starting compromise. The curved lower turn improved intake pressure by only 0.11 Pa on the common mesh, giving little reason to refine the bend further before testing.

All meshes passed `checkMesh`. Flow imbalance stayed below 0.001%; mesh refinement changed mean intake pressure by about 0.3% and exit speed by 2.9%. Four cases missed the strict residual target despite stable mean-pressure monitors.

The model prescribes laptop intake flow and assumes fan pressure. It omits real fan curves, internal laptop resistance, side leakage, heat transfer and the room plume. The results compare slot behavior; actual cooling, total CFM and exhaust carry distance require measurements.

## 8. Specify the fits

> “what tolerances did you assume for slide to fit parts?”

The dovetail has 0.30 mm horizontal allowance per side, 0.30 mm crown clearance and 0.20 mm root clearance. Clearance normal to the sloping flank is smaller. Fixed-key pockets use 0.30 mm nominal offsets plus roof relief. Pins use a Ø4.0 mm shaft, Ø4.1 mm socket and Ø4.2 mm split crown.

No global ASA shrink correction is applied. Print the coupons, inspect elephant foot and adjust individual interfaces as needed. Full-length tray engagement also needs a warping check. See [TOLERANCES.md](../TOLERANCES.md).

## 9. Reproduce and test

The workflow followed the interfaces: establish fit, reconstruct the vents, build the solids, check loads and service motions, audit print support, then compare airflow variants. [DIALOGUE.md](../DIALOGUE.md) preserves the available prompts in order.

| Software | Use |
|---|---|
| Python 3.12; CadQuery 2.8.0 / Open CASCADE | Parametric solids, sections, STEP export and interference checks |
| NumPy; trimesh 5.1.0; Shapely 2.1.2; rtree; NetworkX | Mesh, layer support and connectivity checks |
| Pillow | CAD renders and reference-image annotations |
| Matplotlib; SciPy; VTK | CFD postprocessing and field plots |
| OpenFOAM v1912 | Meshing, mesh checks, flow solution and field export |
| Bambu Studio 2.8.2.61 profile sources | Starting P1S/ASA settings; slicing remains pending |
| Git / GitHub | Source, design files and analysis records |

[PROCESS.md](../PROCESS.md) gives the commands; [requirements.txt](../requirements.txt) records the Python dependencies. The [engineering report](../ENGINEERING_REPORT.md) covers dimensions, assumptions, loads and verification.

Next: measure the laptop, print the coupons, test joint retention and warm structural behavior, then measure intake pressure and workload temperatures with the selected fans and outlet rails. Use those results to decide whether a coupled 3D or thermal model would change the design.

**Printing:** follow the [P1S ASA guide](../P1S_ASA_Print_Guide.md), retain the supplied orientations and inspect the slice. Files are standard 3MF/STL models. Print the individual parts; reference STEP assemblies are for fit inspection.

**License:** [MIT](../LICENSE). Dell reference material is attributed separately in [SOURCES.md](../SOURCES.md). This project is independent of Dell and Bambu Lab.
