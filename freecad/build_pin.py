from pathlib import Path
import json, math, time
import FreeCAD as App, Part, Sketcher
import FreeCADGui as Gui
ROOT = Path(__file__).resolve().parent
D = App.ActiveDocument or App.newDocument('Precision5560Native')
D.Label = 'Precision 5560 — native FreeCAD rebuild'
if D.getObject('PinBody'):
    raise RuntimeError('Pin already exists; refusing duplicate build')
P = D.addObject('Spreadsheet::Sheet', 'Parameters')
P.Label = 'Design parameters (mm)'
rows = [('pinSocketDiameter',4.1),('pinShaftDiametralClearance',.1),
        ('pinCrownDiametralInterference',.1),('pinHeadDiameter',8),
        ('pinHeadHeight',2),('pinHeadChamfer',.6),('pinShaftLength',10),
        ('pinCrownHeight',2),('pinTipDiameter',3.2),('pinSplitWidth',1),
        ('pinSplitStart',4),('outletGap',12)]
for i,(name,value) in enumerate(rows,1):
    P.set('A'+str(i),name); P.set('B'+str(i),str(value)+' mm'); P.setAlias('B'+str(i),name)
P.setColumnWidth('A',240)
D.recompute()
b = D.addObject('PartDesign::Body','PinBody'); b.Label = 'Push pin — master'
def stage(obj):
    D.recompute()
    if hasattr(obj,'Shape') and (obj.Shape.isNull() or not obj.Shape.isValid()):
        raise RuntimeError('Invalid stage: '+obj.Name)
    Gui.activeDocument().activeView().viewAxonometric(); Gui.activeDocument().activeView().fitAll()
    Gui.updateGui()
    App.Console.PrintMessage('Built '+obj.Label+'\n')
    time.sleep(.15)
def circle(name,z,diam,expression):
    s=D.addObject('Sketcher::SketchObject',name); b.addObject(s)
    s.Placement.Base.z=z
    s.addGeometry(Part.Circle(App.Vector(),App.Vector(0,0,1),diam/2),False)
    s.addConstraint(Sketcher.Constraint('Coincident',0,3,-1,1))
    c=s.addConstraint(Sketcher.Constraint('Diameter',0,diam))
    s.setExpression('Constraints['+str(c)+']',expression)
    D.recompute(); return s
s=circle('PinButtonProfile',0,8,'Parameters.pinHeadDiameter')
p=b.newObject('PartDesign::Pad','PinButton'); p.Profile=s
p.setExpression('Length','Parameters.pinHeadHeight'); stage(p); s.Visibility=False
ch=b.newObject('PartDesign::Chamfer','PinButtonChamfer')
edge=['Edge'+str(i+1) for i,e in enumerate(p.Shape.Edges) if abs(e.CenterOfMass.z-2)<1e-6 and e.Length>20]
ch.Base=(p,edge); ch.setExpression('Size','Parameters.pinHeadChamfer'); stage(ch); p.Visibility=False
s=circle('PinShaftProfile',2,4,'Parameters.pinSocketDiameter - Parameters.pinShaftDiametralClearance')
s.setExpression('Placement.Base.z','Parameters.pinHeadHeight')
p=b.newObject('PartDesign::Pad','PinShaft'); p.Profile=s; p.setExpression('Length','Parameters.pinShaftLength'); stage(p); ch.Visibility=False; s.Visibility=False
s0=circle('PinCrownRoot',12,4.2,'Parameters.pinSocketDiameter + Parameters.pinCrownDiametralInterference')
s0.setExpression('Placement.Base.z','Parameters.pinHeadHeight + Parameters.pinShaftLength')
s1=circle('PinCrownTip',14,3.2,'Parameters.pinTipDiameter')
s1.setExpression('Placement.Base.z','Parameters.pinHeadHeight + Parameters.pinShaftLength + Parameters.pinCrownHeight')
l=b.newObject('PartDesign::AdditiveLoft','PinCrown'); l.Profile=s0; l.Sections=[s1]; l.Ruled=True; stage(l); p.Visibility=False; s0.Visibility=False; s1.Visibility=False
s=D.addObject('Sketcher::SketchObject','PinSplitProfile'); b.addObject(s)
s.Placement.Base.z=14.1
s.setExpression('Placement.Base.z','Parameters.pinHeadHeight + Parameters.pinShaftLength + Parameters.pinCrownHeight + 0.1 mm')
pts=[(-.5,-3),(.5,-3),(.5,3),(-.5,3)]
for i in range(4):
    a=pts[i]; q=pts[(i+1)%4]; s.addGeometry(Part.LineSegment(App.Vector(*a,0),App.Vector(*q,0)),False)
for i in range(4): s.addConstraint(Sketcher.Constraint('Coincident',i,2,(i+1)%4,1))
for i in (0,2): s.addConstraint(Sketcher.Constraint('Horizontal',i))
for i in (1,3): s.addConstraint(Sketcher.Constraint('Vertical',i))
for c in [Sketcher.Constraint('DistanceX',0,1,-.5),Sketcher.Constraint('DistanceY',0,1,-3),Sketcher.Constraint('Distance',0,1),Sketcher.Constraint('Distance',1,6)]: s.addConstraint(c)
s.setExpression('Constraints[8]','-Parameters.pinSplitWidth / 2')
s.setExpression('Constraints[10]','Parameters.pinSplitWidth')
p=b.newObject('PartDesign::Pocket','PinSplit'); p.Profile=s
p.setExpression('Length','Parameters.pinHeadHeight + Parameters.pinShaftLength + Parameters.pinCrownHeight + 0.1 mm - Parameters.pinSplitStart')
stage(p); l.Visibility=False; s.Visibility=False
b.Tip=p
D.recompute()
report={'volume_mm3':p.Shape.Volume,'solids':len(p.Shape.Solids),'valid':p.Shape.isValid(),
        'sketch_dof':{o.Name:o.FullyConstrained for o in b.Group if o.TypeId=='Sketcher::SketchObject'},
        'feature_types':{o.Name:o.TypeId for o in b.Group}}
(ROOT/'pin_validation.json').write_text(json.dumps(report,indent=2))
D.recompute(); D.saveAs(str(ROOT/'Precision_5560_Native.FCStd'))
Gui.activeDocument().activeView().saveImage(str(ROOT/'pin_preview.png'),1200,900,'Current')
