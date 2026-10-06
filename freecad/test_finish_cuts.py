from pathlib import Path
import sys,json
import FreeCAD as A,Part
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,A.getResourceDir()+'Mod/Assembly')
d=A.openDocument(str(ROOT/'RailValidation.FCStd'))
p=A.Placement(A.Vector(0,67,-84),A.Rotation(A.Vector(1,0,0),45)).multiply(A.Placement(A.Vector(0,-70,104),A.Rotation()))
report={}
for key in ['04_right_fan_duct','10_right_fan_tray']:
 o=next(o for o in d.Objects if o.TypeId!='App::Link' and getattr(o,'PartKey','')==key);s=o.Shape.copy();s.transformShape(p.inverse().toMatrix())
 cuts=[]
 if 'tray' in key:
  for pts in [[(1,-146),(5,-146),(1,-142)],[(136,-146),(140,-146),(140,-142)]]:
   wire=Part.makePolygon([A.Vector(x,3,z) for x,z in pts+[pts[0]]]);cuts.append(Part.Face(wire).extrude(A.Vector(0,134,0)))
 else:
  for x,cx in [(1,5),(136,136)]:
   box=Part.makeBox(4,16,4,A.Vector(x,121,-101));cyl=Part.makeCylinder(4,16,A.Vector(cx,121,-101),A.Vector(0,1,0));cuts.append(box.cut(cyl))
 t=s.cut(Part.makeCompound(cuts)).removeSplitter()
 entry={'valid':t.isValid(),'solids':len(t.Solids),'removed_volume':s.Volume-t.Volume}
 if 'duct' in key:
  entry['socket_support_removed']=sum(s.cut(t).common(Part.makeCylinder(3.25,8,A.Vector(x,128,-103),A.Vector(0,1,0))).Volume for x in [5,135])
 report[key]=entry
print(json.dumps(report),flush=True);(ROOT/'finish_cut_validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8');A.closeDocument(d.Name)
