"""Create a focused-resolution Rev H case for a longer transient benchmark.

This is a different mesh candidate, not a continuation or validation of case 04.
The original case generator and all recorded results remain unchanged.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path

from generate_revh_transient import BASE, generate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', type=Path, required=True)
    parser.add_argument('--layers', choices=['relative', 'absolute', 'relative-compact'], default='relative')
    parser.add_argument('--refine-defects-from', type=Path)
    args = parser.parse_args()
    case = args.case.resolve()
    generate(case, BASE / 'geometry_revh', 1e-8)
    manifest_path = case / 'case_manifest.json'
    meta = json.loads(manifest_path.read_text())
    mesh_path = case / 'system/snappyHexMeshDict'
    mesh = mesh_path.read_text()
    boxes = meta['refinement_boxes']
    # Full-span edges retain 0.5 mm cells; bulk selected passages use 1 mm.
    # Additional 16 mm-wide strips around the sampled +/-111 mm planes retain
    # the original 0.25 mm target at the front and hinge lips and duct outlets.
    for name, spec in list(boxes.items()):
        old_level = spec['level']
        spec['level'] -= 1
        spec['cell_mm'] *= 2
        old = f'{name} {{mode inside; levels ((1e15 {old_level}));}}'
        assert old in mesh
        mesh = mesh.replace(old, f'{name} {{mode inside; levels ((1e15 {spec["level"]}));}}')
    additions = {}
    for side, x in [('left', -.111), ('right', .111)]:
        for region in ['ductOuterEdge', 'frontLip', side + 'HingeLip']:
            spec = boxes[region]
            additions[side + '_' + region + '_sample_strip'] = {
                'min_m': [x - .008, *spec['min_m'][1:]],
                'max_m': [x + .008, *spec['max_m'][1:]],
                'level': 6, 'cell_mm': .25,
            }
    repairs = None
    if args.refine_defects_from:
        source = args.refine_defects_from.resolve()
        rows = list(csv.DictReader(source.read_text().splitlines()))
        for row in rows:
            center = [float(row[axis + '_m']) for axis in ['x', 'y', 'z']]
            radius = [float(row['span_' + axis + '_m']) / 2 + .002 for axis in ['x', 'y', 'z']]
            additions['repair_' + row['cell_id']] = {
                'min_m': [c-r for c,r in zip(center,radius)],
                'max_m': [c+r for c,r in zip(center,radius)],
                'level': 5, 'cell_mm': .5,
            }
        repairs = {'source': str(source), 'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                   'defect_regions': len(rows), 'padding_m': .002, 'cell_mm': .5}
    def vec(values):
        return '(' + ' '.join(str(x) for x in values) + ')'
    shapes = '\n'.join(f'{name} {{type searchableBox; min {vec(spec["min_m"])}; max {vec(spec["max_m"])};}}' for name, spec in additions.items())
    refs = '\n'.join(f'{name} {{mode inside; levels ((1e15 {spec["level"]}));}}' for name,spec in additions.items())
    mesh = mesh.replace('geometry {', 'geometry {\n' + shapes, 1)
    mesh = mesh.replace('refinementRegions {', 'refinementRegions {\n' + refs, 1)
    boxes.update(additions)
    for patch in ['printed', 'laptop']:
        mesh = mesh.replace(f'{patch} {{level (4 4);', f'{patch} {{level (3 3);')
    mesh = mesh.replace('maxGlobalCells 24000000', 'maxGlobalCells 8000000')
    mesh = mesh.replace('relativeSizes false;', 'relativeSizes true;')
    mesh = mesh.replace('printed {nSurfaceLayers 5;} laptop {nSurfaceLayers 5;} noctua {nSurfaceLayers 3;}',
                        'printed {nSurfaceLayers 4;} laptop {nSurfaceLayers 4;} noctua {nSurfaceLayers 2;}')
    mesh = mesh.replace('firstLayerThickness .00006; minThickness .00002;', 'finalLayerThickness .3; minThickness .15;')
    mesh = mesh.replace('nGrow 0; featureAngle 60;', 'nGrow 1; featureAngle 50;')
    mesh = mesh.replace('maxThicknessToMedialRatio .3;', 'maxThicknessToMedialRatio .25;')
    mesh = mesh.replace('nBufferCellsNoExtrude 1; nLayerIter 60;', 'nBufferCellsNoExtrude 3; nLayerIter 35;')
    if args.layers == 'absolute':
        mesh = mesh.replace('relativeSizes true;', 'relativeSizes false;')
        mesh = mesh.replace('printed {nSurfaceLayers 4;} laptop {nSurfaceLayers 4;}',
                            'printed {nSurfaceLayers 3;} laptop {nSurfaceLayers 3;}')
        mesh = mesh.replace('finalLayerThickness .3; minThickness .15;', 'firstLayerThickness .0001; minThickness .00004;')
        mesh = mesh.replace('nGrow 1; featureAngle 50;', 'nGrow 0; featureAngle 60;')
        mesh = mesh.replace('maxThicknessToMedialRatio .25;', 'maxThicknessToMedialRatio .3;')
    elif args.layers == 'relative-compact':
        mesh = mesh.replace('finalLayerThickness .3; minThickness .15;', 'finalLayerThickness .25; minThickness .1;')
        mesh = mesh.replace('nGrow 1; featureAngle 50;', 'nGrow 0; featureAngle 60;')
        mesh = mesh.replace('nBufferCellsNoExtrude 3; nLayerIter 35;', 'nBufferCellsNoExtrude 1; nLayerIter 60;')
    mesh_path.write_text(mesh, encoding='ascii', newline='\n')

    # A fixed ten-step, 10-microsecond benchmark bounds initial runtime. Write
    # compact probes each step but full volume fields only at its endpoint.
    # Production duration and output spacing depend on measured stability/cost.
    control_path = case / 'system/controlDict'
    control = control_path.read_text()
    control = control.replace('endTime .002; deltaT .00001;', 'endTime .0001; deltaT .00001;')
    control = control.replace('adjustTimeStep yes;', 'adjustTimeStep no;')
    control = control.replace('writeInterval .001;', 'writeInterval .0001;')
    control = control.replace('writeInterval 20;', 'writeInterval 1;')
    control = control.replace('writeInterval 10;', 'writeInterval 1;')
    control_path.write_text(control, encoding='ascii', newline='\n')
    (case / 'config/controlDict.transient').write_text(control, encoding='ascii', newline='\n')
    meta.update({
        'mesh_profile': 'focused_sequence_benchmark',
        'scope': 'Focused-resolution transient commissioning candidate; no validation acceptance or settled-flow claim.',
        'surface_cell_mm': {'printed': 2, 'laptop': 2, 'noctua': 2},
        'requested_layers': {'printed': 4, 'laptop': 4, 'noctua': 2,
                             'relative_sizes': True, 'final_layer_fraction': .3,
                             'minimum_total_thickness_fraction': .15, 'growth': 1.2},
        'requested_max_Co': None, 'requested_max_deltaT_s': .00001,
        'benchmark': {'fixed_deltaT_s': .00001, 'steps': 10,
                      'stop_condition': 'Monitor logged Courant and field bounds; no automatic production extension.'},
        'pilot_end_time_s': .0001,
        'production_plan': 'Measure mesh quality and cost on a bounded benchmark. Then establish flow startup duration and save hundreds of actual section samples; no invented in-between states. A longer run is not a mesh/time-step convergence test.',
        'change_reason': 'Four initialization snapshots cannot form a meaningful flow-evolution video. Reduce background and full-span cell cost while preserving 0.25 mm targets in the plotted lip regions; revisit wall layers.'
    })
    meta['defect_refinement'] = repairs
    meta['layer_profile'] = args.layers
    if args.layers == 'absolute':
        meta['requested_layers'] = {'printed': 3, 'laptop': 3, 'noctua': 2,
                                    'relative_sizes': False, 'first_layer_thickness_mm': .1,
                                    'minimum_total_thickness_mm': .04, 'growth': 1.2}
    elif args.layers == 'relative-compact':
        meta['requested_layers'].update({'final_layer_fraction': .25,
                                        'minimum_total_thickness_fraction': .1})
    manifest_path.write_text(json.dumps(meta, indent=2) + '\n', encoding='utf-8')
    print('Focused sequence benchmark prepared:', case)


if __name__ == '__main__':
    main()
