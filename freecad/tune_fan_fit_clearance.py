from pathlib import Path
import json,math,shutil
import FreeCAD as A,FreeCADGui as G,Part,Sketcher
ROOT=Path(__file__).resolve().parent
D=next(d for d in A.listDocuments().values() if d.FileName and Path(d.FileName).resolve()==(ROOT/'Precision_5560_Native.FCStd').resolve())
assert not D.getObject('FanFitClearance')
D.save();shutil.copy2(D.FileName,ROOT/'BeforeFanFitClearance.FCStd');D.openTransaction('Set fan interface clearances to 0.30 mm')
try:
 group=D.addObject('App::DocumentObjectGroup','FanFitClearance');group.Label='Fan fit-up - 0.30 mm normal clearance'
 p=A.Placement(A.Vector(0,67,-84),A.Rotation(A.Vector(1,0,0),45)).multiply(A.Placement(A.Vector(0,-70,104),A.Rotation()))
 def profile(label,pts,y,length):
  sketch=D.addObject('Sketcher::SketchObject','FitProfile');sketch.Label=label;group.addObject(sketch)
  sketch.Placement=p.multiply(A.Placement(A.Vector(0,y,0),A.Rotation(A.Vector(1,0,0),90)))
  for i,pt in enumerate(pts):
   j=sketch.addGeometry(Part.LineSegment(A.Vector(*pt,0),A.Vector(*pts[(i+1)%len(pts)],0)),False);sketch.addConstraint(Sketcher.Constraint('Block',j))
  ext=D.addObject('Part::Extrusion','FitRelief');ext.Base=sketch;ext.DirMode='Normal';ext.LengthFwd=length;ext.Solid=True;group.addObject(ext);return ext
 front=profile('Cover seam clearance - 0.30 mm',[(-1,-150),(142,-150),(142,-90),(-1,-90)],137,1.3)
 underside=profile('Tray sliding rim clearance - 0.30 mm',[(-1,-110.5),(142,-110.5),(142,-109.7),(-1,-109.7)],137,134)
 off=.3*math.sqrt(1+(1.5/2.1)**2);bottom=1.5+off-.3*1.5/2.1;top=3+off
 grooves=[]
 for cx in [5,135]:
  pts=[(cx-bottom,-110.4),(cx+bottom,-110.4),(cx+top,-108),(cx+top,-107.7),(cx-top,-107.7),(cx-top,-108)]
  grooves.append(profile('Dovetail groove - 0.30 mm normal flank clearance',pts,137,128.3))
 for key,tools in [('04_right_fan_duct',[front,underside]+grooves),('10_right_fan_tray',[front])]:
  source=next(o for o in D.Objects if o.TypeId!='App::Link' and getattr(o,'PartKey','')==key)
  tool=D.addObject('Part::Compound','FitTools');tool.Links=tools;group.addObject(tool)
  cut=D.addObject('Part::Cut','ClearancedFanPart');cut.Base=source.Links[0];cut.Tool=tool;cut.Refine=True;group.addObject(cut);source.Links=[cut]
 D.recompute()
 assert not [o.Name for o in D.Objects if 'Invalid' in o.State]
 links={o.InstanceKey:o for o in D.getObject('InstalledAssembly').Group if o.TypeId=='App::Link'}
 report={}
 for side in ['right','left']:
  keys= ['04_right_fan_duct','06_right_fan_retainer','10_right_fan_tray'] if side=='right' else ['03_left_fan_duct','05_left_fan_retainer','09_left_fan_tray']
  for key in keys:assert links[key].Shape.isValid() and len(links[key].Shape.Solids)==1,key
  for i,j in [(0,1),(0,2),(1,2)]:
   distance=links[keys[i]].Shape.distToShape(links[keys[j]].Shape)[0];report[keys[i]+' / '+keys[j]]=distance
   assert distance>=.29999,(keys[i],keys[j],distance)
 for key,info in json.loads((ROOT/'frozen_print_arms/manifest.json').read_text())['parts'].items():
  arm=D.getObject(info['source']).Shape;ref=Part.read(str(ROOT/'frozen_print_arms'/info['file']))
  assert abs(arm.cut(ref).Volume)+abs(ref.cut(arm).Volume)<1e-6
 for o in group.Group:o.Visibility=False
 D.commitTransaction();D.save();shutil.copy2(D.FileName,ROOT/'FinishValidation.FCStd')
 (ROOT/'fan_fit_clearance.json').write_text(json.dumps({'status':'done','minimum_clearance_mm':report,'arms_difference_mm3':0,'recomputes':1,'flank_normal_offset_mm':.3},indent=2))
 G.Selection.clearSelection();G.updateGui();A.Console.PrintMessage('Fan fit-up clearances verified at 0.30 mm on both sides.\n')
except Exception:D.abortTransaction();D.recompute();raise
