"""Export native M1 solids with baked print poses; verify exchange geometry."""
from pathlib import Path
import hashlib
import json
import math
import xml.etree.ElementTree as ET
import zipfile

import FreeCAD as App
import MeshPart
import Part

from validate import shapes


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hull(points):
    points = sorted(set(points))
    def cross(o, a, b): return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    def half(seq):
        result = []
        for p in seq:
            while len(result) > 1 and cross(result[-2], result[-1], p) <= 0: result.pop()
            result.append(p)
        return result
    return half(points)[:-1] + half(reversed(points))[:-1]


def clip(polygon, axis, limit):
    result = []
    for a, b in zip(polygon, polygon[1:] + polygon[:1]):
        ina, inb = a[axis] <= limit, b[axis] <= limit
        if ina: result.append(a)
        if ina != inb:
            t = (limit-a[axis])/(b[axis]-a[axis])
            result.append(tuple(a[i]+t*(b[i]-a[i]) for i in (0, 1)))
    return result


def orient(key, shape, center=(128, 128)):
    result = shape.copy()
    if key.endswith('_arm') or key.endswith('_key'):
        result.rotate(App.Vector(), App.Vector(0, 1, 0), -90 if 'left' in key else 90)
        if key.endswith('_arm'): result.rotate(App.Vector(), App.Vector(0, 0, 1), 45)
        pose = 'outer flat side down' + ('; diagonal' if key.endswith('_arm') else '')
    else:
        angle = -45 if 'fan_cage' in key else -135 if ('fan_cap' in key or 'cap_pin' in key) else 180
        result.rotate(App.Vector(), App.Vector(1, 0, 0), angle)
        pose = 'grille down' if 'fan_cage' in key else 'front face down' if 'fan_cap' in key else 'lip down' if key.endswith('_dam') else 'button down; split tip up'
    b = result.BoundBox
    result.translate(App.Vector(center[0]-(b.XMin+b.XMax)/2, center[1]-(b.YMin+b.YMax)/2, -b.ZMin))
    if key.endswith('_arm'):
        # Keep the side-down strength orientation; select an in-plane turn that
        # clears the P1S front-left cutter with the requested outer brim.
        original = result.copy()
        found = False
        for angle in (0, 90, 180, 270):
            candidate = original.copy()
            candidate.rotate(App.Vector(128,128,0), App.Vector(0,0,1), angle)
            b = candidate.BoundBox
            for dx,dy in ((0,0), (248-b.XMax,248-b.YMax)):
                moved = candidate.copy()
                moved.translate(App.Vector(dx,dy,0))
                projection = hull([(v.x,v.y) for v in mesh_for(moved).Topology[0]])
                if not clip(clip(projection,0,26.1),1,36.1):
                    result = moved
                    pose += '; plate turn '+str(angle)+' degrees'
                    found = True
                    break
            if found: break
        assert found, (key, 'no brim/cutter-safe in-plane placement')
    return result, pose


def mesh_for(shape):
    return MeshPart.meshFromShape(Shape=shape, LinearDeflection=.035, AngularDeflection=.12, Relative=False)


def model3mf(path, mesh, key):
    vertices, faces = mesh.Topology
    model = ET.Element('model', {'unit': 'millimeter', 'xmlns': 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'})
    obj = ET.SubElement(ET.SubElement(model, 'resources'), 'object', {'id': '1', 'type': 'model', 'name': key})
    m = ET.SubElement(obj, 'mesh')
    vs, ts = ET.SubElement(m, 'vertices'), ET.SubElement(m, 'triangles')
    for v in vertices: ET.SubElement(vs, 'vertex', dict(zip(('x', 'y', 'z'), [format(x, '.9g') for x in v])))
    for f in faces: ET.SubElement(ts, 'triangle', dict(zip(('v1', 'v2', 'v3'), map(str, f))))
    ET.SubElement(ET.SubElement(model, 'build'), 'item', {'objectid': '1'})
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('3D/3dmodel.model', ET.tostring(model, encoding='utf-8', xml_declaration=True))
        z.writestr('[Content_Types].xml', '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
        z.writestr('_rels/.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')


def write_shape(path, key, shape, pose, expected_solids=1):
    assert shape.isValid() and len(shape.Solids) == expected_solids, key
    mesh = mesh_for(shape)
    assert mesh.isSolid(), key
    mesh.write(str(path / (key + '.stl')))
    shape.exportStep(str(path / (key + '.step')))
    check = Part.read(str(path / (key + '.step')))
    assert check.isValid() and len(check.Solids) == expected_solids, key
    difference = check.cut(shape).Volume + shape.cut(check).Volume
    assert difference < .02, (key, difference)
    model3mf(path / (key + '.3mf'), mesh, key)
    b = shape.BoundBox
    projection = hull([(v.x, v.y) for v in mesh.Topology[0]])
    # An axis-expanded cutter rectangle conservatively includes the 8 mm brim.
    cutter_clear = not clip(clip(projection, 0, 26), 1, 36)
    bed_ok = min(b.XMin, b.YMin) >= 7.999 and max(b.XMax, b.YMax) <= 248.001 and b.ZMax <= 256.001
    assert bed_ok and cutter_clear and abs(b.ZMin) < 1e-5, (key, b, cutter_clear)
    return {'orientation': pose, 'volume_mm3': shape.Volume, 'dimensions_mm': [b.XLength, b.YLength, b.ZLength],
            'bounds_mm': [b.XMin,b.YMin,b.ZMin,b.XMax,b.YMax,b.ZMax],
            'closed_mesh': True, 'step_valid_solids': expected_solids, 'step_roundtrip_difference_mm3': difference,
            'bed_and_8mm_brim_clear': bed_ok, 'stock_cutter_and_brim_clear': cutter_clear,
            'sha256': {ext: sha(path / (key + ext)) for ext in ('.stl','.step','.3mf')}}


def export(doc, path):
    path.mkdir(parents=True, exist_ok=True)
    parts = shapes(doc)
    manifest = {'revision': 'Minimalist M1.1 prototype', 'units': 'mm', 'native_sha256': sha(Path(doc.FileName)),
                'standard_3mf_contains_slicer_settings': False, 'parts': {}, 'plates': {}}
    hardware = []
    for key, shape in sorted(parts.items()):
        placed, pose = orient(key, shape)
        manifest['parts'][key] = write_shape(path, key, placed, pose)
        if int(key[:2]) > 8:
            i = len(hardware)
            small, _ = orient(key, shape, (60+(i%4)*40, 70+(i//4)*50))
            hardware.append(small)
    manifest['plates']['21_all_hardware'] = write_shape(path, '21_all_hardware', Part.makeCompound(hardware), '12 separate parts; replaces individual files 09-20', 12)
    manifest['plates']['22_hardware_without_dam'] = optional_hardware(doc, path)
    Part.makeCompound(list(parts.values())).exportStep(str(path / 'M1_assembled.step'))
    manifest['total_volume_mm3'] = sum(s.Volume for s in parts.values())
    (path / 'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print('EXPORT', path.name, len(parts), 'parts and hardware plate PASS', flush=True)
    return manifest


def optional_hardware(doc, path):
    hardware = []
    for key, shape in sorted(shapes(doc).items()):
        if int(key[:2]) <= 8 or '_dam_' in key: continue
        i = len(hardware)
        placed, _ = orient(key, shape, (60+(i%4)*40, 90+(i//4)*50))
        hardware.append(placed)
    assert len(hardware) == 8
    return write_shape(path, '22_hardware_without_dam', Part.makeCompound(hardware),
                       '8 separate parts; use with 01-06 when omitting the dam', 8)
