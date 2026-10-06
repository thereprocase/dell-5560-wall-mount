# Minimalist release development

## Scope and current boundary

Revision H is the ducted prototype. Its exact native model and prototype print
files remain available. Subsequent ducted releases may redesign the arms too;
the prototype's print freeze is not a permanent product constraint.

The minimalist fork is a complete independent set with no frozen parts. Its
purpose is to hold a laptop on a wall and point fans up its back while reducing
plastic and print time. Most enclosed ducting is removed. Structural webs,
fastener lands and working airflow surfaces retain the material they need.

Deliver an editable native FreeCAD model descended through Save As from the
Revision H model, with constrained sketches, stock features, an organized
parameter sheet, and reproducible builders. Keep construction visible in the
FreeCAD GUI and read its error log. Maintain 0.30 mm nominal clearance at new
printed mating surfaces, documenting intentional retention interference.

The target printer is a P1S with a 0.4 mm nozzle and ASA. OrcaSlicer is the
default for preparation and review. STEP/STL/3MF outputs carry their actual
print orientations; CAD acceptance and sliced paths do not prove physical fit
or warm-load durability.

## Implementation sequence

1. Preserve the Rev H prototype and supply print-oriented STEP files.
2. Create `codex/minimalist-release` in its own worktree and Save As the FCStd.
3. Build perforated structural arms, open fan cradles and removable retainers.
4. Add a positive ladder adjustment: two rungs engaged by a removable key,
   retained by a printed pin. The optional dam moves in discrete vertical steps.
5. Parameterize actual laptop width, base-to-hinge depth, closed thickness,
   rear wall gap, and fan dimensions. Screen-size labels are convenience presets,
   not a fit guarantee. Include 13, 14, 15.6, 16 and 17 inch classes.
6. Validate nominal and changed configurations, assembly and service clearances,
   load-path estimates, native reopen, meshes, and P1S-oriented slices. Compare
   material and print time with the ducted prototype using stated settings.
7. Publish the model, print files, measured comparison and interactive Pages
   presentation. Complete the Rev H gallery's missing corrected-geometry views.

## CFD coordination

The CFD collaborator owns `fusion/cfd/` additions and a self-contained
`docs/simulation/revh-transient/` package in `codex/cfd-revh-transient`.
The main Pages layout and minimalist model are owned here. Integrate the CFD
package when the collaborator provides actual results and provenance. The
836,278-cell Revision F exploration must never be relabeled as Revision H or
minimalist CFD. There are no new CFD results at this sprint's start.

## Checkpoints

- 2026-09-08: recovered the complete interrupted conversation and scope.
- 2026-09-08: all 14 Rev H STEP exports reimported as valid solids, matched
  released STL bounds, and delivered in print orientation for the prototype.
- 2026-09-08: independent minimalist branch/worktree created from `f47a03f`.

- 2026-09-08: native M1 complete: 20 installed parts, 51 constrained sketches,
  six dimensioned presets and all nine indexed dam positions checked.
- 2026-09-08: every preset saved/reopened, with valid STEP roundtrips, closed
  print meshes and P1S bed/brim/cutter clearance. Native clean reconstruction
  from the preserved H source also passes the nominal independent validator.
- 2026-09-08: full nominal Orca estimate 388.05 g / 15 h 24 m 54 s, compared
  with 1183.88 g / 34 h 00 m 15 s for the complete H layout. The expanded
  path review includes Overhang wall and all other extrusion features; bridge
  labels alone omitted 8.99 mm fan-hanger and 6.12 mm dam-slot spans.
- 2026-09-08: eight native-derived fit samples include both attachment build
  directions. Physical fit, retention, creep, anchors and cooling remain open.
- 2026-09-08: interactive site passed six-preset, dam-index, exploded-view,
  Rev F/H comparison, CFD gallery and mobile-layout checks. Archive publication
  and final download verification follow the completed all-feature path audit.

- 2026-09-08: all 60 full/optional production plate alternatives and the coupon
  passed the deposited-path screen; seven delivery archives have verified hashes.
- 2026-09-08: merged CFD publication `67fa835` through `188d49e`, preserving
  both histories and all collaborator files. The showcase links the Rev H
  commissioning report with failed expanded checks and 0.0203084 ms completed
  of the planned 2 ms explicit; no shedding, Bernoulli or validation claim.
- 2026-09-08: restored headless preset GUI data in FreeCAD archive order,
  preserving every geometry/parameter stream. All six final native presets
  open in the live GUI with 20 visible parts, five colors and no feature errors.
- 2026-09-08: final local browser review passes both interactive assemblies,
  all six presets, indexed and optional dam controls, mobile layouts, 16
  download links and the CFD commissioning link/status. The final privacy scan
  reports no findings across 218 unique archive payloads. Ready to publish the
  combined release; physical qualification remains explicitly outstanding.

- 2026-09-08 / M1.1: reinforced only the Minimalist wall junctions: 32 mm
  pads and paired 6 mm tapered webs with roots continuous to the print face.
  Matching dam relief preserves all nine positions. All six presets passed
  native/save/reopen/export checks; a clean reconstruction matches all 20 parts.
  The other sixteen part geometries and preserved Rev H source are unchanged.
  Nominal Orca estimate is 400.55 g / 15 h 42 m 30 s (+12.50 g / 17 m 36 s).
  Restored the root README's nine-stage Rev F design story and seven working
  images, with clear historical labels and the new M1.1 before/after comparison.
  Final M1.1 review: all 61 current plate audits have zero disconnected
  floating components; revised arm prior-layer unsupported spans stay below
  0.38 mm. All seven archives passed hashes and offline image/link checks.
  Desktop/mobile browser checks passed all six presets, dam controls and
  sixteen downloads. The six saved presets opened in the live FreeCAD GUI
  with twenty visible parts, restored colors and no invalid features.
