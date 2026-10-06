from pathlib import Path
import json,shutil,math
import FreeCAD as A,FreeCADGui as G,Part
from PySide import QtCore
ROOT=Path(__file__).resolve().parent
D=next(d for d in A.listDocuments().values() if d.FileName and Path(d.FileName).resolve()==(ROOT/'Precision_5560_Native.FCStd').resolve());A.setActiveDocument(D.Name)
assert not D.getObject('DuctWallProtection')
links={o.InstanceKey:o for o in D.getObject('InstalledAssembly').Group if o.TypeId=='App::Link'}
G.Selection.clearSelection();v=G.activeDocument().mdiViewsOfType('Gui::View3DInventor')[0]
q=A.Rotation(.4247082,.1759199,.3398511,.8204732);center=A.Vector(137,104,-41);node=v.getCameraNode();distance=95
position=center+q.multVec(A.Vector(0,0,distance));node.orientation.setValue(*q.Q);node.position.setValue(position.x,position.y,position.z);node.focalDistance.setValue(distance);node.nearDistance.setValue(.1);node.farDistance.setValue(3000);G.updateGui()
D.save();shutil.copy2(D.FileName,ROOT/'BeforeDuctWallProtection.FCStd');D.openTransaction('Protect continuous duct wall from cosmetic corner cuts')
try:
 source=D.getObject('Compound027');shell=D.getObject('Cut016')
 assert source.PartKey=='04_right_fan_duct' and 'shell' in shell.Label.lower()
 before=source.Shape.copy();original_wall=shell.Shape.common(D.getObject('MatchedOutline001').Base.Shape);missing_before=original_wall.cut(before)
 group=D.addObject('App::DocumentObjectGroup','DuctWallProtection');group.Label='Continuous duct skin - protected from corner reliefs'
 for cutname in ['MatchedOutline001','BlendedDuctCorners']:
  feature=D.getObject(cutname);protected=D.addObject('Part::Cut','ReliefOutsideWall');protected.Label='Corner relief restricted outside original duct skin';protected.Base=feature.Tool;protected.Tool=shell;protected.Refine=True;group.addObject(protected);feature.Tool=protected
 D.recompute();assert not [o.Name for o in D.Objects if 'Invalid' in o.State]
 after=source.Shape;missing_after=original_wall.cut(after)
 assert after.isValid() and len(after.Solids)==1
 assert missing_after.Volume<1e-6,missing_after.Volume
 report={'reference':'Original duct skin excluding the pre-existing socket intersection','missing_wall_before_mm3':missing_before.Volume,'missing_wall_after_mm3':missing_after.Volume,'restored_material_per_duct_mm3':after.cut(before).Volume,'gaps_mm':{},'arms_difference_mm3':{}}
 for left in [False,True]:
  keys=['03_left_fan_duct','05_left_fan_retainer','09_left_fan_tray'] if left else ['04_right_fan_duct','06_right_fan_retainer','10_right_fan_tray']
  for k in keys:assert links[k].Shape.isValid() and len(links[k].Shape.Solids)==1
  for i,j in [(0,1),(0,2),(1,2)]:
   gap=links[keys[i]].Shape.distToShape(links[keys[j]].Shape)[0];assert abs(gap-.3)<1e-5,(keys,gap);report['gaps_mm'][keys[i]+' / '+keys[j]]=gap
 for key,info in json.loads((ROOT/'frozen_print_arms/manifest.json').read_text())['parts'].items():
  arm=D.getObject(info['source']).Shape;ref=Part.read(str(ROOT/'frozen_print_arms'/info['file']));delta=arm.cut(ref).Volume+ref.cut(arm).Volume;assert delta<1e-6;report['arms_difference_mm3'][key]=delta
 for o in group.Group:o.Visibility=False
 D.commitTransaction();D.save();shutil.copy2(D.FileName,ROOT/'FinishValidation.FCStd')
 (ROOT/'duct_wall_protection.json').write_text(json.dumps(report,indent=2))
 G.updateGui();QtCore.QTimer.singleShot(1200,lambda:v.saveImage(str(ROOT/'duct_wall_protected.png'),1400,1000,'Current'))
 A.Console.PrintMessage('Original duct skin restored on both sides; zero additional missing wall volume and 0.30 mm fits verified.\n')
except Exception:D.abortTransaction();D.recompute();raise
