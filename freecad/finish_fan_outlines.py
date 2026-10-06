"""Batched FDM-aware cover outline finish; no arm edits."""
from pathlib import Path
import json,math,shutil
import FreeCAD as A,FreeCADGui as G,Part,Sketcher
ROOT=Path(__file__).resolve().parent
D=next(d for d in A.listDocuments().values() if d.FileName and Path(d.FileName).resolve()==(ROOT/'Precision_5560_Native.FCStd').resolve());A.setActiveDocument(D.Name)
if D.getObject('FanOutlineFinish'):raise RuntimeError('Outline finish already present')
D.save();shutil.copy2(D.FileName,ROOT/'BeforeFanFinish.FCStd')
D.openTransaction('Match fan cover outlines with FDM-friendly backing edges')
try:
 group=D.addObject('App::DocumentObjectGroup','FanOutlineFinish');group.Label='Fan modules - matched outlines and print-safe edges'
 p=A.Placement(A.Vector(0,67,-84),A.Rotation(A.Vector(1,0,0),45)).multiply(A.Placement(A.Vector(0,-70,104),A.Rotation()))
 def sketch(label,geometry,y):
  s=D.addObject('Sketcher::SketchObject','FinishProfile');s.Label=label;group.addObject(s)
  s.Placement=p.multiply(A.Placement(A.Vector(0,y,0),A.Rotation(A.Vector(1,0,0),90)))
  for g in geometry:
   i=s.addGeometry(g,False);s.addConstraint(Sketcher.Constraint('Block',i))
  return s
 def lines(points):return [Part.LineSegment(A.Vector(*points[i],0),A.Vector(*points[(i+1)%len(points)],0)) for i in range(len(points))]
 def extrude(s,n):
  o=D.addObject('Part::Extrusion','OutlineRelief');o.Base=s;o.DirMode='Normal';o.LengthFwd=n;o.Solid=True;group.addObject(o);return o
 tray_tools=[]
 for points in [[(1,-146),(5,-146),(1,-142)],[(136,-146),(140,-146),(140,-142)]]:
  tray_tools.append(extrude(sketch('45 degree tray bed-edge relief',lines(points),137),134))
 boss_tools=[]
 for left in [True,False]:
  if left:
   points=[(1,-101),(1,-97),(5,-97)]
   arc=Part.ArcOfCircle(Part.Circle(A.Vector(5,-101,0),A.Vector(0,0,1),4),math.pi/2,math.pi)
  else:
   points=[(136,-97),(140,-97),(140,-101)]
   arc=Part.ArcOfCircle(Part.Circle(A.Vector(136,-101,0),A.Vector(0,0,1),4),0,math.pi/2)
  g=[Part.LineSegment(A.Vector(*points[0],0),A.Vector(*points[1],0)),Part.LineSegment(A.Vector(*points[1],0),A.Vector(*points[2],0)),arc]
  boss_tools.append(extrude(sketch('R4 cover-matched upper boss relief',g,137),16))
 for key,tools in [('10_right_fan_tray',tray_tools),('04_right_fan_duct',boss_tools)]:
  source=next(o for o in D.Objects if o.TypeId!='App::Link' and getattr(o,'PartKey','')==key)
  tool=D.addObject('Part::Compound','PairedReliefs');tool.Links=tools;group.addObject(tool)
  cut=D.addObject('Part::Cut','MatchedOutline');cut.Label=key+' - matched cover outline';cut.Base=source.Links[0];cut.Tool=tool;cut.Refine=True;group.addObject(cut);source.Links=[cut]
 # One recompute for both complete feature chains and their existing mirrors.
 D.recompute()
 errors=[o.Name for o in D.Objects if 'Invalid' in o.State];assert not errors,errors
 assert all(o.FullyConstrained for o in group.Group if o.TypeId=='Sketcher::SketchObject')
 checks={}
 for key,info in json.loads((ROOT/'frozen_print_arms/manifest.json').read_text())['parts'].items():
  a=D.getObject(info['source']).Shape;b=Part.read(str(ROOT/'frozen_print_arms'/info['file']));ab=a.cut(b);ba=b.cut(a)
  assert ab.isValid() and ba.isValid() and abs(ab.Volume)+abs(ba.Volume)<1e-6;checks[key]=0
 for o in group.Group:o.Visibility=False
 for o in D.getObject('InstalledAssembly').Group:
  if o.TypeId=='App::Link':assert o.Shape.isValid() and len(o.Shape.Solids)==1
 D.commitTransaction();D.save();shutil.copy2(D.FileName,ROOT/'FinishValidation.FCStd')
 (ROOT/'fan_finish_build.json').write_text(json.dumps({'status':'done','arms_difference':checks,'new_sketches':4,'recomputes':1}),encoding='utf-8')
 G.updateGui();A.Console.PrintMessage('Fan outlines finished in one recompute; arms unchanged.\n')
except Exception:D.abortTransaction();raise
