"""One native assembly: associative handed parts and explicit rigid interfaces."""
import adsk.core as c
import adsk.fusion as f
from native.kernel import Builder,coll
from pathlib import Path
import json
OUT=Path('F:/Code/dell-5560-wall-mount/fusion/output/native')
d=None
for doc in app.documents:
    candidate=f.Design.cast(doc.products.itemByProductType('DesignProductType'))
    if candidate and candidate.attributes.itemByName('Dell5560','nativePort'):
        d=candidate;doc.activate();break
if not d:raise RuntimeError('Native document not open')
d.activateRootComponent();root=d.rootComponent
parts={}
for o in root.occurrences:
    tag=o.component.attributes.itemByName('Dell5560','family')
    if tag:parts[tag.value]=o
if len(parts)!=6:raise RuntimeError('Six complete part families required')
if d.attributes.itemByName('Dell5560','assembled'):raise RuntimeError('Already assembled')

with Builder(d,root,'ASSEMBLY').group('10 Associative handed components'):
    left={}
    for family in ('cradle','duct','rail','tray','cap'):
        before=root.occurrences.count
        inp=root.features.mirrorFeatures.createInput(coll([parts[family]]),root.yZConstructionPlane)
        feat=root.features.mirrorFeatures.add(inp);feat.name=family+' | LH associative mirror'
        if root.occurrences.count!=before+1:raise RuntimeError('Expected one mirrored occurrence')
        o=root.occurrences.item(before)
        o.component.name=family+' LH';o.component.partNumber='5560-F-'+family.upper()+'-L'
        o.component.componentColor=parts[family].component.componentColor
        o.component.attributes.add('Dell5560','hand','LH')
        left[family]=o
        assert d.exportManager.execute(d.exportManager.createSTEPExportOptions(str(OUT/(family+'_LH.step')),o.component))

pin=parts['pin'];b=Builder(d,pin.component,'PIN')
with b.group('90 Installed pin datum and four instances'):
    body=pin.component.bRepBodies.item(0)
    body=b.rotate_x('Pin insertion axis',body,'90 deg + fanAngle')
    body=b.translate('Pin head seating datum',body,5,
        'fanCenterY + 76 mm*cos(fanAngle) - 1 mm*sin(fanAngle)',
        'fanCenterZ + 76 mm*sin(fanAngle) + 1 mm*cos(fanAngle)')
    pins=[pin]
    for offset in (130,-10,-140):
        matrix=c.Matrix3D.create();matrix.translation=c.Vector3D.create(offset/10,0,0)
        pins.append(root.occurrences.addExistingComponent(pin.component,matrix))

with Builder(d,root,'ASSEMBLY').group('20 Installed rigid interfaces'):
    parts['cradle'].isGrounded=True
    joints=[]
    def rigid(name,a,b):
        inp=root.asBuiltJoints.createInput(a,b,None);inp.setAsRigidJointMotion()
        joint=root.asBuiltJoints.add(inp);joint.name=name;joints.append(joint)
    rigid('Wall mounting | left-to-right spacing',parts['cradle'],left['cradle'])
    for side,table in (('RH',parts),('LH',left)):
        rigid(side+' | duct glued lap joint',table['cradle'],table['duct'])
        rigid(side+' | rail glued keyed joint',table['cradle'],table['rail'])
        rigid(side+' | tray seated dovetails',table['duct'],table['tray'])
        rigid(side+' | fan retainer installed',table['tray'],table['cap'])
    for i,(p,cap) in enumerate(zip(pins,[parts['cap'],parts['cap'],left['cap'],left['cap']])):
        rigid(f'Push pin {i+1} | retained seat',cap,p)

d.attributes.add('Dell5560','assembled','true')
d.activateRootComponent()
root.isConstructionFolderLightBulbOn=False;root.isSketchFolderLightBulbOn=False
app.isComponentColorsDisplayed=True
app.activeViewport.fit()
app.activeViewport.saveAsImageFile(str(OUT/'assembly.png'),1500,1200)
exp=d.exportManager
assert exp.execute(exp.createFusionArchiveExportOptions(str(OUT/'Precision_5560_RevF_native.f3d')))
assert exp.execute(exp.createSTEPExportOptions(str(OUT/'assembly.step')))
result.update(occurrences=root.occurrences.count,joints=root.asBuiltJoints.count,
    components=[{'name':o.component.name,'bodies':o.component.bRepBodies.count} for o in root.occurrences])
(OUT/'assembly.json').write_text(json.dumps(result,indent=2))
