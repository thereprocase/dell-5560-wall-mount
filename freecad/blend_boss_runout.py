from pathlib import Path
import json,math,shutil
import FreeCAD as A,FreeCADGui as G,Part,Sketcher
ROOT=Path(__file__).resolve().parent
D=next(d for d in A.listDocuments().values() if d.FileName and Path(d.FileName).resolve()==(ROOT/'Precision_5560_Native.FCStd').resolve())
assert not D.getObject('BossRunout')
D.save();shutil.copy2(D.FileName,ROOT/'BeforeBossRunout.FCStd')
D.openTransaction('Blend duct corner relief into printable 45 degree runout')
try:
 group=D.addObject('App::DocumentObjectGroup','BossRunout');group.Label='Duct corner relief - 45 degree runout'
 p=A.Placement(A.Vector(0,67,-84),A.Rotation(A.Vector(1,0,0),45)).multiply(A.Placement(A.Vector(0,-70,104),A.Rotation()))
 tools=[]
 for left in [True,False]:
  pts=[(1,-101),(1,-97),(5,-97)] if left else [(136,-97),(140,-97),(140,-101)]
  a,b=(math.pi/2,math.pi) if left else (0,math.pi/2)
  arc=Part.ArcOfCircle(Part.Circle(A.Vector(5 if left else 136,-101,0),A.Vector(0,0,1),4),a,b)
  sketch=D.addObject('Sketcher::SketchObject','RunoutProfile');group.addObject(sketch);sketch.Label='R4 inlet corner runout profile'
  sketch.Placement=p.multiply(A.Placement(A.Vector(0,121.01,0),A.Rotation(A.Vector(1,0,0),90)))
  for g in [Part.LineSegment(A.Vector(*pts[0],0),A.Vector(*pts[1],0)),Part.LineSegment(A.Vector(*pts[1],0),A.Vector(*pts[2],0)),arc]:
   i=sketch.addGeometry(g,False);sketch.addConstraint(Sketcher.Constraint('Block',i))
  ext=D.addObject('Part::Extrusion','RunoutRelief');group.addObject(ext);ext.Base=sketch;ext.DirMode='Custom';ext.Dir=p.Rotation.multVec(A.Vector(0,-1,1));ext.LengthFwd=4.02*math.sqrt(2);ext.Solid=True;tools.append(ext)
 source=next(o for o in D.Objects if o.TypeId!='App::Link' and getattr(o,'PartKey','')=='04_right_fan_duct')
 old=source.Shape.copy()
 tool=D.addObject('Part::Compound','RunoutTools');group.addObject(tool);tool.Links=tools
 cut=D.addObject('Part::Cut','BlendedDuctCorners');group.addObject(cut);cut.Base=source.Links[0];cut.Tool=tool;cut.Refine=True;source.Links=[cut]
 D.recompute()
 removed=old.cut(source.Shape)
 trial=json.loads((ROOT/'boss_runout_trial.json').read_text())
 assert abs(removed.Volume-trial['removed_mm3'])<1e-5,(removed.Volume,trial)
 assert not [o.Name for o in D.Objects if 'Invalid' in o.State]
 for key,info in json.loads((ROOT/'frozen_print_arms/manifest.json').read_text())['parts'].items():
  arm=D.getObject(info['source']).Shape;ref=Part.read(str(ROOT/'frozen_print_arms'/info['file']))
  assert abs(arm.cut(ref).Volume)+abs(ref.cut(arm).Volume)<1e-6
 ducts={}
 for o in D.getObject('InstalledAssembly').Group:
  if o.TypeId=='App::Link' and 'fan_duct' in o.InstanceKey:
   assert o.Shape.isValid() and len(o.Shape.Solids)==1;ducts[o.InstanceKey]=o.Shape.Volume
 assert abs(ducts['03_left_fan_duct']-ducts['04_right_fan_duct'])<1e-5
 for o in group.Group:o.Visibility=False
 D.commitTransaction();D.save();shutil.copy2(D.FileName,ROOT/'FinishValidation.FCStd')
 (ROOT/'boss_runout_build.json').write_text(json.dumps({'status':'done','removed_per_duct_mm3':removed.Volume,'ducts':ducts,'arms_difference_mm3':0,'recomputes':1},indent=2))
 G.updateGui();A.Console.PrintMessage('Duct corner runouts complete; mirrored ducts valid, frozen arms unchanged.\n')
except Exception:D.abortTransaction();raise
