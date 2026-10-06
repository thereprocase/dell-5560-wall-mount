"""Independent geometric acceptance on exported STEP; no live GUI document access."""
from pathlib import Path
import json, math, time
import FreeCAD as App, Part
ROOT=Path(__file__).resolve().parent
s=Part.read(str(ROOT/'Precision_5560_Native.step')).Solids
baseline=json.loads((ROOT/'assembly_native_validation.json').read_text())
# Export order is insertion order, but identify solids independently by center + volume.
shapes={}
remaining=list(s)
for key in baseline['parts']:
    ref=Part.read(str(ROOT.parent/'parts'/(key+'.step'))).Solids[0]
    shape=min(remaining,key=lambda a:(a.CenterOfMass-ref.CenterOfMass).Length+abs(a.Volume-ref.Volume)/1000)
    remaining.remove(shape); shapes[key]=shape
assert len(s)==14 and not remaining
refs=Part.read(str(ROOT.parent/'REFERENCE_Installed_Layout.step')).Solids
lap=next(q for q in refs if q.BoundBox.XLength>300)
fans=[q for q in refs if abs(q.BoundBox.XLength-120)<1e-5]
assert len(fans)==2
checks={'export_solids':len(s),'all_export_solids_valid':all(q.isValid() for q in s),'overlaps_mm3':{},'intentional_pin_overlaps_mm3':{}}
def common(a,b):
    if not a.BoundBox.intersect(b.BoundBox): return 0.0
    result=a.common(b)
    if not result.isValid(): raise RuntimeError('Invalid intersection result')
    return result.Volume
def moved(q,v):
    c=q.copy(); c.translate(App.Vector(*v)); return c
for i,(ka,a) in enumerate(shapes.items()):
    for kb,b in list(shapes.items())[i+1:]:
        v=common(a,b)
        if v>1e-4: checks['intentional_pin_overlaps_mm3' if 'push_pin' in ka+kb else 'overlaps_mm3'][ka+' / '+kb]=v
checks['laptop_interference_mm3']=sum(common(q,lap) for q in s)
checks['fan_interference_mm3']=sum(common(q,f) for q in s for f in fans)
checks['wall_driver_interference_mm3']={str((x,z)):sum(common(q,Part.makeCylinder(8,180,App.Vector(x,10,z),App.Vector(0,1,0))) for q in s) for x in [-162,162] for z in [-36,174]}
cradles=[q for k,q in shapes.items() if 'cradle' in k]
fixed=[q for k,q in shapes.items() if any(t in k for t in ['cradle','fan_duct','outlet_rail'])]
trays=[q for k,q in shapes.items() if 'fan_tray' in k]
for label,word in [('duct_assembly_from_room','fan_duct'),('rail_assembly_from_room','outlet_rail')]:
    checks[label+'_mm3']=max(sum(common(moved(q,(0,d,0)),c) for k,q in shapes.items() if word in k for c in cradles) for d in [0,1,5,15,40,80])
checks['tray_removal_mm3']=max(sum(common(moved(q,(0,d/math.sqrt(2),d/math.sqrt(2))),c) for q in trays for c in fixed) for d in [0,1,10,40,100,160])
checks['fan_removal_mm3']=max(sum(common(moved(q,(0,d/math.sqrt(2),d/math.sqrt(2))),c) for q in fans for c in fixed+trays) for d in [0,10,50,100,160])
checks['laptop_vertical_lift_mm3']=max(sum(common(q,moved(lap,(0,0,d))) for q in s) for d in [1,30,60,105,150])
checks['lift_then_forward_mm3']=max(sum(common(q,moved(lap,(0,d,105))) for q in s) for d in [0,1,10,40,100])
estimated=Part.read(str(ROOT.parent/'REFERENCE_Estimated_Laptop_Profile.step'))
checks['estimated_profile_interference_mm3']=sum(common(q,estimated) for q in s)
checks['all_checks_pass']=not checks['overlaps_mm3'] and all(v<.01 for k,v in checks.items() if k.endswith('_mm3') and isinstance(v,(int,float))) and all(v<.01 for v in checks['wall_driver_interference_mm3'].values()) and checks['all_export_solids_valid']
checks['limitations']='Discrete source service-path samples; intended crown interference retained. No physical load, adhesive, thermal, retention or printing test.'
(ROOT/'clearance_validation.json').write_text(json.dumps(checks,indent=2))
print(json.dumps(checks,indent=2))
assert checks['all_checks_pass']
