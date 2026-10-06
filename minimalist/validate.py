"""Independent native geometry, nominal fit, and sampled service checks."""
from pathlib import Path
import argparse
import hashlib
import itertools
import json
import shutil
import sys
import time

import FreeCAD as App
import Part

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from build import values


def quantity(doc, name):
    value = getattr(doc.getObject('M1Parameters'), name)
    return value.Value if hasattr(value, 'Value') else App.Units.Quantity(str(value)).Value


def shapes(doc):
    return {o.InstanceKey: o.Shape for o in doc.getObject('M1Assembly').Group if o.TypeId == 'App::Link'}


def overlap(a, b):
    if not a.BoundBox.intersect(b.BoundBox): return 0.0
    common = a.common(b)
    if common.isNull(): return 0.0
    assert common.isValid(), 'Invalid intersection result'
    return abs(common.Volume)


def reference_shapes(doc):
    v = {name: float(value) for name, value in values(doc).items()}
    laptop = Part.makeBox(v['laptopWidth'], v['laptopThickness'], v['laptopDepth'],
                         App.Vector(-v['laptopWidth'] / 2, v['wallGap'], v['padThickness']))
    right = Part.makeBox(v['fanWidth'], v['fanWidth'], v['fanThickness'],
                        App.Vector(-v['fanWidth'] / 2, -v['fanWidth'] / 2, -v['fanThickness']))
    right.rotate(App.Vector(), App.Vector(1, 0, 0), 45)
    right.translate(App.Vector(v['armOriginX'] - v['fanOffsetX'], v['fanCenterY'], v['fanCenterZ']))
    matrix = App.Matrix()
    matrix.A11 = -1
    left = right.transformGeometry(matrix)
    return laptop, left, right


def audit(doc, service=True):
    started = time.time()
    doc.recompute()
    parts = shapes(doc)
    report = {'parts': {}, 'bad_features': [], 'underconstrained_sketches': [],
              'overlaps_mm3': {}, 'interface_gaps_mm': {}, 'external_interference_mm3': {},
              'part_count': len(parts)}
    for obj in doc.Objects:
        if 'Invalid' in obj.State or 'Error' in obj.State: report['bad_features'].append(obj.Name)
        if obj.TypeId == 'Sketcher::SketchObject' and not obj.FullyConstrained:
            report['underconstrained_sketches'].append(obj.Name)
    report['sketch_count'] = sum(o.TypeId == 'Sketcher::SketchObject' for o in doc.Objects)
    for key, shape in parts.items():
        b = shape.BoundBox
        report['parts'][key] = {'valid': shape.isValid(), 'solids': len(shape.Solids),
                                'volume_mm3': shape.Volume,
                                'bounds_mm': [b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax]}
    for (ka, a), (kb, b) in itertools.combinations(parts.items(), 2):
        volume = overlap(a, b)
        if volume > 1e-4: report['overlaps_mm3'][ka + ' / ' + kb] = volume
    for side, numbers in [('left', ('01', '03', '05', '07')), ('right', ('02', '04', '06', '08'))]:
        arm, cage, cap, dam = (parts[numbers[i] + '_' + side + '_' + family]
                               for i, family in enumerate(('arm', 'fan_cage', 'fan_cap', 'dam')))
        for name, a, b in [('arm_to_fan', arm, cage), ('arm_to_dam', arm, dam), ('fan_to_cap', cage, cap)]:
            report['interface_gaps_mm'][side + '_' + name] = a.distToShape(b)[0]
    laptop, left_fan, right_fan = reference_shapes(doc)
    for label, ref in [('laptop_envelope', laptop), ('left_fan_envelope', left_fan), ('right_fan_envelope', right_fan)]:
        interference = {key: overlap(shape, ref) for key, shape in parts.items()}
        report['external_interference_mm3'][label] = {k: v for k, v in interference.items() if v > 1e-4}
    report['wall_intrusions'] = {k: s.BoundBox.YMin for k, s in parts.items() if s.BoundBox.YMin < -1e-5}
    if service:
        motions = {}
        lift = quantity(doc, 'tineHeight') + 3
        for z, y in [(0, 0), (10, 0), (25, 0), (lift, 0), (lift, 40), (lift, 90)]:
            moved = laptop.copy()
            moved.translate(App.Vector(0, y, z))
            collisions = {k: overlap(s, moved) for k, s in parts.items()}
            motions[f'laptop_lift_{z:g}_forward_{y:g}'] = {k: v for k, v in collisions.items() if v > 1e-4}
        for side, fan, cage_key in [('left', left_fan, '03_left_fan_cage'), ('right', right_fan, '04_right_fan_cage')]:
            for distance in (0, 10, 50, 130):
                moved = fan.copy()
                moved.translate(App.Rotation(App.Vector(1, 0, 0), 45).multVec(App.Vector(0, distance, 0)))
                # Remove that fan's cap and retainer pins before sliding the fan.
                blockers = {k: s for k, s in parts.items()
                            if not (side in k and ('fan_cap' in k or 'cap_pin' in k))}
                collisions = {k: overlap(s, moved) for k, s in blockers.items()}
                motions[f'{side}_fan_slide_{distance}'] = {k: v for k, v in collisions.items() if v > 1e-4}
        report['sampled_service_interference_mm3'] = motions
    report['total_printed_volume_mm3'] = sum(s.Volume for s in parts.values())
    report['cad_solid_mass_g_at_1_05'] = report['total_printed_volume_mm3'] / 1000 * 1.05
    report['elapsed_seconds'] = time.time() - started
    report['pass'] = (
        len(parts) == 20 and not report['bad_features'] and not report['underconstrained_sketches']
        and all(v['valid'] and v['solids'] == 1 for v in report['parts'].values())
        and not report['overlaps_mm3']
        and not any(report['external_interference_mm3'].values())
        and not report['wall_intrusions']
        and all(abs(g - quantity(doc, 'fitClearance')) < 1e-5 for g in report['interface_gaps_mm'].values())
        and not any(report.get('sampled_service_interference_mm3', {}).values())
    )
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', type=Path, default=ROOT / 'Laptop_Wall_Mount_Minimalist.FCStd')
    ap.add_argument('--output', type=Path, default=ROOT / 'validation.json')
    args = ap.parse_args()
    scratch = ROOT / 'scratch'
    scratch.mkdir(exist_ok=True)
    snapshot = scratch / 'IndependentValidation.FCStd'
    initial = hashlib.sha256(args.source.read_bytes()).hexdigest()
    shutil.copy2(args.source, snapshot)
    doc = App.openDocument(str(snapshot))
    report = audit(doc)
    report['source_sha256'] = initial
    App.closeDocument(doc.Name)
    report['source_unchanged'] = hashlib.sha256(args.source.read_bytes()).hexdigest() == initial
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'parts'}, indent=2), flush=True)
    if not report['pass']: raise SystemExit(1)


if __name__ == '__main__': main()
