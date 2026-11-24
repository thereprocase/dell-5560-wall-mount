import json, os
import FreeCAD as App
import Part

DOC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Laptop_Wall_Mount_TwoUp.FCStd')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'export')
os.makedirs(OUT, exist_ok=True)

doc = App.openDocument(DOC)
rows = []
for o in doc.Objects:
    if not o.Name.startswith('TwoUpInstalled'):
        continue
    key = o.InstanceKey
    try:
        shape = o.Shape
        if shape.isNull() or shape.Volume <= 0:
            rows.append(dict(key=key, error='null or zero volume'))
            continue
        bb = shape.BoundBox
        rows.append(dict(
            key=key,
            volume_mm3=round(shape.Volume, 3),
            mass_g=round(shape.Volume / 1000.0 * 1.05, 3),
            bbox=[round(bb.XLength, 3), round(bb.YLength, 3), round(bb.ZLength, 3)],
            solids=len(shape.Solids),
            valid=shape.isValid(),
        ))
        Part.export([shape], os.path.join(OUT, key + '.step'))
        shape.exportStl(os.path.join(OUT, key + '.stl'), 0.05)
    except Exception as e:
        rows.append(dict(key=key, error=str(e)))

json.dump(rows, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'measured.json'), 'w'), indent=1)
print('PARTS', len(rows))
print('TOTAL_MASS_G', round(sum(r.get('mass_g', 0) for r in rows), 2))
for r in rows:
    if 'error' in r:
        print('ERR', r['key'], r['error'])
print('EXPORTED', len(os.listdir(OUT)))
