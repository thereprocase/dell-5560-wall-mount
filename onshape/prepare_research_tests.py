"""Prepare metadata batch and a reversible parametric perturbation."""
from prepare_pin import *

metadata = json.loads((OUT / '24-metadata-all.json').read_text())['data']
names = {'cf9a24a5d90f7bf7ae0d3004':'Push pin - native',
         '959913d7c8696541b603dc65':'Installed assembly - native WIP'}
items=[]
for item in metadata['items']:
    if item['elementId'] in names:
        prop=next(p for p in item['properties'] if p['name']=='Name')
        items.append(dict(href=item['href'],properties=[dict(propertyId=prop['propertyId'],value=names[item['elementId']])]))
save('rename-tabs-batch',dict(items=items))
variables=json.loads((OUT/'variables-all.json').read_text())
for v in variables:
    if v['name']=='pinHeadRadius': v['expression']='4.5 mm'
save('variables-perturb',variables)
