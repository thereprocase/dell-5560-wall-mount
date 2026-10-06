# CFD preparation after native Fusion verification

2026-09-07. Bounded public-source research and read-only installation inspection. No software installed, solver launched, native model edited, or external CAD API called by this research branch. This document specifies preparation; it does not claim a generated mesh or validated simulation.

## Recommended first deliverable

Prepare an **isothermal airflow study**, with geometry exports, named boundary surfaces, editable input manifests, and a solver-version-specific case generator. Use OpenFOAM externally, optionally through FreeCAD CfdOF. Keep the production Fusion timeline intact. Begin with prescribed delivered flow per fan to compare pressure loss, velocity distribution and leakage under explicitly assumed flows. Add measured fan curves before claiming the operating point. Add thermal physics only after defining heat sources and laptop airflow paths.

The existing native CAD is an assembly of solid obstacles. CFD requires the connected **air volume** and boundary conditions, not merely a mesh of the printed parts. A printable mesh or a valid solid export is not yet a CFD mesh.

## Fusion product boundary

- [Autodesk personal-use licensing guidance](https://help.autodesk.com/view/fusion360/ENU/?caas=caas%2Fsfdcarticles%2Fsfdcarticles%2FFusion-360-Free-License-Changes.html) says Simulation is excluded from Fusion for personal use. The user's actual entitlement was not queried. Do not promise in-app simulation from a native F3D alone.
- [Fusion Electronics Cooling setup](https://help.autodesk.com/cloudhelp/ENU/Fusion-Simulate/files/SIM-ECOOLING-OVERVIEW-TASK.htm) provides a specialized electronics thermal/flow study including fan flow sources. Fusion therefore does have a CFD-related capability in eligible offerings; saying it has no flow simulation would be inaccurate.
- [Fusion Fluid Volume reference](https://help.autodesk.com/view/fusion360/ENU/?contextId=MODEL-FLUID-VOLUME-CMD) points to Autodesk CFD for general fluid analysis. Its Design-workspace Fluid Volume command is direct-modeling-only. In Simulation's Simplify environment the command works with parametric models and changes the simulation model. **Do not turn off production design history to access the Design command.** An independent CFD-prep document or scripted enclosure-minus-obstacles construction avoids damaging the manufacturing timeline.
- [Autodesk's thermal-simulation clarification](https://www.autodesk.com/support/technical/article/caas/sfdcarticles/sfdcarticles/Can-I-add-air-material-to-Fusion-thermal-simulation.html) directs fluid phenomena to Electronics Cooling or Autodesk CFD rather than ordinary thermal-stress simulation.

## Cheap local tooling inventory

Read-only checks found:

- `C:/Program Files/FreeCAD 1.1`, including the previously confirmed bundled `bin/freecadcmd.exe` and `bin/python.exe`.
- No OpenFOAM solver, `blockMesh`, or `gmsh` executable on the inspected Windows PATH. This is not proof that portable installations do not exist elsewhere.
- No CfdOF workbench in the inspected standard installation Mod folder; the conventional per-user Mod lookup did not return an installed CfdOF entry.
- `wsl.exe` exists, but `wsl --list --quiet` returned `Wsl/EnumerateDistros/Service/E_ACCESSDENIED` in this tool environment. **WSL solver inventory remains unknown**, not absent. No permissions or services were changed to complete this optional check.
- No other migration worktree or running agent process was inspected.

[CfdOF's own repository](https://github.com/jaheyns/CfdOF) supports FreeCAD-based setup, several meshers, OpenFOAM solving and ParaView postprocessing. It documents Windows, WSL and Linux solver integration plus dependency checks. Its current compatibility matrix and installation instructions must be matched to whichever OpenFOAM distribution is actually selected; Foundation and OpenCFD releases are distinct. CfdOF is optional if we generate an explicit case directly. We do not need to install its entire optional solver stack for incompressible airflow.

## Geometry preparation contract

These are proposed project-specific engineering steps, not executed results:

1. Freeze a verified native-build snapshot with source commit, parameter values, file hashes, part count, volume/bounds checks, and the assembly transforms actually used. Export the assembled solids to STEP and analysis surfaces to named-region STL/OBJ. Record that STEP coordinates are millimetres and convert CFD coordinates once to metres.
2. Include the installed wall plane and laptop outer shell in the analysis assembly. The current laptop is a reference block, not an internal cooling model. It cannot establish processor temperature, intake restriction or laptop-fan interaction.
3. Preserve the functional duct walls, outlet lip, side cheeks, laptop rear gap, guard bars and any genuine bypass paths affecting the selected study. Cosmetic flutes, concealed pin details and sealed pockets may be excluded from the CFD copy, with every simplification logged. Avoid accidentally sealing real assembly leakage paths.
4. Replace decorative fan hub/spokes with a documented simplified fan representation. They are not actual blade geometry and must not be used to claim blade-resolved CFD. Keep the real effective flow area or hub blockage only when supported by the selected fan dimensions.
5. Identify connected air regions; close only the deliberate inlet/outlet truncation surfaces for an internal study. Name patches from geometric predicates and retained metadata, not unstable CAD face indices. Check normals, intersections, small sliver faces and watertightness of the combined fluid boundary.
6. Use the actual Revision F installed transform. `build_mount.py` rotates the tray/fan frame +45 degrees about X after a translation. A local +Z airflow axis becomes `(0, -sqrt(0.5), +sqrt(0.5))`, wallward and upward. The local deck reference point `(70,70,-104)` maps to `(70,67,-84)` mm. These are datum checks, **not an assertion that the fluid opening is a simple circle at that plane**; derive its boundary from the final deck geometry. The second fan is mirrored across X.

### Two analysis scopes

**A. Duct/gap benchmark:** truncate at each fan discharge and at a deliberately documented outlet section. Prescribe delivered flow at `fan_left` and `fan_right`; pressure outlet at `outlet`. The resulting pressure requirement is conditional on the imposed flow. If the fan boundary is downstream of the guard, this case excludes guard/intake losses and must say so. A prematurely truncated outlet can bias the result; include enough extension or compare against the larger-domain case.

**B. Installed ambient domain:** include the wall, laptop and mount inside a surrounding air enclosure. Put ambient pressure openings on the enclosure, not an artificial sealed cap across every real leak. Keep duct-exit and laptop-gap sampling surfaces as internal measurements. Fans become internal pressure-jump/actuator surfaces, or boundary flow sources only where the chosen truncated geometry supports that interpretation. This scope resolves bypass and recirculation more credibly but costs more mesh cells and needs a domain-size sensitivity check.

## Boundary condition plan for the first incompressible study

The combinations below follow [OpenFOAM's pressure/velocity boundary-condition guidance](https://api.openfoam.com/2406/pageBoundaryConditions.html); exact dictionary syntax and turbulence fields depend on the pinned solver release.

| Region | Velocity U | Pressure p | Required input |
| --- | --- | --- | --- |
| fan_left / fan_right, prescribed-flow benchmark | Flow-rate inlet or equivalent normal velocity | zeroGradient | Delivered volume flow in m3/s for each fan |
| outlet / suitable ambient boundaries | pressureInletOutletVelocity or another documented backflow-safe choice | fixedValue, zero gauge | Ambient reference; backflow transported fields |
| printed_walls, laptop_shell, wall_plane | no-slip, U=(0,0,0) | zeroGradient | Surface grouping; roughness only if measured/assumed explicitly |

Do not prescribe both fan pressure rise and delivered flow as independent fixed conditions at the same boundary. [OpenFOAM fanPressure](https://doc.openfoam.com/2212/tools/processing/boundary-conditions/rtm/derived/inletOutlet/fanPressure/) accepts a pressure-versus-volume-flow curve for a boundary fan. An internal fan disk requires the corresponding internal-jump/actuator treatment for the chosen release; fanPressure is not a universal internal-disk substitute. Fan free-air CFM is not the delivered flow through this assembly.

For an incompressible solver whose `p` is kinematic pressure, pressure differences must be converted consistently with density; do not mix Pa and m2/s2. Turbulence model and inlet turbulence values remain stated assumptions. A steady RANS baseline is reasonable for exploration, but residual convergence alone does not establish a stable physical flow if separation or recirculation is intrinsically unsteady.

## Concrete artifact layout to generate after native completion

```text
fusion/cfd/
  README.md                    # status, scope, commands, limitations
  inputs.json                  # units, air state, flow cases; unknowns null
  geometry_manifest.json       # source hashes, assembly transforms, simplifications
  patches.json                 # names, roles, geometric selection metadata
  geometry/assembled.step      # verified assembled solid snapshot
  geometry/fluid.step          # extracted fluid region, when generated
  geometry/surfaces/            # named wall/inlet/outlet regions, metres
  fan_curve_template.csv       # flow_m3_s, pressure_rise_Pa; headers only until known
  mesh_levels.json             # coarse/medium/fine and local refinement controls
  case_template/              # pinned OpenFOAM distribution/version
    0/                         # U,p and required turbulence fields
    constant/triSurface/
    system/                    # mesh, numerics, monitors, runtime control
  validation/                 # surface/mesh/conservation/convergence evidence
```

This layout is a planned deliverable, not a claim those files already exist. Keep unknown fan flow/curve and heat loads null. A case generator should reject missing required inputs or require an explicit assumed-flow scenario, instead of quietly inventing a fan specification.

[snappyHexMesh's official geometry reference](https://doc.openfoam.com/2212/tools/pre-processing/mesh/generation/snappyhexmesh/geometry/) supports triangulated input under `constant/triSurface`, with named regions becoming patches. Its [meshing overview](https://doc.openfoam.com/2606/tools/pre-processing/mesh/generation/snappyhexmesh/) describes the background mesh, surface feature extraction, snapping, refinement and boundary layers. This supports a reproducible command-driven pipeline, but the documented release is not yet an installed/pinned solver here. Use [surfaceCheck](https://www.openfoam.com/documentation/guides/latest/man/surfaceCheck.html), then mesh-quality checks, before attempting a solve.

## Evidence required before interpreting results

- Geometry scale and placement confirmed; both intended air paths connected; selected wall/leak boundary treatment documented.
- Mesh resolves the 12 mm nominal outlet restriction and important narrow paths. Do not select a fixed cell count solely from appearance. Compare coarse/medium/fine meshes and near-wall treatment appropriate to the chosen model.
- Report inlet/outlet mass balance, pressure-drop and flow monitor stability, residual histories, reverse-flow regions, achieved wall resolution and mesh quality. Compare integrated flow and pressure, not only colored streamlines.
- Recommended initial measurements: per-fan delivered flow, pressure required at each fan plane, left/right flow balance, velocity distribution along the laptop rear gap, bypass fraction, and low-flow/recirculation regions. Domain enlargement and flow-rate sensitivity belong in the evidence package.

## Inputs still needed

- Actual fan model, rotation direction, effective area/hub size, operating RPM or PWM, and pressure-flow curve (or measured delivered flow for explicitly conditional runs).
- Installed laptop position, true intake/exhaust locations and whether laptop internal fans should interact with the model; existing reference geometry does not provide these.
- Room temperature and pressure; air-property assumptions can then be stated reproducibly.
- For later thermal work: laptop heat-load distribution in watts, relevant exposed surface areas, thermal contact assumptions and material properties. A single nameplate wattage is not automatically the heat transferred into the modeled rear air gap.

Thermal fields should remain disabled in the first airflow case. Later placeholders may include `laptop_heat_W`, `heat_patch_area_m2` and `ambient_temperature_K`, with unspecified values null. No cooling-temperature claim is justified until the heat and laptop airflow model are defined and tested.

## fan_assumptions: tentative Noctua NF-A12x25 PWM

The user identified the fan only as a Noctua NF-A model. **NF-A12x25 PWM, standard 12 V original generation, is a provisional setup assumption**, not confirmed identification. NF-A12x15, NF-A12x25 G2, LS-PWM, FLX and 5 V variants must not silently inherit these performance inputs. Exact label, thickness, operating setting and use of the Low-Noise Adaptor remain unresolved. No simulation is requested at this stage.

### Verified nominal endpoint specifications

[Noctua's NF-A12x25 PWM specifications](https://www.noctua.at/en/products/nf-a12x25-pwm/specifications) give:

| Setting | Maximum RPM | Maximum/free-flow airflow | Maximum/shutoff static pressure |
| --- | ---: | ---: | ---: |
| Standard, without Low-Noise Adaptor | 2000 | 102.1 m3/h; 60.09 CFM | 2.34 mm H2O |
| With Low-Noise Adaptor | 1700 | 84.5 m3/h; 49.73 CFM | 1.65 mm H2O |

The listed frame dimensions are 120 x 120 x 25 mm without anti-vibration pads and 120 x 120 x 27 mm with pads; mounting-hole spacing is 105 x 105 mm. The source CAD's 27 mm fan reference thickness therefore has a plausible padded-fan basis. This does not confirm the user's model.

Unit conversions computed for case preparation: standard airflow `102.1 / 3600 = 0.0283611111 m3/s`; LNA airflow `84.5 / 3600 = 0.0234722222 m3/s`. Using conventional `1 mm H2O = 9.80665 Pa`, endpoint pressures are approximately `22.947561 Pa` and `16.1809725 Pa`. These are separate endpoints, **not simultaneous airflow and pressure conditions**.

### P/Q curve availability and provenance

[Noctua's official performance comparison](https://www.noctua.at/en/expertise/tech/nf-a12x25-performance-comparison-to-nf-f12-and-nf-s12a) publishes a P/Q chart and explains operating points as intersections with application impedance. An additional official graph containing the original NF-A12x25 curve is on page 5 of [Noctua's Computex 2025 press kit](https://cdn.noctua.at/media/noctua_computex_2025_press_kit.pdf). The G2 curve on that page is a different fan and must not be substituted.

**No manufacturer numeric curve table/CSV was found** in the bounded specifications/downloads/curve search. The [official downloads page](https://www.noctua.at/en/products/nf-a12x25-pwm/downloads) exposes manuals, an information sheet and STEP geometry, not an evidenced tabulated P/Q dataset. It also says the CAD is accurate for mounting/external dimensions but some features are modified for IP protection; downloaded fan geometry is consequently not a validated blade-resolved CFD model.

Keep `fan_curve_points` null and the fan-curve CSV header-only. Do not create a straight line between the two endpoints and label it a real fan curve. Later options are manufacturer numeric data, measured data, or careful digitization of a documented official graph, recording graph identity, RPM, axis calibration and digitization uncertainty. Digitized approximations must be labeled as such. No curve has been digitized here.

### Conditional delivered-flow sweep for setup only

Prepare these **assumed delivered flows per fan**, for comparing the duct's required pressure and airflow distribution. They are neither measured operating points nor predictions of what the tentative fan delivers.

| Scenario | Per-fan CFM | Per-fan m3/s | Two-fan total CFM |
| --- | ---: | ---: | ---: |
| low_assumed | 20 | 0.009438948864 | 40 |
| mid_assumed | 35 | 0.016518160512 | 70 |
| high_assumed | 50 | 0.023597372160 | 100 |

Conversion uses `1 ft3 = 0.028316846592 m3`. The 50 CFM scenario slightly exceeds the specified 49.73 CFM LNA free-flow endpoint, so it is not a plausible loaded LNA operating point; preserve it only as a conditional flow demand for the standard full-speed hypothesis. Required pressure from a future solved sweep may rule out a demand, but endpoint specs alone cannot establish an achievable operating point. No solver has been run.
