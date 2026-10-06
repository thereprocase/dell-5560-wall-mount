"""Build M1 with native constrained sketches and stock FreeCAD features.

Run stages in the GUI with the existing project queue, or run all stages with
FreeCAD's Python against an isolated FCStd target. No custom feature proxies
are stored in the completed model.
"""
from pathlib import Path
import hashlib
import json
import math
import shutil
import sys
import time

import FreeCAD as App
import Part

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from native import Native, E, rectangle, bind, ex

TARGET = ROOT / 'Laptop_Wall_Mount_Minimalist.FCStd'
BASELINE = ROOT.parent / 'freecad/Precision_5560_Native.FCStd'
PARAMETERS = [
    ('CASE / MEASURE THE CLOSED LAPTOP', None),
    ('laptopWidth', 344.4, 'mm', 'Actual case width, not screen diagonal'),
    ('laptopDepth', 230.3, 'mm', 'Base-to-hinge dimension when installed upright'),
    ('laptopThickness', 20.0, 'mm', 'Maximum closed case thickness'),
    ('wallGap', 40.0, 'mm', 'Wall to laptop underside'),
    ('padThickness', 2.0, 'mm', 'Separate compliant contact pads; not printed'),
    ('caseSideGap', 1.0, 'mm', 'Clearance at each laptop side stop'),
    ('STRUCTURE / PRINTED ARMS', None),
    ('armThickness', 12.0, 'mm', 'Main arm section, inboard of the flat print face'),
    ('sideLip', 3.0, 'mm', 'Thickness of low lateral retention cheek'),
    ('frontLip', 6.0, 'mm', 'Front retaining tine thickness'),
    ('tineHeight', 40.0, 'mm', 'Laptop lift required before forward removal'),
    ('wallBoltDiameter', 7.2, 'mm', 'Clearance for the existing wall-anchor class'),
    ('wallPadDepth', 8.0, 'mm', 'Wall fastener pad thickness'),
    ('wallPadHeight', 32.0, 'mm', 'Wall pad height; bolt centers stay unchanged'),
    ('wallGussetWeb', 6.0, 'mm', 'Paired webs beside each bolt opening'),
    ('wallGussetRise', 16.0, 'mm', 'Tapered web reach beyond the wall pad face'),
    ('FIT / REMOVABLE HARDWARE', None),
    ('fitClearance', 0.3, 'mm', 'Nominal clearance at new mating surfaces'),
    ('carriageThickness', 4.0, 'mm', 'Fan and dam attachment cheek thickness'),
    ('keyWidth', 8.0, 'mm', 'Two-rung key width, along Y'),
    ('keyHeight', 5.0, 'mm', 'Two-rung key tongue height'),
    ('keyPlate', 3.0, 'mm', 'Key connecting plate thickness'),
    ('keeperDiameter', 3.0, 'mm', 'Non-load-bearing withdrawal keeper shaft'),
    ('keeperHead', 2.4, 'mm', 'Pin button thickness'),
    ('retentionInterference', 0.2, 'mm', 'Intentional diametral crown interference'),
    ('FANS / TWO OPEN CRADLES', None),
    ('fanWidth', 120.0, 'mm', 'Square fan envelope width'),
    ('fanThickness', 27.0, 'mm', 'Measured fan envelope; default accepts 25-27 mm'),
    ('fanFrameWall', 3.0, 'mm', 'Open cradle rails and grille base thickness'),
    ('grilleBar', 2.4, 'mm', 'Two diagonal intake-guard bars'),
    ('fanCenterY', 65.0, 'mm', 'Fan outlet-plane center from wall'),
    ('fanCenterZ', -60.0, 'mm', 'Fan outlet-plane center below the laptop'),
    ('capThickness', 3.0, 'mm', 'Removable front retainer thickness'),
    ('capPinDiameter', 4.0, 'mm', 'Front retainer pin shaft'),
    ('LADDER / OPTIONAL AIRFLOW DAM', None),
    ('rungPitch', 12.0, 'mm', 'Positive vertical adjustment step'),
    ('ladderStart', 50.0, 'mm', 'Lowest rung center above the shelf'),
    ('damIndex', 8, '', 'Lower engaged rung: integer 0-8; match both sides'),
    ('damSkin', 1.6, 'mm', 'Open airflow deflector skin'),
    ('outletGap', 12.0, 'mm', 'Nominal top opening behind the case'),
    ('centerSeam', 0.6, 'mm', 'Clear gap between left and right dam halves'),
    ('DERIVED / FOLLOW THE INPUTS', None),
    ('armHeight', '=min(max(laptopDepth - 22 mm + padThickness;186 mm);220 mm)', 'mm', 'Capped to retain one-piece P1S arm printing'),
    ('armOriginX', '=laptopWidth / 2 + caseSideGap + sideLip', 'mm', 'Right outboard print face; mirrored for left'),
    ('rearFace', '=wallGap - padThickness', 'mm', 'Rear pad seat'),
    ('frontFace', '=wallGap + laptopThickness + padThickness', 'mm', 'Front pad seat'),
    ('ladderY', '=rearFace - 7 mm', 'mm', 'Rung/key center line'),
    ('keySeparation', '=2 * rungPitch', 'mm', 'Two engaged rungs separated by one free rung'),
    ('damAttachZ', '=ladderStart + damIndex * rungPitch', 'mm', 'Lower engaged rung center'),
    ('damLift', '=laptopDepth - 178 mm', 'mm', 'Preset-dependent rise above the ladder'),
    ('damStartZ', '=damAttachZ + damLift', 'mm', 'Start of the 45-degree-or-steeper deflector'),
    ('fanOffsetX', '=fanWidth / 2 + armThickness + carriageThickness + 2 * fitClearance', 'mm', 'Fan center inboard of each arm'),
]


def view(doc, message, objects=None):
    App.Console.PrintMessage(message + '\n')
    if not App.GuiUp:
        print(message, flush=True)
        return
    import FreeCADGui as Gui
    App.setActiveDocument(doc.Name)
    Gui.activeDocument().activeView().viewAxonometric()
    Gui.activeDocument().activeView().fitAll()
    Gui.updateGui()


def open_document():
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    if TARGET.exists():
        for d in App.listDocuments().values():
            if d.FileName and Path(d.FileName).resolve() == TARGET.resolve(): return d
        return App.openDocument(str(TARGET))
    source_hash = hashlib.sha256(BASELINE.read_bytes()).hexdigest()
    manifest = json.loads((ROOT.parent / 'print_release/manifest.json').read_text())
    assert source_hash == manifest['native_sha256'], 'Baseline is not the preserved Rev H release'
    sys.path.insert(0, App.getResourceDir() + 'Mod/Assembly')
    doc = App.openDocument(str(BASELINE))
    doc.saveAs(str(TARGET))
    doc.Label = 'Laptop wall mount / Minimalist M1'
    roots = list(doc.RootObjects)
    old = doc.addObject('App::DocumentObjectGroup', 'DuctedPrototypeReference')
    old.Label = 'REFERENCE / Ducted Rev H prototype (hidden)'
    old.addProperty('App::PropertyString', 'NativeSHA256', 'Provenance')
    old.NativeSHA256 = source_hash
    old.addProperty('App::PropertyString', 'Purpose', 'Provenance')
    old.Purpose = 'Save As lineage; this prototype is preserved independently. M1 has no frozen parts.'
    for obj in roots: old.addObject(obj)
    for obj in doc.Objects:
        if hasattr(obj, 'Visibility'): obj.Visibility = False
    old.Visibility = False
    return doc


def setup(doc):
    if doc.getObject('M1Parameters'):
        sheet = doc.getObject('M1Parameters')
        present, missing = {}, []
        for entry in PARAMETERS:
            if entry[1] is None: continue
            cell = sheet.getCellFromAlias(entry[0])
            if cell: present[entry[0]] = cell
            else: missing.append(entry)
        if missing:
            row = max(int(cell[1:]) for cell in present.values()) + 2
            sheet.mergeCells(f'A{row}:D{row}')
            sheet.set(f'A{row}', 'WALL TRANSITIONS / M1.1 REINFORCEMENT')
            sheet.setBackground(f'A{row}:D{row}', (0.81, 0.88, 0.86))
            sheet.setStyle(f'A{row}:D{row}', 'bold', 'add')
            for name, value, unit, description in missing:
                row += 1
                assert not isinstance(value, str), 'Migration requires a numeric default'
                sheet.set(f'A{row}', name)
                sheet.set(f'B{row}', str(value) + ' ' + unit)
                sheet.set(f'C{row}', unit)
                sheet.set(f'D{row}', description)
                sheet.setAlias(f'B{row}', name)
                sheet.setBackground(f'B{row}', (0.83, 0.92, 1.0))
                present[name] = f'B{row}'
            doc.recompute()
            (Path(doc.FileName).parent / 'parameter_cells.json').write_text(json.dumps(present, indent=2))
        return
    sources = doc.addObject('App::DocumentObjectGroup', 'M1Sources')
    sources.Label = 'M1 / Native construction history'
    assembly = doc.addObject('App::Part', 'M1Assembly')
    assembly.Label = 'M1 / Installed minimalist assembly'
    assembly.addProperty('App::PropertyString', 'Revision', 'Design')
    assembly.Revision = 'M1 development'
    sheet = doc.addObject('Spreadsheet::Sheet', 'M1Parameters')
    sheet.Label = 'M1 / Design parameters (measure your laptop)'
    sheet.setColumnWidth('A', 210)
    sheet.setColumnWidth('B', 115)
    sheet.setColumnWidth('C', 55)
    sheet.setColumnWidth('D', 485)
    sheet.mergeCells('A1:D1')
    sheet.set('A1', 'MINIMALIST M1 / DIMENSIONS IN MILLIMETERS')
    sheet.setBackground('A1:D1', (0.10, 0.24, 0.27))
    sheet.setForeground('A1:D1', (1.0, 1.0, 1.0))
    sheet.setStyle('A1:D1', 'bold', 'add')
    sheet.mergeCells('A2:D2')
    sheet.set('A2', 'Blue: measured inputs. Gray: derived. Dam index 0-8. Check fit and printing after edits.')
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
    for cell, formula in derived: sheet.set(cell, formula)
    doc.recompute()
    assert not any(s in ('Invalid', 'Error') for s in sheet.State), sheet.State
    (Path(doc.FileName).parent / 'parameter_cells.json').write_text(json.dumps(cells, indent=2), encoding='utf-8')
    doc.save()
    view(doc, 'M1 Save As complete. The prototype is hidden; the new parameter sheet is ready.')


def values(doc):
    sheet = doc.getObject('M1Parameters')
    result = {}
    for entry in PARAMETERS:
        if entry[1] is None: continue
        name, _, unit, _ = entry
        raw = getattr(sheet, name)
        number = raw.Value if hasattr(raw, 'Value') else App.Units.Quantity(str(raw)).Value
        result[name] = E(number, '(M1Parameters.' + name + (' / (1 mm)' if unit == 'mm' else '') + ')')
    return result


def family(doc, name):
    group = doc.addObject('App::DocumentObjectGroup', 'M1' + name + 'History')
    group.Label = name + ' / native sketches and features'
    doc.getObject('M1Sources').addObject(group)
    return Native(doc, group)


def register(doc, source, key, label, color):
    source.addProperty('App::PropertyString', 'PartKey', 'Identity')
    source.PartKey = key
    source.Label = label + ' / source'
    link = doc.addObject('App::Link', 'M1Installed' + key.replace('_', ''))
    link.setLink(source)
    link.LinkTransform = True
    link.LinkPlacement = App.Placement()
    link.addProperty('App::PropertyString', 'InstanceKey', 'Identity')
    link.InstanceKey = key
    link.Label = label
    doc.getObject('M1Assembly').addObject(link)
    if App.GuiUp:
        source.ViewObject.ShapeColor = color
        source.ViewObject.LineColor = (0.11, 0.16, 0.18)
        source.ViewObject.DisplayMode = 'Flat Lines'
        source.ViewObject.LineWidth = 1.1
    source.Visibility = False
    link.Visibility = True
    return link


def finish(doc, native, message):
    doc.recompute()
    errors = []
    for obj in native.group.Group:
        if obj.TypeId == 'Sketcher::SketchObject' and not obj.FullyConstrained:
            errors.append(obj.Name + ': unconstrained')
        if 'Invalid' in obj.State or 'Error' in obj.State: errors.append(obj.Name + ': ' + str(obj.State))
        if hasattr(obj, 'Shape') and obj.TypeId != 'Sketcher::SketchObject':
            if obj.Shape.isNull() or not obj.Shape.isValid(): errors.append(obj.Name + ': invalid shape')
            if hasattr(obj, 'PartKey') and len(obj.Shape.Solids) != 1:
                errors.append(obj.Name + ': final part has ' + str(len(obj.Shape.Solids)) + ' solids')
    assert not errors, errors
    for obj in native.group.Group: obj.Visibility = False
    doc.getObject('M1Assembly').Visibility = True
    doc.save()
    view(doc, message)
    if App.GuiUp:
        import FreeCADGui as Gui
        Gui.activeDocument().activeView().saveImage(str(ROOT / (native.group.Name + '.png')), 1600, 1100, 'Current')


def fan_transform(n, name, shape, p):
    return n.move(name, shape, (-p['fanOffsetX'], p['fanCenterY'], p['fanCenterZ']),
                  App.Rotation(App.Vector(1, 0, 0), 45))


def fan_cages(doc):
    if doc.getObject('M1FanCagesHistory'): return
    p = values(doc)
    n = family(doc, 'FanCages')
    half, gap, wall = p['fanWidth'] / 2, p['fitClearance'], p['fanFrameWall']
    inner, outer = half + gap, half + gap + wall
    bottom, top = -p['fanThickness'] - wall, gap + 4.8
    opening = half - 4
    rings = [rectangle(-outer, outer, -outer, inner), list(reversed(rectangle(-opening, opening, -opening, opening)))]
    ring = n.extrusion('M1GrilleRim', n.sketch('M1GrilleRimProfile', rings, 'XY', (0, 0, bottom)), wall)
    d = p['grilleBar'] / math.sqrt(2)
    a = opening + 1
    bars = [n.prism('M1GrilleDiagonalA', [(-a, -a + d), (-a + d, -a), (a, a - d), (a - d, a)], 'XY', (0, 0, bottom), wall),
            n.prism('M1GrilleDiagonalB', [(-a, a - d), (-a + d, a), (a, -a + d), (a - d, -a)], 'XY', (0, 0, bottom), wall)]
    right_profile = [(inner, bottom), (outer, bottom), (outer, top),
                     (inner - 4, top), (inner - 4, gap + 4), (inner, gap)]
    right_rail = n.prism('M1FanRightGuide', right_profile, 'XZ', (0, inner, 0), 2 * inner)
    left_rail = n.prism('M1FanLeftGuide', [(-x, z) for x, z in reversed(right_profile)], 'XZ', (0, inner, 0), 2 * inner)
    back = n.box('M1FanBackStop', -outer, outer, -outer, -inner, bottom, gap + 2.4)
    solid = n.fuse('M1OpenFanFrame', [ring, right_rail, left_rail, back] + bars)
    # Apex-up windows retain self-supporting upper edges in grille-down printing.
    windows = []
    for factor in (-.7, -.233333333333, .233333333333, .7):
        center = half * factor
        windows.append([(center - 10, bottom + 6), (center + 10, bottom + 6), (center, bottom + 22)])
    side_tools = n.extrusion('M1FanSideWindows', n.sketch('M1FanSideWindowProfiles', windows, 'YZ', (-outer - 1, 0, 0)), 2 * outer + 2)
    solid = n.cut('M1PerforatedFanGuides', solid, side_tools)
    back_windows = []
    for factor in (-.65, 0, .65):
        x = half * factor
        back_windows.append([(x - 12, bottom + 6), (x + 12, bottom + 6), (x, bottom + 24)])
    back_tools = n.extrusion('M1FanBackWindows', n.sketch('M1FanBackWindowProfiles', back_windows, 'XZ', (0, -inner + 1, 0)), wall + 2)
    solid = n.cut('M1OpenBackStop', solid, back_tools)
    # Two pin sockets sit outside the measured fan envelope.
    boss_x = inner + 3.7
    boss_z = bottom + 16
    bosses = []
    for side, x in [('L', -boss_x), ('R', boss_x)]:
        bosses.append(n.extrusion('M1CapSocketBoss' + side,
                                 n.circle('M1CapSocketBoss' + side + 'Profile', [(x, boss_z, 3.7)], 'XZ', (0, inner, 0)), 8))
    solid = n.fuse('M1FanFrameWithSockets', [solid] + bosses)
    bores = n.extrusion('M1CapSocketBores', n.circle('M1CapSocketBoreProfiles',
                       [(-boss_x, boss_z, p['capPinDiameter'] / 2 + gap),
                        (boss_x, boss_z, p['capPinDiameter'] / 2 + gap)], 'XZ', (0, inner + 1, 0)), 10)
    solid = n.cut('M1FanFrameFinishedLocal', solid, bores)
    relief_radius = p['capPinDiameter'] / 2 + gap + p['retentionInterference'] / 2 + gap
    relief = n.extrusion('M1CapCrownReleaseSpace', n.circle('M1CapCrownReleaseProfiles',
                         [(-boss_x, boss_z, relief_radius), (boss_x, boss_z, relief_radius)],
                         'XZ', (0, inner - 8, 0)), 6)
    solid = n.cut('M1FanFrameCrownClearance', solid, relief)
    frame = fan_transform(n, 'M1FanFrameAt45Degrees', solid, p)
    # Inboard hanger lies beside the arm. Its open triangle reaches the cage's
    # outside rail, so the fan can slide out without passing a screw or brace.
    inside = -p['armThickness'] - gap - p['carriageThickness']
    y = p['ladderY']
    hanger_outline = [(y - 7, -63), (y - 10, -108), (110, -16),
                      (y + 7, -18), (y - 7, -18)]
    hanger = n.prism('M1FanHanger', hanger_outline, 'YZ', (inside, 0, 0), p['carriageThickness'])
    cutouts = [[(y + 11, -57), (y + 11, -28), (94, -24)],
               [(y - 5, -87), (y - 3, -68), (y + 14, -66)]]
    hollow = n.extrusion('M1FanHangerWindows', n.sketch('M1FanHangerWindowProfiles', cutouts, 'YZ', (inside - 1, 0, 0)), p['carriageThickness'] + 2)
    hanger = n.cut('M1OpenFanHanger', hanger, hollow)
    half_y = p['keyWidth'] / 2 + gap
    half_z = p['keyHeight'] / 2 + gap
    holes = [rectangle(y - half_y, y + half_y, z - half_z, z + half_z) for z in (-54, -30)]
    sockets = n.extrusion('M1FanHangerSlots', n.sketch('M1FanHangerSlotProfiles', holes, 'YZ', (inside - 1, 0, 0)), p['carriageThickness'] + 2)
    hanger = n.cut('M1FanHangerFinished', hanger, sockets)
    keeper_x = inside - gap - p['keeperDiameter'] / 2
    keeper_clear = p['keeperDiameter'] / 2 + 2 * gap + p['retentionInterference'] / 2
    channel = n.extrusion('M1FanKeeperServiceChannel', n.circle('M1FanKeeperChannelProfile', [(keeper_x, y, keeper_clear)],
                          'XY', (0, 0, -120)), 120)
    hanger = n.cut('M1FanKeeperClearance', hanger, channel)
    front_limit = n.box('M1HangerFrontLimitLocal', -outer - 20, outer + 20, inner, inner + 100, bottom - 100, top + 100)
    front_limit = fan_transform(n, 'M1HangerFrontLimit', front_limit, p)
    hanger = n.cut('M1HangerClearOfRetainer', hanger, front_limit)
    joined = n.fuse('M1FanCageLocal', [frame, hanger])
    right = n.move('M1RightFanCage', joined, (p['armOriginX'], 0, 0))
    left = n.mirror('M1LeftFanCage', right)
    register(doc, left, '03_left_fan_cage', '03 / Left open fan cradle', (0.15, 0.52, 0.53))
    register(doc, right, '04_right_fan_cage', '04 / Right open fan cradle', (0.15, 0.52, 0.53))
    finish(doc, n, 'M1 fan cradles built: 45-degree outlet axes, open sides, guard bars and removable keyed hangers.')


def caps(doc):
    if doc.getObject('M1FanCapsHistory'): return
    p = values(doc)
    n = family(doc, 'FanCaps')
    half, gap, wall = p['fanWidth'] / 2, p['fitClearance'], p['fanFrameWall']
    inner = half + gap
    bottom, top = -p['fanThickness'] - wall, gap + 4.8
    boss_x, boss_z = inner + 3.7, bottom + 16
    outer = boss_x + 3.7
    profiles = [rectangle(-outer, outer, bottom, top),
                list(reversed(rectangle(-half + 4, half - 4, bottom + 5, top - 5)))]
    cap_front = inner + gap + p['capThickness']
    frame = n.extrusion('M1FanCapFrame', n.sketch('M1FanCapOutline', profiles, 'XZ', (0, cap_front, 0)), p['capThickness'])
    bores = n.extrusion('M1FanCapPinBores', n.circle('M1FanCapPinCircles',
                        [(-boss_x, boss_z, p['capPinDiameter'] / 2 + gap),
                         (boss_x, boss_z, p['capPinDiameter'] / 2 + gap)],
                         'XZ', (0, cap_front + 1, 0)), p['capThickness'] + 2)
    frame = n.cut('M1FanCapFinishedLocal', frame, bores)
    # An open wire notch exits through the bottom edge, so the cable is not
    # threaded through a trapped hole during fan removal.
    notch = n.box('M1FanWireNotch', -3, 3, inner, cap_front + 1, bottom - 1, bottom + 5.1)
    frame = n.cut('M1FanCapWithWireExit', frame, notch)
    right = n.move('M1RightFanCap', fan_transform(n, 'M1FanCapAt45Degrees', frame, p), (p['armOriginX'], 0, 0))
    left = n.mirror('M1LeftFanCap', right)
    register(doc, left, '05_left_fan_cap', '05 / Left removable fan retainer', (0.20, 0.58, 0.57))
    register(doc, right, '06_right_fan_cap', '06 / Right removable fan retainer', (0.20, 0.58, 0.57))
    finish(doc, n, 'M1 fan retainers built with a cable exit and two accessible printed pin sockets.')


def dams(doc):
    if doc.getObject('M1DamsHistory'): return
    p = values(doc)
    n = family(doc, 'Dams')
    gap, thick = p['fitClearance'], p['damSkin']
    start, end_y = p['damStartZ'], p['wallGap'] - p['outletGap']
    run, rise = end_y - 2, end_y + 2
    slope = rise / run
    factor = E(math.sqrt(1 + float(slope) ** 2), 'sqrt(1 + (' + ex(slope) + ') * (' + ex(slope) + '))')
    upper = start + rise + 6
    profile = [(2, start), (end_y, start + rise), (end_y, upper),
               (end_y - thick, upper), (end_y - thick, start + rise + thick * (factor - slope)),
               (2, start + thick * factor)]
    x0 = -p['armOriginX'] + p['centerSeam'] / 2
    x1 = -p['armThickness'] - gap
    blade = n.prism('M1OpenDamSkin', profile, 'YZ', (x0, 0, 0), x1 - x0)
    inside = x1 - p['carriageThickness']
    y, z = p['ladderY'], p['damAttachZ']
    carriage = n.box('M1DamCarriage', inside, x1, y - 7, y + 7, z - 5, upper)
    half_y, half_z = p['keyWidth'] / 2 + gap, p['keyHeight'] / 2 + gap
    profiles = [rectangle(y - half_y, y + half_y, zz - half_z, zz + half_z)
                for zz in (z, z + p['keySeparation'])]
    slots = n.extrusion('M1DamCarriageSlots', n.sketch('M1DamSlotProfiles', profiles, 'YZ', (inside - 1, 0, 0)), p['carriageThickness'] + 2)
    carriage = n.cut('M1DamIndexedCarriage', carriage, slots)
    lightening = n.prism('M1DamCarriageWindow', [(y - 3, z + 12), (y, z + 8), (y + 3, z + 12), (y, z + 16)],
                        'YZ', (inside - 1, 0, 0), p['carriageThickness'] + 2)
    carriage = n.cut('M1DamOpenCarriage', carriage, lightening)
    keeper_x = inside - gap - p['keeperDiameter'] / 2
    keeper_clear = p['keeperDiameter'] / 2 + 2 * gap + p['retentionInterference'] / 2
    channel = n.extrusion('M1DamKeeperServiceChannel', n.circle('M1DamKeeperChannelProfile', [(keeper_x, y, keeper_clear)],
                          'XY', (0, 0, z - 10)), upper - z + 20)
    carriage = n.cut('M1DamKeeperClearance', carriage, channel)
    joined = n.fuse('M1DamBeforePadRelief', [blade, carriage])
    # Clear the entire travel envelope of the reinforced wall junctions.
    # Offset the tapered face by the nominal clearance in its normal direction.
    toe, knee = -27, -p['armThickness'] + 3
    taper = p['wallGussetRise'] / (knee - toe)
    normal_gap = gap * E(math.sqrt(1 + float(taper) ** 2),
                         'sqrt(1 + (' + ex(taper) + ') * (' + ex(taper) + '))')
    base_y = p['wallPadDepth'] + normal_gap
    relief_profile = [(-30 - gap, -1), (x1 + 1, -1),
                      (x1 + 1, base_y + taper * (x1 + 1 - toe)),
                      (toe, base_y), (-30 - gap, base_y)]
    pad_relief = n.prism('M1DamWallPadRelief', relief_profile, 'XY', (0, 0, z - 10), upper - z + 11)
    joined = n.cut('M1DamLocal', joined, pad_relief)
    right = n.move('M1RightDam', joined, (p['armOriginX'], 0, 0))
    left = n.mirror('M1LeftDam', right)
    register(doc, left, '07_left_dam', '07 / Left optional adjustable dam', (0.28, 0.61, 0.55))
    register(doc, right, '08_right_dam', '08 / Right optional adjustable dam', (0.28, 0.61, 0.55))
    finish(doc, n, 'M1 open dam built: 1.6 mm normal skin, split center, native width/depth expressions and indexed height.')


def make_pin(n, name, p, diameter, shaft_length, head_radius):
    head, radius, gap = p['keeperHead'], diameter / 2, p['fitClearance']
    crown_radius = radius + gap + p['retentionInterference'] / 2
    base = n.extrusion(name + 'Button', n.circle(name + 'ButtonProfile', [(0, 0, head_radius)]), head)
    if name == 'M1KeeperPin':
        flat = n.box(name + 'ButtonFlatTool', radius, head_radius + 1, -head_radius - 1, head_radius + 1, -1, head + 1)
        base = n.cut(name + 'FlatGripButton', base, flat)
    shaft = n.extrusion(name + 'Shaft', n.circle(name + 'ShaftProfile', [(0, 0, radius)], 'XY', (0, 0, head)), shaft_length)
    sections = [n.circle(name + 'CrownRoot', [(0, 0, radius)], 'XY', (0, 0, head + shaft_length)),
                n.circle(name + 'CrownMax', [(0, 0, crown_radius)], 'XY', (0, 0, head + shaft_length + .8)),
                n.circle(name + 'CrownTip', [(0, 0, radius - .3)], 'XY', (0, 0, head + shaft_length + 2.0))]
    crown = n.obj('Part::Loft', name + 'RetentionCrown', name + 'RetentionCrown')
    crown.Sections, crown.Solid, crown.Ruled = sections, True, True
    for section in sections: section.Visibility = False
    body = n.fuse(name + 'BeforeSplit', [base, shaft, crown])
    slot = n.box(name + 'FlexureSlot', -.4, .4, -crown_radius - 1, crown_radius + 1,
                 head + 5, head + shaft_length + 3)
    return n.cut(name + 'Finished', body, slot)


def hardware(doc):
    if doc.getObject('M1HardwareHistory'): return
    p = values(doc)
    n = family(doc, 'Hardware')
    gap, height, width = p['fitClearance'], p['keyHeight'], p['keyWidth']
    separation = p['keySeparation']
    carriage_inner = -p['armThickness'] - gap - p['carriageThickness']
    keeper_x = carriage_inner - gap - p['keeperDiameter'] / 2
    keeper_hole = p['keeperDiameter'] / 2 + gap
    tip = keeper_x - keeper_hole - 2
    plate = n.box('M1KeyBackplate', gap, gap + p['keyPlate'], -width / 2 - 2, width / 2 + 2, -height / 2 - 1.5, separation + height / 2 + 1.5)
    tongues = [n.box('M1KeyTongue' + str(i), tip, gap, -width / 2, width / 2, z - height / 2, z + height / 2)
               for i, z in enumerate((0, separation))]
    key = n.fuse('M1TwoRungKeyBeforeBore', [plate] + tongues)
    bore = n.extrusion('M1KeyKeeperBore', n.circle('M1KeyKeeperBoreProfile', [(keeper_x, 0, keeper_hole)],
                       'XY', (0, 0, -height / 2 - 1)), separation + height + 2)
    key = n.cut('M1TwoRungKey', key, bore)
    keeper = make_pin(n, 'M1KeeperPin', p, p['keeperDiameter'], separation + height, 3.5)
    cap_pin = make_pin(n, 'M1CapPin', p, p['capPinDiameter'], p['capThickness'] + gap + 8 - .3, 4.0)
    color = (0.83, 0.65, 0.30)
    for kind, at_z, numbers in [('fan', -54, (9, 10, 13, 14)),
                               ('dam', p['damAttachZ'], (11, 12, 15, 16))]:
        right_key = n.move('M1Right' + kind.title() + 'Key', key, (p['armOriginX'], p['ladderY'], at_z))
        left_key = n.mirror('M1Left' + kind.title() + 'Key', right_key)
        register(doc, left_key, f'{numbers[0]:02}_left_{kind}_key', f'{numbers[0]:02} / Left {kind} two-rung key', color)
        register(doc, right_key, f'{numbers[1]:02}_right_{kind}_key', f'{numbers[1]:02} / Right {kind} two-rung key', color)
        top = at_z + separation + height / 2 + gap + p['keeperHead']
        right_pin = n.move('M1Right' + kind.title() + 'Keeper', keeper,
                           (p['armOriginX'] + keeper_x, p['ladderY'], top), App.Rotation(App.Vector(1, 0, 0), 180))
        left_pin = n.mirror('M1Left' + kind.title() + 'Keeper', right_pin)
        register(doc, left_pin, f'{numbers[2]:02}_left_{kind}_keeper', f'{numbers[2]:02} / Left {kind} keeper pin', color)
        register(doc, right_pin, f'{numbers[3]:02}_right_{kind}_keeper', f'{numbers[3]:02} / Right {kind} keeper pin', color)
    inner = p['fanWidth'] / 2 + gap
    boss_x = inner + 3.7
    boss_z = -p['fanThickness'] - p['fanFrameWall'] + 16
    front = inner + gap + p['capThickness'] + p['keeperHead']
    for i, x in enumerate((-boss_x, boss_x)):
        local = n.move('M1CapPinLocal' + str(i), cap_pin, (x, front, boss_z), App.Rotation(App.Vector(1, 0, 0), 90))
        right = n.move('M1RightCapPin' + str(i), fan_transform(n, 'M1CapPinTilt' + str(i), local, p), (p['armOriginX'], 0, 0))
        left = n.mirror('M1LeftCapPin' + str(i), right)
        for side, obj, number in [('left', left, 17 + i * 2), ('right', right, 18 + i * 2)]:
            register(doc, obj, f'{number:02}_{side}_cap_pin_{i+1}', f'{number:02} / {side.title()} retainer pin {i+1}', color)
    finish(doc, n, 'M1 removable hardware built: four identical two-rung keys, four keepers and four fan-retainer pins.')


def arms(doc):
    if doc.getObject('M1ArmsHistory'): return
    p = values(doc)
    n = family(doc, 'Arms')
    t, h, back, front = p['armThickness'], p['armHeight'], p['rearFace'], p['frontFace']
    outer = front + p['frontLip']
    outline = [(0, -72), (2, -74), (8, -74), (30, -64), (outer, -12),
               (outer, p['tineHeight'] - 2), (outer - 2, p['tineHeight']),
               (front + 2, p['tineHeight']), (front, p['tineHeight'] - 2),
               (front, 2), (front - 2, 0), (back, 0), (back, h - 2),
               (back - 2, h), (2, h), (0, h - 2)]
    body = n.prism('M1ArmOutline', outline, 'YZ', (-t, 0, 0), t)
    windows = []
    cell = (h - 30) / 5
    for i in range(5):
        low, high = 14 + i * cell, 14 + (i + 1) * cell - 8
        left, right = 10, back - 16
        windows.append([(left, low + 2), (left + 2, low), (right - 2, low),
                        (right, low + 2), (right, high - 2), (right - 2, high),
                        (left + 2, high), (left, high - 2)])
    windows += [[(12, -57), (23, -53), (23, -16), (12, -16)],
                [(36, -40), (outer - 9, -16), (36, -16)],
                rectangle(front + 1.8, outer - 1.8, 12, p['tineHeight'] - 9)]
    tools = n.extrusion('M1ArmLightening', n.sketch('M1ArmWindows', windows, 'YZ', (-t - 1, 0, 0)), t + 2)
    body = n.cut('M1ArmOpenFrame', body, tools)
    pads, gussets = [], []
    half_pad, web = p['wallPadHeight'] / 2, p['wallGussetWeb']
    for index, z in enumerate((18, h - 16)):
        outline_pad = [(-30, z - half_pad + 3), (-27, z - half_pad),
                       (-3, z - half_pad), (0, z - half_pad + 3),
                       (0, z + half_pad - 3), (-3, z + half_pad),
                       (-27, z + half_pad), (-30, z + half_pad - 3)]
        pads.append(n.prism('M1WallPad' + str(index), outline_pad, 'XZ', (0, p['wallPadDepth'], 0), p['wallPadDepth']))
        # Continue both web roots through the complete arm thickness. Adding
        # them only above the old 12 mm layer would leave a bridge over a window.
        depth = p['wallPadDepth']
        web_profile = [(-27, depth - 2), (-27, depth),
                       (-t + 3, depth + p['wallGussetRise']),
                       (0, depth + p['wallGussetRise']), (0, depth - 2)]
        for side, low in [('Lower', z - half_pad), ('Upper', z + half_pad - web)]:
            gussets.append(n.prism('M1WallGusset' + str(index) + side,
                                   web_profile, 'XY', (0, 0, low), web))
    cheek = n.box('M1LateralStop', -p['sideLip'], 0, back, front, -2, 14)
    body = n.fuse('M1ArmWithWallPads', [body, cheek] + pads + gussets)
    slots = []
    for z in [-54, -30] + [p['ladderStart'] + i * p['rungPitch'] for i in range(11)]:
        half_y = p['keyWidth'] / 2 + p['fitClearance']
        half_z = p['keyHeight'] / 2 + p['fitClearance']
        slots.append(rectangle(p['ladderY'] - half_y, p['ladderY'] + half_y, z - half_z, z + half_z))
    slots_tool = n.extrusion('M1LadderAndFanSlots', n.sketch('M1RungProfiles', slots, 'YZ', (-t - 1, 0, 0)), t + 2)
    body = n.cut('M1ArmIndexed', body, slots_tool)
    holes, roofs = [], []
    radius = p['wallBoltDiameter'] / 2
    q = radius / math.sqrt(2)
    for index, z in enumerate((18, h - 16)):
        holes.append((-18, z, radius))
        roofs.append([(-18 - q, z - q), (-18 - 2 * q, z), (-18 - q, z + q)])
    bores = n.extrusion('M1WallBores', n.circle('M1WallBoreCircles', holes, 'XZ', (0, p['wallPadDepth'] + 1, 0)), p['wallPadDepth'] + 2)
    roof = n.extrusion('M1WallBoreRoofs', n.sketch('M1WallTeardrops', roofs, 'XZ', (0, p['wallPadDepth'] + 1, 0)), p['wallPadDepth'] + 2)
    body = n.cut('M1ArmFinished', body, n.fuse('M1WallHoleTools', [bores, roof]))
    right = n.move('M1RightArm', body, (p['armOriginX'], 0, 0))
    left = n.mirror('M1LeftArm', right)
    register(doc, left, '01_left_arm', '01 / Left perforated arm', (0.23, 0.30, 0.33))
    register(doc, right, '02_right_arm', '02 / Right perforated arm', (0.23, 0.30, 0.33))
    finish(doc, n, 'M1.1 arms built: paired tapered wall gussets, continuous web roots and unchanged bolt/ladder centers.')


def run(stage='arms'):
    doc = open_document()
    setup(doc)
    sheet = doc.getObject('M1Parameters')
    if isinstance(getattr(sheet, 'fanCenterZ'), str):
        sheet.set(sheet.getCellFromAlias('fanCenterZ'), '=' + getattr(sheet, 'fanCenterZ'))
    legacy = doc.getObject('DuctedPrototypeReference')
    if legacy and legacy.Group:
        snapshots = ROOT / 'snapshots'
        snapshots.mkdir(exist_ok=True)
        shutil.copy2(TARGET, snapshots / 'M1_Original_SaveAs.FCStd')
        # The full ducted native model is independently preserved. Retain its
        # lineage, not a second assembly solver and hundreds of unused features.
        origin = doc.getObject('M1Assembly').Origin
        keep_origin = {o.Name for o in [origin] + list(origin.OriginFeatures)}
        for obj in reversed(list(doc.Objects)):
            if not obj.Name.startswith('M1') and obj.Name != legacy.Name and obj.Name not in keep_origin:
                doc.removeObject(obj.Name)
        legacy.Label = 'PROVENANCE / Save As from ducted Rev H'
        legacy.addProperty('App::PropertyString', 'SourceModel', 'Provenance')
        legacy.SourceModel = '../freecad/Precision_5560_Native.FCStd'
    doc.recompute()
    if stage in ('arms', 'all'): arms(doc)
    if stage in ('fans', 'all'):
        fan_cages(doc)
        caps(doc)
    if stage in ('dams', 'all'): dams(doc)
    if stage in ('hardware', 'all'): hardware(doc)
    assembly = doc.getObject('M1Assembly')
    if not hasattr(assembly, 'Revision'):
        assembly.addProperty('App::PropertyString', 'Revision', 'Design')
    if doc.getObject('M1WallGusset0Lower'):
        assembly.Revision = 'M1.1 / reinforced wall transitions'
        doc.Label = 'Laptop wall mount / Minimalist M1.1'
    doc.save()
    return doc


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', nargs='?', default='arms', choices=('arms','fans','dams','hardware','all'))
    parser.add_argument('--target', type=Path, help='Separate native Save As target for a clean rebuild')
    args = parser.parse_args()
    if args.target: TARGET = args.target.resolve()
    run(args.stage)
