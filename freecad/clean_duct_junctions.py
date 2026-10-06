from pathlib import Path
import json,shutil
import FreeCAD as A,FreeCADGui as G,Part
ROOT=Path(__file__).resolve().parent
D=next(d for d in A.listDocuments().values() if d.FileName and Path(d.FileName).resolve()==(ROOT/'Precision_5560_Native.FCStd').resolve())
D.save();shutil.copy2(D.FileName,ROOT/'BeforeJunctionCleanup.FCStd');D.openTransaction('Remove duct runout seam slivers')
try:
 p=A.Placement(A.Vector(0,67,-84),A.Rotation(A.Vector(1,0,0),45)).multiply(A.Placement(A.Vector(0,-70,104),A.Rotation()))
 for o in D.getObject('BossRunout').Group:
  if o.TypeId=='Sketcher::SketchObject':o.Placement=p.multiply(A.Placement(A.Vector(0,121,0),A.Rotation(A.Vector(1,0,0),90)))
 D.recompute()
 assert not [o.Name for o in D.Objects if 'Invalid' in o.State]
 report={}
 for o in D.getObject('InstalledAssembly').Group:
  if o.TypeId=='App::Link' and 'fan_duct' in o.InstanceKey:
   assert o.Shape.isValid() and len(o.Shape.Solids)==1
   report[o.InstanceKey]={'faces_below_0_1_mm2':sum(f.Area<.1 for f in o.Shape.Faces),'short_edges_below_0_05_mm':sum(e.Length<.05 for e in o.Shape.Edges)}
 assert all(v['faces_below_0_1_mm2']==0 for v in report.values()),report
 D.commitTransaction();D.save();shutil.copy2(D.FileName,ROOT/'FinishValidation.FCStd')
 (ROOT/'junction_cleanup.json').write_text(json.dumps(report,indent=2));G.updateGui()
 A.Console.PrintMessage('Duct seam cleanup: no faces below 0.1 mm2 remain.\n')
except Exception:D.abortTransaction();D.recompute();raise
