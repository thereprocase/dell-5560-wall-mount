"""Editable analysis surrogates; preserve all fourteen manufacturing occurrences."""
import adsk.core as c
import adsk.fusion as f
from native.kernel import Builder,add,sub,coll
from pathlib import Path
import json
d=f.Design.cast(app.activeProduct)
if not d.attributes.itemByName('Dell5560','assembled'):raise RuntimeError('Native assembly required')
d.activateRootComponent();root=d.rootComponent
if any(o.component.attributes.itemByName('Dell5560','analysisHelper') for o in root.occurrences):
    raise RuntimeError('CFD helpers already exist')
o=root.occurrences.addNewComponent(c.Matrix3D.create());comp=o.component
comp.name='90 CFD helpers | NOT PRINTED';comp.componentColor=c.Color.create(175,180,187,255)
comp.attributes.add('Dell5560','analysisHelper','true');o.activate()
b=Builder(d,comp,'CFD')
w=b.param('laptopWidth',344.4,'DELL DOCUMENTED | Exterior width')
h=b.param('laptopHeight',230.3,'DELL DOCUMENTED | Hinge-to-front dimension')
t=b.param('laptopEnvelopeThickness',20,'CLEARANCE ENVELOPE | Source model thickness; not measured internal chassis')
skin=b.param('surrogateCaseSkin',1.2,'ASSUMED | Laptop surrogate wall thickness')
air=b.param('internalAirDepth',8,'ASSUMED | Simplified internal intake/turning space')
vent_w=b.param('ventBandWidth',290,'UNMEASURED | Long underside intake grille width')
vent_h=b.param('ventBandHeight',30,'UNMEASURED | Intake band height toward hinge')
vent_setback=b.param('ventHingeSetback',35,'UNMEASURED | Intake centre below hinge')
fan_x=b.param('dellBlowerOffset',110,'UNMEASURED | Symmetric blower centre offset')
fan_setback=b.param('dellBlowerSetback',45,'UNMEASURED | Blower centre below hinge')
fan_d=b.param('dellBlowerInletDiameter',50,'UNMEASURED | Surrogate actuator disk diameter')
exhaust_w=b.param('hingeExhaustWidth',65,'UNMEASURED | Hinge exhaust width per blower')
exhaust_h=b.param('hingeExhaustHeight',5,'UNMEASURED | Hinge opening depth normal to underside')
wall_w=b.param('wallHalfWidth',400,'CFD DOMAIN | Wall lateral extent, sensitivity test required')
wall_t=b.param('wallThickness',20,'CFD REFERENCE | Solid wall lies entirely behind Y=0')
top=add(h,2);inside_y=add('wallGap',skin)
roles=[]
def role(body,name,kind,comment,visible=True):
    body.name=name;body.attributes.add('CFD','role',kind);body.attributes.add('CFD','assumption',comment)
    body.isVisible=visible
    roles.append({'name':name,'role':kind,'assumption':comment,'volume_mm3':body.volume*1000})

with b.group('01 Wall boundary reference'):
    wall=b.box('Wall plane solid',f'-({wall_w})',wall_w,f'-({wall_t})',0,-300,500)
    role(wall,'WALL | solid obstacle; face Y=0','solid_wall','Arbitrary finite extent; wall plane is source datum',False)
with b.group('02 Laptop shell and connected internal passage'):
    shell=b.box('Laptop external envelope',f'-({w})/2',f'({w})/2','wallGap',add('wallGap',t),2,top,fillet=4,axis='Y')
    cavity=b.box('Internal airflow surrogate',f'-({w})/2+4 mm',f'({w})/2-4 mm',inside_y,add(inside_y,air),22,sub(top,skin),fillet=2,axis='Y')
    shell=b.cut('Hollow simplified internal intake space',shell,cavity)
with b.group('03 Underside intake and hinge exhaust paths'):
    centre=sub(top,vent_setback)
    vent=b.box('Underside intake band',f'-({vent_w})/2',f'({vent_w})/2','wallGap-0.1 mm',add(inside_y,.2),
        sub(centre,f'({vent_h})/2'),add(centre,f'({vent_h})/2'),axis='Y')
    shell=b.cut('Open underside grille envelope',shell,vent)
    for side,sign in (('LH',-1),('RH',1)):
        x=f'{sign}*({fan_x})'
        slot=b.box(side+' hinge exhaust',sub(x,f'({exhaust_w})/2'),add(x,f'({exhaust_w})/2'),inside_y,
            add(inside_y,exhaust_h),sub(top,5),add(top,.2),axis='Y')
        shell=b.cut(side+' open connected hinge exhaust',shell,slot)
    role(shell,'LAPTOP | vented airflow surrogate','laptop_shell',
        'Topology from Dell manuals; internal cavity, vent dimensions, fin losses and leakage are unmeasured')
with b.group('04 Dell blower actuator zones | NOT obstructions'):
    for side,sign in (('LH',-1),('RH',1)):
        disk=b.cylinder(side+' Dell blower actuator',f'({fan_d})/2',2,
            (f'{sign}*({fan_x})',add(inside_y,2),sub(top,fan_setback)))
        role(disk,side+' DELL FAN | actuator zone; NOT solid','fan_actuator_zone',
            'Separate internal blower; axial intake +Y then hinge discharge +Z. Pressure-flow curve and RPM unknown',False)
    screen=b.box('Intake grille resistance zone',f'-({vent_w})/2',f'({vent_w})/2','wallGap',
        'wallGap+0.1 mm',sub(centre,f'({vent_h})/2'),add(centre,f'({vent_h})/2'),axis='Y')
    role(screen,'INTAKE GRILLE | porous interface; NOT solid','porous_interface_zone',
        'Open area and pressure-loss law unmeasured; do not treat this marker as an impermeable wall',False)
comp.isConstructionFolderLightBulbOn=False;comp.isSketchFolderLightBulbOn=False;comp.isOriginFolderLightBulbOn=False
d.activateRootComponent()
out=Path('F:/Code/dell-5560-wall-mount/fusion/output/native')
report={'helper_component':comp.name,'roles':roles,'fully_constrained':all(s.isFullyConstrained for s in comp.sketches),
        'features_healthy':all(int(x.healthState)==0 for x in comp.features),'parameters':
        [{'name':p.name,'expression':p.expression,'comment':p.comment} for p in d.userParameters if p.name.startswith('CFD_')],
        'printed_occurrences':14,'total_root_occurrences':root.occurrences.count,
        'solver_status':'Geometry surrogates only; Dell blower curve, grille/fin resistance, and heat load are unset'}
(out/'cfd_helpers.json').write_text(json.dumps(report,indent=2))
exp=d.exportManager
assert exp.execute(exp.createSTEPExportOptions(str(out/'cfd_helpers.step'),comp))
assert exp.execute(exp.createFusionArchiveExportOptions(str(out/'Precision_5560_RevF_native_with_CFD_helpers.f3d')))
result.update(report)
