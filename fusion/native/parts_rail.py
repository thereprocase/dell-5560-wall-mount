"""Native Fusion outlet rail, matching build_mount.right_rail (Revision F).

Coordinates are millimetres in the installed right-hand frame.  The builder
preserves sketches/extrusions/booleans in the timeline and accepts expressions
for profile coordinates and extrusion extents.  Mirroring is the caller's job.
"""


def build(b):
    """Build and return the right outlet rail at the shared outletGap value."""
    top = "outletZ"
    bottom = "railBottomZ"
    outer = "outboardX"
    cheek_t = b.param("railCheekThickness", 4, "Outer cheek and diagonal arm thickness")
    panel_t = b.param("railPanelThickness", 2, "Lower air panel thickness")
    skin_inset = b.param("railSkinInset", 2.4, "Outlet skin horizontal inset")
    bridge = b.param("railDriverBridge", 4, "Printable flat over the wall-driver passage")

    cheek_inner = f"{outer} - {cheek_t}"
    outlet_front = "wallGap - outletGap"
    outlet_back = f"wallGap - outletGap - {skin_inset}"

    with b.group("Rail - continuous outlet air skin"):
        panel = b.box("Lower air panel", .2, 139, 0, panel_t, bottom, 198)
        ramp = b.prism(
            "Inclined outlet skin", "YZ", .2,
            [(0, 196), (4, 198), (outlet_front, f"{top} - 6 mm"),
             (outlet_front, top), (outlet_back, top),
             (outlet_back, f"{top} - 5 mm"), (0, 201)],
            f"{cheek_inner} - 0.2 mm",
        )
        rail = b.join("Join panel and continuous skin", panel, ramp)

    with b.group("Rail - cheek and structural supports"):
        # XZ has normal -Y: extrusion from Y=30.3 through 4 mm ends at 26.3.
        arm = b.prism(
            "Diagonal joint arm", "XZ", 30.3,
            [(140, bottom), (outer, bottom), (outer, top),
             (cheek_inner, top), (140, 188)],
            cheek_t,
        )
        cheek = b.box("Outer air cheek", cheek_inner, outer, 0, "wallGap - 1 mm", bottom, top)
        lip = b.box("Laptop-side retaining lip", "outboardX - 10.6 mm", outer,
                    "wallGap - 3 mm", "wallGap - 1 mm", bottom, top)
        link = b.box("Upper wall-side link", 136, outer, 0, 4, f"{top} - 6 mm", top)
        rib = b.prism(
            "Outlet end reinforcement", "YZ", 136,
            [(0, 196), (4, 198), (outlet_front, f"{top} - 6 mm"),
             (outlet_front, top), (0, top)],
            4,
        )
        rail = b.join("Join cheek lip arm link and rib", rail, arm, cheek, lip, link, rib)

    with b.group("Rail - glued cradle joint tenons"):
        rail = b.join("Join sloped rail tenons", rail, *b.keys("Rail tenons", "rail"))

    with b.group("Rail - wall-driver access and lower clearance"):
        driver = b.roof_hole(
            "Upper wall-driver clearance", 10, "wallGap + 2 mm",
            ("wallBoltX", -1, "upperWallBoltZ"),
            roof="-Z", bridge=bridge,
        )
        rail = b.cut("Cut printable driver passage", rail, driver)
        clearance = b.box(
            "Lower cheek clearance tool", f"{cheek_inner} - 0.3 mm",
            f"{outer} + 0.3 mm", -.3, 26.3,
            f"{bottom} - 0.3 mm", 184.3,
        )
        rail = b.cut("Open lower cheek for cradle joint", rail, clearance)

    return rail
