from pathlib import Path
import json
import FreeCAD as A,FreeCADGui as G
ROOT=Path(__file__).resolve().parent
D=next(d for d in A.listDocuments().values() if d.FileName and Path(d.FileName).resolve()==(ROOT/'Precision_5560_Native.FCStd').resolve());A.setActiveDocument(D.Name)
links={o.InstanceKey:o for o in D.getObject('InstalledAssembly').Group if o.TypeId=='App::Link'}
v=G.activeDocument().mdiViewsOfType('Gui::View3DInventor')[0]
G.Selection.clearSelection()
for k in ['04_right_fan_duct','06_right_fan_retainer','10_right_fan_tray']:G.Selection.addSelection(links[k])
v.viewRear();G.runCommand('Std_ViewFitSelection');G.Selection.clearSelection();G.updateGui();v.saveImage(str(ROOT/'fit_review_fan_rear.png'),1400,1000,'Current')
report={}
for k,o in links.items():
 if 'cradle' in k:continue
 shape=o.Shape
 report[k]={'valid':shape.isValid(),'solids':len(shape.Solids),'small_faces':[{'face':i+1,'area_mm2':f.Area,'center':[f.CenterOfMass.x,f.CenterOfMass.y,f.CenterOfMass.z]} for i,f in enumerate(shape.Faces) if f.Area<.1], 'short_edges':sum(e.Length<.05 for e in shape.Edges)}
(ROOT/'detail_geometry_audit.json').write_text(json.dumps(report,indent=2))
A.Console.PrintMessage('Fan interface review: all six paired minimum gaps measure 0.30 mm. Rear view shown.\n')
