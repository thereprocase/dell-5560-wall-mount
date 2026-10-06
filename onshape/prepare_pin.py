"""Prepare ordinary sketch/revolve/extrude payloads; no network access."""
import json
import math
from pathlib import Path

OUT = Path(__file__).resolve().parent / 'exploration_20'
OUT.mkdir(exist_ok=True)

def save(name, obj):
    (OUT / (name + '.json')).write_text(json.dumps(obj, indent=2))

def query(pid, expression):
    return dict(btType='BTMParameterQueryList-148', parameterId=pid,
                queries=[dict(btType='BTMIndividualQuery-138', queryString='query=' + expression + ';')])

def enum(pid, typ, value):
    return dict(btType='BTMParameterEnum-145', parameterId=pid, enumName=typ, value=value)

def quantity(pid, expression):
    return dict(btType='BTMParameterQuantity-147', parameterId=pid, expression=expression)

def boolean(pid, value):
    return dict(btType='BTMParameterBoolean-144', parameterId=pid, value=value)

def feature(name, typ, params):
    return dict(feature=dict(btType='BTMFeature-134', name=name, featureType=typ, parameters=params))

def polygon(name, points):
    entities = []
    for i, (a, b) in enumerate(zip(points, points[1:] + points[:1])):
        dx, dy = b[0]-a[0], b[1]-a[1]
        length = math.hypot(dx, dy)
        entities.append(dict(btType='BTMSketchCurveSegment-155', entityId=f'edge{i}',
            startPointId=f'edge{i}.start', endPointId=f'edge{i}.end',
            startParam=0, endParam=length/1000,
            geometry=dict(btType='BTCurveGeometryLine-117', pntX=a[0]/1000, pntY=a[1]/1000,
                          dirX=dx/length, dirY=dy/length)))
    return dict(feature=dict(btType='BTMSketch-151', name=name, featureType='newSketch',
        parameters=[query('sketchPlane', 'qCreatedBy(makeId("Front"), EntityType.FACE)')],
        entities=entities, constraints=[]))

def fid(label):
    files = [p for p in OUT.glob(f'*-{label}.json') if not p.name.endswith('-request.json')]
    return json.loads(files[0].read_text())['data']['feature']['featureId']

def prepare():
    save('profile', polygon('Pin - axial profile (mm)', [(0,0),(4,0),(4,1.4),(3.4,2),
                        (2,2),(2,12),(2.1,12),(1.6,14),(0,14)]))
    save('slot', polygon('Pin - 1 mm split from z=4', [(-.5,4),(.5,4),(.5,14.1),(-.5,14.1)]))
    if list(OUT.glob('*-profile-add.json')):
        sketch = fid('profile-add')
        save('revolve', feature('Pin - revolve 360 degrees', 'revolve', [
            enum('bodyType','ExtendedToolBodyType','SOLID'),
            enum('operationType','NewBodyOperationType','NEW'),
            query('entities',f'qSketchRegion(makeId("{sketch}"))'),
            query('axis',f'qNthElement(qContainsPoint(qCreatedBy(makeId("{sketch}"), EntityType.EDGE), vector(0,0,7)*millimeter), 0)'),
            enum('revolveType','RevolveType','FULL')]))
        if list(OUT.glob('*-revolve-add.json')):
            d = json.loads((OUT / 'revolve.json').read_text())
            d['feature']['featureId'] = fid('revolve-add')
            save('revolve-fix', d)
    if list(OUT.glob('*-slot-add.json')):
        sketch = fid('slot-add')
        save('split', feature('Pin - split cut symmetric 6 mm', 'extrude', [
            enum('bodyType','ExtendedToolBodyType','SOLID'),
            enum('operationType','NewBodyOperationType','REMOVE'),
            query('entities',f'qSketchRegion(makeId("{sketch}"))'),
            enum('endBound','BoundingType','BLIND'), quantity('depth','6 mm'),
            boolean('symmetric',True), boolean('defaultScope',True)]))

if __name__ == '__main__':
    prepare()
