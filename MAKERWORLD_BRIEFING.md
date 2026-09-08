Briefing for the agent preparing the MakerWorld early-adopter release

Prepared September 8, 2026. Package the published laptop wall-mount designs for experienced early adopters who can measure their machine, print fit coupons, and report results. Make the listings welcoming and easy to follow while being explicit about what remains untested. Use the current released geometry and retain the revision names throughout the files, descriptions and images.

Use a checkout of `thereprocase/dell-5560-wall-mount`; file paths below are relative to its root. The geometry snapshot is commit `8a3e1578beca56075d8f48235a3a1bac8fccd034`. Main was synchronized through `ba36330` before publishing this briefing, preserving H-R1 and the newer CFD sequence and video work. The owner previously confirmed `e8d4070` on main and Pages; later simulation publications do not by themselves change the print geometry. Inspect current state before changing anything and preserve the other agent's CFD work. Use an isolated worktree if editing the repository. This briefing supplies engineering and packaging context; continue under the user's existing instructions for your upload task.

The public starting points are the [project and interactive models](https://thereprocase.github.io/dell-5560-wall-mount/), [GitHub source](https://github.com/thereprocase/dell-5560-wall-mount), [M1.1 print and assembly guide](https://thereprocase.github.io/dell-5560-wall-mount/minimalist-guide.html), and [H-R1 installation guide](https://thereprocase.github.io/dell-5560-wall-mount/revh-retainers.html). Keep those links in the listings so adopters can find current instructions and revisions.

There are two independent mount designs and one add-on. Suggested listing structure:

| Suggested title | Scope and files |
|---|---|
| **Minimalist Laptop Wall Mount M1.1 — Early-Adopter Prototype** | Main open-frame design with two removable fan cradles and an optional indexed airflow dam. Six dimensioned examples. Files: `minimalist/presets/<name>/print/`; native files and coupons under `minimalist/`. |
| **Dell Precision 5560 Ducted Wall Mount Rev H — Early-Adopter Prototype** | Separate, heavier ducted design. Fourteen original parts. Files: `print_release/` and `print_release_step/`; native source: `freecad/Precision_5560_Native.FCStd`. |
| **Rev H-R1 Removable Retainers — Rev H Add-On** | Two side bars and two keepers for the preserved Rev H geometry. Requires the Rev H mount; does not fit M1.1. Files: `revh_retention/print/`; native source and engineering notes in `revh_retention/`. |

Cross-link the listings. Make M1.1 the lead option for people starting from scratch, with the material estimate and open-frame construction explaining that choice. Present H-R1 as an accessory, never as a complete four-part mount. The six M1 sizes belong together as clearly named variants where the platform permits. Do not mix M1 and Rev H parts. Root `print_ready/`, root assembly STEP, and the original Fusion/Onshape ports contain Revision F history; they are not the current Rev H release. Leave unrelated development branches out of this release.

**Cable-management update, H-C1:** the [new cable guide](https://thereprocase.github.io/dell-5560-wall-mount/revh-cables.html) supplies replacement Rev H covers **05/06** with edge-open, lay-in cable grooves and trays **09/10** with two external zip-tie anchors each. The tray closes the cable passage when the cover is fitted, so the connector never needs to pass through a hole. Four replacements, not four added parts; they work with or without H-R1 and leave the printed arms, ducts, rails, pins and H-R1 geometry unchanged. Use `revh_cables/print/` and `docs/downloads/Precision_5560_RevH_Cable_Management_C1.zip`. Start with `00_cable_fit_coupon`; then print `20_both_cable_covers` plus trays 09/10, three full-size plates. Preserve the older Rev H files as a named baseline and make the C1 replacement choice explicit within the Rev H listing. Read `revh_cables/release-report.json` for current estimates; do not reuse the old cover/tray totals. The checked 4 mm cable envelope has 0.5 mm minimum gap; cable fit, abrasion and tie-lug strength remain physically untested. This update does not change M1.1 or establish a new CFD/cooling result.

Use an opening disclosure along these lines:

> This is an early-adopter prototype with editable CAD, print files, fit coupons and illustrated assembly instructions. CAD and slicer checks have been completed, but complete physical fit, joint retention, long-term deformation and cooling performance remain unqualified. Start with the fit coupon and a supported trial assembly, and help improve the design by reporting measured fit and printing results.

The owner has reported printing the preserved Rev H arms. That does not establish a successful complete Rev H assembly, an M1 print, or an H-R1 retention test. Recheck whether the owner has newer physical results or genuine photographs before describing anything as printed or tested. Avoid claims of a rated laptop weight, universal compatibility, proven cooling gains, or doubled strength. M1.1's larger wall junction is a measured CAD section change, not a tested strength multiplier.

M1.1's nominal closed-laptop envelope is **344.4 × 230.3 × 20 mm**, with a **40 mm rear gap**, separate **2 mm compliant contact pads**, and two modeled **120 × 120 × 27 mm fan envelopes** aimed 45° up the rear gap. A 25 mm fan requires suitable spacing to prevent rattle. Check the actual fan body, wire exit and connector. Additional required items include the fans and suitable power arrangement, compliant pads, and four wall fasteners with washers and anchors selected for the actual wall. No specific wall anchor has been qualified.

The six M1 examples are:

| File/preset name | Closed case width × depth × thickness |
|---|---|
| `5560` | 344.4 × 230.3 × 20 mm |
| `13-inch-example` | 304 × 210 × 16 mm |
| `14-inch-example` | 320 × 220 × 18 mm |
| `15-6-inch-example` | 360 × 245 × 24 mm |
| `16-inch-example` | 360 × 250 × 24 mm |
| `17-inch-example` | 400 × 275 × 28 mm |

Screen diagonals are labels, not fit specifications or a continuous validated size range. Ask adopters to measure width, depth and maximum closed thickness, including feet and protrusions, then check vents, ports and contact points. Custom sizes should be generated through the native FreeCAD parameters and rechecked; uniform slicer scaling also changes the fan seats, fastener bores and printed fits. M1 needs at least 43 mm upward laptop movement for removal; do not copy the historical Rev F 110 mm overhead instruction into its listing.

Printing instructions must prevent duplicate parts:

1. **M1.1 coupon first:** `minimalist/coupons/00_fit_coupon_plate.3mf`. It exercises the key, keeper, fan-hanger and cap-pin interfaces in their full-part print directions.
2. **M1.1 with dam:** print one each of **01–08 plus `21_all_hardware`**, nine supplied plates and twenty installed parts. The twelve individual files 09–20 are replacement alternatives already included on plate 21.
3. **M1.1 without dam:** print **01–06 plus `22_hardware_without_dam`**, seven plates and fourteen installed parts. Use plate 22 instead of plate 21. The optional dam has nine positions over 96 mm; both sides must use the same index.
4. **Rev H:** print one each of **01–14**. Parts 11–14 are four pins. Owners with the matching arms already printed need only 03–14 for the original assembly. Keep H-R1 as four additional parts if using removable withdrawal retention.
5. **H-R1 coupon first:** print `revh_retention/print/01_right_arm_fit_test.3mf` and test it on the actual right Rev H arm. After that passes, print `00_four_retainer_parts.3mf` once. It contains parts 15–18; the individual files are replacement alternatives. The coupon is not an installed retainer.

Use **OrcaSlicer** for preparation and toolpath review, as required by this project's `AGENTS.md`. The recorded process is OrcaSlicer 2.4.2, Bambu P1S, ASA, 0.4 mm nozzle, 0.20 mm layers, six walls, six top/bottom layers, 100% rectilinear infill, Arachne walls, 8 mm outer brim and supports off. The CAD already contains deliberate openings and hollow regions. These are reviewed starting settings, not qualification of other materials, printers or reduced wall/infill settings. Temperatures and drying must match the actual spool.

Keep supplied orientation and 100% scale. Arms print on their outer sides; other parts have their own baked orientations in the guides. **Rev H ducts 03 and 04 require both Bridge direction and Internal bridge direction at 180°, with Relative bridge angle and Align infill direction to model off.** Automatic bridge direction spans the long slots lengthwise. The corrected review crosses the slots, with a maximum unsupported span of 5.19 mm. Read `print_release_step/ORCA_BRIDGE_REVIEW.txt`. Do not apply that Rev H override indiscriminately to M1.

Use these slicer estimates, labeled as estimates and tied to the process and plate layouts above:

| Set | Filament | Estimated print time |
|---|---:|---:|
| M1.1 5560, with dam | 400.55 g | 15 h 42 m 30 s |
| M1.1 5560, without dam | 362.86 g | 12 h 49 m 10 s |
| M1.1 fit coupon | 35.09 g | 2 h 7 m 35 s |
| Rev H original fourteen parts | 1,183.88 g | 34 h 00 m 15 s |
| H-R1 four-part add-on | 59.21 g | 2 h 13 m 41 s |
| H-R1 right-arm coupon | 13.92 g | 39 min |

M1.1 uses 66.2% less estimated filament than the original complete Rev H set under that comparison. Rev H's comparison prints the four pins individually, whereas M1 combines hardware; a different plate layout changes startup overhead and time. Rev H's figure excludes H-R1. Coupon quantities are separate. Do not substitute solid CAD mass for slicer filament mass.

For H-R1, explain the service interaction prominently: all fourteen Rev H parts remain geometrically unchanged. The two external bars engage existing arm windows and retain the duct and upper rail without drilling the arms, extra metal fasteners, or adhesive at those two joints. The original keys and shoulders still carry the intended assembly loads. **Removing one bar releases both its duct and its rail. Remove the laptop and support both modules during service.** Release the keeper's split crown, pull the keeper down, then slide the bar outward. Retention force, bar stiffness, keeper life and warm ASA creep remain untested. H-R1 is a fixed-size add-on; editing the old Rev H parameter spreadsheet does not automatically adapt it.

Keep these evidence distinctions in the listing and any responses to adopters:

- Native checks, reopened models, STEP roundtrips, closed meshes and plate-clearance checks support the delivered geometry. Six M1 examples were checked at nine dam indices each. Sampled service motions are not a complete physical assembly test.
- The reviewed toolpaths contain no disconnected floating components. M1 still has unsupported overhang-wall runs up to 8.99 mm at the fan hanger and 6.12 mm at dam slots; its bridge-tagged maximum alone is only 3.02 mm. H-R1's maximum unsupported deposition span is 3.28 mm. These screens do not prove ASA sag or adhesion. The coupons target the relevant interfaces.
- M1 has no CFD or cooling benchmark. Rev F's historical simulations are not results for M1 or Rev H. Rev H has ongoing CFD commissioning with unresolved validation limits; link its current report if useful, but do not market it as proven suction, settled airflow or lower laptop temperatures. H-R1 preserves the original duct airways and adds no airflow result.

The CFD agent's latest coordination update identifies the new [four-hour exploratory sequence](https://thereprocase.github.io/dell-5560-wall-mount/simulation/revh-transient/sequence/). Its `simulation/revh-transient/sequence/run-status.json` is separate from the older four-frame pilot's `simulation/revh-transient/status.json`. Do not use the pilot file to report the new run's progress. Hourly videos are scheduled around 13:12, 14:12, 15:12 and 16:12 EDT on September 8, plus rendering time; those are publication targets, not evidence that a video or simulation milestone has completed. Recheck the sequence page when preparing listing links. The CFD agent will fetch and merge before each publication; reciprocate before any repository publication of your own. Keep this coordination detail in the handoff, not as a fixed schedule in the MakerWorld listing.

The ready-made ZIPs live under `docs/downloads/`: `Minimalist_M1_5560.zip`, the five other `Minimalist_M1_<preset>.zip` archives, `Minimalist_M1_Fit_Coupons.zip`, `Precision_5560_RevH_Prototype_STEP.zip`, `Precision_5560_RevH_Print_Set.zip`, and `Precision_5560_RevH_Removable_Retainers_R1.zip`. They are also available through the public guides. Use the manifests and `minimalist/reports/release.json` or `revh_retention/release-report.json` to verify identity. The M1 archives retain `M1` in their filenames; their release reports identify the contents as **M1.1**. Do not rename versions based only on the ZIP name.

Standard model 3MF files contain geometry and orientation, not printer settings. STEP and STL are alternative representations of the same parts. The assembled STEP is for inspection, not a printable plate. Separately labeled Orca review archives contain reviewed settings and embedded G-code; they are not automatically suitable MakerWorld print profiles or universal ready-to-print jobs.

Check MakerWorld's current model-image requirements, supported upload formats and print-profile attestations in its upload UI. Bambu's [published print-profile policy](https://blog.bambulab.com/makerworld-in-20-days/) requires real printed-result photographs as evidence. Do not mark a render as a real photograph or certify an unprinted profile as tested. Do not assume uploading raw models removes current model-photo requirements. If qualifying photos are missing, complete the files, description, gallery and draft, then identify the exact missing evidence. If the platform requires Bambu Studio for profile creation, explain that specific fallback, preserve the Orca-reviewed orientations and process, and inspect the resulting Bambu slice—especially the Rev H bridges. Saving a file through another slicer does not transfer the old validation to its new paths.

Use images from the matching current native model. Good M1 assets are `docs/assets/minimalist-native.png`, `minimalist-with-envelopes.png`, the wall-junction before/after images and `minimalist-key-diagram.svg`. Good H-R1 assets are `docs/assets/revh-retainers-installed.png`, `revh-retainers-lower.png`, `revh-retainers-upper.png` and `revh-retainers-removed.png`. Label CAD renders, transparent reference envelopes and added-material highlights accurately. Gold reinforcement is part of a single fused arm, not a separately printed insert. Supplement with genuine photographs of the exact printed revision when available. Avoid using the historical Rev F hero image as a current Rev H assembly photograph.

The repository's current license is **MIT**, copyright 2026 `thereprocase`. Include the license and preserve attribution; do not silently select a different license or enroll the existing public release in an exclusivity arrangement. If the platform cannot represent the intended license, resolve that specific choice with the owner. Use the owner's configured identity for any commits, with no AI author/co-author trailers or badges. Run a final privacy pass over upload files, image metadata, embedded paths and profile metadata, preserving intentional public attribution.

Ask early adopters to report the exact revision and preset, measured laptop and fan dimensions, printer/nozzle/material/settings, coupon results, difficult interfaces, bridge sag, cracking or keeper release problems, and photos showing the issue. Later cooling observations should record ambient temperature, workload, fan settings and dam position so comparisons are interpretable. Invite feedback through the listing and the linked repository without promising a load rating or a particular temperature reduction.

Your completion report should identify each listing or draft URL, the uploaded revision/files, included profiles and actual print evidence, chosen license, working guide links, and any specific unresolved publication requirement. Re-download a representative uploaded file and check its contents, units, orientation and completeness. Keep the public descriptions focused on choosing a variant, printing the coupon, assembling it and reporting useful results; the engineering history can remain in the linked documentation.
