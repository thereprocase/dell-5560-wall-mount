from pathlib import Path
import sys,json,math
import FreeCAD as A,Part
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,A.getResourceDir()+'Mod/Assembly')
d=A.openDocument(str(ROOT/'FinishValidation.FCStd'))
p=A.Placement(A.Vector(0,67,-84),A.Rotation(A.Vector(1,0,0),45)).multiply(A.Placement(A.Vector(0,-70,104),A.Rotation()))
source=next(o for o in d.Objects if o.TypeId!='App::Link' and getattr(o,'PartKey','')=='04_right_fan_duct')
tools=[]
for x,left in [(1,True),(140,False)]:
 pts=[(1,-101),(1,-97),(5,-97)] if left else [(136,-97),(140,-97),(140,-101)]
 a,b=(math.pi/2,math.pi) if left else (0,math.pi/2)
 arc=Part.ArcOfCircle(Part.Circle(A.Vector(5 if left else 136,-101,0),A.Vector(0,0,1),4),a,b).toShape()
 edges=[Part.makeLine(A.Vector(*pts[0],0),A.Vector(*pts[1],0)),Part.makeLine(A.Vector(*pts[1],0),A.Vector(*pts[2],0)),arc]
 face=Part.Face(Part.Wire(edges));face.Placement=p.multiply(A.Placement(A.Vector(0,121.01,0),A.Rotation(A.Vector(1,0,0),90)))
 tool=face.extrude(p.Rotation.multVec(A.Vector(0,-4.02,4.02)));tools.append(tool)
tool=Part.makeCompound(tools);new=source.Shape.cut(tool).removeSplitter();removed=source.Shape.cut(new)
checks={'removed_mm3':removed.Volume,'valid':new.isValid(),'solids':len(new.Solids),'socket_envelope_removed_mm3':0}
for x in [5,135]:
 env=Part.makeCylinder(3.25,14,A.Vector(x,122,-103),A.Vector(0,1,0));env.Placement=p
 checks['socket_envelope_removed_mm3']+=env.common(removed).Volume
print(json.dumps(checks),flush=True)
(ROOT/'boss_runout_trial.json').write_text(json.dumps(checks,indent=2))
assert new.isValid() and len(new.Solids)==1 and checks['socket_envelope_removed_mm3']<1e-6
A.closeDocument(d.Name)
