import adsk.core as c
import adsk.fusion as f
from pathlib import Path
import json
d=f.Design.cast(app.activeProduct)
if not d.attributes.itemByName('Dell5560','assembled'):raise RuntimeError('Assembly not complete')
d.activateRootComponent();root=d.rootComponent
out=Path('F:/Code/dell-5560-wall-mount/fusion/output/native')
labels={'cradle':'01 Cradle','duct':'02 Fan duct','rail':'03 Outlet rail','tray':'04 Fan tray','cap':'05 Fan retainer','pin':'06 Push pin'}
seen=set()
for o in root.occurrences:
    comp=o.component
    if comp.id in seen:continue
    seen.add(comp.id)
    family=next((key for key in labels if key in comp.name.lower()),None)
    if family:
        side='LH' if comp.attributes.itemByName('Dell5560','hand') else 'RH'
        comp.name=labels[family]+(' | shared x4' if family=='pin' else ' | '+side)
    comp.isConstructionFolderLightBulbOn=False;comp.isSketchFolderLightBulbOn=False
    comp.isOriginFolderLightBulbOn=False
    for body in comp.bRepBodies:body.name=comp.name+' | print solid'
root.isConstructionFolderLightBulbOn=False;root.isSketchFolderLightBulbOn=False;root.isOriginFolderLightBulbOn=False
root.isJointsFolderLightBulbOn=False
app.isComponentColorsDisplayed=True
camera=app.activeViewport.camera
camera.cameraType=c.CameraTypes.OrthographicCameraType
camera.eye=c.Point3D.create(60,90,55)
camera.target=c.Point3D.create(0,5,4)
camera.upVector=c.Vector3D.create(0,0,1)
app.activeViewport.camera=camera
app.activeViewport.fit()
camera=app.activeViewport.camera
camera.viewExtents*=1.1
app.activeViewport.camera=camera
app.activeViewport.saveAsImageFile(str(out/'assembly.png'),1500,1200)
exp=d.exportManager
assert exp.execute(exp.createFusionArchiveExportOptions(str(out/'Precision_5560_RevF_native.f3d')))
assert exp.execute(exp.createSTEPExportOptions(str(out/'assembly.step')))
report={'occurrences':root.occurrences.count,'joints':root.asBuiltJoints.count,
    'components':[{'name':o.component.name,'bodies':o.component.bRepBodies.count} for o in root.occurrences],
    'parameters':[{'name':p.name,'expression':p.expression,'comment':p.comment} for p in d.userParameters],
    'sketches':[{'component':comp.name,'name':s.name,'fully_constrained':s.isFullyConstrained} for comp in d.allComponents for s in comp.sketches],
    'issues':[{'name':x.name,'health':int(x.healthState),'message':x.errorOrWarningMessage} for comp in d.allComponents for x in comp.features if int(x.healthState)]}
(out/'assembly.json').write_text(json.dumps(report,indent=2))
result.update(occurrences=report['occurrences'],joints=report['joints'],sketches=len(report['sketches']),parameters=len(report['parameters']),issues=report['issues'])
