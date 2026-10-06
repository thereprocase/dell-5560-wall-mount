"""Staged, repeatable native build. The bridge owns main-thread execution."""
import adsk.core as c
import adsk.fusion as f
from native.kernel import Builder,coll
from pathlib import Path
import json
import time

OUT=Path('F:/Code/dell-5560-wall-mount/fusion/output/native')
OUT.mkdir(parents=True,exist_ok=True)
stage=request.get('stage','create')
if stage=='create':
    d=f.Design.cast(app.activeProduct)
    if not d or not d.attributes.itemByName('Dell5560','nativePort') or d.userParameters.count:
        doc=app.documents.add(c.DocumentTypes.FusionDesignDocumentType)
        doc.name='Precision 5560 | Rev F | Native Engineering'
        d=f.Design.cast(app.activeProduct)
    d.designType=f.DesignTypes.ParametricDesignType
    d.attributes.add('Dell5560','nativePort','20260907')
    params=[
        ('outboardX',184,'mm','LAYOUT | Outer cradle and rail face'),
        ('wallGap',40,'mm','LAYOUT | Rear laptop air gap'),
        ('wallBoltX',162,'mm','WALL INTERFACE | Bolt half spacing'),
        ('lowerWallBoltZ',-36,'mm','WALL INTERFACE | Lower bolt elevation'),
        ('upperWallBoltZ',174,'mm','WALL INTERFACE | Upper bolt elevation'),
        ('railBottomZ',154,'mm','OUTLET | Lower keyed joint elevation'),
        ('outletZ',232,'mm','OUTLET | Lip elevation'),
        ('outletGap',12,'mm','OUTLET | Nominal 12 mm; verify 8 and 16 mm variants'),
        ('fanAngle',45,'deg','FAN DATUM | Installed inclination'),
        ('fanCenterY',67,'mm','FAN DATUM | Installed pivot outward from wall'),
        ('fanCenterZ',-84,'mm','FAN DATUM | Installed pivot below shelf'),
        ('ductSkin',2,'mm','AIR PATH | Normal station inset and side wall thickness'),
        ('keyClearance',.3,'mm','GLUED JOINTS | Mortise allowance per side'),
        ('pinSocketDiameter',4.1,'mm','PIN INTERFACE | Duct socket bore'),
        ('pinPassageDiameter',4.5,'mm','PIN INTERFACE | Cap clearance passage'),
        ('pinHeadRadius',4,'mm','PIN | Head radius'),('pinHeadHeight',2,'mm','PIN | Head height'),
        ('pinHeadChamfer',.6,'mm','PIN | Head edge break'),('pinShaftDiameter',4,'mm','PIN | Shaft diameter'),
        ('pinShaftLength',10,'mm','PIN | Shaft length'),('pinCrownDiameter',4.2,'mm','PIN | Retention crown diameter'),
        ('pinCrownHeight',2,'mm','PIN | Tapered crown height'),('pinTipRadius',1.6,'mm','PIN | Tip radius'),
        ('pinSplitWidth',1,'mm','PIN | Flexure slit width'),('pinSplitRoot',4,'mm','PIN | Flexure root elevation'),
        ('pinSplitOverrun',.1,'mm','PIN | Through-cut allowance')]
    for name,value,unit,comment in params:
        p=d.userParameters.add(name,c.ValueInput.createByString(f'{value} {unit}'),unit,comment);p.isFavorite=True
    app.isComponentColorsDisplayed=True
else:
    d=None
    for doc in app.documents:
        candidate=f.Design.cast(doc.products.itemByProductType('DesignProductType'))
        if candidate and candidate.attributes.itemByName('Dell5560','nativePort'):
            d=candidate;doc.activate();break
    if not d:raise RuntimeError('Create native document first')

colors={'cradle':(64,117,174),'duct':(49,155,153),'rail':(137,105,172),'tray':(226,155,62),'cap':(103,153,88),'pin':(196,85,70)}
if stage in colors:
    root=d.rootComponent
    existing=[o for o in root.occurrences if o.component.attributes.itemByName('Dell5560','family') and o.component.attributes.itemByName('Dell5560','family').value==stage]
    if existing:
        if not request.get('rebuild'):raise RuntimeError('Component already built')
        d.activateRootComponent()
        for old in existing:old.deleteMe()
    o=root.occurrences.addNewComponent(c.Matrix3D.create());comp=o.component
    o.activate()
    comp.name=stage+' RH' if stage!='pin' else 'pin | reusable'
    comp.partNumber='5560-F-'+stage.upper()+'-R'
    comp.description='Native Revision F | dimensions in mm | see fusion/README.md'
    comp.componentColor=c.Color.create(*colors[stage],255)
    comp.attributes.add('Dell5560','family',stage)
    b=Builder(d,comp,stage.upper())
    if stage=='cradle':
        from native.parts_cradle import build
    elif stage=='rail':
        from native.parts_rail import build
    elif stage=='duct':
        from native.parts_duct import build
    elif stage=='tray':
        from native.parts_tray_cap import build_tray as build
    elif stage=='cap':
        from native.parts_tray_cap import build_cap as build
    else:
        from native.parts_pin import build
    body=build(b)
    if stage in ('tray','cap'):
        with b.group('90 Installed fan datum'):
            body=b.tilt('Installed fan placement',body)
    body.name=stage+' | finished print'
    body.isVisible=True
    comp.isConstructionFolderLightBulbOn=False;comp.isSketchFolderLightBulbOn=False
    if comp.bRepBodies.count!=1:raise RuntimeError(f'{stage}: expected one final body, got {comp.bRepBodies.count}')
    exp=d.exportManager
    assert exp.execute(exp.createSTEPExportOptions(str(OUT/(stage+'.step')),comp))
    report={'stage':stage,'volume_mm3':body.getPhysicalProperties(f.CalculationAccuracy.VeryHighCalculationAccuracy).volume*1000,
            'sketches':[{'name':s.name,'fully_constrained':s.isFullyConstrained} for s in comp.sketches],
            'features':[{'name':x.name,'health':int(x.healthState),'message':x.errorOrWarningMessage} for x in comp.features],
            'bodies':comp.bRepBodies.count}
    (OUT/(stage+'.json')).write_text(json.dumps(report,indent=2))
    result.update(report)
elif stage=='inspect':
    result.update(timeline=d.timeline.count,components=[x.component.name for x in d.rootComponent.occurrences])

app.activeViewport.fit()
exp=d.exportManager
assert exp.execute(exp.createFusionArchiveExportOptions(str(OUT/'Precision_5560_RevF_native_working.f3d')))
result.update(stage=stage,timeline=d.timeline.count)
