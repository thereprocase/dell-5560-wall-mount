"""Native right cradle, matching Revision F's ordered CSG construction.

Sources: base_geometry.right_cradle, then build_mount.right_cradle.
The caller mirrors this finished component for the left-hand cradle.
All profile coordinates remain in the assembly X/Y/Z coordinate system.
"""


def build(b):
    """Build the cradle with native, constrained profiles through the builder."""
    # Shared assembly datums keep mates and all part families in agreement.
    outer = "outboardX"
    width = b.param("width", 44, "Cradle width inward from the outboard bed face")
    anchor_x = "wallBoltX"
    anchor_low = "lowerWallBoltZ"
    anchor_high = "upperWallBoltZ"
    tine_h = b.param("tine_height", 94, "Front retention tine tip height")
    shroud_top = b.param("shroud_top_z", 153.7, "Air shroud top; clearance below rail")
    skin_t = b.param("shroud_thickness", 4, "Outboard air shroud thickness")
    lip_inset = b.param("lip_inset", 10.6, "Inward lip reach from outboard face")
    glue_gap = "keyClearance"

    def x_from_outer(distance):
        return f"({outer}) - {distance} mm"

    inner = f"({outer}) - ({width})"
    tine_below = f"({tine_h}) - 6 mm"
    tine_taper_x = f"({inner}) + 10 mm"

    with b.group("01 Load-bearing cradle blanks"):
        back = b.box("Backplate | R4 outline", inner, outer, 0, 10, -65, 184, fillet=4)
        shelf = b.box("Laptop shelf | R2 outline", inner, outer, 0, 84, -12, 0, fillet=2)
        lower = b.box("Lower contact block | R4 outline", inner, outer, 8, 38, -1, 42, fillet=4)
        front = b.prism(
            "Front retention tine | R2 outline", "YZ", inner,
            [(64, -6), (84, -6), (84, 0), (75.1875, tine_h),
             (67, tine_h), (64, tine_below)], width,
            # Revision F's OCCT fillet omits this shallow (~5 degree) bend.
            fillet={'radius':2,'omit_vertices':[(84,0)]},
        )
        taper = b.prism(
            "Tine inboard taper cutter", "XZ", 86,
            [(f"({inner}) - 1 mm", 0), (tine_taper_x, tine_h),
             (tine_taper_x, f"({tine_h}) + 3 mm"),
             (f"({inner}) - 1 mm", f"({tine_h}) + 3 mm")], 24,
        )
        front = b.cut("Taper inboard tine face", front, taper)
        guide = b.box("Lower side guide | R2 outline", x_from_outer(9), outer,
                      36, 66, -2, 24, fillet=2)
        gusset = b.prism("Shelf diagonal gusset", "YZ", x_from_outer(8),
                         [(10, -51), (84, -12), (10, -12)], 8)
        spine = b.box("Vertical spine | R4 outline", x_from_outer(36), outer,
                      8, 26, -12, 164, fillet=4)
        upper = b.box("Upper laptop contact | R4 outline", x_from_outer(34), outer,
                      8, 38, 126, 152, fillet=4)
        upper_rib = b.prism("Upper contact diagonal rib", "YZ", x_from_outer(28),
                            [(10, tine_h), (38, 126), (10, 134)], 28)
        receiver = b.box("Lower joint receiver | R3 outline", x_from_outer(42), outer,
                         8, 26, -65, -12, fillet=3)
        rail_receiver = b.box("Outlet rail receiver | R3 outline", inner, outer,
                              8, 26, 154, 166, fillet=3)
        solid = b.join("Unite load-bearing cradle", back, shelf, lower, front, guide,
                       gusset, spine, upper, upper_rib, receiver, rail_receiver)

    with b.group("02 Wall anchors and driver access"):
        for label, z in (("Lower", anchor_low), ("Upper", anchor_high)):
            hole = b.roof_hole(f"{label} wall-anchor roofed clearance", 3.5, 12,
                               (anchor_x, -1, z), roof="-X")
            solid = b.cut(f"{label} wall-anchor bore", solid, hole)
        access = b.roof_hole("Lower anchor driver access cutter", 9, 20,
                            (anchor_x, 10, anchor_low), roof="-X", bridge=4)
        solid = b.cut("Lower anchor driver access", solid, access)

    with b.group("03 Hollow sections and retained skins"):
        hollow = b.prism(
            "Spine neutral-axis cavity | R4 outline", "YZ", x_from_outer(32.8),
            [(7, 44), (19, 44), (22, 70), (22, 150), (4, 150), (4, 70)],
            28.8, fillet=4,
        )
        solid = b.cut("Hollow spine", solid, hollow)
        for index, (y0, y1) in enumerate(((11, 21), (23, 33)), 1):
            tool = b.box(f"Lower contact cavity {index} | R2 outline",
                         x_from_outer(41.6), x_from_outer(4), y0, y1, 5, 36, fillet=2)
            solid = b.cut(f"Hollow lower contact {index}", solid, tool)
        tool = b.box("Shelf cavity | R1.5 outline", x_from_outer(41.6), x_from_outer(4),
                     14, 61, -8, -4, fillet=1.5)
        solid = b.cut("Hollow laptop shelf", solid, tool)
        tine_void = b.prism(
            "Tine cavity | R1.3 outline", "YZ", x_from_outer(42),
            [(68, 14), (78.6875, 14), (72.125, f"({tine_h}) - 10 mm"),
             (68, f"({tine_h}) - 10 mm")], 38, fillet=1.3,
        )
        inner_skin = b.prism(
            "Retained tapered tine skin mask", "XZ", 86,
            [(f"({inner}) - 1 mm", 0), (f"({inner}) + 2.2 mm", 0),
             (f"({inner}) + 13.2 mm", tine_h), (f"({inner}) - 1 mm", tine_h)], 24,
        )
        tine_void = b.cut("Trim cavity to preserve inboard tine skin", tine_void, inner_skin)
        solid = b.cut("Hollow retention tine", solid, tine_void)

    with b.group("04 Rounded shear-web windows"):
        window = b.prism("Triangular gusset window | R1.5 outline", "YZ", x_from_outer(9),
                         [(30, -33), (65, -15), (30, -15)], 10, fillet=1.5)
        solid = b.cut("Open gusset shear-web window", solid, window)
        window = b.box("Guide window | R3 outline", x_from_outer(10),
                       f"({outer}) + 1 mm", 43, 59, 5, 18, fillet=3)
        solid = b.cut("Open lower guide window", solid, window)

    with b.group("05 Revision F air shroud"):
        skin = b.box("Outboard air skin | R2 outline", f"({outer}) - ({skin_t})", outer,
                     0, 39, -10, shroud_top, fillet=2)
        lip = b.box("Inward sealing lip", f"({outer}) - ({lip_inset})", outer,
                    37, 39, 0, shroud_top)
        solid = b.join("Unite Revision F shroud and lip", solid, skin, lip)

    with b.group("06 Revision F keyed glue-joint mortises"):
        for kind in ("duct", "rail"):
            tools = b.keys(f"{kind.title()} receiver", kind, clearance=glue_gap)
            for index, tool in enumerate(tools, 1):
                solid = b.cut(f"Open {kind} mortise {index}", solid, tool)
    return solid
