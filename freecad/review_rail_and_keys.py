from pathlib import Path
import json
import FreeCAD as A,FreeCADGui as G,Part
from PySide import QtCore
ROOT=Path(__file__).resolve().parent
D=next(d for d in A.listDocuments().values() if d.FileName and Path(d.FileName).resolve()==(ROOT/'Precision_5560_Native.FCStd').resolve())
links={o.InstanceKey:o for o in D.getObject('InstalledAssembly').Group if o.TypeId=='App::Link'}
G.Selection.clearSelection();G.Selection.addSelection(links['08_right_outlet_rail']);v=G.activeDocument().mdiViewsOfType('Gui::View3DInventor')[0];v.viewAxonometric();G.runCommand('Std_ViewFitSelection');G.Selection.clearSelection();G.updateGui()
report={}
for side in ['right','left']:
 arm=links['02_right_cradle' if side=='right' else '01_left_cradle'].Shape
 duct=links['04_right_fan_duct' if side=='right' else '03_left_fan_duct'].Shape
 for i,(a,b) in enumerate([(146,154),(167,175)]):
  # Isolate only the male key, away from its bonded shoulder.
  region=Part.makeBox(b-a,12.6,40,A.Vector(a,14,-59))
  if side=='left':region=region.mirror(A.Vector(),A.Vector(1,0,0))
  key=duct.common(region);assert key.Volume>0
  distance=key.distToShape(arm)[0];assert distance>=.29999,distance
  report[side+'_duct_key_'+str(i)]=distance
(ROOT/'fixed_key_fit_audit.json').write_text(json.dumps(report,indent=2))
QtCore.QTimer.singleShot(1200,lambda:v.saveImage(str(ROOT/'fit_review_rail.png'),1400,1000,'Current'))
A.Console.PrintMessage('Reviewing upper rail shoulder. All four frozen-arm duct-key fits retain at least 0.30 mm.\n')
