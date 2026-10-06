from pathlib import Path
import sys,json
import FreeCAD as A,Part
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,A.getResourceDir()+'Mod/Assembly')
d=A.openDocument(str(ROOT/'RailValidation.FCStd'))
o=next(o for o in d.Objects if o.TypeId!='App::Link' and getattr(o,'PartKey','')=='08_right_outlet_rail')
for i,e in enumerate(o.Shape.Edges,1):
 b=e.BoundBox
 if b.XMin>179.9 and b.ZMin>179 and b.ZMax<189:
  print(i,e.Length,str(b),flush=True)
A.closeDocument(d.Name)
