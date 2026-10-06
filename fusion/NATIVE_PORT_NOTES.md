# Native Fusion port — working engineering record

The user requested one complete native document with parameter-driven sketches,
durable operations, logical timeline groups and component colors. The original
CadQuery Revision F exports remain the geometry authority. The FreeCAD port in
another worktree is independent.

## Live workflow

`FusionNativeBridge` watches only `fusion/queue/*.request.json`. Background work
only schedules Fusion custom events; all CAD API operations run on the main
thread. Workspace Python modules reload for each command. Requests/results are
retained, including failures. No network listener and no Onshape calls.

There is one production document, identified by the `Dell5560/nativePort`
attribute. Part rebuilds replace only the named generated component in that
document. The user closed the initial disposable helper checks. Do not create
more test documents or replace the user's pin pilot.

## Modeling choices

- Six authored part families; handed partners use associative native mirrors.
- Shared wall/joint datums, pin interface dimensions, fan pose and outlet gap.
- Part-specific dimensions have family prefixes and explanatory comments.
- Origin-offset construction planes, rather than generated-face attachments.
- Rectangles use anchored corners, horizontal/vertical constraints and two
  driving dimensions. Polygon profiles use constrained edge chains with driving
  dimensions. Datum axes alone use fixed endpoints; profiles are not fixed.
- Source rounding occurs before union/cuts when that order affects geometry.
- Repeated tray guards and vent tools use native rectangular patterns.
- The duct uses three two-station loft spans to preserve the ruled channel.
- Named stage groups organize load paths, lightening, airflow and interfaces.
- Each family has a consistent component color shared with its handed partner.

## Fusion API findings established by execution

1. Fixing a sketch construction line does not fully constrain its endpoints.
   Fixing the two datum endpoints does. Check `sketch.isFullyConstrained`.
2. Repeated ordinate dimensions conflicted on the pin profile. Constrained edge
   chains worked and are clearer to edit. Rectangle anchor/width/height works.
3. `Line3D` has start/end points, not a `direction` property. Axial fillet
   selection uses the vector between them.
4. Rotate Move needs an assembly-context proxy for a component origin axis.
   Activating the occurrence or replacing the axis with a sketch line did not
   solve the context mismatch. `axis.createForAssemblyContext(occurrence)` did.
   This behavior is also documented in the [Autodesk forum example](https://forums.autodesk.com/t5/fusion-api-and-scripts-forum/quot-invalid-entity-quot-when-defining-a-rotate-move-feature/td-p/12358591).
5. FusionUnitsManager.defaultLengthUnits is read-only. Expressions explicitly
   specify mm, API geometry uses cm, and angles explicitly use deg.
6. Collapsed timeline groups affect visible timeline indexing; inventory the
   actual objects before reorganizing history.

## Geometry fidelity findings

- Pin, rail, tray and cap: valid single solids; both directional Boolean
  differences empty against the source STEP exports.
- Cradle: OCCT omits the shallow front-tine corner round at Y84/Z0. Fusion's
  additional R2 fillet removes 0.0059950433 mm3, with maximum deviation
  0.002186 mm. The recipe explicitly omits that corner to preserve the source;
  corrected export has empty Boolean differences.
- Duct: a 0.049564 mm3 socket/channel junction difference is being resolved with
  an explicitly bounded relief derived from the first inner ruled wall. Do not
  redrill the entire socket: that removes additional material absent in source.
- Raw kernel volume integrals disagree slightly even when Boolean differences
  are empty. Independent converging tessellation distinguishes integration
  error from actual geometry differences. Do not relax the Boolean tolerance.

## Parameter evidence

`output/native/parameter_checks.json` records nine live edit/restore cases:
outletGap 8/16, pinHeadRadius4.5, pinSplitWidth1.2, pinSplitRoot4.5,
keyClearance.35, tray_height38, ductSkin2.2, tine_height96 (mm).
All passed with no underconstrained sketches or unhealthy features. Maximum
restored volume difference was about 6.3e-8 mm3. These checks establish those
edits, not arbitrary parameter ranges or physical load/print qualification.

## Remaining verification at this checkpoint

Corrected duct export, mirrored assembly, final parameter propagation, image
inspection and final archive validation are still pending. The working archive
is overwritten after successful stages; the final archive will be separate.
