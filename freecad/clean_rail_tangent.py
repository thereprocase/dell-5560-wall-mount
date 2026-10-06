from pathlib import Path
import json,shutil
import FreeCAD as A,FreeCADGui as G,Part
ROOT=Path(__file__).resolve().parent
D=next(d for d in A.listDocuments().values() if d.FileName and Path(d.FileName).resolve()==(ROOT/'Precision_5560_Native.FCStd').resolve())
D.save();shutil.copy2(D.FileName,ROOT/'BeforeRailTangentCleanup.FCStd');D.openTransaction('Make rail lead-in tangent to rounded arm clearance')
try:
 sk=next(o for o in D.getObject('RailRefinement').Group if o.TypeId=='Sketcher::SketchObject' and 'Assembly lead-in over rear shoulder' in o.Label)
 edited=[]
 for i,c in enumerate(sk.Constraints):
  if c.Type=='DistanceY' and abs(c.Value-6.3)<1e-6:sk.setDatum(i,A.Units.Quantity('6 mm'));edited.append(i)
 assert len(edited)==2,edited
 D.recompute();assert not [o.Name for o in D.Objects if 'Invalid' in o.State]
 links={o.InstanceKey:o for o in D.getObject('InstalledAssembly').Group if o.TypeId=='App::Link'};report={}
 for railkey,armkey in [('08_right_outlet_rail','02_right_cradle'),('07_left_outlet_rail','01_left_cradle')]:
  rail,arm=links[railkey].Shape,links[armkey].Shape
  assert rail.isValid() and len(rail.Solids)==1
  gap=rail.distToShape(arm)[0];assert gap>=.29999,gap
  overlaps=[]
  for dy in [0,.1,.3,1,3,5,10,20,40,60]:
   moved=rail.copy();moved.translate(A.Vector(0,dy,0));overlaps.append(moved.common(arm).Volume)
  assert max(overlaps)<1e-6,overlaps
  report[railkey]={'clearance_mm':gap,'insertion_max_overlap_mm3':max(overlaps),'faces_below_0_1_mm2':sum(f.Area<.1 for f in rail.Faces),'short_edges':sum(e.Length<.05 for e in rail.Edges)}
 assert all(v['faces_below_0_1_mm2']==0 for v in report.values()),report
 for key,info in json.loads((ROOT/'frozen_print_arms/manifest.json').read_text())['parts'].items():
  arm=D.getObject(info['source']).Shape;ref=Part.read(str(ROOT/'frozen_print_arms'/info['file']));assert arm.cut(ref).Volume+ref.cut(arm).Volume<1e-6
 D.commitTransaction();D.save();shutil.copy2(D.FileName,ROOT/'FinishValidation.FCStd')
 (ROOT/'rail_tangent_cleanup.json').write_text(json.dumps(report,indent=2));G.updateGui()
 A.Console.PrintMessage('Rail shoulder tangent cleanup complete; 0.30 mm clearance and insertion samples pass.\n')
except Exception:D.abortTransaction();D.recompute();raise
