"""Parametric FreeCAD builder for the Two-Banger 5560 Rack.

Greenfield back-to-back A-frame desk-standing rack for two Dell Precision 5560
laptops (344.4 x 230.3 x 20.0 mm) and two 140 x 140 x 25 mm fans.

Run headless:
    flatpak run --command=freecadcmd org.freecad.FreeCAD "$PWD"/two-banger/work/build_rack.py
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

TARGET_FCSTD = ROOT / 'TwoBanger.FCStd'
EXPORT_DIR = ROOT / 'export'
PAGE_MODELS_DIR = ROOT.parent / 'page' / 'models'


def _pt_yz(y_base: float, z_base: float, s: float, w: float,
           sin_t: float, cos_t: float, sign_y: int) -> tuple:
    """Convert cradle-local (s along laptop depth, w outward normal) to (Y, Z)."""
    y = sign_y * (y_base - s * sin_t + w * cos_t)
    z = z_base + s * cos_t + w * sin_t
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


def _register(doc, assembly, source, key: str, label: str, color: tuple):
    source.addProperty('App::PropertyString', 'PartKey', 'Identity')
    source.PartKey = key
    source.Label = label + ' / source'
    link = doc.addObject('App::Link', 'Rack_' + key)
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
    sheet.Label = 'Two-Banger Parameters'
    sheet.setColumnWidth('A', 190)
    sheet.setColumnWidth('B', 100)
    sheet.setColumnWidth('C', 55)
    sheet.setColumnWidth('D', 420)
    sheet.mergeCells('A1:D1')
    sheet.set('A1', 'TWO-BANGER 5560 RACK / DIMENSIONS IN MM')
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


def build_end_frames(doc, sources, assembly, p: dict):
    """Build 02_right_end_frame and mirror to 01_left_end_frame."""
    grp = doc.addObject('App::DocumentObjectGroup', 'EndFramesHistory')
    sources.addObject(grp)

    sin_t, cos_t, tan_t = p['sinTilt'], p['cosTilt'], p['tanTilt']
    yb = p['plenumBaseHalfY']     # 71.0 mm
    zb = p['laptopBaseZ']         # 47.0 mm
    c = p['cradleClearance']      # 0.5 mm
    t_lap = p['laptopThickness']  # 20.0 mm
    lip_h = p['outerLipHeight']   # 24.0 mm
    top_z = p['endFrameTopZ']     # 228.0 mm
    inner_x = p['innerWallX']     # 172.7 mm
    outer_t = p['endFrameThickness']  # 10.0 mm
    rail_t = p['railInboardDepth']    # 12.5 mm

    # S coordinate along tilted axis where outer cheek reaches top_z (228.0 mm)
    s_top = (top_z - zb) / cos_t  # (228 - 47) / 0.9703 = 186.54 mm
    y_top_inner = yb - s_top * sin_t - c / cos_t  # ~25.35 mm

    # Bottom outer corner of the cradle pocket (w = t_lap + 8.5, s = -8.5)
    y_foot_out = yb + (t_lap + 8.5) * cos_t + 8.5 * sin_t  # ~101.5 mm
    # Bottom inner corner of the foot arch (leaves 110 mm wide x 15 mm tall intake arch)
    y_arch = 55.0
    z_arch = p['deskClearanceZ'] - 1.0  # 15.0 mm

    # Outer plate YZ profile (extruded from X=172.7 to X=182.7 mm)
    # Positive Y side then mirrored across Y=0 to negative Y side
    p_lip_top_out = _pt_yz(yb, zb, lip_h, t_lap + 8.5, sin_t, cos_t, +1)
    p_lip_top_in = _pt_yz(yb, zb, lip_h, t_lap + c, sin_t, cos_t, +1)
    p_seat_in = _pt_yz(yb, zb, -c, t_lap + c, sin_t, cos_t, +1)
    p_seat_back = _pt_yz(yb, zb, -c, -c, sin_t, cos_t, +1)
    p_foot_corner = _pt_yz(yb, zb, -8.5, t_lap + 8.5, sin_t, cos_t, +1)

    outer_pts = [
        (y_arch, 0.0),
        (y_foot_out, 0.0),
        (y_foot_out, p_foot_corner[1]),
        p_lip_top_out,
        p_lip_top_in,
        p_seat_in,
        p_seat_back,
        (y_top_inner, top_z),
        (-y_top_inner, top_z),
        (-p_seat_back[0], p_seat_back[1]),
        (-p_seat_in[0], p_seat_in[1]),
        (-p_lip_top_in[0], p_lip_top_in[1]),
        (-p_lip_top_out[0], p_lip_top_out[1]),
        (-y_foot_out, p_foot_corner[1]),
        (-y_foot_out, 0.0),
        (-y_arch, 0.0),
        (-y_arch, z_arch),
        (y_arch, z_arch),
    ]
    sk_outer = _add_polygon_sketch(doc, grp, 'EndFrameOuterProfile', [outer_pts], 'YZ', (inner_x, 0.0, 0.0))
    outer_plate = _extrude(doc, grp, 'EndFrameOuterPlate', sk_outer, outer_t)

    # Inboard laptop support rails (X = 160.2 to 172.7 mm): one per laptop side (+Y and -Y)
    # Kept strictly behind underside (w <= -0.5) above Z=46.5, plus bottom cradle pocket!
    rail_x0 = inner_x - rail_t  # 160.2 mm
    rails = []
    for sign_y, tag in [(+1, 'Front'), (-1, 'Back')]:
        r_pts = [
            _pt_yz(yb, zb, -8.5, -10.5, sin_t, cos_t, sign_y),
            _pt_yz(yb, zb, -8.5, t_lap + 8.5, sin_t, cos_t, sign_y),
            _pt_yz(yb, zb, lip_h, t_lap + 8.5, sin_t, cos_t, sign_y),
            _pt_yz(yb, zb, lip_h, t_lap + c, sin_t, cos_t, sign_y),
            _pt_yz(yb, zb, -c, t_lap + c, sin_t, cos_t, sign_y),
            _pt_yz(yb, zb, -c, -c, sin_t, cos_t, sign_y),
            _pt_yz(yb, zb, s_top - 4.0, -c, sin_t, cos_t, sign_y),
            _pt_yz(yb, zb, s_top - 4.0, -10.5, sin_t, cos_t, sign_y),
        ]
        if sign_y < 0:
            r_pts = list(reversed(r_pts))
        sk_r = _add_polygon_sketch(doc, grp, f'EndFrameRail{tag}Sk', [r_pts], 'YZ', (rail_x0, 0.0, 0.0))
        rails.append(_extrude(doc, grp, f'EndFrameRail{tag}', sk_r, rail_t))

    frame_raw = _fuse(doc, grp, 'EndFrameRaw', [outer_plate] + rails)

    # Two M4 clearance holes (dia 4.5 mm) at Y = +/- 50.0 mm, Z = 23.0 mm to bolt to Fan Tray
    r_m4 = p['m4ClearanceDia'] / 2.0
    sk_holes = _add_circle_sketch(
        doc, grp, 'EndFrameBoltSk',
        [(-50.0, 23.0, r_m4), (50.0, 23.0, r_m4)],
        'YZ', (inner_x - 1.0, 0.0, 0.0),
    )
    hole_tool = _extrude(doc, grp, 'EndFrameBoltCuts', sk_holes, outer_t + 2.0)
    right_frame = _cut(doc, grp, 'RightEndFrame', frame_raw, hole_tool)
    left_frame = _mirror_x(doc, grp, 'LeftEndFrame', right_frame)

    _register(doc, assembly, left_frame, '01_left_end_frame', '01 / Left A-frame end cheek', (0.20, 0.34, 0.38))
    _register(doc, assembly, right_frame, '02_right_end_frame', '02 / Right A-frame end cheek', (0.20, 0.34, 0.38))


def build_fan_trays(doc, sources, assembly, p: dict):
    """Build 04_right_fan_tray and mirror to 03_left_fan_tray."""
    grp = doc.addObject('App::DocumentObjectGroup', 'FanTraysHistory')
    sources.addObject(grp)

    x_in = p['fitClearance'] / 2.0     # 0.1 mm (0.2 mm gap between L & R trays)
    x_out = p['trayHalfSpanX']         # 172.5 mm
    y_half = p['fanSize'] / 2.0 + p['fanClearance'] + p['trayFlangeThickness']  # 74.5 mm
    z_bot = p['deskClearanceZ']        # 16.0 mm
    deck_t = p['trayDeckThickness']    # 5.0 mm (deck top at Z = 21.0 mm)
    flange_h = p['trayFlangeHeight']   # 14.0 mm (flange top at Z = 30.0 mm)
    flange_t = p['trayFlangeThickness']  # 4.0 mm
    fc_x = p['fanCenterX']             # 71.0 mm

    # 1. Base deck plate (X in [0.1, 172.5], Y in [-74.5, +74.5], Z in [16.0, 21.0])
    deck_pts = [(x_in, -y_half), (x_out, -y_half), (x_out, y_half), (x_in, y_half)]
    sk_deck = _add_polygon_sketch(doc, grp, 'TrayDeckSk', [deck_pts], 'XY', (0.0, 0.0, z_bot))
    deck = _extrude(doc, grp, 'TrayDeck', sk_deck, deck_t)

    # 2. U-shaped perimeter stiffening flanges (center X=0.1..4.1, outer X=164.5..172.5,
    #    front Y=70.5..74.5, back Y=-74.5..-70.5) on top of deck (Z = 21.0 to 30.0 mm)
    z_deck_top = z_bot + deck_t
    flange_up = flange_h - deck_t  # 9.0 mm above deck
    # Outer end boss is 8.0 mm thick in X (X = 164.5..172.5) for M4 heat-set inserts
    flange_outer_pts = [
        (x_in, -y_half), (x_out, -y_half), (x_out, y_half), (x_in, y_half),
        (x_in, y_half - flange_t), (x_out - 8.0, y_half - flange_t),
        (x_out - 8.0, -y_half + flange_t), (x_in, -y_half + flange_t),
    ]
    # Center flange along X = 0.1..4.1 mm
    c_flange_pts = [(x_in, -y_half), (x_in + flange_t, -y_half), (x_in + flange_t, y_half), (x_in, y_half)]
    sk_f1 = _add_polygon_sketch(doc, grp, 'TrayPerimFlangeSk', [flange_outer_pts], 'XY', (0.0, 0.0, z_deck_top))
    sk_f2 = _add_polygon_sketch(doc, grp, 'TrayCenterFlangeSk', [c_flange_pts], 'XY', (0.0, 0.0, z_deck_top))
    f1 = _extrude(doc, grp, 'TrayPerimFlange', sk_f1, flange_up)
    f2 = _extrude(doc, grp, 'TrayCenterFlange', sk_f2, flange_up)

    # Note: keep center and perimeter flanges cleanly merged
    tray_raw = _fuse(doc, grp, 'TrayRaw', [deck, f1, f2])

    # 3. Cut circular 134 mm fan bore + four 4.3 mm fan mounting holes (124.5 mm square)
    half_pitch = p['fanHolePitch'] / 2.0  # 62.25 mm
    r_fan_bore = 67.0                     # 134.0 mm dia clear opening
    r_fan_hole = p['fanHoleDiameter'] / 2.0  # 2.15 mm
    fan_circles = [(fc_x, 0.0, r_fan_bore)] + [
        (fc_x + sx * half_pitch, sy * half_pitch, r_fan_hole)
        for sx in (-1, +1) for sy in (-1, +1)
    ]
    sk_fan_cuts = _add_circle_sketch(doc, grp, 'TrayFanCutsSk', fan_circles, 'XY', (0.0, 0.0, z_bot - 1.0))
    fan_cut_tool = _extrude(doc, grp, 'TrayFanCutTool', sk_fan_cuts, deck_t + 2.0)
    tray_bored = _cut(doc, grp, 'TrayFanBored', tray_raw, fan_cut_tool)

    # 4. Cut M4 bolt holes in end flange (M4 insert pilot dia 5.6 mm at Y=+/-50, Z=23)
    #    and center splice flange (M4 clearance dia 4.5 mm at Y=+/-45, Z=25.5)
    r_ins = p['m4InsertDia'] / 2.0
    r_clr = p['m4ClearanceDia'] / 2.0
    sk_end_holes = _add_circle_sketch(
        doc, grp, 'TrayEndInsertSk',
        [(-50.0, 23.0, r_ins), (50.0, 23.0, r_ins)],
        'YZ', (x_out - 9.0, 0.0, 0.0),
    )
    end_hole_tool = _extrude(doc, grp, 'TrayEndInsertCuts', sk_end_holes, 10.0)
    tray_end_cut = _cut(doc, grp, 'TrayEndCut', tray_bored, end_hole_tool)

    sk_ctr_holes = _add_circle_sketch(
        doc, grp, 'TrayCenterBoltSk',
        [(-45.0, 25.5, r_clr), (45.0, 25.5, r_clr)],
        'YZ', (x_in - 1.0, 0.0, 0.0),
    )
    ctr_hole_tool = _extrude(doc, grp, 'TrayCenterBoltCuts', sk_ctr_holes, flange_t + 2.0)
    right_tray = _cut(doc, grp, 'RightFanTray', tray_end_cut, ctr_hole_tool)
    left_tray = _mirror_x(doc, grp, 'LeftFanTray', right_tray)

    _register(doc, assembly, left_tray, '03_left_fan_tray', '03 / Left 140 mm fan tray half', (0.16, 0.50, 0.52))
    _register(doc, assembly, right_tray, '04_right_fan_tray', '04 / Right 140 mm fan tray half', (0.16, 0.50, 0.52))


def orient_for_print(key: str, shape):
    """Orient part flat onto the Bambu P1S XY bed with zero supports."""
    result = shape.copy()
    if key == '01_left_end_frame':
        result.rotate(App.Vector(), App.Vector(0, 1, 0), 90)
        pose = 'outer flat face down'
    elif key == '02_right_end_frame':
        result.rotate(App.Vector(), App.Vector(0, 1, 0), -90)
        pose = 'outer flat face down'
    else:
        pose = 'bottom deck flat down'
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
        # 1. Print-oriented STEP and STL for slicing
        placed, pose = orient_for_print(key, shape)
        placed.exportStep(str(EXPORT_DIR / f'{key}.step'))
        mesh_print = MeshPart.meshFromShape(Shape=placed, LinearDeflection=0.05, AngularDeflection=0.15, Relative=False)
        mesh_print.write(str(EXPORT_DIR / f'{key}.stl'))

        # 2. Installed-position STL for the Three.js assembly viewer
        mesh_asm = MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.05, AngularDeflection=0.15, Relative=False)
        mesh_asm.write(str(PAGE_MODELS_DIR / f'{key}.stl'))

        b = placed.BoundBox
        vol_cm3 = float(shape.Volume) / 1000.0
        mass_g = vol_cm3 * p['petgDensity']
        manifest_parts.append({
            'key': key,
            'label': link.Label,
            'family': 'frame' if 'end_frame' in key else 'tray',
            'orientation': pose,
            'footprint_mm': [round(float(b.XLength), 2), round(float(b.YLength), 2), round(float(b.ZLength), 2)],
            'with_brim_mm': [round(float(b.XLength) + brim_xy, 2), round(float(b.YLength) + brim_xy, 2)],
            'volume_cm3': round(vol_cm3, 2),
            'mass_g': round(mass_g, 2),
        })

    manifest = {
        'name': 'Two-Banger 5560 Rack',
        'material': 'PETG',
        'density_g_per_cm3': p['petgDensity'],
        'bed': {'x': p['bedLimit'], 'y': p['bedLimit'], 'z': p['bedLimit'], 'brim': p['brimWidth']},
        'laptop': {
            'width': p['laptopWidth'],
            'depth': p['laptopDepth'],
            'thickness': p['laptopThickness'],
            'tilt_deg': p['tiltDeg'],
            'plenum_base_half_y': p['plenumBaseHalfY'],
            'base_z': p['laptopBaseZ'],
        },
        'fan': {
            'size': p['fanSize'],
            'thickness': p['fanThickness'],
            'center_x': p['fanCenterX'],
            'deck_top_z': p['fanDeckTopZ'],
        },
        'parts': manifest_parts,
    }
    (PAGE_MODELS_DIR / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(f'Exported {len(links)} STEP and STL files to {EXPORT_DIR} and viewer STLs to {PAGE_MODELS_DIR}', flush=True)


def build_all():
    if TARGET_FCSTD.exists():
        TARGET_FCSTD.unlink()
    doc = App.newDocument('TwoBanger5560')
    doc.Label = 'Two-Banger 5560 Rack'
    sources = doc.addObject('App::DocumentObjectGroup', 'RackSources')
    assembly = doc.addObject('App::Part', 'RackAssembly')
    assembly.Label = 'Two-Banger Assembled Rack'

    p = setup_parameters(doc)
    build_end_frames(doc, sources, assembly, p)
    build_fan_trays(doc, sources, assembly, p)
    doc.recompute()
    doc.saveAs(str(TARGET_FCSTD))
    export_parts(doc, assembly, p)
    print(f'Saved {TARGET_FCSTD}', flush=True)


build_all()
