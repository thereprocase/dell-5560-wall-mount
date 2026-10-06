from pathlib import Path
import json,shutil,math
import FreeCAD as A,FreeCADGui as G,Part
ROOT=Path(__file__).resolve().parent
D=next(d for d in A.listDocuments().values() if d.FileName and Path(d.FileName).resolve()==(ROOT/'Precision_5560_Native.FCStd').resolve());A.setActiveDocument(D.Name)
assert not D.getObject('FlowInnerBlend')
D.save();shutil.copy2(D.FileName,ROOT/'BeforeFlowRefinement.FCStd');D.openTransaction('R12 internal airflow blends with R14 wall support')
try:
 source=D.getObject('Compound027');base=source.Links[0];old=base.Shape.copy()
 group=D.addObject('App::DocumentObjectGroup','AirflowRefinement');group.Label='Airflow refinement - tangent bends / reinforced walls'
 def select(shape,points):
  result=[]
  for y,z in points:
   hits=[i for i,e in enumerate(shape.Edges,1) if e.BoundBox.XLength>130 and abs(e.CenterOfMass.y-y)<1e-5 and abs(e.CenterOfMass.z-z)<1e-5]
   assert len(hits)==1,(y,z,hits);result+=hits
  return result
 f=D.addObject('Part::Fillet','FlowOuterSupport');f.Label='Exterior bend support - R14';f.Base=base;f.Edges=[(i,14.,14.) for i in select(old,[(42,-10),(66,-28)])];group.addObject(f);D.recompute()
 g=D.addObject('Part::Fillet','FlowInnerBlend');g.Label='Airway tangent bends - R12';g.Base=f;g.Edges=[(i,12.,12.) for i in select(f.Shape,[(9.4891388813,-78.6649099685),(64.5108611187,-29.3350900315),(40.3291658355,-11.099233003)])];group.addObject(g);source.Links=[g];D.recompute()
 assert not [o.Name for o in D.Objects if 'Invalid' in o.State]
 assert g.Shape.isValid() and len(g.Shape.Solids)==1
 links={o.InstanceKey:o for o in D.getObject('InstalledAssembly').Group if o.TypeId=='App::Link'}
 gaps={}
 for keys in [['04_right_fan_duct','06_right_fan_retainer','10_right_fan_tray'],['03_left_fan_duct','05_left_fan_retainer','09_left_fan_tray']]:
  for i,j in [(0,1),(0,2),(1,2)]:
   gap=links[keys[i]].Shape.distToShape(links[keys[j]].Shape)[0];assert abs(gap-.3)<1e-5;gaps[keys[i]+' / '+keys[j]]=gap
 for key,info in json.loads((ROOT/'frozen_print_arms/manifest.json').read_text())['parts'].items():
  arm=D.getObject(info['source']).Shape;ref=Part.read(str(ROOT/'frozen_print_arms'/info['file']));assert arm.cut(ref).Volume+ref.cut(arm).Volume<1e-6
 change=old.cut(g.Shape).fuse(g.Shape.cut(old));assert change.BoundBox.ZMax<-.1
 inlet=A.Vector(0,-1/math.sqrt(2),1/math.sqrt(2));origin=A.Vector(0,67,-84)
 assert min((v.Point-origin).dot(inlet) for v in change.Vertexes)>10
 report={'revision':'H','native_features':['FlowOuterSupport','FlowInnerBlend'],'internal_radius_mm':12,'external_support_radius_mm':14,'bends_per_duct':3,'unchanged_inlet_and_outlet':True,'gaps_mm':gaps,'frozen_arms_difference_mm3':0,'net_material_change_per_duct_mm3':g.Shape.Volume-old.Volume,'added_to_original_airway_mm3':g.Shape.cut(old).common(D.getObject('Loft001').Shape).Volume,'removed_from_original_wall_mm3':D.getObject('OriginalWallSkin').Shape.cut(g.Shape).Volume}
 P=D.getObject('Parameters')
 for row,label,value,detail in [(78,'Airway tangent radius','12 mm','Native FlowInnerBlend Edges; matched on both ducts'),(79,'Exterior support radius','14 mm','Native FlowOuterSupport Edges; preserves bend wall stock')]:
  assert not P.getContents('A'+str(row)),row
  P.set('A'+str(row),label);P.set('B'+str(row),value);P.set('D'+str(row),detail);P.set('F'+str(row),'Reference');P.setBackground('B'+str(row),(.90,.92,.93))
 for o in group.Group:o.Visibility=False
 base.Visibility=False;D.recompute();D.commitTransaction();D.save();shutil.copy2(D.FileName,ROOT/'FinishValidation.FCStd');(ROOT/'flow_refinement.json').write_text(json.dumps(report,indent=2))
 A._flow_review_visibility={o.Name:o.Visibility for o in links.values()}
 for k,o in links.items():o.Visibility=k=='04_right_fan_duct'
 G.Selection.clearSelection();v=G.activeDocument().mdiViewsOfType('Gui::View3DInventor')[0];v.viewAxonometric();v.fitAll();G.updateGui();v.saveImage(str(ROOT/'flow_refinement.png'),1600,1200,'Current')
 A.Console.PrintMessage('Revision H: R12 tangent airway bends and R14 wall support saved; frozen arms and 0.30 mm fits verified.\n')
except Exception:
 D.abortTransaction();D.recompute();raise
