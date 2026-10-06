from pathlib import Path
import sys,json
import FreeCAD as A,Part
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,A.getResourceDir()+'Mod/Assembly')
d=A.openDocument(str(ROOT/'RailValidation.FCStd'))
p=A.Placement(A.Vector(0,67,-84),A.Rotation(A.Vector(1,0,0),45)).multiply(A.Placement(A.Vector(0,-70,104),A.Rotation()))
report={}
for key in ['04_right_fan_duct','06_right_fan_retainer','10_right_fan_tray']:
 o=next(o for o in d.Objects if o.TypeId!='App::Link' and getattr(o,'PartKey','')==key);s=o.Shape.copy();s.transformShape(p.inverse().toMatrix());info={'bounds':str(s.BoundBox),'corner_edges':[]}
 for i,e in enumerate(s.Edges,1):
  b=e.BoundBox
  if (abs(b.XMin-1)<1e-5 and abs(b.XMax-1)<1e-5 or abs(b.XMin-140)<1e-5 and abs(b.XMax-140)<1e-5) and b.YLength>2 and b.ZLength<1e-6:
   info['corner_edges'].append({'i':i,'bounds':str(b),'z':b.ZMin})
 if key=='04_right_fan_duct':
  ids=[e['i'] for e in info['corner_edges'] if abs(e['z']+97)<1e-5]
  try:
   t=s.makeFillet(4,[s.Edges[i-1] for i in ids]);info['test']={'ids':ids,'valid':t.isValid(),'solids':len(t.Solids),'removed':s.Volume-t.Volume}
  except Exception as ex:info['test']={'error':str(ex),'ids':ids}
 report[key]=info
(ROOT/'finish_audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report),flush=True)
A.closeDocument(d.Name)
