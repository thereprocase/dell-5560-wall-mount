from pathlib import Path
import sys,json
import FreeCAD as A,Part
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,A.getResourceDir()+'Mod/Assembly')
d=A.openDocument(str(ROOT/'RailValidation.FCStd'))
o=next(o for o in d.Objects if o.TypeId!='App::Link' and getattr(o,'PartKey','')=='08_right_outlet_rail')
s=o.Shape
edges=[e for e in s.Edges if abs(e.BoundBox.YMin)<1e-6 and abs(e.BoundBox.YMax)<1e-6 and abs(e.BoundBox.ZMin-184.3)<1e-6 and abs(e.BoundBox.ZMax-184.3)<1e-6 and e.BoundBox.XMin>179.9]
t=s.makeFillet(2,edges)
print(json.dumps({'edges':len(edges),'valid':t.isValid(),'solids':len(t.Solids),'removed':s.Volume-t.Volume}),flush=True)
A.closeDocument(d.Name)
