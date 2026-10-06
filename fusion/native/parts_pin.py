"""Revision F split push pin using a native axial revolve and centered slot.

Nominal axial profile follows the verified FusionPinPilot; the shared Builder
fully constrains every profile ordinate, including the split root and centering.
The caller supplies the shared pin user parameters and installed occurrences.
"""
import adsk.core as c
import adsk.fusion as f


def build(b):
    """Return the local +Z push-pin body; installation is a caller transform."""
    shoulder_z = "pinHeadHeight + pinShaftLength"
    tip_z = "pinHeadHeight + pinShaftLength + pinCrownHeight"
    with b.group("01 Pin head, shaft and retaining crown"):
        profile = b.polygon(
            "Pin axial section", "XZ", 0,
            [(0, 0),
             ("pinHeadRadius", 0),
             ("pinHeadRadius", "pinHeadHeight - pinHeadChamfer"),
             ("pinHeadRadius - pinHeadChamfer", "pinHeadHeight"),
             ("pinShaftDiameter / 2", "pinHeadHeight"),
             ("pinShaftDiameter / 2", shoulder_z),
             ("pinCrownDiameter / 2", shoulder_z),
             ("pinTipRadius", tip_z),
             (0, tip_z)],
        )
        revolve_input = b.c.features.revolveFeatures.createInput(
            profile.profiles.item(0), b.c.zConstructionAxis,
            f.FeatureOperations.NewBodyFeatureOperation,
        )
        revolve_input.setAngleExtent(False, c.ValueInput.createByString("360 deg"))
        revolve = b.c.features.revolveFeatures.add(revolve_input)
        revolve.name = "Pin | full axial revolve"
        body = revolve.bodies.item(0)
        body.name = "Revision F split push pin"
        profile.isVisible = False

    with b.group("02 Centered compliant split"):
        cutter = b.box(
            "Pin centered split cutter", "-pinSplitWidth / 2", "pinSplitWidth / 2",
            -3, 3, "pinSplitRoot", f"{tip_z} + pinSplitOverrun", axis="Y",
        )
        body = b.cut("Pin | open compliant split", body, cutter)
        body.name = "Revision F split push pin"
    return body
