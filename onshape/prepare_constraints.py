"""Add native connectivity, orientation and editable length constraints."""
from prepare_pin import *

def string(pid, value):
    return dict(btType='BTMParameterString-149', parameterId=pid, value=value)

def constraint(cid, typ, params):
    return dict(btType='BTMSketchConstraint-2', entityId=cid, constraintType=typ, parameters=params)

features = []
for label, payload in [('profile-add', 'profile'), ('slot-add', 'slot')]:
    f = json.loads((OUT / (payload + '.json')).read_text())['feature']
    f['featureId'] = fid(label)
    edges = f['entities']
    c = []
    for i,e in enumerate(edges):
        c.append(constraint(f'join{i}', 'COINCIDENT', [
            string('localFirst',e['endPointId']), string('localSecond',edges[(i+1)%len(edges)]['startPointId'])]))
        g = e['geometry']
        typ = 'HORIZONTAL' if abs(g['dirY']) < 1e-9 else 'VERTICAL' if abs(g['dirX']) < 1e-9 else None
        if typ:
            c.append(constraint(f'orient{i}',typ,[string('localFirst',e['entityId'])]))
        # Rectangle has two independent lengths; avoid redundant opposite dimensions.
        if payload == 'profile' or i < 2:
            c.append(constraint(f'length{i}','LENGTH',[string('localFirst',e['entityId']),
                quantity('length',f"{e['endParam']*1000:.12g} mm")]))
    c.append(constraint('anchor','FIX',[string('localFirst',edges[0]['startPointId'])]))
    f['constraints'] = c
    features.append(f)
save('constraints',dict(btType='BTUpdateFeaturesCall-1748',features=features))
