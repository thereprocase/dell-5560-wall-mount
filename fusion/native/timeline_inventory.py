import adsk.fusion as f
d=f.Design.cast(app.activeProduct)
result['timeline']=[]
for i in range(d.timeline.count):
    t=d.timeline.item(i)
    try:entity=t.entity;name=entity.name;kind=entity.objectType
    except Exception:name=t.name;kind=t.objectType
    result['timeline'].append({'index':i,'name':name,'kind':kind,'group':t.isGroup})
