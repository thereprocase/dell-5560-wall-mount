# Precision 5560 server wall mount — engineering report

Revision F · 7 September 2026 · prototype design

**The mount aims to support the laptop's own cooling system.** Two inclined fans feed a shrouded rear gap; an upper restriction retains modeled intake pressure and directs bypass air toward the hinge exhaust. The laptop lifts out for access. Geometry checks, structural screening and comparative CFD are complete. Printing, joint retention and cooling performance need physical validation.

![Installed and empty assembly, rendered from the CAD](Precision_5560_Wall_Mount_Preview.png)

## 1. Design basis

The mount holds a closed Dell Precision 5560 used as a web server. The hinge faces up, placing the exhaust at the upper edge. The underside faces the fan-fed wall gap. The laptop lifts out for keyboard access.

| Parameter | Revision F |
|---|---|
| Laptop reference envelope | 344.4 × 230.3 × 20 mm |
| Bare retention slot / front tine height | 26 / 94 mm |
| Nominal underside-to-wall gap | 40 mm |
| Fans | Two 120 mm frames, 25–27 mm thick |
| Fan airflow direction | Wallward and upward at 45° |
| Wall attachment | Four Ø7 mm holes; axes normal to wall |
| Hole centers | X = ±162 mm; Z = −36 and +174 mm |
| Tool clearance | Ø16 mm room-side corridors |
| Default outlet / alternatives | 12 mm / 8 and 16 mm |
| Printed assembly | 14 pieces, including four identical split pins |
| Laptop removal | 105 mm lift, then forward; allow 110 mm overhead |

Coordinates are X across the laptop, Y outward from the wall and Z upward in the exported assembly. Inspect the installed-reference STEP when positioning the mount. Physical measurements should resolve the stated profile uncertainty before permanent assembly.

## 2. Reference geometry and vent alignment

![Scaled Dell images and estimated profile](Laptop_Profile_References.png)

Dell's published width and depth set the image scales. Selected points from the side view define the estimated silhouette. The inside-base-cover image reveals a covered center behind the broad exterior grille, leaving two inferred intake regions.

We observed the following:

- The scaled inside-cover image places two approximately 70 × 40 mm intake regions near X = ±111 mm and Z ≈151–191 mm.
- The image-derived intake location carries an estimated ±4 mm uncertainty.
- The reconstructed side profile carries an estimated ±2 mm uncertainty. The assembly retains a 20 mm thickness envelope.
- The model assumes a 2 mm rear-foot projection. No dimensioned factory cross-section or physical measurement establishes that value.

The contraction begins at Z = 198 mm, above the estimated intake band. It reaches its throat at Z = 226 mm and exits at Z = 232 mm, close to the hinge edge at Z = 232.3 mm. These locations retain a nominal gap between the intake and contraction; they require verification on the actual machine.

![Intake band, contraction and outlet alignment](Vent_Layout_and_Outlet.png)

The [profile JSON](profile_reconstruction.json) preserves pixel picks, scale factors, source hashes and uncertainty. The [reference STEP](REFERENCE_Estimated_Laptop_Profile.step) is an inferred silhouette, not manufacturer geometry. Source links appear in [SOURCES.md](SOURCES.md).

## 3. Airflow design and numerical evidence

The lower fans feed the rear plenum. Cheeks limit side leakage, and the upper restriction sits downstream of the intake band. The aim is to retain static pressure at the laptop intake while directing bypass air upward. The laptop remains vertical, with noncontact clearances for removal.

Restricting the outlet can increase upstream pressure while reducing total flow. At limited supply pressure, a narrower opening need not produce a faster jet. The laptop's blowers and internal resistance also govern intake flow.

![OpenFOAM field results and common-mesh comparison](CFD_Plenum_Study.png)

Eight OpenFOAM v1912 `simpleFoam` runs use steady incompressible RANS with k–omega SST. The domain is a representative sealed 2D fan-band section with a 1 mm empty extrusion. Nominal inlet total pressure is 20 Pa; the outlet uses zero-gauge static pressure. The intake patch has a prescribed 0.4 m/s demand. Sensitivity cases use 10 Pa supply and 0.8 m/s intake demand.

| Common-mesh case | Mean intake pressure, Pa | Mean slot exit speed, m/s |
|---|---:|---:|
| Curved lower turn, 8 mm slot | 18.80 | 4.01 |
| Curved lower turn, 12 mm slot | 17.67 | 4.42 |
| Curved lower turn, 16 mm slot | 15.43 | 5.16 |
| Straight lower turn, 12 mm slot | 17.56 | 4.39 |

The 12 mm slot remains the first prototype configuration. The 8 mm variant retains more modeled intake pressure but passes less bypass flow and leaves less clearance. The 16 mm variant passes more flow at lower intake pressure. The gentler turn changes mean intake pressure by only about 0.11 Pa on the common mesh; that result does not establish a meaningfully optimized bend.

All eight meshes passed `checkMesh`, and reported flow imbalance stays below 0.001%. Coarse-to-fine refinement changes mean intake pressure by about 0.3% and exit speed by about 2.9%. Four cases miss the strict residual target at 1,600 iterations even though the final mean-pressure monitors change by less than 0.01% between saved states. The [CFD report](CFD_Design_Report.md) identifies every case and preserves the boundary conditions and convergence limits.

**Model limits:** intake flow and fan supply pressure are prescribed. The study omits real fan curves, 3D leakage, fan hubs and swirl, detailed grilles and ribs, internal laptop resistance, heat transfer and the room plume. It compares the proposed slot geometries. Actual CFM, cooling improvement and exhaust carry distance require measurements.

## 4. Material reduction and structure

Hollow box sections, thin duct skins, framed trays and pocketed caps reduce material. Saddle roots, bearing shoulders and wall holes retain the load-carrying sections. Section calculations guided these edits; no generative or topology solver was run.

| Checkpoint | Solid CAD volume, cm³ | Interpretation |
|---|---:|---|
| Revision D | 1,810.4 | Earlier reference |
| Revision E | 1,164.2 | Lightweight baseline |
| Revision F | 1,177.3 | Shrouded, inclined, CA/pin assembly |

Revision F reduces solid volume by 35.0% relative to D. The latest containment and assembly changes add 13.1 cm³ relative to E, approximately 14 g at the assumed ASA density of 1.07 g/cm³. These comparisons use equal fill policy and exclude brims and process allowances; they are not slicer filament estimates.

The structural screen uses a 2.5 kg laptop, a 6 kg complete installation, a 1 kg allowance per fan module, 3g acceleration and a 50 N outward hinge pull. It adopts 5 MPa normal/bearing and 2 MPa shear limits, a 1,000 MPa effective modulus, a 1.5 local stress multiplier and a 10% section-property allowance. These are chosen screening values, not measured warm printed ASA properties.

Net section properties come from the actual cradle geometry at 0.5 mm stations and include voids and unsymmetric bending. The rear-section calculation ignores the additional cheek stiffness. The minimum ratio of assumed stress limit to calculated stress is **1.19**, governed by the combined rear-rail case. It does not establish a tested assembly safety factor. The full [strength report](Strength_and_Installation_Check.md) lists each calculation and load demand.

The calculations do not resolve adhesive peel and pullout, pin retention, anchor capacity in the actual wall, torsion, local buckling, fatigue, impact or long-term thermal creep. In particular, each duct has a calculated 47.8 N outward joint demand and each pin a 7.4 N retention demand that still require physical qualification.

## 5. FDM design and assembly

![Print orientations by part family](FDM_Print_Orientations.png)

The cradles print on their outer sides to place the main bracket load path within the layer planes. The ducts print from their inclined fan-inlet faces, and the outlet rails print lip down. Sloped joint roofs and skins avoid broad unsupported ceilings. Deliberate short bridges close hollow sections without filling them with support.

All individual parts, including an 8 mm brim, fit the P1S's 256 mm bed while avoiding the stock front-left cutter exclusion. The 0.20 mm geometric layer audit finds no floating starts. The largest intentional bridge spans 18 mm in the rear spine; its maximum sampled unsupported reach is 8.8 mm. Dovetail roofs span 6.6 mm. These checks evaluate geometric support, not extrusion quality.

The Bambu Studio runtime could not execute in the design environment. The files have therefore not passed an actual Bambu toolpath preview or print trial. The [ASA guide](P1S_ASA_Print_Guide.md) provides starting process settings and highlights the required preview.

![Sections through the actual printable geometry](FDM_Sections.png)

Fixed ducts and rails use keyed lap joints. Their shoulders carry vertical load; CA resists withdrawal. The fan trays slide into dovetails, and two split pins retain each fan cap. The assembly needs no M3/M4 screws, nuts or heat-set inserts. All four wall bolts remain perpendicular to the wall with clear tool access.

The nominal sliding allowance is 0.30 mm horizontally per side, with 0.30 mm crown and 0.20 mm root clearance. The keyed CA pockets use 0.30 mm nominal offsets plus roof relief. Split pins use a 4.0 mm shaft, 4.1 mm socket and 4.2 mm retaining crown. [TOLERANCES.md](TOLERANCES.md) distinguishes diametral, radial and coordinate allowances; no global shrink compensation is assumed.

![Exploded fixed and removable joints](Tool_Free_Assembly.png)

## 6. Verification record and next decisions

| Evidence completed | Practical limit |
|---|---|
| 14 valid solids; STEP reimport | Solid validity does not establish manufacturability |
| Fit, service motion and driver-path checks | Laptop envelope and image-derived profile need physical confirmation |
| No unintended part overlap | Four pin crowns intentionally interfere by 0.05 mm radially |
| Watertight oriented meshes and bed/brim check | Slicer-generated extras and extrusion paths remain to be inspected |
| Geometric layer support audit | Bridges and surface quality need printing |
| Net-section strength screen | Bonds, anchors, retention and warm creep remain unqualified |
| Eight CFD cases with raw logs and fields | Comparative 2D study with prescribed laptop demand |

The next prototype should proceed in this order:

1. Measure the actual closed laptop, feet and intake boundaries. Confirm noncontact cheek and outlet clearance before choosing the rail pair.
2. Print the joint and pin coupons in the intended ASA process. Check sliding fit, CA retention and repeated pin use. Check long tray engagement for warping.
3. Preview the full parts in Bambu Studio, including bridge direction, extrusion continuity and brim placement. Print and inspect the structural brackets before loading the laptop.
4. Qualify the assembled joints and wall attachment against the stated demands, then assess deformation and creep at the measured operating temperature.
5. Fit the selected fans, measure plenum pressure near both intake regions, and compare repeatable workload temperatures and noise with fans off/on and alternative outlet rails. Record ambient temperature, fan speed and laptop workload.
6. Use the measured fan curve, pressure, leakage and laptop response to decide whether a coupled 3D or thermal CFD model would change the design. Revisit material reduction only after the physical joint and creep behavior are established.

## 7. Reproducibility

[PROCESS.md](PROCESS.md) records the decisions and regeneration commands. The `cfd/` directory contains case definitions and archived fields and logs. Scripts use repository-relative paths. [SOURCES.md](SOURCES.md) links the manufacturer references, and [DIALOGUE.md](DIALOGUE.md) records the available project prompts.
