"""Parametric FreeCAD builder for the Tight Wall-Mount Stacked Two-Banger Rack.

6 printed parts (no splice keys, no keeper pins, no glue):
  - 01_left_lower_arm, 02_right_lower_arm (Z = -80..155 mm, 235 mm)
  - 03_left_upper_arm, 04_right_upper_arm (Z = 155..390 mm, 235 mm)
  - 05_left_fan_tray, 06_right_fan_tray (140 mm fans at 55 deg)

Run headless:
    flatpak run --command=freecadcmd org.freecad.FreeCAD "$PWD"/two-banger/wall/work/build_wall_rack.py
"""
from pathlib import Path
import json
import math
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from params import PARAMETERS, get_params

import FreeCAD as App
import MeshPart
import Part
import Sketcher

TARGET_FCSTD = ROOT / 'TwoBangerWall.FCStd'
EXPORT_DIR = ROOT / 'export'
PAGE_MODELS_DIR = ROOT.parent / 'page' / 'models'


def _pt_yz(y_base: float, z_base: float, s: float, w: float,
           sin_t: float, cos_t: float) -> tuple:
    """Convert cradle-local (s up along laptop, w outward +Y) to (Y, Z)."""
    y = y_base + s * sin_t + w * cos_t
    z = z_base + s * cos_t - w * sin_t
    return (y, z)


def _add_polygon_sketch(doc, group, name: str, wires: list, plane: str = 'XY', origin=(0, 0, 0)):
    obj = doc.addObject('Sketcher::SketchObject', name)
    obj.Label = name
    group.addObject(obj)
    rotations = {
        'XY': App.Rotation(),
        'YZ': App.Rotation(App.Vector(0, 1, 0), App.Vector(0, 0, 1), App.Vector(1, 0, 0), 'ZXY'),
        'XZ': App.Rotation(App.Vector(1, 0, 0), 90),
    }
    obj.Placement = App.Placement(App.Vector(*map(float, origin)), rotations[plane])
    for pts in wires:
        first = obj.GeometryCount
        n = len(pts)
        segs = [
            Part.LineSegment(
                App.Vector(float(pts[i][0]), float(pts[i][1]), 0.0),
                App.Vector(float(pts[(i + 1) % n][0]), float(pts[(i + 1) % n][1]), 0.0),
            )
            for i in range(n)
        ]
        obj.addGeometry(segs, False)
        for i in range(n):
            obj.addConstraint(Sketcher.Constraint('Coincident', first + i, 2, first + (i + 1) % n, 1))
        for i, (px, py) in enumerate(pts):
            obj.addConstraint(Sketcher.Constraint('DistanceX', first + i, 1, float(px)))
            obj.addConstraint(Sketcher.Constraint('DistanceY', first + i, 1, float(py)))
    obj.Visibility = False
    return obj


def _add_circle_sketch(doc, group, name: str, circles: list, plane: str = 'XY', origin=(0, 0, 0)):
    obj = _add_polygon_sketch(doc, group, name, [], plane, origin)
    for cx, cy, r in circles:
        idx = obj.addGeometry(
            Part.Circle(App.Vector(float(cx), float(cy), 0.0), App.Vector(0, 0, 1), float(r)),
            False,
        )
        obj.addConstraint(Sketcher.Constraint('DistanceX', idx, 3, float(cx)))
        obj.addConstraint(Sketcher.Constraint('DistanceY', idx, 3, float(cy)))
        obj.addConstraint(Sketcher.Constraint('Radius', idx, float(r)))
    return obj


def _extrude(doc, group, name: str, sketch, length: float):
    obj = doc.addObject('Part::Extrusion', name)
    obj.Label = name
    group.addObject(obj)
    obj.Base = sketch
    obj.DirMode = 'Normal'
    obj.LengthFwd = float(length)
    obj.Solid = True
    sketch.Visibility = False
    obj.Visibility = False
    return obj


def _fuse(doc, group, name: str, shapes: list):
    obj = doc.addObject('Part::MultiFuse', name)
    obj.Label = name
    group.addObject(obj)
    obj.Shapes = shapes
    obj.Refine = True
    for s in shapes:
        s.Visibility = False
    obj.Visibility = False
    return obj


def _cut(doc, group, name: str, base, tool):
    obj = doc.addObject('Part::Cut', name)
    obj.Label = name
    group.addObject(obj)
    obj.Base = base
    obj.Tool = tool
    obj.Refine = True
    base.Visibility = tool.Visibility = obj.Visibility = False
    return obj


def _mirror_x(doc, group, name: str, src):
    obj = doc.addObject('Part::Mirroring', name)
    obj.Label = name
    group.addObject(obj)
    obj.Source = src
    obj.Normal = App.Vector(1, 0, 0)
    obj.Visibility = False
    return obj


def _move(doc, group, name: str, src, origin=(0, 0, 0), rotation=None):
    obj = doc.addObject('Part::Compound', name)
    obj.Label = name
    group.addObject(obj)
    obj.Links = [src]
    src.Visibility = False
    obj.Placement = App.Placement(App.Vector(*map(float, origin)), rotation or App.Rotation())
    obj.Visibility = False
    return obj


def _register(doc, assembly, source, key: str, label: str):
    source.addProperty('App::PropertyString', 'PartKey', 'Identity')
    source.PartKey = key
    source.Label = label + ' / source'
    link = doc.addObject('App::Link', 'WallRack_' + key)
    link.setLink(source)
    link.LinkTransform = True
    link.LinkPlacement = App.Placement()
    link.addProperty('App::PropertyString', 'InstanceKey', 'Identity')
    link.InstanceKey = key
    link.Label = label
    assembly.addObject(link)
    source.Visibility = False
    link.Visibility = True
    return link


def setup_parameters(doc) -> dict:
    sheet = doc.addObject('Spreadsheet::Sheet', 'Parameters')
    sheet.Label = 'Tight Wall Two-Banger Parameters'
    sheet.setColumnWidth('A', 190)
    sheet.setColumnWidth('B', 100)
    sheet.setColumnWidth('C', 55)
    sheet.setColumnWidth('D', 420)
    sheet.mergeCells('A1:D1')
    sheet.set('A1', 'TIGHT WALL TWO-BANGER 5560 / DIMENSIONS IN MM')
    row = 3
    for entry in PARAMETERS:
        if entry[1] is None:
            sheet.mergeCells(f'A{row}:D{row}')
            sheet.set(f'A{row}', entry[0])
        else:
            name, val, unit, desc = entry
            sheet.set(f'A{row}', name)
            sheet.set(f'B{row}', f'{val} {unit}' if unit else str(val))
            sheet.set(f'C{row}', unit)
            sheet.set(f'D{row}', desc)
            sheet.setAlias(f'B{row}', name)
        row += 1
    doc.recompute()
    return get_params()


def _offset_poly_2d(pts: list, d: float) -> list:
    """Offset a CCW 2D polygon outward by d mm using edge-normal intersection."""
    n = len(pts)
    out = []
    for i in range(n):
        p0 = pts[(i - 1) % n]
        p1 = pts[i]
        p2 = pts[(i + 1) % n]
        e1x, e1y = p1[0] - p0[0], p1[1] - p0[1]
        e2x, e2y = p2[0] - p1[0], p2[1] - p1[1]
        l1 = math.hypot(e1x, e1y)
        l2 = math.hypot(e2x, e2y)
        n1x, n1y = e1y / l1, -e1x / l1
        n2x, n2y = e2y / l2, -e2x / l2
        # Intersect (p1 + d*n1) + s*e1 and (p1 + d*n2) + t*e2
        det = e1x * e2y - e1y * e2x
        if abs(det) < 1e-9:
            out.append((p1[0] + d * n1x, p1[1] + d * n1y))
        else:
            dx = d * (n2x - n1x)
            dy = d * (n2y - n1y)
            s = (dx * e2y - dy * e2x) / det
            out.append((p1[0] + d * n1x + s * e1x, p1[1] + d * n1y + s * e1y))
    return out


def _add_bed_inlay_with_vgroove(doc, grp, arm_plate, pts_yz: list, x_bed: float, prefix: str):
    """Cut a 1 mm deep pocket with 1 mm x 1 mm 45-deg V-groove bevel on x_bed,
    and build the matching 1.0 mm thick 2nd-color inlay body touching at x_bed - 1.0.
    """
    pts_outer = _offset_poly_2d(pts_yz, 1.1)
    w_in = Part.makePolygon([App.Vector(x_bed - 1.0, y, z) for y, z in pts_yz] + [App.Vector(x_bed - 1.0, pts_yz[0][0], pts_yz[0][1])])
    w_out = Part.makePolygon([App.Vector(x_bed + 0.1, y, z) for y, z in pts_outer] + [App.Vector(x_bed + 0.1, pts_outer[0][0], pts_outer[0][1])])
    loft_shape = Part.makeLoft([w_in, w_out], True)
    tool_obj = doc.addObject('Part::Feature', f'{prefix}GrooveTool')
    tool_obj.Label = f'{prefix}GrooveTool'
    grp.addObject(tool_obj)
    tool_obj.Shape = loft_shape
    tool_obj.Visibility = False
    arm_cut = _cut(doc, grp, f'{prefix}ArmWithGroove', arm_plate, tool_obj)

    sk_inlay = _add_polygon_sketch(doc, grp, f'{prefix}InlaySk', [pts_yz], 'YZ', (x_bed - 1.0, 0.0, 0.0))
    inlay = _extrude(doc, grp, f'{prefix}Inlay', sk_inlay, 1.0)
    return arm_cut, inlay


def _add_wall_pads_and_holes(doc, grp, body, z_stations, p: dict, prefix: str):
    outer_x = p['outerWallX']
    pad_x0 = outer_x - p['wallPadWidthX']
    pad_t = p['wallPadThickness']
    pad_h = p['wallPadHeightZ']
    pads = []
    for i, zc in enumerate(z_stations):
        z0 = zc - pad_h / 2.0
        z1 = zc + pad_h / 2.0
        # Chamfered octagonal wall pad profile in XZ (3 mm corner bevels)
        pts = [
            (pad_x0 + 3.0, z0), (outer_x - 3.0, z0),
            (outer_x, z0 + 3.0), (outer_x, z1 - 3.0),
            (outer_x - 3.0, z1), (pad_x0 + 3.0, z1),
            (pad_x0, z1 - 3.0), (pad_x0, z0 + 3.0),
        ]
        sk = _add_polygon_sketch(doc, grp, f'{prefix}Pad{i}Sk', [pts], 'XZ', (0.0, pad_t, 0.0))
        pads.append(_extrude(doc, grp, f'{prefix}Pad{i}', sk, pad_t))
    fused = _fuse(doc, grp, f'{prefix}WithPads', [body] + pads)

    r_wall = p['wallBoltDiameter'] / 2.0
    bolt_x = outer_x - p['wallPadWidthX'] / 2.0
    sk_h = _add_circle_sketch(
        doc, grp, f'{prefix}WallBoresSk',
        [(bolt_x, zc, r_wall) for zc in z_stations],
        'XZ', (0.0, pad_t + 1.0, 0.0),
    )
    hole_tool = _extrude(doc, grp, f'{prefix}WallBores', sk_h, pad_t + 2.0)
    return _cut(doc, grp, f'{prefix}Drilled', fused, hole_tool)


def build_arms(doc, sources, assembly, p: dict):
    """Build 01/02 Lower Arms and 03/04 Upper Arms."""
    grp = doc.addObject('App::DocumentObjectGroup', 'WallArmsHistory')
    sources.addObject(grp)

    sin_t, cos_t, tan_t = p['sinTilt'], p['cosTilt'], p['tanTilt']
    yg = p['wallGap']             # 35.0 mm
    c = p['cradleClearance']      # 0.5 mm
    t_lap = p['laptopThickness']  # 20.0 mm
    lip_h = p['outerLipHeight']   # 24.0 mm
    inner_x = p['innerWallX']     # 172.7 mm
    arm_t = p['armThickness']     # 8.0 mm
    rail_t = p['railInboardDepth']  # 12.0 mm
    rail_x0 = inner_x - rail_t    # 160.7 mm
    seat_extra_t = p['seatInboardDepth'] - rail_t  # 14.0 mm (26 mm total seat width)
    seat_x0 = rail_x0 - seat_extra_t               # 146.7 mm

    z_bot = p['lowerArmBottomZ']  # -105.0 mm
    z_split = p['armSplitZ']      # 133.0 mm
    z_tier2 = p['stackPitchZ']    # 212.0 mm
    z_top = p['upperArmTopZ']     # 371.0 mm

    # --- 1. Lower Arm (Z = -105.0 to +133.0 mm) ---
    # Fan plate M4 bolt stations at fan-local y = +/-45.0 mm, z = 6.0 mm (midplane of 12 mm plate).
    # App.Rotation(X, +50 deg) maps (y, z) -> (fy + y*cf - z*sf, fz + y*sf + z*cf).
    fy, fz = p['fanCenterY'], p['fanCenterZ']
    sf, cf = p['sinFan'], p['cosFan']
    fb1 = (fy - 45.0 * cf - 6.0 * sf, fz - 45.0 * sf + 6.0 * cf)  # lower-rear M4
    fb2 = (fy + 45.0 * cf - 6.0 * sf, fz + 45.0 * sf + 6.0 * cf)  # upper-front M4

    p_lip_out = _pt_yz(yg, 0.0, lip_h, t_lap + 6.5, sin_t, cos_t)
    p_lip_in = _pt_yz(yg, 0.0, lip_h, t_lap + c, sin_t, cos_t)
    p_seat_in = _pt_yz(yg, 0.0, -c, t_lap + c, sin_t, cos_t)
    p_seat_back = _pt_yz(yg, 0.0, -c, -c, sin_t, cos_t)
    p_under_split = (yg - c / cos_t + z_split * tan_t, z_split)

    # Full-height lateral retention cheek (covers t=18 mm of 20 mm laptop thickness)
    p_cheek_1_bot = _pt_yz(yg, 0.0, lip_h, 18.0, sin_t, cos_t)
    p_cheek_1_split = (yg + 18.0 / cos_t + z_split * tan_t, z_split)

    # Outer cheek wraps cleanly around the 50-deg solid fan plate (y_loc=-74.5..+74.5)
    p_lip_tip_out = _pt_yz(yg, 0.0, lip_h - 3.0, t_lap + 6.5, sin_t, cos_t)
    p_lip_tip_top = _pt_yz(yg, 0.0, lip_h, t_lap + 3.5, sin_t, cos_t)
    p_lip_join = _pt_yz(yg, 0.0, 32.0, t_lap + 6.5, sin_t, cos_t)
    fan_bot_y = fy - 74.5 * cf
    fan_top_y = fy + 74.5 * cf
    fan_top_z = fz + 74.5 * sf
    lower_outer_pts = [
        (0.0, z_bot + 6.0),
        (6.0, z_bot),
        (fan_bot_y + 4.0, z_bot),
        (fan_top_y, fan_top_z - 4.0),
        (fan_top_y, fan_top_z),
        (fan_top_y - 12.0 * sf, fan_top_z + 12.0 * cf),
        p_lip_join,
        p_lip_tip_out,
        p_lip_tip_top,
        p_lip_in,
        p_cheek_1_bot,
        p_cheek_1_split,
        (0.0, z_split),
    ]
    sk_l_out = _add_polygon_sketch(doc, grp, 'LowerOuterSk', [lower_outer_pts], 'YZ', (inner_x, 0.0, 0.0))
    l_outer = _extrude(doc, grp, 'LowerOuterPlate', sk_l_out, arm_t)

    # Flush 2-color bed-face inlay with 1 mm x 1 mm V-groove (zero bridging)
    l_recess_pts = [
        (12.0, 12.0),
        (28.0, 12.0),
        (yg + 116.0 * tan_t - 10.0, 116.0),
        (12.0, 116.0),
    ]
    l_outer, r_low_inlay = _add_bed_inlay_with_vgroove(doc, grp, l_outer, l_recess_pts, inner_x + arm_t, 'Lower')

    # Inboard Tier 1 support rail (X = 160.7..172.7 mm, clears fan and ports)
    l_rail_pts = [
        _pt_yz(yg, 0.0, -7.0, -9.0, sin_t, cos_t),
        _pt_yz(yg, 0.0, -7.0, t_lap + 3.5, sin_t, cos_t),
        _pt_yz(yg, 0.0, -4.0, t_lap + 6.5, sin_t, cos_t),
        p_lip_tip_out,
        p_lip_tip_top,
        p_lip_in,
        p_seat_in,
        p_seat_back,
        p_under_split,
        (p_under_split[0] - 9.0, z_split),
    ]
    sk_l_rail = _add_polygon_sketch(doc, grp, 'LowerRailSk', [l_rail_pts], 'YZ', (rail_x0, 0.0, 0.0))
    l_rail = _extrude(doc, grp, 'LowerRail', sk_l_rail, rail_t)

    # Extended inboard seat + under-seat gusset onto frame rail (X = 146.7..160.7 mm)
    l_seat_pts = [
        _pt_yz(yg, 0.0, -22.0, -9.0, sin_t, cos_t),
        _pt_yz(yg, 0.0, -7.0, 16.0, sin_t, cos_t),
        _pt_yz(yg, 0.0, -7.0, t_lap + 3.5, sin_t, cos_t),
        _pt_yz(yg, 0.0, -4.0, t_lap + 6.5, sin_t, cos_t),
        p_lip_tip_out,
        p_lip_tip_top,
        p_lip_in,
        p_seat_in,
        p_seat_back,
        _pt_yz(yg, 0.0, 88.0, -c, sin_t, cos_t),
        _pt_yz(yg, 0.0, 88.0, -9.0, sin_t, cos_t),
    ]
    sk_l_seat = _add_polygon_sketch(doc, grp, 'LowerSeatGussetSk', [l_seat_pts], 'YZ', (seat_x0, 0.0, 0.0))
    l_seat = _extrude(doc, grp, 'LowerSeatGusset', sk_l_seat, seat_extra_t)
    l_raw = _fuse(doc, grp, 'LowerArmRaw', [l_outer, l_rail, l_seat])

    # Cut M4 fan-tray bolt holes at fb1, fb2 (dia 4.5 mm + flush 8.0 mm counterbore)
    r_m4 = p['m4ClearanceDia'] / 2.0
    sk_l_fan_h = _add_circle_sketch(
        doc, grp, 'LowerFanBoltsSk',
        [(fb1[0], fb1[1], r_m4), (fb2[0], fb2[1], r_m4)],
        'YZ', (inner_x - 1.0, 0.0, 0.0),
    )
    l_fan_h_tool = _extrude(doc, grp, 'LowerFanBoltsCut', sk_l_fan_h, arm_t + 2.0)
    l_fcut = _cut(doc, grp, 'LowerFanCut', l_raw, l_fan_h_tool)

    sk_l_cb = _add_circle_sketch(
        doc, grp, 'LowerFanCbSk',
        [(fb1[0], fb1[1], 4.0), (fb2[0], fb2[1], 4.0)],
        'YZ', (inner_x + arm_t - 2.5, 0.0, 0.0),
    )
    l_cb_tool = _extrude(doc, grp, 'LowerFanCbCut', sk_l_cb, 3.5)
    l_fcut = _cut(doc, grp, 'LowerFanCbDone', l_fcut, l_cb_tool)

    right_lower = _add_wall_pads_and_holes(doc, grp, l_fcut, (-28.0, 114.0), p, 'Lower')
    left_lower = _mirror_x(doc, grp, 'LeftLowerArm', right_lower)
    _register(doc, assembly, left_lower, '01_left_lower_arm', '01 / Left lower wall arm')
    _register(doc, assembly, right_lower, '02_right_lower_arm', '02 / Right lower wall arm')
    l_low_inlay = _mirror_x(doc, grp, 'LeftLowerInlay', r_low_inlay)
    _register(doc, assembly, l_low_inlay, '07_left_lower_inlay', '07 / Left lower 2-color inlay')
    _register(doc, assembly, r_low_inlay, '08_right_lower_inlay', '08 / Right lower 2-color inlay')

    # --- 2. Upper Arm (Z = +133.0 to +371.0 mm) ---
    p2_lip_out = _pt_yz(yg, z_tier2, lip_h, t_lap + 6.5, sin_t, cos_t)
    p2_lip_tip_out = _pt_yz(yg, z_tier2, lip_h - 3.0, t_lap + 6.5, sin_t, cos_t)
    p2_lip_tip_top = _pt_yz(yg, z_tier2, lip_h, t_lap + 3.5, sin_t, cos_t)
    p2_lip_in = _pt_yz(yg, z_tier2, lip_h, t_lap + c, sin_t, cos_t)
    p2_seat_in = _pt_yz(yg, z_tier2, -c, t_lap + c, sin_t, cos_t)
    p2_seat_back = _pt_yz(yg, z_tier2, -c, -c, sin_t, cos_t)
    p2_cheek_bot = _pt_yz(yg, z_tier2, lip_h, 18.0, sin_t, cos_t)
    # Tier 2 base (Y=35, Z=212) tucks 15 mm below Tier 1 hinge (Y=75, Z=227),
    # stepping from Tier 1 underside at Z=198 mm back to Tier 2 base at Z=212 mm.
    z_step = z_tier2 - 14.0
    y_cheek1_step = yg + 18.0 / cos_t + z_step * tan_t
    y_cheek2_top = yg + 18.0 / cos_t + (z_top - z_tier2) * tan_t
    y_cheek2_chamfer = yg + 18.0 / cos_t + (z_top - 4.0 - z_tier2) * tan_t
    y_upper_top = yg - c / cos_t + (z_top - z_tier2) * tan_t
    y_upper_chamfer = yg - c / cos_t + (z_top - 4.0 - z_tier2) * tan_t

    upper_outer_pts = [
        (0.0, z_split),
        p_cheek_1_split,
        (y_cheek1_step, z_step),
        _pt_yz(yg, z_tier2, -7.0, t_lap + 3.5, sin_t, cos_t),
        _pt_yz(yg, z_tier2, -4.0, t_lap + 6.5, sin_t, cos_t),
        p2_lip_tip_out,
        p2_lip_tip_top,
        p2_lip_in,
        p2_cheek_bot,
        (y_cheek2_chamfer, z_top - 4.0),
        (y_cheek2_top - 4.0, z_top),
        (0.0, z_top),
    ]
    sk_u_out = _add_polygon_sketch(doc, grp, 'UpperOuterSk', [upper_outer_pts], 'YZ', (inner_x, 0.0, 0.0))
    u_outer = _extrude(doc, grp, 'UpperOuterPlate', sk_u_out, arm_t)

    # Flush 2-color bed-face inlay with 1 mm x 1 mm V-groove on Upper Arm
    u_recess_pts = [
        (12.0, z_tier2 + 12.0),
        (28.0, z_tier2 + 12.0),
        (yg + (354.0 - z_tier2) * tan_t - 10.0, 354.0),
        (12.0, 354.0),
    ]
    u_outer, r_up_inlay = _add_bed_inlay_with_vgroove(doc, grp, u_outer, u_recess_pts, inner_x + arm_t, 'Upper')

    # Inboard rails: upper tail of Tier 1 (Z=133..198) + Tier 2 cradle (Z=212..371)
    u_rail1_pts = [
        (p_under_split[0] - 9.0, z_split),
        p_under_split,
        (yg - c / cos_t + 198.0 * tan_t, 198.0),
        (yg - c / cos_t + 198.0 * tan_t - 9.0, 198.0),
    ]
    u_rail2_pts = [
        _pt_yz(yg, z_tier2, -7.0, -9.0, sin_t, cos_t),
        _pt_yz(yg, z_tier2, -7.0, t_lap + 3.5, sin_t, cos_t),
        _pt_yz(yg, z_tier2, -4.0, t_lap + 6.5, sin_t, cos_t),
        p2_lip_tip_out,
        p2_lip_tip_top,
        p2_lip_in,
        p2_seat_in,
        p2_seat_back,
        (y_upper_chamfer, z_top - 4.0),
        (y_upper_top - 4.0, z_top),
        (y_upper_top - 9.0, z_top),
    ]
    sk_ur1 = _add_polygon_sketch(doc, grp, 'UpperRail1Sk', [u_rail1_pts], 'YZ', (rail_x0, 0.0, 0.0))
    sk_ur2 = _add_polygon_sketch(doc, grp, 'UpperRail2Sk', [u_rail2_pts], 'YZ', (rail_x0, 0.0, 0.0))
    u_r1 = _extrude(doc, grp, 'UpperRail1', sk_ur1, rail_t)
    u_r2 = _extrude(doc, grp, 'UpperRail2', sk_ur2, rail_t)

    # Extended inboard seat + under-seat gusset onto frame rail for Tier 2 (X = 146.7..160.7 mm)
    u_seat_pts = [
        _pt_yz(yg, z_tier2, -22.0, -9.0, sin_t, cos_t),
        _pt_yz(yg, z_tier2, -7.0, 16.0, sin_t, cos_t),
        _pt_yz(yg, z_tier2, -7.0, t_lap + 3.5, sin_t, cos_t),
        _pt_yz(yg, z_tier2, -4.0, t_lap + 6.5, sin_t, cos_t),
        p2_lip_tip_out,
        p2_lip_tip_top,
        p2_lip_in,
        p2_seat_in,
        p2_seat_back,
        _pt_yz(yg, z_tier2, 88.0, -c, sin_t, cos_t),
        _pt_yz(yg, z_tier2, 88.0, -9.0, sin_t, cos_t),
    ]
    sk_u_seat = _add_polygon_sketch(doc, grp, 'UpperSeatGussetSk', [u_seat_pts], 'YZ', (seat_x0, 0.0, 0.0))
    u_seat = _extrude(doc, grp, 'UpperSeatGusset', sk_u_seat, seat_extra_t)
    u_raw = _fuse(doc, grp, 'UpperArmRaw', [u_outer, u_r1, u_r2, u_seat])

    right_upper = _add_wall_pads_and_holes(doc, grp, u_raw, (240.0, 356.0), p, 'Upper')
    left_upper = _mirror_x(doc, grp, 'LeftUpperArm', right_upper)
    _register(doc, assembly, left_upper, '03_left_upper_arm', '03 / Left upper stacking arm')
    _register(doc, assembly, right_upper, '04_right_upper_arm', '04 / Right upper stacking arm')
    l_up_inlay = _mirror_x(doc, grp, 'LeftUpperInlay', r_up_inlay)
    _register(doc, assembly, l_up_inlay, '09_left_upper_inlay', '09 / Left upper 2-color inlay')
    _register(doc, assembly, r_up_inlay, '10_right_upper_inlay', '10 / Right upper 2-color inlay')


def build_fan_trays(doc, sources, assembly, p: dict):
    """Build 55-deg solid 12 mm fan mounting plates (05_left_fan_tray, 06_right_fan_tray).

    Flat butt seam at X = 0 glues into one rigid 345 mm plate; M4 heat-set inserts
    in the outer ends (y_local = +/-45 mm, z_local = 6 mm) accept M4 screws driven
    in from the outside of the Lower Arm side panels.
    """
    grp = doc.addObject('App::DocumentObjectGroup', 'WallFanTraysHistory')
    sources.addObject(grp)

    x_in = p['fitClearance'] / 2.0
    x_out = p['trayHalfSpanX']
    y_half = p['fanSize'] / 2.0 + p['fanClearance'] + p['trayFlangeThickness']  # 74.5 mm
    plate_t = p['trayDeckThickness']  # 12.0 mm solid plate
    fc_x = p['fanCenterX']

    # Solid 12 mm plate in fan-local XY (Z in [0, 12]; fan sits on Z in [-25, 0])
    # Flat butt edge at X = x_in for gluing; 6 mm chamfers on outer corners
    plate_pts = [
        (x_in, -y_half), (x_out - 6.0, -y_half),
        (x_out, -y_half + 6.0), (x_out, y_half - 6.0),
        (x_out - 6.0, y_half), (x_in, y_half),
    ]
    sk_plate = _add_polygon_sketch(doc, grp, 'SolidFanPlateSk', [plate_pts], 'XY', (0.0, 0.0, 0.0))
    plate_raw = _extrude(doc, grp, 'SolidFanPlateRaw', sk_plate, plate_t)

    # Cut 134 mm fan bore + four M4 heat-set insert pilot holes (dia 5.6 mm)
    half_pitch = p['fanHolePitch'] / 2.0
    r_fan_bore = 67.0
    r_ins = p['m4InsertDia'] / 2.0
    fan_circles = [(fc_x, 0.0, r_fan_bore)] + [
        (fc_x + sx * half_pitch, sy * half_pitch, r_ins)
        for sx in (-1, +1) for sy in (-1, +1)
    ]
    sk_fan_cuts = _add_circle_sketch(doc, grp, 'SolidFanCutsSk', fan_circles, 'XY', (0.0, 0.0, -1.0))
    fan_cut_tool = _extrude(doc, grp, 'SolidFanCutTool', sk_fan_cuts, plate_t + 2.0)
    plate_bored = _cut(doc, grp, 'SolidFanPlateBored', plate_raw, fan_cut_tool)

    # Flush radial intake guard on fan intake face (4.0 mm thick diagonal cross + 36 mm hub)
    guard_t = 4.0
    bar_w = 2.4 / math.sqrt(2.0)
    span = 68.0
    spoke_a = [
        (fc_x - span, -span + bar_w), (fc_x - span + bar_w, -span),
        (fc_x + span, span - bar_w), (fc_x + span - bar_w, span),
    ]
    spoke_b = [
        (fc_x - span, span - bar_w), (fc_x - span + bar_w, span),
        (fc_x + span, -span + bar_w), (fc_x + span - bar_w, -span),
    ]
    sk_sa = _add_polygon_sketch(doc, grp, 'FanGuardSpokeASk', [spoke_a], 'XY', (0.0, 0.0, 0.0))
    sk_sb = _add_polygon_sketch(doc, grp, 'FanGuardSpokeBSk', [spoke_b], 'XY', (0.0, 0.0, 0.0))
    g_sa = _extrude(doc, grp, 'FanGuardSpokeA', sk_sa, guard_t)
    g_sb = _extrude(doc, grp, 'FanGuardSpokeB', sk_sb, guard_t)
    sk_hub = _add_circle_sketch(doc, grp, 'FanGuardHubSk', [(fc_x, 0.0, 18.0)], 'XY', (0.0, 0.0, 0.0))
    g_hub = _extrude(doc, grp, 'FanGuardHub', sk_hub, guard_t)
    plate_guarded = _fuse(doc, grp, 'SolidFanPlateGuarded', [plate_bored, g_sa, g_sb, g_hub])

    # M4 heat-set insert bores (dia 5.6 mm x 12 mm deep) in outer end at y_local = +/-45, z_local = 6.0
    sk_end_holes = _add_circle_sketch(
        doc, grp, 'SolidFanEndInsSk',
        [(-45.0, 6.0, r_ins), (45.0, 6.0, r_ins)],
        'YZ', (x_out - 12.0, 0.0, 0.0),
    )
    end_hole_tool = _extrude(doc, grp, 'SolidFanEndInsCuts', sk_end_holes, 13.0)
    tray_r_local = _cut(doc, grp, 'SolidFanPlateRightLocal', plate_guarded, end_hole_tool)

    # Rotate +55 deg around X so outlet normal points wallward (-Y) and upward (+Z)
    right_tray = _move(
        doc, grp, 'RightAngledFanTray', tray_r_local,
        (0.0, p['fanCenterY'], p['fanCenterZ']),
        App.Rotation(App.Vector(1, 0, 0), p['fanTiltDeg']),
    )
    left_tray = _mirror_x(doc, grp, 'LeftAngledFanTray', right_tray)
    _register(doc, assembly, left_tray, '05_left_fan_tray', '05 / Left 55-deg solid fan plate')
    _register(doc, assembly, right_tray, '06_right_fan_tray', '06 / Right 55-deg solid fan plate')


def orient_for_print(key: str, shape, p: dict):
    """Orient part flat onto the Bambu P1S XY bed with zero supports."""
    result = shape.copy()
    if 'left_' in key and ('arm' in key or 'inlay' in key):
        result.rotate(App.Vector(), App.Vector(0, 1, 0), 90)
        pose = 'outer flat face down'
    elif 'right_' in key and ('arm' in key or 'inlay' in key):
        result.rotate(App.Vector(), App.Vector(0, 1, 0), -90)
        pose = 'outer flat face down'
    else:
        result.rotate(App.Vector(), App.Vector(1, 0, 0), -p['fanTiltDeg'])
        pose = 'fan tray deck flat down'
    b = result.BoundBox
    result.translate(App.Vector(128.0 - (b.XMin + b.XMax) / 2.0, 128.0 - (b.YMin + b.YMax) / 2.0, -b.ZMin))
    return result, pose


def export_parts(doc, assembly, p: dict):
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    PAGE_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    links = sorted(
        [o for o in assembly.Group if o.TypeId == 'App::Link'],
        key=lambda o: o.InstanceKey,
    )
    brim_xy = 2.0 * p['brimWidth']
    manifest_parts = []
    for link in links:
        key = link.InstanceKey
        shape = link.Shape
        placed, pose = orient_for_print(key, shape, p)
        placed.exportStep(str(EXPORT_DIR / f'{key}.step'))
        mesh_print = MeshPart.meshFromShape(Shape=placed, LinearDeflection=0.05, AngularDeflection=0.15, Relative=False)
        mesh_print.write(str(EXPORT_DIR / f'{key}.stl'))

        mesh_asm = MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.05, AngularDeflection=0.15, Relative=False)
        mesh_asm.write(str(PAGE_MODELS_DIR / f'{key}.stl'))

        b = placed.BoundBox
        vol_cm3 = float(shape.Volume) / 1000.0
        mass_g = vol_cm3 * p['petgDensity']
        family = 'inlay' if 'inlay' in key else ('arm' if 'arm' in key else 'tray')
        manifest_parts.append({
            'key': key,
            'label': link.Label,
            'family': family,
            'orientation': pose,
            'footprint_mm': [round(float(b.XLength), 2), round(float(b.YLength), 2), round(float(b.ZLength), 2)],
            'with_brim_mm': [round(float(b.XLength) + brim_xy, 2), round(float(b.YLength) + brim_xy, 2)],
            'volume_cm3': round(vol_cm3, 2),
            'mass_g': round(mass_g, 2),
        })

    manifest = {
        'name': 'Tight Wall-Mount Two-Banger 5560 Rack',
        'material': 'PETG',
        'density_g_per_cm3': p['petgDensity'],
        'bed': {'x': p['bedLimit'], 'y': p['bedLimit'], 'z': p['bedLimit'], 'brim': p['brimWidth']},
        'laptop': {
            'width': p['laptopWidth'],
            'depth': p['laptopDepth'],
            'thickness': p['laptopThickness'],
            'tilt_deg': p['tiltDeg'],
            'wall_gap': p['wallGap'],
            'stack_pitch_z': p['stackPitchZ'],
        },
        'fan': {
            'size': p['fanSize'],
            'thickness': p['fanThickness'],
            'center_x': p['fanCenterX'],
            'center_y': p['fanCenterY'],
            'center_z': p['fanCenterZ'],
            'tilt_deg': p['fanTiltDeg'],
        },
        'parts': manifest_parts,
    }
    (PAGE_MODELS_DIR / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(f'Exported {len(links)} STEP and STL files to {EXPORT_DIR} and viewer STLs to {PAGE_MODELS_DIR}', flush=True)


def build_all():
    if TARGET_FCSTD.exists():
        TARGET_FCSTD.unlink()
    doc = App.newDocument('TwoBangerWall5560')
    doc.Label = 'Tight Wall-Mount Two-Banger 5560 Rack'
    sources = doc.addObject('App::DocumentObjectGroup', 'WallRackSources')
    assembly = doc.addObject('App::Part', 'WallRackAssembly')
    assembly.Label = 'Tight Wall-Mount Two-Banger Assembled Rack'

    p = setup_parameters(doc)
    build_arms(doc, sources, assembly, p)
    build_fan_trays(doc, sources, assembly, p)
    doc.recompute()
    doc.saveAs(str(TARGET_FCSTD))
    export_parts(doc, assembly, p)
    print(f'Saved {TARGET_FCSTD}', flush=True)


build_all()
