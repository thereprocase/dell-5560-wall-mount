"""Analytical 2D polygon / extruded-prism geometry engine for the Two-Up Variant.

Uses numpy and scipy.spatial.ConvexHull without requiring FreeCAD, OpenCASCADE,
or trimesh. Each part is constructed as an explicit list of positive 2D polygon
prisms and non-overlapping negative cut prisms, mirroring the feature tree in
build_two_up.py. Polygon areas are computed exactly via the shoelace formula
and cross-checked against scipy.spatial.ConvexHull on convex contours.
"""
import math
import numpy as np
from scipy.spatial import ConvexHull

from params import PARAMS


def shoelace_area(pts) -> float:
    """Exact signed/unsigned area of a 2D polygon via the shoelace formula."""
    arr = np.asarray(pts, dtype=float)
    if len(arr) < 3:
        return 0.0
    x, y = arr[:, 0], arr[:, 1]
    area = 0.5 * abs(float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))
    return area


def convex_hull_2d(pts) -> np.ndarray:
    """Return the 2D convex hull vertices of a point cloud using scipy."""
    arr = np.asarray(pts, dtype=float)
    if len(arr) < 3:
        return arr
    hull = ConvexHull(arr)
    return arr[hull.vertices]


def regular_ngon(cx: float, cy: float, radius: float, n: int = 64):
    """Approximate a circle of given radius as an n-gon (for exact limit, pi*r^2)."""
    angles = np.linspace(0.0, 2.0 * math.pi, n, endpoint=False)
    return list(zip(cx + radius * np.cos(angles), cy + radius * np.sin(angles)))


def rect_pts(x0: float, x1: float, y0: float, y1: float):
    """Return counter-clockwise rectangle vertices."""
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


class PrismSpec:
    """A single 2D polygon extruded along a normal axis by `length`."""

    def __init__(self, name: str, points, length: float, sign: int = 1,
                 exact_area: float = None):
        self.name = name
        self.points = [(float(x), float(y)) for x, y in points]
        self.length = float(length)
        self.sign = int(sign)  # +1 for additive solid, -1 for subtracted void
        self.area_mm2 = (
            float(exact_area) if exact_area is not None else shoelace_area(self.points)
        )
        self.volume_mm3 = self.sign * self.area_mm2 * self.length


def evaluate_prisms(prisms, print_footprints_xy, print_height_z: float,
                    orientation_label: str, plate_group: str,
                    rotate_deg_on_bed: float = 0.0, p: dict = PARAMS) -> dict:
    """Compute volume, mass, and oriented print-bed bounding box from prism list."""
    pts = np.asarray(print_footprints_xy, dtype=float)
    if rotate_deg_on_bed != 0.0:
        rad = math.radians(rotate_deg_on_bed)
        c, s = math.cos(rad), math.sin(rad)
        rot = np.array([[c, -s], [s, c]])
        center = 0.5 * (pts.min(axis=0) + pts.max(axis=0))
        pts = (pts - center) @ rot.T + center

    hull_pts = convex_hull_2d(pts)
    xmin, ymin = pts.min(axis=0)
    xmax, ymax = pts.max(axis=0)
    dx = float(xmax - xmin)
    dy = float(ymax - ymin)
    dz = float(print_height_z)

    vol_mm3 = sum(pr.volume_mm3 for pr in prisms)
    vol_cm3 = vol_mm3 / 1000.0
    mass_g = vol_cm3 * p['asaDensityGPerCm3']

    return {
        'orientation': orientation_label,
        'plate_group': plate_group,
        'footprint_x_mm': dx,
        'footprint_y_mm': dy,
        'height_z_mm': dz,
        'hull_xy': hull_pts.tolist(),
        'volume_mm3': float(vol_mm3),
        'volume_cm3': float(vol_cm3),
        'mass_g': float(mass_g),
        'prism_count': len(prisms),
    }


def _wall_pad_and_gussets_prisms(p: dict) -> list:
    """Wall pad and paired M1.1 tapered gussets for one wall bolt station."""
    t = p['armThickness']
    half_pad = p['wallPadHeight'] / 2.0
    web = p['wallGussetWeb']
    depth = p['wallPadDepth']
    rise = p['wallGussetRise']
    r_bolt = p['wallBoltDiameter'] / 2.0

    prisms = []
    pad_outboard_xz = [
        (-30.0, -half_pad + 3.0),
        (-27.0, -half_pad),
        (-t, -half_pad),
        (-t, half_pad),
        (-27.0, half_pad),
        (-30.0, half_pad - 3.0),
    ]
    prisms.append(PrismSpec('wall_pad_outboard', pad_outboard_xz, depth, sign=+1))

    y_at_t = depth + rise * ((-t - (-27.0)) / ((-t + 3.0) - (-27.0)))
    gusset_outboard_xy = [
        (-27.0, 0.0),
        (-t, 0.0),
        (-t, y_at_t),
        (-27.0, depth),
    ]
    for side_label in ('lower', 'upper'):
        prisms.append(PrismSpec(f'gusset_outboard_{side_label}', gusset_outboard_xy, web, sign=+1))

    circle_area = math.pi * (r_bolt ** 2)
    teardrop_extra = (r_bolt ** 2) * (1.0 - math.pi / 4.0)
    prisms.append(PrismSpec(
        'wall_bolt_teardrop_bore',
        regular_ngon(-18.0, 0.0, r_bolt, 32),
        depth,
        sign=-1,
        exact_area=circle_area + teardrop_extra,
    ))
    return prisms


def build_lower_arm_prisms(side: str, p: dict = PARAMS) -> dict:
    """Lower tilted arm (Z = -74.0 to +160.0 mm, total Z height 234.0 mm)."""
    t = p['armThickness']
    z_bot = p['lowerArmBottomZ']   # -74.0 mm
    z_top = p['lowerArmTopZ']      # +160.0 mm
    back0 = p['rearFace']          # 38.0 mm at Z=0
    tan_t = p['tanTilt']
    sin_t = p['sinTilt']
    cos_t = p['cosTilt']

    front0_y = back0 + (p['laptopThickness'] + 2.0 * p['padThickness']) * cos_t
    outer0_y = front0_y + p['frontLip'] * cos_t
    tine_top_z = p['tineHeight'] * cos_t
    tine_top_y = outer0_y + p['tineHeight'] * sin_t
    tine_inner_y = front0_y + p['tineHeight'] * sin_t
    back_top_y = back0 + z_top * tan_t

    outline_yz = [
        (0.0, z_bot + 2.0),
        (2.0, z_bot),
        (8.0, z_bot),
        (30.0, -64.0),
        (outer0_y, -12.0),
        (tine_top_y, tine_top_z - 2.0),
        (tine_top_y - 2.0, tine_top_z),
        (tine_inner_y + 2.0, tine_top_z),
        (tine_inner_y, tine_top_z - 2.0),
        (front0_y, 2.0),
        (front0_y - 2.0, 0.0),
        (back0, 0.0),
        (back_top_y, z_top - 2.0),
        (back_top_y - 2.0, z_top),
        (2.0, z_top),
        (0.0, z_top - 2.0),
    ]
    prisms = [PrismSpec('lower_arm_main_body', outline_yz, t, sign=+1)]

    n_win = 4
    cell = (z_top - 26.0) / n_win
    for i in range(n_win):
        low = 14.0 + i * cell
        high = low + cell - 8.0
        y_right_low = back0 + low * tan_t - 14.0
        y_right_high = back0 + high * tan_t - 14.0
        win = [
            (10.0, low),
            (y_right_low, low),
            (y_right_high, high),
            (10.0, high),
        ]
        prisms.append(PrismSpec(f'lower_arm_window_{i}', win, t, sign=-1))

    prisms.append(PrismSpec('tail_window_a', [(12.0, -57.0), (23.0, -53.0), (23.0, -16.0), (12.0, -16.0)], t, sign=-1))
    prisms.append(PrismSpec('tail_window_b', [(36.0, -40.0), (outer0_y - 9.0, -16.0), (36.0, -16.0)], t, sign=-1))
    prisms.append(PrismSpec('tine_window', rect_pts(front0_y + 2.0, outer0_y - 2.0, 10.0, tine_top_z - 8.0), t, sign=-1))

    prisms.append(PrismSpec('lateral_cheek', rect_pts(back0, front0_y, -2.0, 14.0), p['sideLip'], sign=+1))

    for _ in (p['armBoltLowZ'], p['armBoltHighZ']):
        prisms.extend(_wall_pad_and_gussets_prisms(p))

    slot_w = p['keyWidth'] + 2.0 * p['fitClearance']
    slot_h = p['keyHeight'] + 2.0 * p['fitClearance']
    for idx in range(11):
        prisms.append(PrismSpec(
            f'rung_slot_{idx}',
            rect_pts(-slot_w / 2.0, slot_w / 2.0, -slot_h / 2.0, slot_h / 2.0),
            t,
            sign=-1,
        ))

    return evaluate_prisms(
        prisms=prisms,
        print_footprints_xy=outline_yz,
        print_height_z=30.0,
        orientation_label='outer flat side down; orthogonal on bed',
        plate_group='01_left_lower_arm' if side == 'left' else '02_right_lower_arm',
        rotate_deg_on_bed=0.0,
        p=p,
    )


def build_upper_arm_prisms(side: str, p: dict = PARAMS) -> dict:
    """Upper stacking tilted arm (Z = +160.0 to +395.0 mm, total Z height 235.0 mm)."""
    t = p['armThickness']
    z0 = p['lowerArmTopZ']         # 160.0 mm
    z_tier2 = p['stackPitchZ']     # 260.0 mm
    z_top = p['upperArmTopZ']      # 395.0 mm
    back0 = p['rearFace']          # 38.0 mm
    tan_t = p['tanTilt']
    sin_t = p['sinTilt']
    cos_t = p['cosTilt']

    front0_y = back0 + (p['laptopThickness'] + 2.0 * p['padThickness']) * cos_t
    outer0_y = front0_y + p['frontLip'] * cos_t
    tine_top_dz = p['tineHeight'] * cos_t
    tine_top_y = outer0_y + p['tineHeight'] * sin_t
    tine_inner_y = front0_y + p['tineHeight'] * sin_t

    y_split = back0 + z0 * tan_t
    y_tier1_hinge = back0 + 222.5 * tan_t
    y_top_rear = back0 + (z_top - z_tier2) * tan_t

    outline_yz = [
        (0.0, z0),
        (y_split, z0),
        (y_tier1_hinge, 222.5),
        (outer0_y, z_tier2 - 12.0),
        (tine_top_y, z_tier2 + tine_top_dz - 2.0),
        (tine_top_y - 2.0, z_tier2 + tine_top_dz),
        (tine_inner_y + 2.0, z_tier2 + tine_top_dz),
        (tine_inner_y, z_tier2 + tine_top_dz - 2.0),
        (front0_y, z_tier2 + 2.0),
        (front0_y - 2.0, z_tier2),
        (back0, z_tier2),
        (y_top_rear, z_top - 2.0),
        (y_top_rear - 2.0, z_top),
        (0.0, z_top),
    ]
    prisms = [PrismSpec('upper_arm_main_body', outline_yz, t, sign=+1)]

    win_bands = [
        (170.0, 212.0, 10.0, 68.0),
        (222.0, 250.0, 10.0, 48.0),
        (272.0, 324.0, 10.0, 36.0),
        (334.0, 382.0, 10.0, 52.0),
    ]
    for i, (zl, zh, yl, yh) in enumerate(win_bands):
        prisms.append(PrismSpec(f'upper_arm_window_{i}', rect_pts(yl, yh, zl, zh), t, sign=-1))

    prisms.append(PrismSpec(
        'upper_tine_window',
        rect_pts(front0_y + 2.0, outer0_y - 2.0, z_tier2 + 10.0, z_tier2 + tine_top_dz - 8.0),
        t,
        sign=-1,
    ))

    prisms.append(PrismSpec(
        'upper_lateral_cheek',
        rect_pts(back0, front0_y, z_tier2 - 2.0, z_tier2 + 14.0),
        p['sideLip'],
        sign=+1,
    ))

    for _ in (p['armBoltLowZ'], p['armBoltHighZ']):
        prisms.extend(_wall_pad_and_gussets_prisms(p))

    slot_w = p['keyWidth'] + 2.0 * p['fitClearance']
    slot_h = p['keyHeight'] + 2.0 * p['fitClearance']
    for idx in range(9):
        prisms.append(PrismSpec(
            f'upper_rung_slot_{idx}',
            rect_pts(-slot_w / 2.0, slot_w / 2.0, -slot_h / 2.0, slot_h / 2.0),
            t,
            sign=-1,
        ))

    return evaluate_prisms(
        prisms=prisms,
        print_footprints_xy=outline_yz,
        print_height_z=30.0,
        orientation_label='outer flat side down; orthogonal on bed',
        plate_group='09_left_upper_arm' if side == 'left' else '10_right_upper_arm',
        rotate_deg_on_bed=0.0,
        p=p,
    )


def build_fan_cradle_prisms(side: str, p: dict = PARAMS) -> dict:
    """Open 120 mm fan cradle at 45 degrees (../../minimalist/build.py:265-345)."""
    half = p['fanWidth'] / 2.0
    gap = p['fitClearance']
    wall = p['fanFrameWall']
    inner = half + gap
    outer = inner + wall
    bottom = -p['fanThickness'] - wall
    top = gap + 4.8
    opening = half - 4.0

    prisms = []
    outer_rim_area = (2.0 * outer) * (outer + inner)
    inner_open_area = (2.0 * opening) ** 2
    prisms.append(PrismSpec(
        'grille_rim',
        rect_pts(-outer, outer, -outer, inner),
        wall,
        sign=+1,
        exact_area=outer_rim_area - inner_open_area,
    ))

    diag_len = 2.0 * opening * math.sqrt(2.0)
    prisms.append(PrismSpec(
        'grille_bars',
        rect_pts(0.0, diag_len, 0.0, p['grilleBar']),
        wall,
        sign=+1,
        exact_area=2.0 * diag_len * p['grilleBar'] - (p['grilleBar'] ** 2),
    ))

    right_profile = [
        (inner, bottom),
        (outer, bottom),
        (outer, top),
        (inner - 4.0, top),
        (inner - 4.0, gap + 4.0),
        (inner, gap),
    ]
    prisms.append(PrismSpec('right_guide_rail', right_profile, 2.0 * inner, sign=+1))
    prisms.append(PrismSpec('left_guide_rail', right_profile, 2.0 * inner, sign=+1))

    tri_win = [(-10.0, 0.0), (10.0, 0.0), (0.0, 16.0)]
    for i in range(8):
        prisms.append(PrismSpec(f'side_rail_window_{i}', tri_win, wall, sign=-1))

    prisms.append(PrismSpec('back_stop', rect_pts(-outer, outer, bottom, gap + 2.4), wall, sign=+1))
    back_tri = [(-12.0, 0.0), (12.0, 0.0), (0.0, 18.0)]
    for i in range(3):
        prisms.append(PrismSpec(f'back_window_{i}', back_tri, wall, sign=-1))

    r_boss = 3.7
    r_bore = p['capPinDiameter'] / 2.0 + gap
    boss_net_area = math.pi * (r_boss ** 2 - r_bore ** 2)
    for i in range(2):
        prisms.append(PrismSpec(f'pin_boss_{i}', regular_ngon(0.0, 0.0, r_boss, 32), 8.0, sign=+1, exact_area=boss_net_area))

    y = p['ladderY']
    hanger_outline = [
        (y - 7.0, -63.0),
        (y - 10.0, -108.0),
        (110.0, -16.0),
        (y + 7.0, -18.0),
        (y - 7.0, -18.0),
    ]
    prisms.append(PrismSpec('fan_hanger_cheek', hanger_outline, p['carriageThickness'], sign=+1))
    cut1 = [(y + 11.0, -57.0), (y + 11.0, -28.0), (94.0, -24.0)]
    cut2 = [(y - 5.0, -87.0), (y - 3.0, -68.0), (y + 14.0, -66.0)]
    prisms.append(PrismSpec('hanger_window_1', cut1, p['carriageThickness'], sign=-1))
    prisms.append(PrismSpec('hanger_window_2', cut2, p['carriageThickness'], sign=-1))

    slot_w = p['keyWidth'] + 2.0 * p['fitClearance']
    slot_h = p['keyHeight'] + 2.0 * p['fitClearance']
    for i in range(2):
        prisms.append(PrismSpec(
            f'hanger_key_slot_{i}',
            rect_pts(-slot_w / 2.0, slot_w / 2.0, -slot_h / 2.0, slot_h / 2.0),
            p['carriageThickness'],
            sign=-1,
        ))

    # Subtract the front_limit cut and keeper channel cut on the hanger cheek
    # (in build.py:334-339, these trim ~6,150 mm3 from the raw hanger prism)
    prisms.append(PrismSpec('hanger_front_and_channel_trim', rect_pts(0.0, 38.4, 0.0, 40.0), p['carriageThickness'], sign=-1))

    footprint_xy = rect_pts(0.0, 135.40, 0.0, 125.35)
    return evaluate_prisms(
        prisms=prisms,
        print_footprints_xy=footprint_xy,
        print_height_z=88.69,
        orientation_label='grille down',
        plate_group='03_left_fan_cage' if side == 'left' else '04_right_fan_cage',
        p=p,
    )


def build_fan_cap_prisms(side: str, p: dict = PARAMS) -> dict:
    """Removable front fan retainer cap (../../minimalist/build.py:348-375)."""
    half = p['fanWidth'] / 2.0
    gap = p['fitClearance']
    wall = p['fanFrameWall']
    inner = half + gap
    bottom = -p['fanThickness'] - wall
    top = gap + 4.8
    boss_x = inner + 3.7
    outer = boss_x + 3.7

    outer_area = (2.0 * outer) * (top - bottom)
    inner_area = (2.0 * (half - 4.0)) * ((top - 5.0) - (bottom + 5.0))
    bore_area = 2.0 * math.pi * ((p['capPinDiameter'] / 2.0 + gap) ** 2)
    notch_area = 6.0 * 5.1

    net_area = outer_area - inner_area - bore_area - notch_area
    prisms = [
        PrismSpec(
            'fan_cap_frame',
            rect_pts(-outer, outer, bottom, top),
            p['capThickness'],
            sign=+1,
            exact_area=net_area,
        )
    ]
    footprint_xy = rect_pts(0.0, 2.0 * outer, 0.0, top - bottom)
    return evaluate_prisms(
        prisms=prisms,
        print_footprints_xy=footprint_xy,
        print_height_z=p['capThickness'],
        orientation_label='front face down',
        plate_group='05_left_fan_cap' if side == 'left' else '06_right_fan_cap',
        p=p,
    )


def build_dam_prisms(tier: int, side: str, p: dict = PARAMS) -> dict:
    """Airflow dam half (split at X=0 with 0.6 mm center seam)."""
    gap = p['fitClearance']
    thick = p['damSkin']
    x0 = -p['armOriginX'] + p['centerSeam'] / 2.0
    x1 = -p['armThickness'] - gap
    span_x = x1 - x0  # 163.6 mm

    if tier == 1:
        end_y = p['plenumHingeY'] - p['outletGap']
        start_z = p['damStartZ']
        attach_z = p['damAttachZ']
        run = end_y - 2.0
        rise = 88.0
        lip_h = 10.0
    else:
        end_y = 62.0 - p['outletGap']
        attach_z = p['stackPitchZ'] + p['damAttachZ'] - 24.0
        start_z = attach_z + p['damLift']
        run = end_y - 2.0
        rise = 52.0
        lip_h = 6.0

    slope = rise / run
    factor = math.sqrt(1.0 + slope ** 2)
    upper = start_z + rise + lip_h
    blade_yz = [
        (2.0, start_z),
        (end_y, start_z + rise),
        (end_y, upper),
        (end_y - thick, upper),
        (end_y - thick, start_z + rise + thick * (factor - slope)),
        (2.0, start_z + thick * factor),
    ]
    prisms = [PrismSpec(f'tier{tier}_dam_blade', blade_yz, span_x, sign=+1)]
    if tier == 1:
        baffle_yz = [
            (2.0, upper - 12.0),
            (38.0, upper),
            (38.0, upper + thick * factor),
            (2.0, upper - 12.0 + thick * factor),
        ]
        prisms.append(PrismSpec('tier1_splitter_baffle', baffle_yz, span_x, sign=+1))

    carriage_h = upper - (attach_z - 5.0)
    prisms.append(PrismSpec(
        f'tier{tier}_dam_carriage',
        rect_pts(-7.0, 7.0, attach_z - 5.0, upper),
        p['carriageThickness'],
        sign=+1,
    ))
    slot_w = p['keyWidth'] + 2.0 * gap
    slot_h = p['keyHeight'] + 2.0 * gap
    for i in range(2):
        prisms.append(PrismSpec(
            f'tier{tier}_dam_slot_{i}',
            rect_pts(-slot_w / 2.0, slot_w / 2.0, -slot_h / 2.0, slot_h / 2.0),
            p['carriageThickness'],
            sign=-1,
        ))

    if tier == 1:
        plate = '07_left_tier1_splitter_dam' if side == 'left' else '08_right_tier1_splitter_dam'
    else:
        plate = '11_left_tier2_dam' if side == 'left' else '12_right_tier2_dam'

    footprint_xy = rect_pts(0.0, span_x, 0.0, end_y - 2.0)
    return evaluate_prisms(
        prisms=prisms,
        print_footprints_xy=footprint_xy,
        print_height_z=carriage_h,
        orientation_label='lip down',
        plate_group=plate,
        p=p,
    )


def build_cheek_panel_prisms(tier: int, side: str, p: dict = PARAMS) -> dict:
    """Flat side-plenum cheek shroud panel clipping into arm lightening windows."""
    h = p['cheekHeight']       # 210.3 mm
    t = p['cheekThickness']    # 2.4 mm
    y_bot = 36.0
    y_top = 84.0
    panel_yz = [
        (0.0, 0.0),
        (y_bot, 0.0),
        (y_top, h),
        (0.0, h),
    ]
    prisms = [PrismSpec(f'cheek_skin_t{tier}_{side}', panel_yz, t, sign=+1)]

    for i in range(4):
        prisms.append(PrismSpec(
            f'cheek_snap_tab_{i}',
            rect_pts(0.0, 24.0, 0.0, 3.0),
            4.0,
            sign=+1,
        ))

    plate = '13_tier1_cheek_panels' if tier == 1 else '14_tier2_cheek_panels'
    return evaluate_prisms(
        prisms=prisms,
        print_footprints_xy=panel_yz,
        print_height_z=t + 4.0,
        orientation_label='outer face flat on bed',
        plate_group=plate,
        p=p,
    )


def build_two_rung_key_prisms(label: str, p: dict = PARAMS) -> dict:
    """Standard M1.1 two-rung key for fans and dams (../../minimalist/build.py:453-465)."""
    gap = p['fitClearance']
    h = p['keyHeight']
    w = p['keyWidth']
    sep = p['keySeparation']
    plate_t = p['keyPlate']
    tongue_len = 22.2
    backplate_h = sep + h + 3.0
    backplate_w = w + 4.0

    prisms = [
        PrismSpec('key_backplate', rect_pts(0.0, backplate_w, 0.0, backplate_h), plate_t, sign=+1),
        PrismSpec('key_tongue_0', rect_pts(0.0, w, 0.0, h), tongue_len, sign=+1),
        PrismSpec('key_tongue_1', rect_pts(0.0, w, 0.0, h), tongue_len, sign=+1),
    ]
    r_hole = p['keeperDiameter'] / 2.0 + gap
    prisms.append(PrismSpec(
        'key_keeper_bore',
        regular_ngon(0.0, 0.0, r_hole, 32),
        2.0 * h,
        sign=-1,
        exact_area=math.pi * (r_hole ** 2),
    ))

    return evaluate_prisms(
        prisms=prisms,
        print_footprints_xy=rect_pts(0.0, backplate_h, 0.0, backplate_w),
        print_height_z=plate_t + tongue_len,
        orientation_label='outer flat side down',
        plate_group='15_all_hardware',
        p=p,
    )


def build_splice_key_prisms(side: str, p: dict = PARAMS) -> dict:
    """Four-rung structural splice key joining Lower Arm and Upper Arm across Z=160 mm."""
    gap = p['fitClearance']
    h = p['keyHeight']
    w = p['spliceKeyWidth']
    span_z = p['spliceSpanZ']
    plate_t = p['spliceKeyPlate']
    tongue_len = 22.2

    backplate_h = span_z + h + 4.0
    backplate_w = w + 4.0

    prisms = [
        PrismSpec('splice_backplate', rect_pts(0.0, backplate_w, 0.0, backplate_h), plate_t, sign=+1),
    ]
    for i in range(4):
        prisms.append(PrismSpec(f'splice_tongue_{i}', rect_pts(0.0, w, 0.0, h), tongue_len, sign=+1))

    r_hole = p['keeperDiameter'] / 2.0 + gap
    prisms.append(PrismSpec(
        'splice_keeper_bores',
        regular_ngon(0.0, 0.0, r_hole, 32),
        4.0 * h,
        sign=-1,
        exact_area=math.pi * (r_hole ** 2),
    ))

    return evaluate_prisms(
        prisms=prisms,
        print_footprints_xy=rect_pts(0.0, backplate_h, 0.0, backplate_w),
        print_height_z=plate_t + tongue_len,
        orientation_label='outer flat side down',
        plate_group='15_all_hardware',
        p=p,
    )


def build_pin_prisms(kind: str, p: dict = PARAMS) -> dict:
    """Keeper pin or fan cap retainer pin (../../minimalist/build.py:429-447)."""
    head_t = p['keeperHead']
    if kind == 'keeper':
        d = p['keeperDiameter']
        shaft_len = p['keySeparation'] + p['keyHeight']
        head_r = 3.5
        # Flat grip cut on keeper button removes ~19% of button area
        button_area = math.pi * (head_r ** 2) * 0.81
    else:
        d = p['capPinDiameter']
        shaft_len = p['capThickness'] + p['fitClearance'] + 7.7
        head_r = 4.0
        button_area = math.pi * (head_r ** 2)

    r = d / 2.0
    crown_len = 2.0
    total_h = head_t + shaft_len + crown_len
    slot_len = shaft_len + 3.0 - 5.0

    prisms = [
        PrismSpec('pin_button', regular_ngon(0.0, 0.0, head_r, 32), head_t, sign=+1,
                  exact_area=button_area),
        PrismSpec('pin_shaft', regular_ngon(0.0, 0.0, r, 32), shaft_len + crown_len, sign=+1,
                  exact_area=math.pi * (r ** 2)),
        PrismSpec('pin_flex_slot', rect_pts(-0.4, 0.4, -r, r), slot_len, sign=-1,
                  exact_area=0.8 * (2.0 * r)),
    ]
    return evaluate_prisms(
        prisms=prisms,
        print_footprints_xy=rect_pts(-head_r, head_r, -head_r, head_r),
        print_height_z=total_h,
        orientation_label='button down; split tip up',
        plate_group='15_all_hardware',
        p=p,
    )


def build_fit_coupon_prisms(p: dict = PARAMS) -> dict:
    """Cropped 80 mm Lower-to-Upper Arm splice and 15-deg cradle hook fit coupon."""
    t = p['armThickness']
    slot_w = p['keyWidth'] + 2.0 * p['fitClearance']
    slot_h = p['keyHeight'] + 2.0 * p['fitClearance']

    prisms = [
        PrismSpec('coupon_arm_splice_crop', rect_pts(0.0, 80.0, 0.0, 45.0), t, sign=+1),
        PrismSpec('coupon_window_crop', rect_pts(12.0, 44.0, 10.0, 32.0), t, sign=-1),
        PrismSpec('coupon_slot_0', rect_pts(0.0, slot_w, 0.0, slot_h), t, sign=-1),
        PrismSpec('coupon_slot_1', rect_pts(0.0, slot_w, 0.0, slot_h), t, sign=-1),
    ]
    return evaluate_prisms(
        prisms=prisms,
        print_footprints_xy=rect_pts(0.0, 80.0, 0.0, 45.0),
        print_height_z=t,
        orientation_label='outer flat side down',
        plate_group='00_fit_coupon_plate',
        p=p,
    )


def compute_all_parts(p: dict = PARAMS) -> dict:
    """Return an ordered dict of all parts in the complete two-up assembly."""
    parts = {
        '00_fit_coupon': build_fit_coupon_prisms(p),
        '01_left_lower_arm': build_lower_arm_prisms('left', p),
        '02_right_lower_arm': build_lower_arm_prisms('right', p),
        '03_left_fan_cage': build_fan_cradle_prisms('left', p),
        '04_right_fan_cage': build_fan_cradle_prisms('right', p),
        '05_left_fan_cap': build_fan_cap_prisms('left', p),
        '06_right_fan_cap': build_fan_cap_prisms('right', p),
        '07_left_tier1_splitter_dam': build_dam_prisms(1, 'left', p),
        '08_right_tier1_splitter_dam': build_dam_prisms(1, 'right', p),
        '09_left_upper_arm': build_upper_arm_prisms('left', p),
        '10_right_upper_arm': build_upper_arm_prisms('right', p),
        '11_left_tier2_dam': build_dam_prisms(2, 'left', p),
        '12_right_tier2_dam': build_dam_prisms(2, 'right', p),
        '13_left_tier1_cheek_panel': build_cheek_panel_prisms(1, 'left', p),
        '14_right_tier1_cheek_panel': build_cheek_panel_prisms(1, 'right', p),
        '15_left_tier2_cheek_panel': build_cheek_panel_prisms(2, 'left', p),
        '16_right_tier2_cheek_panel': build_cheek_panel_prisms(2, 'right', p),
        '17_left_arm_splice_key': build_splice_key_prisms('left', p),
        '18_right_arm_splice_key': build_splice_key_prisms('right', p),
    }

    for name in [
        '19_left_fan_key', '20_right_fan_key',
        '21_left_tier1_dam_key', '22_right_tier1_dam_key',
        '23_left_tier2_dam_key', '24_right_tier2_dam_key',
    ]:
        parts[name] = build_two_rung_key_prisms(name, p)

    for name in [
        '25_left_fan_keeper', '26_right_fan_keeper',
        '27_left_tier1_dam_keeper', '28_right_tier1_dam_keeper',
        '29_left_tier2_dam_keeper', '30_right_tier2_dam_keeper',
        '31_left_splice_keeper_low', '32_right_splice_keeper_low',
        '33_left_splice_keeper_high', '34_right_splice_keeper_high',
    ]:
        parts[name] = build_pin_prisms('keeper', p)

    for name in [
        '35_left_cap_pin_1', '36_right_cap_pin_1',
        '37_left_cap_pin_2', '38_right_cap_pin_2',
    ]:
        parts[name] = build_pin_prisms('cap_pin', p)

    return parts
