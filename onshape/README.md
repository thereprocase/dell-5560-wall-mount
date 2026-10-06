# Native Onshape rebuild

**Status: native push-pin pilot built and tested; full mount rebuild remains unfinished.**

The 2026-09-07 exploration used 34 of 40 authorized request attempts. The document now has a constrained native pin, 38 shared variables and four positioned pin instances in its Assembly tab. See [EFFICIENT_NATIVE_WORKFLOW.md](EFFICIENT_NATIVE_WORKFLOW.md) for tested batching methods, validation limits and the next execution plan, and [RESEARCH_NOTES.md](RESEARCH_NOTES.md) for the running evidence notebook.

Current user direction: each distinct part gets its own Part Studio tab, with reusable instances in an Assembly. The grouped family descriptions below remain construction guidance; handed parts should occupy separate tabs.

Target: [Dell Precision 5560 Wall Mount - Native Rebuild](https://cad.onshape.com/documents/c452b7f3224726ea2f11cdda/w/3231ffbfcf00782c1dba2494).
Created on 2026-09-07 with one API request (HTTP 200); IDs saved in local ignored `.env`.
See [MCP_WORKFLOW.md](MCP_WORKFLOW.md) for connection status, quota constraints and the modeling workflow.

The current Revision F source is CadQuery. STEP carries its boundary geometry, but the native Onshape deliverable must reconstruct the design history and relationships. This directory records that reconstruction so it can proceed in a session with authenticated Onshape access.

## Deliverable structure

| Tab | Contents |
|---|---|
| Design variables | Shared dimensions and fit allowances from `design_parameters.json` |
| Layout | Wall plane, symmetry plane, laptop envelope, vent band, fan planes, bolt centers and service directions |
| Cradles | Right cradle plus a native mirror for the left |
| Fan ducts | Right duct plus mirror |
| Fan trays | Right tray plus mirror |
| Fan caps | Right cap plus mirror |
| Outlet rails | Right rail plus mirror; 8 / 12 / 16 mm configurations |
| Push pin | One reusable pin part |
| Installed assembly | Ten handed parts and four instances of the pin: 14 printed instances |

The working geometry should use ordinary constrained sketches, extrudes, removes, lofts, patterns, mirrors and fillets. Keep those features named and individually editable. Use shared variables and layout references for mating interfaces. The supplied STEP is the baseline for comparison, not the source feature of the native design.

A custom FeatureScript can automate repetitive work if needed. A single custom feature containing the entire mount would not provide the ordinary feature-tree editing specified here.

## Feature structure

### Layout and variables

Coordinates remain X across the laptop, Y outward from the wall and Z upward. Set the wall at Y = 0 and the symmetry plane at X = 0. Establish mating references from this skeleton before adding pockets or fillets.

The current Python geometry contains hard-coded coordinates alongside named dimensions. Native variables therefore require dependency refactoring; changing one existing Python constant is not sufficient to move every mating face coherently. Rebuild the relationships explicitly, starting from the current nominal dimensions.

### Cradles

Source: `base_geometry.py: right_cradle()` and `build_mount.py: right_cradle()`.

1. Constrain the side profiles for the wall back, shelf, lower pad, front tine and upper support.
2. Extrude the structural sections to their specified widths; retain the tapered tine and diagonal gussets.
3. Add the duct saddle receiver, outlet receiver, side cheek and inward lip.
4. Cut the two wall holes and the lower tool clearance with their printable roofs.
5. Cut the spine, shelf and tine cavities and the web windows. Preserve the side-print skin thicknesses.
6. Cut the duct and rail key pockets using the shared key definitions and clearances.
7. Apply the original outline and cavity fillets at the appropriate construction stage. Some fillets precede booleans in the source; moving all fillets to the end may change the shape or fail.
8. Mirror the finished right cradle across the layout symmetry plane.

### Fan ducts

Source: `build_mount.py: loft_channel()` and `right_duct()`.

1. Define the four outer section profiles in the layout. Construct the inner profiles from their specified insets.
2. Reproduce the ruled outer and inner lofts and subtract the inner volume. A smooth global loft would change the existing plenum.
3. Build the fan deck, inlet aperture, side bosses, dovetail grooves and pin sockets in the fan coordinate system.
4. Position the deck from the shared fan plane.
5. Add the keyed saddle and sloped buttress, then cut the wall-bolt tool corridor.
6. Mirror the completed duct.

If the Onshape loft interface cannot reproduce the same ruled transitions in one feature, loft adjacent profile pairs with straight transitions and join them. Compare the resulting surfaces with the STEP baseline.

### Fan trays

Source: `base_geometry.py: right_tray()` and `tongue()`; placement in `build_mount.py: tilt()`.

1. Build the tray frame, fan ledges and end stop in the fan coordinate system.
2. Add the grille bars and central support with native patterns.
3. Add the two male dovetails using the same master section as the duct grooves.
4. Cut the side and end windows and ledge pockets.
5. Position the tray from the shared fan plane and mirror it.

### Fan caps

Source: `base_geometry.py: right_cap()` and `build_mount.py: right_cap()`.

1. Extrude the cap outline and locating toe.
2. Cut the face flutes, cable notch and pin passages.
3. Pocket the rear while preserving the face, perimeter and ribs.
4. Apply the source corner radii, position from the fan plane and mirror.

### Outlet rails

Source: `build_mount.py: right_rail()` and `tenons()`.

1. Sketch the lower panel, contraction and outlet lip in the YZ plane.
2. Drive the throat from `outletGap`, with configuration choices 8, 12 and 16 mm.
3. Add the support arm, cheek, inward lip, top link and end rib.
4. Add the keyed attachment from the shared rail-key geometry.
5. Remove the wall-bolt corridor and cradle overlap relief.
6. Mirror the rail. Couple both halves to the same outlet configuration.

Keep the contraction start, throat and outlet heights explicit. Any changes must be checked against the vent band and the intended lip-down print orientation.

### Push pin

Source: `build_mount.py: pin()`.

1. Extrude the button and chamfer its upper edge.
2. Extrude the shaft.
3. Loft the retaining crown to its smaller tip.
4. Cut the axial split.
5. Use four instances in the assembly.

## Assembly and service states

Use explicit mate connectors tied to layout planes and interface centers. Avoid transient fillet edges as mating references.

- Locate both cradles from the wall layout and fix them in the installed assembly.
- Fasten each duct and rail to its cradle at the seated keyed joint.
- Give each tray a slider along its dovetail direction for service inspection. At 45°, the outward removal direction is `(0, +1/sqrt(2), +1/sqrt(2))`.
- Fasten the caps and pin instances in the installed state; use an exploded/service view to show removal.
- Keep the laptop and fan envelopes as reference components excluded from the printed-part count.
- Check the laptop with a 105 mm vertical lift followed by outward movement. This is a two-stage removal path, not a single unrestricted slider.

The fixed joints represent CA assembly. Assembly mates do not establish adhesive strength, pin retention or physical clearances.

## Native acceptance checks

`revision_f_baseline.json` preserves the current part volumes, bounding boxes and fit results, linked to source and STEP hashes.

1. Regenerate all native features without errors at the Revision F defaults.
2. Confirm 11 distinct modeled parts: five mirrored pairs and one pin; confirm 14 printed instances in the assembly.
3. Export the assembly to STEP. Compare each part's volume, bounds and symmetric geometric difference against Revision F. Matching volume alone is insufficient.
4. Investigate any differences above CAD numerical noise. Do not label a changed loft or omitted fillet an exact conversion.
5. Repeat the wall-driver, laptop, fan, tray and joint insertion checks from `validate_assembly.py` against the native export.
6. Check both outlet alternatives and several small changes to the exposed dimensions. Verify that mating parts update together and do not introduce interference or unsupported print geometry.
7. Confirm the default native export still supports the supplied print orientations. Re-run the layer and strength checks after geometric changes.
8. Save a named Onshape version of the validated nominal design and document which parameter changes were exercised.

The existing structural and CFD results apply to the checked Revision F geometry and assumptions. Native parameter edits need appropriate revalidation.

## Access required to continue

An authenticated Onshape API integration with document read/write access is needed to create the Part Studios, assembly and configurations, and to verify regeneration and exports. A document URL identifies the destination but does not authenticate this session.

Official references: [Onshape feature API](https://onshape-public.github.io/docs/api-adv/featureaccess/), [FeatureScript](https://cad.onshape.com/FsDoc/), [standard library](https://cad.onshape.com/FsDoc/library.html).
