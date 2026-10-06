"""Prepare a shared native Variable Studio and existing-dimension updates offline."""
import re
from prepare_pin import *

spec = json.loads((OUT.parent / 'design_parameters.json').read_text())
names = {p['name'] for p in spec['parameters']}
variables = []
for p in spec['parameters']:
    expression = p.get('relationship', f"{p['nominal']} {p['unit']}")
    if 'relationship' in p:
        expression = re.sub(r'\b[A-Za-z][A-Za-z0-9]*\b', lambda m: '#'+m[0] if m[0] in names else m[0], expression)
    variables.append(dict(name=p['name'], type='ANGLE' if p['unit']=='deg' else 'LENGTH',
                          expression=expression, description=p['role']))
for name, value in [('pinHeadRadius',4),('pinHeadHeight',2),('pinHeadChamfer',.6),
                    ('pinShaftLength',10),('pinCrownHeight',2),('pinTipRadius',1.6),
                    ('pinSplitWidth',1),('pinSplitRoot',4),('pinSplitOverrun',.1),('pinCutDepth',6)]:
    variables.append(dict(name=name,type='LENGTH',expression=f'{value} mm',description='Revision F pin dimension'))
save('variables-all',variables)
save('create-variables',dict(name='Design variables - Revision F'))
save('variables-auto',dict(isAutomaticallyInserted=True))

if list(OUT.glob('*-profile-constraints-single.json')):
    profile = json.loads(next(OUT.glob('*-profile-constraints-single.json')).read_text())['data']['feature']
    slot = json.loads(next(OUT.glob('*-slot-constraints-single.json')).read_text())['data']['feature']
    exprs = ['#pinHeadRadius','#pinHeadHeight - #pinHeadChamfer','sqrt(2) * #pinHeadChamfer',
             '#pinHeadRadius - #pinHeadChamfer - #pinShaftDiameter/2','#pinShaftLength',
             '(#pinCrownDiameter - #pinShaftDiameter)/2',
             'sqrt((#pinCrownDiameter/2 - #pinTipRadius)^2 + #pinCrownHeight^2)',
             '#pinTipRadius','#pinHeadHeight + #pinShaftLength + #pinCrownHeight']
    for f in [profile,slot]:
        for c in f['constraints']:
            if c['entityId'].startswith('length'):
                index = int(c['entityId'][6:])
                exp = exprs[index] if f is profile else ['#pinSplitWidth',
                    '#pinHeadHeight + #pinShaftLength + #pinCrownHeight + #pinSplitOverrun - #pinSplitRoot'][index]
                for param in c['parameters']:
                    if param['parameterId']=='length':
                        param['expression']=exp
    save('dimensions-to-variables',dict(btType='BTUpdateFeaturesCall-1748',features=[profile,slot]))
