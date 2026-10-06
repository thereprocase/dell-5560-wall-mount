"""Put independent component histories in engineering assembly order."""
import adsk.fusion as f
from pathlib import Path
import json
d=f.Design.cast(app.activeProduct)
if not d.attributes.itemByName('Dell5560','nativePort'):raise RuntimeError('Wrong document')
d.activateRootComponent()
blocks={}
family=None
for i in range(d.timeline.count):
    obj=d.timeline.item(i)
    if not obj.isGroup:
        entity=obj.entity
        if isinstance(entity,f.Occurrence):
            tag=entity.component.attributes.itemByName('Dell5560','family')
            family=tag.value if tag else None
    if family:blocks.setdefault(family,[]).append(obj)
for family in reversed(('cradle','duct','rail','tray','cap','pin')):
    block=blocks[family]
    target=d.timeline.item(0)
    if block[0].index==0:continue
    for obj in block:
        if not obj.reorder(target.index):raise RuntimeError('Could not reorder '+family)
d.computeAll()
issues=[{'name':x.name,'health':int(x.healthState),'message':x.errorOrWarningMessage} for comp in d.allComponents for x in comp.features if int(x.healthState)]
result.update(issues=issues,timeline=d.timeline.count)
if issues:raise RuntimeError('Unhealthy feature after ordering')
assert d.exportManager.execute(d.exportManager.createFusionArchiveExportOptions(
    'F:/Code/dell-5560-wall-mount/fusion/output/native/Precision_5560_RevF_native_working.f3d'))
