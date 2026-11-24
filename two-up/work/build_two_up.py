"""Build the Two-Up Stacked Variant with native constrained sketches and stock FreeCAD features.

Follows the conventions of ../../minimalist/build.py and
../../minimalist/native.py: uses the Native class, E/bind parametric
expressions, a TwoUpParameters spreadsheet, and family/register/finish helpers.
Exports oriented STEP and STL files for all 39 parts (00_fit_coupon plus 01-38
assembly parts) to two-up/work/export/ and writes
measured B-rep volumes and bounding boxes to measured.json.
"""
from pathlib import Path
import argparse
import json
import math
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from params import PARAMETERS, make_params

try:
    import FreeCAD as App
    import MeshPart
    import Part
    from native import Native, E, rectangle, bind, ex
    HAS_FREECAD = True
except ImportError:
    App = None
    MeshPart = None
    Part = None
    Native = None
    HAS_FREECAD = False

    class E(float):
        """Fallback expression float when FreeCAD is not loaded."""

        def __new__(cls, value, expression):
            obj = super().__new__(cls, value)
            obj.expression = expression
            return obj

        def op(self, other, sign, operation):
            return E(operation(float(self), float(other)), '(' + ex(self) + sign + ex(other) + ')')

        def __add__(self, v): return self.op(v, '+', lambda a, b: a + b)
        __radd__ = __add__
        def __sub__(self, v): return self.op(v, '-', lambda a, b: a - b)
        def __rsub__(self, v): return E(float(v) - float(self), '(' + ex(v) + '-' + ex(self) + ')')
        def __mul__(self, v): return self.op(v, '*', lambda a, b: a * b)
        __rmul__ = __mul__
        def __truediv__(self, v): return self.op(v, '/', lambda a, b: a / b)
        def __neg__(self): return E(-float(self), '(-' + ex(self) + ')')

    def ex(value):
        return value.expression if isinstance(value, E) else repr(float(value))

    def bind(obj, prop, value):
        if isinstance(value, E):
            obj.setExpression(prop, value.expression)

    def rectangle(x0, x1, y0, y1):
        return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


TARGET = ROOT / 'Laptop_Wall_Mount_TwoUp.FCStd'
EXPORT_DIR = ROOT / 'export'
MEASURED_JSON = ROOT / 'measured.json'


def require_freecad():
    if not HAS_FREECAD:
        raise RuntimeError(
            'FreeCAD Python modules are not available in this interpreter. '
            'Run via: flatpak run --command=freecadcmd org.freecad.FreeCAD '
            'two-up/work/build_two_up.py --stage all'
        )


def view(doc, message):
    require_freecad()
    App.Console.PrintMessage(message + '\n')
    if not App.GuiUp:
        print(message, flush=True)
        return
    import FreeCADGui as Gui
    App.setActiveDocument(doc.Name)
    Gui.activeDocument().activeView().viewAxonometric()
    Gui.activeDocument().activeView().fitAll()
    Gui.updateGui()


def open_document(fresh=False):
    require_freecad()
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    if fresh and TARGET.exists():
        TARGET.unlink()
    if TARGET.exists():
        for d in App.listDocuments().values():
            if d.FileName and Path(d.FileName).resolve() == TARGET.resolve():
                return d
        return App.openDocument(str(TARGET))
    doc = App.newDocument('TwoUpWallMount')
    doc.Label = 'Laptop wall mount / Minimalist Two-Up Variant'
    doc.saveAs(str(TARGET))
    return doc


def setup(doc):
    require_freecad()
    if doc.getObject('TwoUpParameters'):
        return
    sources = doc.addObject('App::DocumentObjectGroup', 'TwoUpSources')
    sources.Label = 'TwoUp / Native construction history'
    assembly = doc.addObject('App::Part', 'TwoUpAssembly')
    assembly.Label = 'TwoUp / Installed two-laptop assembly'
    assembly.addProperty('App::PropertyString', 'Revision', 'Design')
    assembly.Revision = 'Two-Up M1.1 Stacked Variant'
    sheet = doc.addObject('Spreadsheet::Sheet', 'TwoUpParameters')
    sheet.Label = 'TwoUp / Design parameters (15-deg two-laptop stack)'
    sheet.setColumnWidth('A', 210)
    sheet.setColumnWidth('B', 125)
    sheet.setColumnWidth('C', 55)
    sheet.setColumnWidth('D', 485)
    sheet.mergeCells('A1:D1')
    sheet.set('A1', 'MINIMALIST TWO-UP STACK / DIMENSIONS IN MILLIMETERS')
    sheet.setBackground('A1:D1', (0.10, 0.24, 0.27))
    sheet.setForeground('A1:D1', (1.0, 1.0, 1.0))
    sheet.setStyle('A1:D1', 'bold', 'add')
    sheet.mergeCells('A2:D2')
    sheet.set('A2', 'Blue: inputs. Gray: derived. Check P1S 256 mm bed fit after edits.')
    row, cells, derived = 4, {}, []
    for entry in PARAMETERS:
        if entry[1] is None:
            sheet.mergeCells(f'A{row}:D{row}')
            sheet.set(f'A{row}', entry[0])
            sheet.setBackground(f'A{row}:D{row}', (0.81, 0.88, 0.86))
            sheet.setStyle(f'A{row}:D{row}', 'bold', 'add')
        else:
            name, value, unit, description = entry
            cell = 'B' + str(row)
            cells[name] = cell
            sheet.set('A' + str(row), name)
            sheet.set('C' + str(row), unit)
            sheet.set('D' + str(row), description)
            if isinstance(value, str):
                derived.append((cell, value))
                sheet.set(cell, '1 ' + unit)
                sheet.setBackground(cell, (0.91, 0.92, 0.92))
            else:
                sheet.set(cell, ('=' if value < 0 else '') + str(value) + (' ' + unit if unit else ''))
                sheet.setBackground(cell, (0.83, 0.92, 1.0))
            sheet.setAlias(cell, name)
        row += 1
    for cell, formula in derived:
        sheet.set(cell, formula)
    doc.recompute()
    assert not any(s in ('Invalid', 'Error') for s in sheet.State), sheet.State
    (Path(doc.FileName).parent / 'parameter_cells.json').write_text(
        json.dumps(cells, indent=2), encoding='utf-8'
    )
    doc.save()
    view(doc, 'TwoUp parameter spreadsheet initialized.')


def values(doc):
    require_freecad()
    sheet = doc.getObject('TwoUpParameters')
    result = {}
    for entry in PARAMETERS:
        if entry[1] is None:
            continue
        name, _, unit, _ = entry
        raw = getattr(sheet, name)
        number = raw.Value if hasattr(raw, 'Value') else App.Units.Quantity(str(raw)).Value
        unit_div = ' / (1 mm)' if unit == 'mm' else ' / (1 deg)' if unit == 'deg' else ''
        result[name] = E(number, '(TwoUpParameters.' + name + unit_div + ')')
    return result


def family(doc, name):
    require_freecad()
    group = doc.addObject('App::DocumentObjectGroup', 'TwoUp' + name + 'History')
    group.Label = name + ' / native sketches and features'
    doc.getObject('TwoUpSources').addObject(group)
    return Native(doc, group)


def register(doc, source, key, label, color):
    require_freecad()
    source.addProperty('App::PropertyString', 'PartKey', 'Identity')
    source.PartKey = key
    source.Label = label + ' / source'
    link = doc.addObject('App::Link', 'TwoUpInstalled' + key.replace('_', ''))
    link.setLink(source)
    link.LinkTransform = True
    link.LinkPlacement = App.Placement()
    link.addProperty('App::PropertyString', 'InstanceKey', 'Identity')
    link.InstanceKey = key
    link.Label = label
    doc.getObject('TwoUpAssembly').addObject(link)
    if App.GuiUp:
        source.ViewObject.ShapeColor = color
        source.ViewObject.LineColor = (0.11, 0.16, 0.18)
        source.ViewObject.DisplayMode = 'Flat Lines'
        source.ViewObject.LineWidth = 1.1
    source.Visibility = False
    link.Visibility = True
    return link


def finish(doc, native, message):
    require_freecad()
    doc.recompute()
    errors = []
    for obj in native.group.Group:
        if obj.TypeId == 'Sketcher::SketchObject' and not obj.FullyConstrained:
            errors.append(obj.Name + ': unconstrained')
        if 'Invalid' in obj.State or 'Error' in obj.State:
            errors.append(obj.Name + ': ' + str(obj.State))
        if hasattr(obj, 'Shape') and obj.TypeId != 'Sketcher::SketchObject':
            if obj.Shape.isNull() or not obj.Shape.isValid():
                errors.append(obj.Name + ': invalid shape')
            if hasattr(obj, 'PartKey') and len(obj.Shape.Solids) != 1:
                errors.append(obj.Name + ': final part has ' + str(len(obj.Shape.Solids)) + ' solids')
    assert not errors, errors
    for obj in native.group.Group:
        obj.Visibility = False
    doc.getObject('TwoUpAssembly').Visibility = True
    doc.save()
    view(doc, message)


def _add_wall_pads_and_holes(n, p, body, z_stations, prefix):
    """Fuse reinforced M1.1 wall pads + 6 mm tapered gusset webs and cut teardrop bores."""
    t = p['armThickness']
    half_pad = p['wallPadHeight'] / 2
    web = p['wallGussetWeb']
    depth = p['wallPadDepth']
    pads, gussets = [], []
    for index, z in enumerate(z_stations):
        outline_pad = [
            (-30, z - half_pad + 3), (-27, z - half_pad),
            (-3, z - half_pad), (0, z - half_pad + 3),
            (0, z + half_pad - 3), (-3, z + half_pad),
            (-27, z + half_pad), (-30, z + half_pad - 3),
        ]
        pads.append(n.prism(f'{prefix}WallPad{index}', outline_pad, 'XZ', (0, depth, 0), depth))
        web_profile = [
            (-27, depth - 2), (-27, depth),
            (-t + 3, depth + p['wallGussetRise']),
            (0, depth + p['wallGussetRise']), (0, depth - 2),
        ]
        for side, low in [('Lower', z - half_pad), ('Upper', z + half_pad - web)]:
            gussets.append(n.prism(f'{prefix}WallGusset{index}{side}', web_profile, 'XY', (0, 0, low), web))
    body = n.fuse(f'{prefix}WithWallPads', [body] + pads + gussets)

    holes, roofs = [], []
    radius = p['wallBoltDiameter'] / 2
    q = radius / math.sqrt(2)
    for z in z_stations:
        holes.append((-18, z, radius))
        roofs.append([(-18 - q, z - q), (-18 - 2 * q, z), (-18 - q, z + q)])
    bores = n.extrusion(f'{prefix}WallBores', n.circle(f'{prefix}WallBoreCircles', holes, 'XZ', (0, depth + 1, 0)), depth + 2)
    roof = n.extrusion(f'{prefix}WallBoreRoofs', n.sketch(f'{prefix}WallTeardrops', roofs, 'XZ', (0, depth + 1, 0)), depth + 2)
    return n.cut(f'{prefix}Finished', body, n.fuse(f'{prefix}WallHoleTools', [bores, roof]))


def arms(doc):
    """Build Lower Tilted Arms (01/02), Upper Stacking Tilted Arms (09/10), and Fit Coupon (00)."""
    if doc.getObject('TwoUpArmsHistory'):
        return
    p = values(doc)
    num = make_params()
    n = family(doc, 'Arms')
    t = p['armThickness']
    back0 = p['rearFace']
    tan_t = num['tanTilt']
    sin_t = num['sinTilt']
    cos_t = num['cosTilt']

    front0_y = back0 + (p['laptopThickness'] + 2 * p['padThickness']) * cos_t
    outer0_y = front0_y + p['frontLip'] * cos_t
    tine_top_z = p['tineHeight'] * cos_t
    tine_top_y = outer0_y + p['tineHeight'] * sin_t
    tine_inner_y = front0_y + p['tineHeight'] * sin_t

    # 0. Fit Coupon (00_fit_coupon): 80 x 45 x 12 mm splice/cradle sample block
    half_y = p['keyWidth'] / 2 + p['fitClearance']
    half_z = p['keyHeight'] / 2 + p['fitClearance']
    coupon_body = n.prism('TwoUpCouponBase', rectangle(0, 45, 0, 80), 'YZ', (-t, 0, 0), t)
    coupon_cuts = [
        rectangle(10, 32, 12, 44),
        rectangle(20 - half_y, 20 + half_y, 52 - half_z, 52 + half_z),
        rectangle(20 - half_y, 20 + half_y, 68 - half_z, 68 + half_z),
    ]
    coupon_tool = n.extrusion('TwoUpCouponCuts', n.sketch('TwoUpCouponCutProfiles', coupon_cuts, 'YZ', (-t - 1, 0, 0)), t + 2)
    coupon_done = n.cut('TwoUpCouponFinished', coupon_body, coupon_tool)
    coupon_placed = n.move('TwoUpFitCoupon', coupon_done, (p['armOriginX'], 0, -140))
    register(doc, coupon_placed, '00_fit_coupon', '00 / Cropped arm splice & cradle fit coupon', (0.72, 0.45, 0.22))

    # 1. Lower Tilted Arm (Z = -74.0 to +160.0 mm -> 234.0 mm total length)
    z_bot, z_split = p['lowerArmBottomZ'], p['lowerArmTopZ']
    back_split_y = back0 + z_split * tan_t
    lower_outline = [
        (0, z_bot + 2), (2, z_bot), (8, z_bot), (30, -64), (outer0_y, -12),
        (tine_top_y, tine_top_z - 2), (tine_top_y - 2, tine_top_z),
        (tine_inner_y + 2, tine_top_z), (tine_inner_y, tine_top_z - 2),
        (front0_y, 2), (front0_y - 2, 0), (back0, 0),
        (back_split_y, z_split - 2), (back_split_y - 2, z_split),
        (2, z_split), (0, z_split - 2),
    ]
    lower_body = n.prism('TwoUpLowerArmOutline', lower_outline, 'YZ', (-t, 0, 0), t)
    lower_wins = []
    cell = (z_split - 26) / 4
    for i in range(4):
        low, high = 14 + i * cell, 14 + (i + 1) * cell - 8
        r_low = back0 + low * tan_t - 14
        r_high = back0 + high * tan_t - 14
        lower_wins.append([(10, low), (r_low, low), (r_high, high), (10, high)])
    lower_wins += [
        [(12, -57), (23, -53), (23, -16), (12, -16)],
        [(36, -40), (outer0_y - 9, -16), (36, -16)],
        rectangle(front0_y + 2, outer0_y - 2, 10, tine_top_z - 8),
    ]
    lower_tools = n.extrusion('TwoUpLowerArmLightening', n.sketch('TwoUpLowerArmWindows', lower_wins, 'YZ', (-t - 1, 0, 0)), t + 2)
    lower_body = n.cut('TwoUpLowerArmOpen', lower_body, lower_tools)
    cheek1 = n.box('TwoUpLowerLateralStop', -p['sideLip'], 0, back0, front0_y, -2, 14)
    lower_body = n.fuse('TwoUpLowerWithCheek', [lower_body, cheek1])

    lower_rungs = [-54, -30] + [p['ladderStart'] + i * p['rungPitch'] for i in range(7)] + [138, 150]
    lower_slots = [rectangle(p['ladderY'] - half_y, p['ladderY'] + half_y, z - half_z, z + half_z) for z in lower_rungs]
    lower_slot_tool = n.extrusion('TwoUpLowerSlots', n.sketch('TwoUpLowerRungs', lower_slots, 'YZ', (-t - 1, 0, 0)), t + 2)
    lower_body = n.cut('TwoUpLowerIndexed', lower_body, lower_slot_tool)
    lower_body = _add_wall_pads_and_holes(n, p, lower_body, (p['armBoltLowZ'], p['armBoltHighZ']), 'TwoUpLower')

    right_lower = n.move('TwoUpRightLowerArm', lower_body, (p['armOriginX'], 0, 0))
    left_lower = n.mirror('TwoUpLeftLowerArm', right_lower)
    register(doc, left_lower, '01_left_lower_arm', '01 / Left lower tilted arm', (0.23, 0.30, 0.33))
    register(doc, right_lower, '02_right_lower_arm', '02 / Right lower tilted arm', (0.23, 0.30, 0.33))

    # 2. Upper Stacking Tilted Arm (Z = +160.0 to +395.0 mm -> 235.0 mm total length)
    z_tier2, z_top = p['stackPitchZ'], p['upperArmTopZ']
    y_tier1_hinge = back0 + 222.5 * tan_t
    y_top_rear = back0 + (z_top - z_tier2) * tan_t
    upper_outline = [
        (0, z_split), (back_split_y, z_split), (y_tier1_hinge, 222.5),
        (outer0_y, z_tier2 - 12),
        (tine_top_y, z_tier2 + tine_top_z - 2), (tine_top_y - 2, z_tier2 + tine_top_z),
        (tine_inner_y + 2, z_tier2 + tine_top_z), (tine_inner_y, z_tier2 + tine_top_z - 2),
        (front0_y, z_tier2 + 2), (front0_y - 2, z_tier2), (back0, z_tier2),
        (y_top_rear, z_top - 2), (y_top_rear - 2, z_top), (0, z_top),
    ]
    upper_body = n.prism('TwoUpUpperArmOutline', upper_outline, 'YZ', (-t, 0, 0), t)
    upper_wins = [
        rectangle(10, 68, 170, 212),
        rectangle(10, 48, 222, 250),
        rectangle(10, 36, 272, 324),
        rectangle(10, 52, 334, 382),
        rectangle(front0_y + 2, outer0_y - 2, z_tier2 + 10, z_tier2 + tine_top_z - 8),
    ]
    upper_tools = n.extrusion('TwoUpUpperArmLightening', n.sketch('TwoUpUpperArmWindows', upper_wins, 'YZ', (-t - 1, 0, 0)), t + 2)
    upper_body = n.cut('TwoUpUpperArmOpen', upper_body, upper_tools)
    cheek2 = n.box('TwoUpUpperLateralStop', -p['sideLip'], 0, back0, front0_y, z_tier2 - 2, z_tier2 + 14)
    upper_body = n.fuse('TwoUpUpperWithCheek', [upper_body, cheek2])

    upper_rungs = [166, 190] + [z_tier2 + p['ladderStart'] + i * p['rungPitch'] for i in range(7)]
    upper_slots = [rectangle(p['ladderY'] - half_y, p['ladderY'] + half_y, z - half_z, z + half_z) for z in upper_rungs]
    upper_slot_tool = n.extrusion('TwoUpUpperSlots', n.sketch('TwoUpUpperRungs', upper_slots, 'YZ', (-t - 1, 0, 0)), t + 2)
    upper_body = n.cut('TwoUpUpperIndexed', upper_body, upper_slot_tool)
    upper_body = _add_wall_pads_and_holes(
        n, p, upper_body,
        (z_tier2 + p['armBoltLowZ'], z_tier2 + p['armBoltHighZ'] - 25),
        'TwoUpUpper',
    )

    right_upper = n.move('TwoUpRightUpperArm', upper_body, (p['armOriginX'], 0, 0))
    left_upper = n.mirror('TwoUpLeftUpperArm', right_upper)
    register(doc, left_upper, '09_left_upper_arm', '09 / Left upper stacking arm', (0.26, 0.34, 0.38))
    register(doc, right_upper, '10_right_upper_arm', '10 / Right upper stacking arm', (0.26, 0.34, 0.38))
    finish(doc, n, 'Two-Up lower and upper tilted arms built within P1S 256 mm bed limits.')


def fan_transform(n, name, shape, p):
    return n.move(
        name, shape,
        (-p['fanOffsetX'], p['fanCenterY'], p['fanCenterZ']),
        App.Rotation(App.Vector(1, 0, 0), 45),
    )


def fans(doc):
    """Build M1.1 open fan cradles (03/04) and removable caps (05/06) matching minimalist/build.py:265-375."""
    if doc.getObject('TwoUpFansHistory'):
        return
    p = values(doc)
    n = family(doc, 'Fans')
    half, gap, wall = p['fanWidth'] / 2, p['fitClearance'], p['fanFrameWall']
    inner, outer = half + gap, half + gap + wall
    bottom, top = -p['fanThickness'] - wall, gap + 4.8
    opening = half - 4
    rings = [rectangle(-outer, outer, -outer, inner), list(reversed(rectangle(-opening, opening, -opening, opening)))]
    ring = n.extrusion('TwoUpGrilleRim', n.sketch('TwoUpGrilleRimProfile', rings, 'XY', (0, 0, bottom)), wall)
    d = p['grilleBar'] / math.sqrt(2)
    a = opening + 1
    bars = [
        n.prism('TwoUpGrilleDiagA', [(-a, -a + d), (-a + d, -a), (a, a - d), (a - d, a)], 'XY', (0, 0, bottom), wall),
        n.prism('TwoUpGrilleDiagB', [(-a, a - d), (-a + d, a), (a, -a + d), (a - d, -a)], 'XY', (0, 0, bottom), wall),
    ]
    right_profile = [(inner, bottom), (outer, bottom), (outer, top), (inner - 4, top), (inner - 4, gap + 4), (inner, gap)]
    right_rail = n.prism('TwoUpFanRightGuide', right_profile, 'XZ', (0, inner, 0), 2 * inner)
    left_rail = n.prism('TwoUpFanLeftGuide', [(-x, z) for x, z in reversed(right_profile)], 'XZ', (0, inner, 0), 2 * inner)
    back = n.box('TwoUpFanBackStop', -outer, outer, -outer, -inner, bottom, gap + 2.4)
    solid = n.fuse('TwoUpOpenFanFrame', [ring, right_rail, left_rail, back] + bars)

    windows = []
    for factor in (-0.7, -0.233333333333, 0.233333333333, 0.7):
        center = half * factor
        windows.append([(center - 10, bottom + 6), (center + 10, bottom + 6), (center, bottom + 22)])
    side_tools = n.extrusion('TwoUpFanSideWindows', n.sketch('TwoUpFanSideWindowProfiles', windows, 'YZ', (-outer - 1, 0, 0)), 2 * outer + 2)
    solid = n.cut('TwoUpPerforatedFanGuides', solid, side_tools)

    back_windows = []
    for factor in (-0.65, 0, 0.65):
        x = half * factor
        back_windows.append([(x - 12, bottom + 6), (x + 12, bottom + 6), (x, bottom + 24)])
    back_tools = n.extrusion('TwoUpFanBackWindows', n.sketch('TwoUpFanBackWindowProfiles', back_windows, 'XZ', (0, -inner + 1, 0)), wall + 2)
    solid = n.cut('TwoUpOpenBackStop', solid, back_tools)

    boss_x, boss_z = inner + 3.7, bottom + 16
    bosses = [
        n.extrusion('TwoUpCapBoss' + s, n.circle('TwoUpCapBossProf' + s, [(x, boss_z, 3.7)], 'XZ', (0, inner, 0)), 8)
        for s, x in [('L', -boss_x), ('R', boss_x)]
    ]
    solid = n.fuse('TwoUpFanWithSockets', [solid] + bosses)
    bores = n.extrusion(
        'TwoUpCapBores',
        n.circle('TwoUpCapBoreProfs', [(-boss_x, boss_z, p['capPinDiameter'] / 2 + gap), (boss_x, boss_z, p['capPinDiameter'] / 2 + gap)], 'XZ', (0, inner + 1, 0)),
        10,
    )
    solid = n.cut('TwoUpFanFrameLocal', solid, bores)
    relief_radius = p['capPinDiameter'] / 2 + gap + p['retentionInterference'] / 2 + gap
    relief = n.extrusion(
        'TwoUpCapCrownReleaseSpace',
        n.circle('TwoUpCapCrownReleaseProfiles', [(-boss_x, boss_z, relief_radius), (boss_x, boss_z, relief_radius)], 'XZ', (0, inner - 8, 0)),
        6,
    )
    solid = n.cut('TwoUpFanFrameCrownClearance', solid, relief)
    frame = fan_transform(n, 'TwoUpFanAt45', solid, p)

    inside = -p['armThickness'] - gap - p['carriageThickness']
    y = p['ladderY']
    hanger_outline = [(y - 7, -63), (y - 10, -108), (110, -16), (y + 7, -18), (y - 7, -18)]
    hanger = n.prism('TwoUpFanHanger', hanger_outline, 'YZ', (inside, 0, 0), p['carriageThickness'])
    cutouts = [
        [(y + 11, -57), (y + 11, -28), (94, -24)],
        [(y - 5, -87), (y - 3, -68), (y + 14, -66)],
    ]
    hollow = n.extrusion('TwoUpFanHangerWindows', n.sketch('TwoUpFanHangerWindowProfiles', cutouts, 'YZ', (inside - 1, 0, 0)), p['carriageThickness'] + 2)
    hanger = n.cut('TwoUpOpenFanHanger', hanger, hollow)
    half_y = p['keyWidth'] / 2 + gap
    half_z = p['keyHeight'] / 2 + gap
    holes = [rectangle(y - half_y, y + half_y, z - half_z, z + half_z) for z in (-54, -30)]
    sockets = n.extrusion('TwoUpFanHangerSlots', n.sketch('TwoUpFanHangerSlotProfiles', holes, 'YZ', (inside - 1, 0, 0)), p['carriageThickness'] + 2)
    hanger = n.cut('TwoUpFanHangerFinished', hanger, sockets)
    keeper_x = inside - gap - p['keeperDiameter'] / 2
    keeper_clear = p['keeperDiameter'] / 2 + 2 * gap + p['retentionInterference'] / 2
    channel = n.extrusion(
        'TwoUpFanKeeperServiceChannel',
        n.circle('TwoUpFanKeeperChannelProfile', [(keeper_x, y, keeper_clear)], 'XY', (0, 0, -120)),
        120,
    )
    hanger = n.cut('TwoUpFanKeeperClearance', hanger, channel)
    front_limit = n.box('TwoUpHangerFrontLimitLocal', -outer - 20, outer + 20, inner, inner + 100, bottom - 100, top + 100)
    front_limit = fan_transform(n, 'TwoUpHangerFrontLimit', front_limit, p)
    hanger = n.cut('TwoUpHangerClearOfRetainer', hanger, front_limit)

    joined = n.fuse('TwoUpFanCageLocal', [frame, hanger])
    right_cage = n.move('TwoUpRightFanCage', joined, (p['armOriginX'], 0, 0))
    left_cage = n.mirror('TwoUpLeftFanCage', right_cage)
    register(doc, left_cage, '03_left_fan_cage', '03 / Left open fan cradle', (0.15, 0.52, 0.53))
    register(doc, right_cage, '04_right_fan_cage', '04 / Right open fan cradle', (0.15, 0.52, 0.53))

    # Fan retainer caps (05/06)
    outer_cap = boss_x + 3.7
    cap_profiles = [rectangle(-outer_cap, outer_cap, bottom, top), list(reversed(rectangle(-half + 4, half - 4, bottom + 5, top - 5)))]
    cap_front = inner + gap + p['capThickness']
    cap_frame = n.extrusion('TwoUpFanCapFrame', n.sketch('TwoUpFanCapOutline', cap_profiles, 'XZ', (0, cap_front, 0)), p['capThickness'])
    cap_bores = n.extrusion(
        'TwoUpFanCapPinBores',
        n.circle('TwoUpFanCapPinCircles', [(-boss_x, boss_z, p['capPinDiameter'] / 2 + gap), (boss_x, boss_z, p['capPinDiameter'] / 2 + gap)], 'XZ', (0, cap_front + 1, 0)),
        p['capThickness'] + 2,
    )
    cap_frame = n.cut('TwoUpFanCapBored', cap_frame, cap_bores)
    notch = n.box('TwoUpFanWireNotch', -3, 3, inner, cap_front + 1, bottom - 1, bottom + 5.1)
    cap_frame = n.cut('TwoUpFanCapWithWireExit', cap_frame, notch)
    right_cap = n.move('TwoUpRightFanCap', fan_transform(n, 'TwoUpFanCapAt45', cap_frame, p), (p['armOriginX'], 0, 0))
    left_cap = n.mirror('TwoUpLeftFanCap', right_cap)
    register(doc, left_cap, '05_left_fan_cap', '05 / Left removable fan retainer', (0.20, 0.58, 0.57))
    register(doc, right_cap, '06_right_fan_cap', '06 / Right removable fan retainer', (0.20, 0.58, 0.57))
    finish(doc, n, 'Two-Up fan cradles and retainer caps built.')


def _build_dam_solid(n, p, prefix, start_z, attach_z, end_y, rise, lip_h, add_baffle=False):
    gap, thick = p['fitClearance'], p['damSkin']
    x0 = -p['armOriginX'] + p['centerSeam'] / 2
    x1 = -p['armThickness'] - gap
    inside = x1 - p['carriageThickness']
    y = p['ladderY']
    run = end_y - 2.0
    slope = rise / run
    factor = math.sqrt(1.0 + float(slope) ** 2)
    upper = start_z + rise + lip_h
    profile = [
        (2, start_z),
        (end_y, start_z + rise),
        (end_y, upper),
        (end_y - thick, upper),
        (end_y - thick, start_z + rise + thick * (factor - slope)),
        (2, start_z + thick * factor),
    ]
    blade = n.prism(prefix + 'Blade', profile, 'YZ', (x0, 0, 0), x1 - x0)
    parts_to_fuse = [blade]
    if add_baffle:
        baffle_prof = [
            (2, upper - 12.0),
            (38.0, upper),
            (38.0, upper + thick * factor),
            (2, upper - 12.0 + thick * factor),
        ]
        baffle = n.prism(prefix + 'ReturnBaffle', baffle_prof, 'YZ', (x0, 0, 0), x1 - x0)
        parts_to_fuse.append(baffle)

    carriage = n.box(prefix + 'Carriage', inside, x1, y - 7, y + 7, attach_z - 5, upper)
    half_y, half_z = p['keyWidth'] / 2 + gap, p['keyHeight'] / 2 + gap
    slot_profs = [rectangle(y - half_y, y + half_y, zz - half_z, zz + half_z) for zz in (attach_z, attach_z + p['keySeparation'])]
    slots = n.extrusion(prefix + 'CarriageSlots', n.sketch(prefix + 'SlotProfs', slot_profs, 'YZ', (inside - 1, 0, 0)), p['carriageThickness'] + 2)
    carriage = n.cut(prefix + 'IndexedCarriage', carriage, slots)
    parts_to_fuse.append(carriage)
    return n.fuse(prefix + 'Solid', parts_to_fuse)


def dams_and_cheeks(doc):
    """Build Tier 1 splitter dams (07/08), Tier 2 dams (11/12), and cheek panels (13-16)."""
    if doc.getObject('TwoUpDamsHistory'):
        return
    p = values(doc)
    num = make_params()
    n = family(doc, 'Dams')

    # Tier 1 splitter dam + return baffle
    end_y1 = num['plenumHingeY'] - float(p['outletGap'])
    start1 = float(p['damStartZ'])
    attach1 = float(p['damAttachZ'])
    dam1 = _build_dam_solid(n, p, 'TwoUpTier1Dam', start1, attach1, end_y1, 88.0, 10.0, add_baffle=True)
    right_dam1 = n.move('TwoUpRightTier1Dam', dam1, (p['armOriginX'], 0, 0))
    left_dam1 = n.mirror('TwoUpLeftTier1Dam', right_dam1)
    register(doc, left_dam1, '07_left_tier1_splitter_dam', '07 / Left Tier 1 splitter dam', (0.28, 0.61, 0.55))
    register(doc, right_dam1, '08_right_tier1_splitter_dam', '08 / Right Tier 1 splitter dam', (0.28, 0.61, 0.55))

    # Tier 2 upper dam
    end_y2 = 62.0 - float(p['outletGap'])
    attach2 = float(p['stackPitchZ']) + float(p['damAttachZ']) - 24.0
    start2 = attach2 + float(p['damLift'])
    dam2 = _build_dam_solid(n, p, 'TwoUpTier2Dam', start2, attach2, end_y2, 52.0, 6.0, add_baffle=False)
    right_dam2 = n.move('TwoUpRightTier2Dam', dam2, (p['armOriginX'], 0, 0))
    left_dam2 = n.mirror('TwoUpLeftTier2Dam', right_dam2)
    register(doc, left_dam2, '11_left_tier2_dam', '11 / Left Tier 2 upper dam', (0.28, 0.61, 0.55))
    register(doc, right_dam2, '12_right_tier2_dam', '12 / Right Tier 2 upper dam', (0.28, 0.61, 0.55))

    # Side plenum cheek panels (Tier 1: 13/14, Tier 2: 15/16)
    cheek_h, cheek_t = float(p['cheekHeight']), float(p['cheekThickness'])
    for tier_idx, z_base, nums in [(1, 0.0, (13, 14)), (2, float(p['stackPitchZ']), (15, 16))]:
        cheek_prof = [(0.0, z_base), (36.0, z_base), (84.0, z_base + cheek_h), (0.0, z_base + cheek_h)]
        panel = n.prism(f'TwoUpTier{tier_idx}CheekSkin', cheek_prof, 'YZ', (0, 0, 0), cheek_t)
        tabs = [
            n.box(f'TwoUpTier{tier_idx}CheekTab{i}', -4.0, 0.0, 14.0, 17.0, z_base + 25.0 + i * 45.0, z_base + 49.0 + i * 45.0)
            for i in range(4)
        ]
        panel_full = n.fuse(f'TwoUpTier{tier_idx}CheekFull', [panel] + tabs)
        r_panel = n.move(f'TwoUpRightTier{tier_idx}Cheek', panel_full, (p['armOriginX'], 0, 0))
        l_panel = n.mirror(f'TwoUpLeftTier{tier_idx}Cheek', r_panel)
        register(doc, l_panel, f'{nums[0]:02}_left_tier{tier_idx}_cheek_panel', f'{nums[0]:02} / Left Tier {tier_idx} cheek panel', (0.35, 0.45, 0.48))
        register(doc, r_panel, f'{nums[1]:02}_right_tier{tier_idx}_cheek_panel', f'{nums[1]:02} / Right Tier {tier_idx} cheek panel', (0.35, 0.45, 0.48))

    finish(doc, n, 'Two-Up Tier 1/2 dams and side cheek panels built.')


def make_pin(n, name, p, diameter, shaft_length, head_radius):
    head, radius, gap = p['keeperHead'], diameter / 2, p['fitClearance']
    crown_radius = radius + gap + p['retentionInterference'] / 2
    base = n.extrusion(name + 'Button', n.circle(name + 'ButtonProfile', [(0, 0, head_radius)]), head)
    if 'Keeper' in name:
        flat = n.box(name + 'ButtonFlatTool', radius, head_radius + 1, -head_radius - 1, head_radius + 1, -1, head + 1)
        base = n.cut(name + 'FlatGripButton', base, flat)
    shaft = n.extrusion(name + 'Shaft', n.circle(name + 'ShaftProfile', [(0, 0, radius)], 'XY', (0, 0, head)), shaft_length)
    sections = [
        n.circle(name + 'CrownRoot', [(0, 0, radius)], 'XY', (0, 0, head + shaft_length)),
        n.circle(name + 'CrownMax', [(0, 0, crown_radius)], 'XY', (0, 0, head + shaft_length + 0.8)),
        n.circle(name + 'CrownTip', [(0, 0, radius - 0.3)], 'XY', (0, 0, head + shaft_length + 2.0)),
    ]
    crown = n.obj('Part::Loft', name + 'RetentionCrown', name + 'RetentionCrown')
    crown.Sections, crown.Solid, crown.Ruled = sections, True, True
    for section in sections:
        section.Visibility = False
    body = n.fuse(name + 'BeforeSplit', [base, shaft, crown])
    slot = n.box(name + 'FlexureSlot', -0.4, 0.4, -crown_radius - 1, crown_radius + 1, head + 5, head + shaft_length + 3)
    return n.cut(name + 'Finished', body, slot)


def hardware(doc):
    """Build four-rung splice keys (17/18) and all two-rung keys, keepers, and cap pins (19-38)."""
    if doc.getObject('TwoUpHardwareHistory'):
        return
    p = values(doc)
    n = family(doc, 'Hardware')
    gap, height, width = p['fitClearance'], p['keyHeight'], p['keyWidth']
    separation = p['keySeparation']
    w_splice = p['spliceKeyWidth']
    span_z = p['spliceSpanZ']
    carriage_inner = -p['armThickness'] - gap - p['carriageThickness']
    keeper_x = carriage_inner - gap - p['keeperDiameter'] / 2
    keeper_hole = p['keeperDiameter'] / 2 + gap
    tip = keeper_x - keeper_hole - 2
    color = (0.83, 0.65, 0.30)

    # 1. Four-rung structural splice keys (17/18)
    s_plate = n.box(
        'TwoUpSpliceBackplate',
        gap, gap + p['spliceKeyPlate'],
        -w_splice / 2 - 2, w_splice / 2 + 2,
        -height / 2 - 2, span_z + height / 2 + 2,
    )
    s_tongues = [
        n.box(f'TwoUpSpliceTongue{i}', tip, gap, -w_splice / 2, w_splice / 2, z - height / 2, z + height / 2)
        for i, z in enumerate((0, 24, 36, 60))
    ]
    s_key_raw = n.fuse('TwoUpSpliceKeyBeforeBore', [s_plate] + s_tongues)
    s_bore = n.extrusion(
        'TwoUpSpliceKeeperBore',
        n.circle('TwoUpSpliceKeeperBoreProf', [(keeper_x, 0, keeper_hole)], 'XY', (0, 0, -height / 2 - 1)),
        span_z + height + 2,
    )
    splice_key = n.cut('TwoUpSpliceKeySolid', s_key_raw, s_bore)
    r_splice = n.move('TwoUpRightSpliceKey', splice_key, (p['armOriginX'], p['ladderY'], 130))
    l_splice = n.mirror('TwoUpLeftSpliceKey', r_splice)
    register(doc, l_splice, '17_left_arm_splice_key', '17 / Left four-rung arm splice key', color)
    register(doc, r_splice, '18_right_arm_splice_key', '18 / Right four-rung arm splice key', color)

    # 2. Standard M1.1 two-rung keys (19-24) and keeper pins (25-34)
    plate = n.box('TwoUpKeyBackplate', gap, gap + p['keyPlate'], -width / 2 - 2, width / 2 + 2, -height / 2 - 1.5, separation + height / 2 + 1.5)
    tongues = [n.box('TwoUpKeyTongue' + str(i), tip, gap, -width / 2, width / 2, z - height / 2, z + height / 2) for i, z in enumerate((0, separation))]
    key_raw = n.fuse('TwoUpTwoRungKeyBeforeBore', [plate] + tongues)
    bore = n.extrusion('TwoUpKeyKeeperBore', n.circle('TwoUpKeyKeeperBoreProf', [(keeper_x, 0, keeper_hole)], 'XY', (0, 0, -height / 2 - 1)), separation + height + 2)
    key = n.cut('TwoUpTwoRungKey', key_raw, bore)

    keeper = make_pin(n, 'TwoUpKeeperPin', p, p['keeperDiameter'], separation + height, 3.5)
    cap_pin = make_pin(n, 'TwoUpCapPin', p, p['capPinDiameter'], p['capThickness'] + gap + 8 - 0.3, 4.0)

    key_stations = [
        ('fan', -54, (19, 20), (25, 26)),
        ('tier1_dam', p['damAttachZ'], (21, 22), (27, 28)),
        ('tier2_dam', p['stackPitchZ'] + p['damAttachZ'] - 24, (23, 24), (29, 30)),
    ]
    for kind, at_z, k_nums, p_nums in key_stations:
        rk = n.move(f'TwoUpRight_{kind}_Key', key, (p['armOriginX'], p['ladderY'], at_z))
        lk = n.mirror(f'TwoUpLeft_{kind}_Key', rk)
        register(doc, lk, f'{k_nums[0]:02}_left_{kind}_key', f'{k_nums[0]:02} / Left {kind} two-rung key', color)
        register(doc, rk, f'{k_nums[1]:02}_right_{kind}_key', f'{k_nums[1]:02} / Right {kind} two-rung key', color)

        top_z = at_z + separation + height / 2 + gap + p['keeperHead']
        rp = n.move(f'TwoUpRight_{kind}_Keeper', keeper, (p['armOriginX'] + keeper_x, p['ladderY'], top_z), App.Rotation(App.Vector(1, 0, 0), 180))
        lp = n.mirror(f'TwoUpLeft_{kind}_Keeper', rp)
        register(doc, lp, f'{p_nums[0]:02}_left_{kind}_keeper', f'{p_nums[0]:02} / Left {kind} keeper pin', color)
        register(doc, rp, f'{p_nums[1]:02}_right_{kind}_keeper', f'{p_nums[1]:02} / Right {kind} keeper pin', color)

    # Splice keeper pins (31-34)
    for tag, at_z, p_nums in [('splice_keeper_low', 158, (31, 32)), ('splice_keeper_high', 194, (33, 34))]:
        rp = n.move(f'TwoUpRight_{tag}', keeper, (p['armOriginX'] + keeper_x, p['ladderY'], at_z), App.Rotation(App.Vector(1, 0, 0), 180))
        lp = n.mirror(f'TwoUpLeft_{tag}', rp)
        register(doc, lp, f'{p_nums[0]:02}_left_{tag}', f'{p_nums[0]:02} / Left {tag}', color)
        register(doc, rp, f'{p_nums[1]:02}_right_{tag}', f'{p_nums[1]:02} / Right {tag}', color)

    # Fan retainer cap pins (35-38)
    inner = p['fanWidth'] / 2 + gap
    boss_x = inner + 3.7
    boss_z = -p['fanThickness'] - p['fanFrameWall'] + 16
    front = inner + gap + p['capThickness'] + p['keeperHead']
    for i, x in enumerate((-boss_x, boss_x)):
        local = n.move(f'TwoUpCapPinLocal{i}', cap_pin, (x, front, boss_z), App.Rotation(App.Vector(1, 0, 0), 90))
        right_p = n.move(f'TwoUpRightCapPin{i}', fan_transform(n, f'TwoUpCapPinTilt{i}', local, p), (p['armOriginX'], 0, 0))
        left_p = n.mirror(f'TwoUpLeftCapPin{i}', right_p)
        for side, obj, number in [('left', left_p, 35 + i * 2), ('right', right_p, 36 + i * 2)]:
            register(doc, obj, f'{number:02}_{side}_cap_pin_{i+1}', f'{number:02} / {side.title()} retainer pin {i+1}', color)

    finish(doc, n, 'Two-Up splice keys and all 22 hardware parts built.')


def orient_for_print(key: str, shape):
    """Orient a part into its declared Bambu P1S build orientation on the XY bed."""
    result = shape.copy()
    if key == '00_fit_coupon' or key.endswith('_arm') or key.endswith('_key') or key.endswith('_cheek_panel'):
        result.rotate(App.Vector(), App.Vector(0, 1, 0), -90 if 'left' in key else 90)
        pose = 'outer flat side down'
    elif 'fan_cage' in key:
        result.rotate(App.Vector(), App.Vector(1, 0, 0), -45)
        pose = 'grille down'
    elif 'fan_cap' in key or 'cap_pin' in key:
        result.rotate(App.Vector(), App.Vector(1, 0, 0), -135)
        pose = 'front face down' if 'fan_cap' in key else 'button down; split tip up'
    elif key.endswith('_dam'):
        result.rotate(App.Vector(), App.Vector(1, 0, 0), 180)
        pose = 'lip down'
    else:
        result.rotate(App.Vector(), App.Vector(1, 0, 0), 180)
        pose = 'button down; split tip up'

    b = result.BoundBox
    result.translate(App.Vector(128.0 - (b.XMin + b.XMax) / 2.0, 128.0 - (b.YMin + b.YMax) / 2.0, -b.ZMin))
    return result, pose


def export_all(doc, export_dir: Path = EXPORT_DIR, measured_path: Path = MEASURED_JSON):
    """Export STEP and STL for every registered part and write measured B-rep JSON."""
    require_freecad()
    export_dir.mkdir(parents=True, exist_ok=True)
    assembly = doc.getObject('TwoUpAssembly')
    links = sorted(
        [o for o in assembly.Group if o.TypeId == 'App::Link'],
        key=lambda o: o.InstanceKey,
    )
    measured = {
        'revision': 'Two-Up M1.1 Stacked Variant',
        'units': 'mm',
        'density_g_per_cm3': 1.05,
        'part_count': len(links),
        'parts': {},
    }
    total_vol_mm3 = 0.0
    coupon_vol_mm3 = 0.0

    for link in links:
        key = link.InstanceKey
        raw_shape = link.Shape
        assert raw_shape.isValid() and len(raw_shape.Solids) == 1, f'{key}: invalid solid ({len(raw_shape.Solids)} solids)'
        placed, pose = orient_for_print(key, raw_shape)
        b = placed.BoundBox

        step_file = export_dir / f'{key}.step'
        stl_file = export_dir / f'{key}.stl'
        placed.exportStep(str(step_file))
        mesh = MeshPart.meshFromShape(Shape=placed, LinearDeflection=0.05, AngularDeflection=0.15, Relative=False)
        mesh.write(str(stl_file))

        vol_mm3 = float(placed.Volume)
        vol_cm3 = vol_mm3 / 1000.0
        mass_g = vol_cm3 * 1.05
        dx, dy, dz = float(b.XLength), float(b.YLength), float(b.ZLength)
        bx, by = dx + 16.0, dy + 16.0
        fits_bed = ((bx <= 256.001 and by <= 256.001) or (by <= 256.001 and bx <= 256.001)) and dz <= 256.001

        measured['parts'][key] = {
            'orientation': pose,
            'footprint_x_mm': round(dx, 3),
            'footprint_y_mm': round(dy, 3),
            'with_8mm_brim_x_mm': round(bx, 3),
            'with_8mm_brim_y_mm': round(by, 3),
            'height_z_mm': round(dz, 3),
            'fits_256_bed_with_brim': bool(fits_bed),
            'volume_mm3': round(vol_mm3, 3),
            'volume_cm3': round(vol_cm3, 3),
            'mass_g': round(mass_g, 3),
            'solids': len(placed.Solids),
            'step_path': str(step_file),
            'stl_path': str(stl_file),
        }
        if key == '00_fit_coupon':
            coupon_vol_mm3 += vol_mm3
        else:
            total_vol_mm3 += vol_mm3

    measured['assembly_01_to_38_volume_cm3'] = round(total_vol_mm3 / 1000.0, 3)
    measured['assembly_01_to_38_mass_g'] = round((total_vol_mm3 / 1000.0) * 1.05, 3)
    measured['coupon_00_volume_cm3'] = round(coupon_vol_mm3 / 1000.0, 3)
    measured['coupon_00_mass_g'] = round((coupon_vol_mm3 / 1000.0) * 1.05, 3)

    measured_path.write_text(json.dumps(measured, indent=2) + '\n', encoding='utf-8')
    print(
        f'EXPORT COMPLETE: {len(links)} parts exported to {export_dir}, '
        f'assembly mass = {measured["assembly_01_to_38_mass_g"]:.2f} g, '
        f'coupon mass = {measured["coupon_00_mass_g"]:.2f} g',
        flush=True,
    )
    return measured


def run(stage='all'):
    require_freecad()
    doc = open_document(fresh=(stage == 'all'))
    setup(doc)
    doc.recompute()
    if stage in ('arms', 'all'):
        arms(doc)
    if stage in ('fans', 'all'):
        fans(doc)
    if stage in ('dams', 'all'):
        dams_and_cheeks(doc)
    if stage in ('hardware', 'all'):
        hardware(doc)
    doc.save()
    if stage == 'all':
        export_all(doc)
    return doc


def main():
    parser = argparse.ArgumentParser(description='Build Two-Up Dell 5560 Wall Mount in FreeCAD.')
    parser.add_argument(
        '--stage',
        default='all',
        choices=('arms', 'fans', 'dams', 'hardware', 'all'),
        help='Build stage to execute',
    )
    parser.add_argument('--target', type=Path, help='Custom output FCStd path')
    args, _ = parser.parse_known_args()
    global TARGET
    if args.target:
        TARGET = args.target.resolve()
    run(args.stage)


if HAS_FREECAD:
    main()


