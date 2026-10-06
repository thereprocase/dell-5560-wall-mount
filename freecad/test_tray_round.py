from pathlib import Path
import sys,json
import FreeCAD as A,Part
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,A.getResourceDir()+'Mod/Assembly')
d=A.openDocument(str(ROOT/'RailValidation.FCStd'))
o=next(o for o in d.Objects if o.TypeId!='App::Link' and getattr(o,'PartKey','')=='10_right_fan_tray')
# Inverse of the source fan-plane installation transform.
p=A.Placement(A.Vector(0,67,-84),A.Rotation(A.Vector(1,0,0),45)).multiply(A.Placement(A.Vector(0,-70,104),A.Rotation()))
s=o.Shape.copy();s.transformShape(p.inverse().toMatrix())
ids=[]
for i,e in enumerate(s.Edges,1):
 b=e.BoundBox
 if abs(b.ZMin+146)<1e-6 and abs(b.ZMax+146)<1e-6 and (abs(b.XMin-1)<1e-6 and abs(b.XMax-1)<1e-6 or abs(b.XMin-140)<1e-6 and abs(b.XMax-140)<1e-6) and b.YLength>5:ids.append(i)
print('EDGES',ids,flush=True)
t=s.makeFillet(4,[s.Edges[i-1] for i in ids]);print(json.dumps({'valid':t.isValid(),'solids':len(t.Solids),'removed':s.Volume-t.Volume}),flush=True)
(ROOT/'tray_round_edges.json').write_text(json.dumps({'edges':ids,'radius':4,'valid':t.isValid(),'solids':len(t.Solids)}),encoding='utf-8')
A.closeDocument(d.Name)
