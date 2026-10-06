# Manufacturing finish audit — 2026-09-07

The two gray cradles are PRINT FROZEN. `frozen_print_arms/manifest.json` identifies their exact saved BRep baselines. This freeze applied to the preserved Rev H prototype and its already-printed arms. It does not constrain future ducted or Minimalist revisions: the user explicitly authorized new arms, size variations and adjustable airflow parts. Preserve the H artifact and repeat fit and print checks for each new revision.

| Source family | Finding and action | FDM / fit boundary |
|---|---|---|
| Left/right cradles | Preserved exactly; print-freeze metadata added | Printing already started; zero Boolean difference against frozen baselines |
| Left/right outlet rails | Square clearance notch replaced with a contoured native sketch relief; rear lead-in retained; exposed tip rounded R2 | 0.30 mm fixed printed-arm clearance. A fully wrapped rear shoulder caught during insertion and was rejected |
| Left/right outlet rails, upper structure | Roof across the wall-side trough; closed side windows; 0.6 mm exposed top-edge chamfer | Central laptop-side exhaust slot stays open. Back remains open. Lip-down print orientation retained; top cover becomes bed-facing material |
| Left/right fan trays | Square lower corners projected beyond R4 front cover; added 4 mm, 45-degree corner reliefs | Retains a supported first-layer progression for guard-side-down printing. Does not alter the dovetail or fan-support ledge height |
| Left/right fan ducts | Upper backing bosses projected beyond the R4 cover outline; trimmed to matching R4 profiles with native sketch cuts | Keeps at least the checked 1.20 mm radial material band beyond the 2.05 mm socket radius. No material removed from the tested R3.25 socket-support envelope |
| Left/right front retainers | Existing R4 outline is the matching reference; retained | Bed-down face and socket/vent openings preserved |
| Shared pin (four instances) | Head bevel, tapered split crown, shaft and socket relationship retained | Functional interference and split geometry retained; no cosmetic rounding of retention surfaces |
| Keys, tray tongues and support roofs | Intentional straight/45-degree features retained | Rounding these would change seating, retention, clearance, or support-free roofs |

The fan-deck R3 rounding and cover R4 rounding lie in different planes and perform different jobs; they were not blindly standardized. The matching audit concerns exposed assembled outlines and functional interfaces.

Evidence: `rail_refinement_validation.json` checks arms, rails, laptop, screw access and discrete insertion samples; `finish_cut_validation.json` tests both fan modifications and the socket-support envelope; `fan_finish_build.json` confirms one batched GUI recompute. `clearance_validation.json` is rerun against the updated full STEP. This is geometric/print-orientation reasoning, not a completed physical print test.

Native edit points: `RailRefinement`, `RailTipRound`, `FanOutlineFinish`. Frozen-offset/finish profiles are deliberately constrained manufacturing profiles. They are editable native sketches, but later size changes need renewed fit checks; old broad parameter-test reports do not certify the refinements for arbitrary dimensions.


Follow-up: selected left duct Instance003 Faces9/10/11/24 exposed the abrupt end
of the previous R4 relief at local Y121. Added matching native R4 profiles with
45-degree oblique extrusion runouts; removes 24.7541 mm3 per duct and eliminates
the abrupt fin. Right master drives the left mirror. Socket support envelope has
zero additional removal; both arms have zero Boolean difference. One recompute.
See boss_runout_trial.json and boss_runout_build.json. The operation removes
material progressively toward the top of the inlet-down print, with a 45-degree
runout; physical bridge quality and slicer paths remain unverified.
