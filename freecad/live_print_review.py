from pathlib import Path
import json,math
import FreeCAD as A,FreeCADGui as G
from PySide import QtCore
ROOT=Path(__file__).resolve().parent
D=next(d for d in A.listDocuments().values() if d.FileName and Path(d.FileName).resolve()==(ROOT/'Precision_5560_Native.FCStd').resolve())
links={o.InstanceKey:o for o in D.getObject('InstalledAssembly').Group if o.TypeId=='App::Link'}
v=G.activeDocument().mdiViewsOfType('Gui::View3DInventor')[0]
original={k:o.Visibility for k,o in links.items()};camera=v.getCamera()
p=A.Rotation(A.Vector(1,0,0),45);iso=A.Rotation(.4247082,.1759199,.3398511,.8204732)
stages=[('04_right_fan_duct','Duct: inlet-down print review',p),('10_right_fan_tray','Tray: grille-down print review',p),('06_right_fan_retainer','Cap: front-face-down print review',p.multiply(A.Rotation(A.Vector(1,0,0),90))),('08_right_outlet_rail','Rail: lip-down print review',A.Rotation(A.Vector(1,0,0),180)),('12_right_push_pin','Pin: button-down print review',p.multiply(A.Rotation(A.Vector(1,0,0),90)))]
state={'index':0};timer=QtCore.QTimer();timer.setInterval(6500);A._fit_review_timer=timer
report={}
def show():
 i=state['index']
 if i>=len(stages):
  timer.stop()
  for k,o in links.items():o.Visibility=original[k]
  v.setCamera(camera);G.updateGui()
  (ROOT/'print_view_review.json').write_text(json.dumps(report,indent=2))
  A.Console.PrintMessage('Print orientation review finished; assembly visibility restored.\n');return
 key,label,rot=stages[i];state['index']+=1
 for k,o in links.items():o.Visibility=(k==key)
 G.Selection.clearSelection()
 q=rot.multiply(iso);cam=v.getCameraOrientation();node=v.getCameraNode();shape=links[key].Shape;box=shape.BoundBox
 center=box.Center;radius=box.DiagonalLength/2;angle=float(node.heightAngle.getValue()) if hasattr(node,'heightAngle') else .5
 distance=radius/math.sin(angle/2)*1.12;position=center+q.multVec(A.Vector(0,0,distance))
 node.orientation.setValue(*q.Q);node.position.setValue(position.x,position.y,position.z);node.focalDistance.setValue(distance)
 node.nearDistance.setValue(max(.01,distance-radius*2));node.farDistance.setValue(distance+radius*2)
 if hasattr(node,'height'):node.height.setValue(radius*2.3)
 G.updateGui()
 shape=links[key].Shape;report[key]={'valid':shape.isValid(),'single_solid':len(shape.Solids)==1,'small_faces':sum(f.Area<.1 for f in shape.Faces),'short_edges':sum(e.Length<.05 for e in shape.Edges),'view':label}
 A.Console.PrintMessage(label+'\n')
 QtCore.QTimer.singleShot(1200,lambda k=key:v.saveImage(str(ROOT/('review_'+k+'.png')),1400,1000,'Current'))
timer.timeout.connect(show);show();timer.start()
