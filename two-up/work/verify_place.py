import FreeCAD as App
doc = App.openDocument('two-up/work/Laptop_Wall_Mount_TwoUp.FCStd')
links=[o for o in doc.Objects if o.TypeId=='App::Link' and hasattr(o,'InstanceKey')]
print('LINKS', len(links))
for o in sorted(links, key=lambda x: x.InstanceKey):
    p=o.LinkPlacement.Base
    print(f"{o.InstanceKey:<30} base=({p.x:7.1f},{p.y:7.1f},{p.z:7.1f}) vol={o.Shape.Volume:10.1f} valid={o.Shape.isValid()}")
