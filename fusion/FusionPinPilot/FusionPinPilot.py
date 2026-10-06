"""One-shot Fusion-native pilot. Creates a NEW document; never edits an existing one."""
import adsk.core
import adsk.fusion
import json
import math
import threading
import time
import traceback
from pathlib import Path

OUT = Path('F:/Code/dell-5560-wall-mount/fusion/output')
EVENT = 'Dell5560FusionPinPilotOnce'
handlers = []
app = None

def write(name, data):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(data, indent=2), encoding='utf-8')

def pilot():
    if (OUT/'result.json').exists():
        return
    doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    doc.name = 'Precision 5560 - Native Fusion Pilot'
    design = adsk.fusion.Design.cast(app.activeProduct)
    design.designType = adsk.fusion.DesignTypes.ParametricDesignType
    root = design.rootComponent
    first = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    comp = first.component
    comp.name = 'Push pin - native'
    values = {'pinHeadRadius':4,'pinHeadHeight':2,'pinHeadChamfer':.6,
              'pinShaftDiameter':4,'pinShaftLength':10,'pinCrownDiameter':4.2,
              'pinCrownHeight':2,'pinTipRadius':1.6,'pinSplitWidth':1,'pinSplitRoot':4,
              'pinSplitOverrun':.1}
    for name,value in values.items():
        design.userParameters.add(name,adsk.core.ValueInput.createByString(f'{value} mm'),'mm','Revision F pin')
    sketch=comp.sketches.add(comp.xZConstructionPlane)
    sketch.name='Pin - dimensioned axial profile'
    points=[(0,0),(4,0),(4,1.4),(3.4,2),(2,2),(2,12),(2.1,12),(1.6,14),(0,14)]
    expressions=['pinHeadRadius','pinHeadHeight-pinHeadChamfer','sqrt(2)*pinHeadChamfer',
        'pinHeadRadius-pinHeadChamfer-pinShaftDiameter/2','pinShaftLength',
        '(pinCrownDiameter-pinShaftDiameter)/2',
        'sqrt((pinCrownDiameter/2-pinTipRadius)^2+pinCrownHeight^2)',
        'pinTipRadius','pinHeadHeight+pinShaftLength+pinCrownHeight']
    def sketchpoint(s,x,z):
        return s.modelToSketchSpace(adsk.core.Point3D.create(x/10,0,z/10))
    curves=[]
    for i,(a,b) in enumerate(zip(points,points[1:]+points[:1])):
        start=curves[-1].endSketchPoint if curves else sketchpoint(sketch,*a)
        end=curves[0].startSketchPoint if i==len(points)-1 else sketchpoint(sketch,*b)
        line=sketch.sketchCurves.sketchLines.addByTwoPoints(start,end)
        curves.append(line)
    curves[0].startSketchPoint.isFixed=True
    for i,line in enumerate(curves):
        a,b=points[i],points[(i+1)%len(points)]
        if a[1]==b[1]: sketch.geometricConstraints.addHorizontal(line)
        elif a[0]==b[0]: sketch.geometricConstraints.addVertical(line)
        d=sketch.sketchDimensions.addDistanceDimension(line.startSketchPoint,line.endSketchPoint,
            adsk.fusion.DimensionOrientations.AlignedDimensionOrientation,
            sketchpoint(sketch,(a[0]+b[0])/2+1,(a[1]+b[1])/2))
        d.parameter.expression=expressions[i]
    assert sketch.profiles.count==1
    revinput=comp.features.revolveFeatures.createInput(sketch.profiles.item(0),curves[-1],
            adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    revinput.setAngleExtent(False,adsk.core.ValueInput.createByString('360 deg'))
    rev=comp.features.revolveFeatures.add(revinput)
    rev.name='Pin - full revolve'
    slot=comp.sketches.add(comp.xZConstructionPlane)
    slot.name='Pin - split profile'
    rect=slot.sketchCurves.sketchLines.addTwoPointRectangle(sketchpoint(slot,-.5,4),sketchpoint(slot,.5,14.1))
    # Nominal rectangular cut; explicit dimensions make it editable. Root/centering refinement is future work.
    rect.item(0).startSketchPoint.isFixed=True
    for i,expression in [(0,'pinSplitWidth'),(1,'pinHeadHeight+pinShaftLength+pinCrownHeight+pinSplitOverrun-pinSplitRoot')]:
        line=rect.item(i)
        d=slot.sketchDimensions.addDistanceDimension(line.startSketchPoint,line.endSketchPoint,
            adsk.fusion.DimensionOrientations.AlignedDimensionOrientation,
            adsk.core.Point3D.create(.2,-.8,0))
        d.parameter.expression=expression
    cutinput=comp.features.extrudeFeatures.createInput(slot.profiles.item(0),adsk.fusion.FeatureOperations.CutFeatureOperation)
    cutinput.setSymmetricExtent(adsk.core.ValueInput.createByString('6 mm'),True)
    cut=comp.features.extrudeFeatures.add(cutinput)
    cut.name='Pin - symmetric split cut'
    sketch.isVisible=False
    slot.isVisible=False
    body=comp.bRepBodies.item(0)
    body.name='Revision F split push pin'
    def measure():
        props=body.getPhysicalProperties(adsk.fusion.CalculationAccuracy.VeryHighCalculationAccuracy)
        b=body.boundingBox
        return dict(solids=comp.bRepBodies.count,volume_mm3=props.volume*1000,
                    bounds_mm=[[p.x*10,p.y*10,p.z*10] for p in [b.minPoint,b.maxPoint]])
    nominal=measure()
    p=design.userParameters.itemByName('pinHeadRadius')
    try:
        p.expression='4.5 mm'
        design.computeAll()
        perturbed=measure()
    finally:
        p.expression='4 mm'
        design.computeAll()
    restored=measure()
    assert abs(nominal['volume_mm3']-204.56030211054718)<.001
    assert abs(perturbed['bounds_mm'][1][0]-4.5)<.001
    assert abs(restored['volume_mm3']-nominal['volume_mm3'])<.001
    # Save an isolated pin STEP and image, then an assembly F3D with four native occurrences.
    exp=design.exportManager
    assert exp.execute(exp.createSTEPExportOptions(str(OUT/'Fusion_native_pin.step'),comp))
    app.activeViewport.fit()
    app.activeViewport.saveAsImageFile(str(OUT/'Fusion_native_pin.png'),1000,850)
    s=math.sqrt(.5)
    for i,x in enumerate([-135,-5,5,135]):
        transform=adsk.core.Matrix3D.create()
        transform.setWithArray([1,0,0,x/10,0,-s,-s,(67+75*s)/10,
                               0,s,-s,(-84+77*s)/10,0,0,0,1])
        if i==0: first.transform2=transform
        else: root.occurrences.addExistingComponent(comp,transform)
    app.activeViewport.fit()
    assert exp.execute(exp.createFusionArchiveExportOptions(str(OUT/'Fusion_native_pin_assembly.f3d')))
    result=dict(status='success',fusion_version=app.version,nominal=nominal,perturbed=perturbed,
        restored=restored,occurrences=root.occurrences.count,profile_fully_constrained=sketch.isFullyConstrained,
        slot_fully_constrained=slot.isFullyConstrained,timeline_count=design.timeline.count,
        features=[dict(name=comp.features.item(i).name,health=str(comp.features.item(i).healthState)) for i in range(comp.features.count)],
        limitation='Pin pilot only; split anchor nominal; occurrences positioned, not jointed. No human edit preservation test yet.')
    write('result.json',result)

class Execute(adsk.core.CustomEventHandler):
    def notify(self,args):
        try: pilot()
        except Exception: write('error.json',dict(error=traceback.format_exc()))

def run(context):
    global app
    app=adsk.core.Application.get()
    write('started.json',dict(context=str(context),version=app.version))
    h=Execute()
    handlers.append(h)
    app.registerCustomEvent(EVENT).add(h)
    def later():
        time.sleep(12)
        app.fireCustomEvent(EVENT)
    threading.Thread(target=later,daemon=True).start()

def stop(context):
    if app:
        app.unregisterCustomEvent(EVENT)
    handlers.clear()
