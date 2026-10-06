"""Native Fusion construction of the un-tilted Revision E tray and cap.

Revision F applies placement tilt after construction; it does not alter these
local solids.  Coordinates and operation order follow base_geometry.py.
The builder supplies sketch/extrude/fillet/combine operations, not BRep imports.
"""


def _offset(expression, millimeters):
    """Keep feature dimensions dependent on an existing user parameter."""
    if millimeters == 0:
        return expression
    return f"({expression}) + ({millimeters} mm)"


def build_tray(b):
    """Build the right tray in source coordinates, with its guard at Z=-146."""
    height = b.param("tray_height", 36, "Tray depth below the fixed Z=-110 duct interface")
    ledge_thickness = b.param("fan_ledge_thickness", 7, "Fan support ledge thickness")
    guard_thickness = b.param("guard_thickness", 3, "Printed fan finger-guard thickness")
    guard_width = b.param("guard_rib_width", 2.4, "Finger-guard crossbar and spine width")
    guard_pitch = b.param("guard_rib_pitch", 12, "Fan finger-guard crossbar spacing")
    side_vent_pitch = b.param("side_vent_pitch", 20, "Side ventilation window spacing")
    rear_vent_pitch = b.param("rear_vent_pitch", 22, "Rear stop ventilation window spacing")
    # Keep the mating beams and tongues fixed when changing the fan depth.
    top = "-110 mm"
    bottom = f"({top}) - ({height})"
    ledge_top = f"({bottom}) + ({ledge_thickness})"
    guard_top = f"({bottom}) + ({guard_thickness})"

    with b.group("Tray walls and fan support ledges"):
        side_l = b.box("Inboard tray wall", 1, 5, 4, 136, bottom, top)
        side_r = b.box("Outboard tray wall", 135, 140, 4, 136, bottom, top)
        stop = b.box("Rear fan insertion stop", 1, 140, 4, 9, bottom, top)
        ledge_l = b.box("Inboard fan support ledge", 1, 19, 4, 136, bottom, ledge_top)
        ledge_r = b.box("Outboard fan support ledge", 121, 140, 4, 136, bottom, ledge_top)

    with b.group("Tray fan finger guard"):
        crossbar = b.box(
            "Guard crossbar seed", 8, 133, 16, f"16 mm + ({guard_width})",
            bottom, guard_top,
        )
        guard = b.pattern("Ten fan guard crossbars", crossbar, "Y", 10, guard_pitch)
        guard.append(b.box(
            "Guard central spine", 69, f"69 mm + ({guard_width})",
            4, 136, bottom, guard_top,
        ))

    with b.group("Tray dovetail support beams and lands"):
        # XZ has a -Y normal, so origin Y=136 and depth 132 span Y=4..136.
        beam_profile = [
            (1, _offset(top, -9)), (5, _offset(top, -9)),
            (9, _offset(top, -5)), (9, top), (1, top),
        ]
        beam = b.prism("Inboard dovetail support beam", "XZ", 136, beam_profile, 132)
        # Exact equivalent of source mirror('YZ').translate((140, 0, 0)).
        other = b.prism(
            "Outboard dovetail support beam", "XZ", 136,
            [(140 - x, z) for x, z in beam_profile], 132,
        )
        lands = [
            b.box(
                f"{side} {end} dovetail support land", x0, x1, y0, y1,
                ledge_top, top,
            )
            for side, x0, x1 in (("Inboard", 5, 9), ("Outboard", 131, 135))
            for end, y0, y1 in (("Rear", 9, 30), ("Front", 110, 136))
        ]
        tongues = [
            b.tongue(f"{side} duct slide tongue", x, 9, 135.5)
            for side, x in (("Inboard", 5), ("Outboard", 135))
        ]
        # Match the original fuse order, including guard and tongues last.
        tray = b.join(
            "Join tray frame guard and slide tongues", side_l, side_r, stop,
            ledge_l, ledge_r, beam, other, *lands, *guard, *tongues,
        )

    with b.group("Tray side ventilation windows"):
        profile = [
            (16, _offset(top, -26)), (32, _offset(top, -26)),
            (32, _offset(top, -14)), (26, _offset(top, -8)),
            (22, _offset(top, -8)), (16, _offset(top, -14)),
        ]
        for side, x0, x1 in (("Inboard", 0, 9.1), ("Outboard", 130.9, 141)):
            name = f"{side} side vents"
            tool = b.prism(f"{name} seed tool", "YZ", x0, profile, x1 - x0)
            tools = b.pattern(f"Six {side.lower()} ventilation windows", tool, "Y", 6, side_vent_pitch)
            tray = b.cut(name, tray, *tools)

    with b.group("Tray rear ventilation windows"):
        profile = [
            (22, _offset(top, -26)), (38, _offset(top, -26)),
            (38, _offset(top, -14)), (32, _offset(top, -8)),
            (28, _offset(top, -8)), (22, _offset(top, -14)),
        ]
        tool = b.prism("Rear stop vent seed tool", "XZ", 10, profile, 7)
        tools = b.pattern("Five rear stop ventilation windows", tool, "X", 5, rear_vent_pitch)
        tray = b.cut("Rear stop vents", tray, *tools)

    with b.group("Tray fan ledge weight relief"):
        for side, x0, x1 in (("Inboard", 9, 19), ("Outboard", 121, 131)):
            name = f"{side} ledge relief"
            tool = b.box(f"{name} tool", x0, x1, 36, 104, guard_top, ledge_top)
            tray = b.cut(name, tray, tool)
    return tray


def build_cap(b):
    """Build the right removable fan-tray cap before Revision F placement."""
    front_y = b.param("front_print_face_y", 144, "Cap outer print-bed face, local Y")
    thickness = b.param("cap_thickness", 8, "Cap body depth before weight relief")
    outer_skin = b.param("outer_face_thickness", 2.4, "Continuous outer cap face")
    screw_radius = "pinPassageDiameter / 2"
    rear_y = f"({front_y}) - ({thickness})"
    pocket_y = f"({front_y}) - ({outer_skin})"

    with b.group("Cap rounded plate and locating toe"):
        cap = b.box("Cap outer plate", 1, 140, rear_y, front_y, -146, -97, fillet=4, axis="Y")
        toe = b.box("Tray locating toe", 14, 126, 131, 137, -138, -112, fillet=3, axis="Y")
        cap = b.join("Join cap plate and locating toe", cap, toe)

    with b.group("Cap print-friendly outer V flutes"):
        for index, z in enumerate((-131, -125), 1):
            name = f"Outer V flute {index}"
            tool = b.prism(
                f"{name} profile tool", "YZ", 30,
                [(_offset(front_y, 0.1), z - 1.5),
                 (_offset(front_y, 0.1), z + 1.5),
                 (_offset(front_y, -1.4), z)],
                80,
            )
            cap = b.cut(name, cap, tool)

    with b.group("Cap cable passage and retaining screws"):
        cable = b.box("Rounded cable passage tool", 117, 127, 130, 145, -115, -106, fillet=2, axis="Y")
        cap = b.cut("Cable passage", cap, cable)
        for side, x in (("Inboard", 5), ("Outboard", 135)):
            tool = b.cylinder(f"{side} cap screw tool", screw_radius, 10, (x, 135, -103), axis="Y")
            cap = b.cut(f"{side} cap screw clearance", cap, tool)

    with b.group("Cap internal pockets preserving rim and ribs"):
        # Preserve both overlapping source pocket passes and their order.
        # The first pass and the larger second pass are intentionally separate.
        for index, (x0, x1) in enumerate(((18, 45), (47, 94), (96, 122)), 1):
            name = f"Locating toe relief {index}"
            tool = b.box(f"{name} tool", x0, x1, 130, pocket_y, -134, -116, fillet=2, axis="Y")
            cap = b.cut(name, cap, tool)
        for index, (x0, x1) in enumerate(((4, 45), (47, 94), (96, 136)), 1):
            name = f"Lower cap rim and rib pocket {index}"
            tool = b.box(f"{name} tool", x0, x1, 130, pocket_y, -141, -111, fillet=2, axis="Y")
            cap = b.cut(name, cap, tool)
        tool = b.box("Upper cap weight relief tool", 12, 129, 130, pocket_y, -111, -99, fillet=2, axis="Y")
        cap = b.cut("Upper cap weight relief", cap, tool)
    return cap
