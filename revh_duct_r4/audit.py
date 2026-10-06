"""Check exported meshes, full deposition support and the formerly blocked bores."""
from pathlib import Path
import hashlib
import json
import sys
import tempfile
import zipfile
import xml.etree.ElementTree as ET
import numpy as np
from scipy.spatial import cKDTree
from shapely.geometry import LineString, box

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
(OUT / 'reports').mkdir(exist_ok=True)
sys.path.insert(0, str(OUT / 'tools'))
from support_audit import audit, read_paths
from mesh import flatten
CACHE = tempfile.TemporaryDirectory(prefix='revh-d4-audit-')


def gcode_from_project(archive):
    folder = Path(CACHE.name) / hashlib.sha256(archive.read_bytes()).hexdigest()
    folder.mkdir(exist_ok=True)
    target = folder / 'preview.gcode'
    if not target.exists():
        with zipfile.ZipFile(archive) as source:
            names = [n for n in source.namelist() if n.endswith('.gcode')]
            assert len(names) == 1
            target.write_bytes(source.read(names[0]))
    return target


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect_socket_paths(key, root):
    archive = root / 'slices' / key / (key + '.gcode.3mf')
    with zipfile.ZipFile(archive) as source:
        settings = json.loads(source.read('Metadata/project_settings.config'))
    offset = [float(v) for v in settings['extruder_offset'][0].split('x')]
    layers, _ = read_paths(gcode_from_project(archive))
    centers = (44.75, 174.75) if 'right' in key else (211.25, 81.25)
    rows = []
    for center in centers:
        # Inspect a 3 mm wide passage from 0.25 to 7.45 mm inside the face.
        # This stays clear of the legitimate curved bore walls and blind bottom.
        region = box(center - 1.5, 128.25 + 58.15, center + 1.5, 135.45 + 58.15)
        by_feature = {}
        for z in (6.4, 6.6, 6.8, 7.0):
            assert z in layers
            for points, width, feature in layers[z]:
                path = LineString([(x + offset[0], y + offset[1]) for x, y in points])
                overlap = path.buffer(width / 2, quad_segs=2).intersection(region).area
                if overlap > 1e-6:
                    by_feature[feature] = by_feature.get(feature, 0) + overlap
        rows.append({'plate_x_mm': center, 'configured_extruder_offset_mm': offset,
                     'inspected_z_mm': [6.4, 6.6, 6.8, 7.0],
                     'passage_bounds_xy_mm': list(region.bounds),
                     'extrusion_overlap_area_sum_mm2': by_feature})
    return rows


for key in (sys.argv[1:] or ['03_left_fan_duct', '04_right_fan_duct']):
    folder = OUT / 'slices' / key
    archive = folder / (key + '.gcode.3mf')
    vertices, faces = flatten(OUT / 'print' / (key + '.3mf'))
    equivalent = []
    for target in [OUT / 'prepared' / (key + '.3mf'), archive]:
        other_vertices, other_faces = flatten(target)
        distance, index = cKDTree(other_vertices).query(vertices)
        assert distance.max() < .00005
        assert sorted(tuple(sorted(int(index[i]) for i in face)) for face in faces) == sorted(
            tuple(sorted(face)) for face in other_faces)
        equivalent.append({'file': str(target.relative_to(OUT)), 'sha256': sha(target),
                           'max_vertex_error_mm': float(distance.max()),
                           'identical_mapped_topology': True, 'triangles': len(faces)})
    with zipfile.ZipFile(archive) as source:
        assert source.testzip() is None
        settings = json.loads(source.read('Metadata/project_settings.config'))
        assert settings['filament_vendor'] == ['Polymaker']
        assert settings['wall_loops'] == '6' and settings['sparse_infill_density'] == '100%'
        ranges = ET.fromstring(source.read('Metadata/layer_config_ranges.xml'))
        assert len(ranges.findall('.//range')) == 1
        assert float(ranges.find('.//range').get('min_z')) == 2.0
        assert float(ranges.find('.//range').get('max_z')) == 2.4
    old = inspect_socket_paths(key, OUT / 'baseline')
    new = inspect_socket_paths(key, OUT)
    assert all(sum(row['extrusion_overlap_area_sum_mm2'].values()) > 10 for row in old)
    assert all(not row['extrusion_overlap_area_sum_mm2'] for row in new), new
    print(key + ': original obstruction detected; both D4 passages clear', flush=True)
    report = audit(gcode_from_project(archive), OUT / 'reports' / (key + '-support.png'))
    report['mesh_equivalence'] = equivalent
    report['socket_regression'] = {'original_D3': old, 'corrected_D4': new, 'passed': True}
    report['acceptance'] = {
        'no_floating_model_islands': not report['floating_components'],
        'no_floating_support_islands': not report['support_floating_components'],
        'max_unsupported_span_below_8_mm': report['max_unsupported_deposition_span_mm'] < 8,
        'socket_passages_clear_of_model_and_support': True,
        'prepared_and_sliced_meshes_match': True,
    }
    (OUT / 'reports' / (key + '.json')).write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'part': key, 'acceptance': report['acceptance'],
                      'max_unsupported_span_mm': report['max_unsupported_deposition_span_mm']}), flush=True)
    assert all(report['acceptance'].values()), key

CACHE.cleanup()
