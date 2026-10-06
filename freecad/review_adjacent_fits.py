from pathlib import Path
import json,math
import FreeCAD as A,FreeCADGui as G,Part
ROOT=Path(__file__).resolve().parent
D=next(d for d in A.listDocuments().values() if d.FileName and Path(d.FileName).resolve()==(ROOT/'Precision_5560_Native.FCStd').resolve());A.setActiveDocument(D.Name)
links={o.InstanceKey:o for o in D.getObject('InstalledAssembly').Group if o.TypeId=='App::Link'}
G.Selection.clearSelection()
for k in ['04_right_fan_duct','06_right_fan_retainer','10_right_fan_tray']:G.Selection.addSelection(links[k])
v=G.activeDocument().mdiViewsOfType('Gui::View3DInventor')[0];v.viewAxonometric();G.runCommand('Std_ViewFitSelection');G.updateGui()
p=A.Placement(A.Vector(0,67,-84),A.Rotation(A.Vector(1,0,0),45)).multiply(A.Placement(A.Vector(0,-70,104),A.Rotation()))
report=[]
for ka,kb in [('04_right_fan_duct','06_right_fan_retainer'),('04_right_fan_duct','10_right_fan_tray'),('06_right_fan_retainer','10_right_fan_tray'),('04_right_fan_duct','02_right_cradle'),('08_right_outlet_rail','02_right_cradle')]:
 a,b=links[ka].Shape,links[kb].Shape
 distance,points,info=a.distToShape(b);common=a.common(b)
 report.append({'parts':[ka,kb],'distance_mm':distance,'common_volume_mm3':common.Volume,'common_area_mm2':common.Area,'closest_points_local':[[[round(t,5) for t in p.inverse().multVec(x)] for x in pair] for pair in points[:12]]})
(ROOT/'adjacent_fit_audit.json').write_text(json.dumps(report,indent=2))
A.Console.PrintMessage('Live interface review: right fan cap, duct and tray. Fit measurements recorded.\n')
