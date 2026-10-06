"""Native traced Dell silhouette, paired intakes and internal blower ducts."""
import adsk.core as c
import adsk.fusion as f
from native.kernel import Builder, add, sub
from pathlib import Path
import json, hashlib
rootpath=Path('F:/Code/dell-5560-wall-mount')
tracepath=rootpath/'profile_reconstruction.json'
trace=json.loads(tracepath.read_text())
d=f.Design.cast(app.activeProduct)
if not d or not d.attributes.itemByName('Dell5560','assembled'):raise RuntimeError('Activate production native assembly')
d.activateRootComponent();root=d.rootComponent
old=[o for o in root.occurrences if o.component.attributes.itemByName('Dell5560','analysisHelper')]
out=rootpath/'fusion/output/native'
backup=out/'Precision_5560_before_traced_helpers.f3d'
if not backup.exists():assert d.exportManager.execute(d.exportManager.createFusionArchiveExportOptions(str(backup)))
o=root.occurrences.addNewComponent(c.Matrix3D.create());comp=o.component
comp.name='90 CFD | Dell traced shell and twin blower ducts'
comp.attributes.add('Dell5560','analysisHelper','traced-v2')
comp.componentColor=c.Color.create(175,180,187,255);o.activate()
b=Builder(d,comp,'CFD2')
w=b.param('width',344.4,'Dell documented width')
skin=b.param('caseSkin',1.2,'ASSUMED duct underside clearance from nominal wallGap')
depth=b.param('ductDepth',8,'ASSUMED internal duct depth; not measured Dell internals')
fanDiameter=b.param('blowerDiameter',50,'ASSUMED fan actuator diameter')
fanThickness=b.param('actuatorThickness',2,'NUMERICAL actuator thickness, not blade geometry')
inside=add('wallGap',skin)
roles=[]
def role(body,name,kind,assumption,visible=True):
 body.name=name;body.attributes.add('CFD','role',kind);body.attributes.add('CFD','assumption',assumption)
 body.isVisible=visible
 centre=body.physicalProperties.centerOfMass
 roles.append(dict(name=name,role=kind,assumption=assumption,volume_mm3=body.volume*1000,centroid_mm=[centre.x*10,centre.y*10,centre.z*10]))
with b.group('01 Wall datum'):
 wall=b.box('Wall',-400,400,-20,0,-300,500)
 role(wall,'WALL | Y=0','solid_wall','Finite domain extent assumption',False)
with b.group('02 Dell traced side profile | uncertainty +/-2 mm'):
 pts=[]
 for i,(y,z) in enumerate(trace['profile_yz_mm']):
  yp=b.param('profileY%02d'%i,y-40,'TRACE ordinate relative to wallGap, +/-2 mm')
  zp=b.param('profileZ%02d'%i,z,'TRACE front-to-hinge station, +/-2 mm')
  pts.append((add('wallGap',yp),zp))
 shell=b.prism('Closed laptop Dell silhouette','YZ',f'-({w})/2',pts,w)
with b.group('03 Twin internal airflow ducts | assumed interiors'):
 windows=[]
 for i,window in enumerate(trace['effective_intake_windows']):
  side='LH' if i==0 else 'RH'
  x0=b.param(side+'intakeX0',window['x_mm'][0],'Dell inside-cover trace, +/-4 mm')
  x1=b.param(side+'intakeX1',window['x_mm'][1],'Dell inside-cover trace, +/-4 mm')
  z0=b.param(side+'intakeZ0',window['z_mm'][0],'Dell inside-cover trace, +/-4 mm')
  z1=b.param(side+'intakeZ1',window['z_mm'][1],'Dell inside-cover trace, +/-4 mm')
  windows.append((side,x0,x1,z0,z1))
  cavity=b.box(side+' internal fan-to-hinge duct',x0,x1,inside,add(inside,depth),sub(z0,10),229,axis='Y')
  shell=b.cut(side+' internal duct passage',shell,cavity)
with b.group('04 Two traced intakes and hinge discharge'):
 for side,x0,x1,z0,z1 in windows:
  vent=b.box(side+' traced active intake',x0,x1,'wallGap-1 mm',add(inside,.2),z0,z1,axis='Y')
  shell=b.cut(side+' open active grille',shell,vent)
  slot=b.box(side+' hinge exhaust opening',add(x0,2.5),sub(x1,2.5),inside,add(inside,depth),227,234,axis='Y')
  shell=b.cut(side+' connected hinge outlet',shell,slot)
 role(shell,'LAPTOP | traced shell with twin internal ducts','laptop_shell','14-point Dell image trace +/-2 mm; two traced intakes +/-4 mm; internal ducts/exhausts assumed')
with b.group('05 Internal simulated blower actuators and porous markers'):
 for side,x0,x1,z0,z1 in windows:
  xc=f'(({x0})+({x1}))/2';zc=f'(({z0})+({z1}))/2'
  disk=b.cylinder(side+' simulated internal blower',f'({fanDiameter})/2',fanThickness,(xc,add(inside,2),zc))
  role(disk,side+' DELL FAN | actuator, not obstruction','fan_actuator_zone','Assumed axial +Y pressure source within intake-to-hinge duct; no measured P/Q curve',False)
  marker=b.box(side+' porous grille marker',x0,x1,'wallGap-0.14017041996 mm','wallGap-0.04017041996 mm',z0,z1,axis='Y')
  role(marker,side+' INTAKE GRILLE | porous marker','porous_interface_zone','Traced active region; porosity and resistance unknown',False)
comp.isConstructionFolderLightBulbOn=False;comp.isSketchFolderLightBulbOn=False;comp.isOriginFolderLightBulbOn=False
assert all(s.isFullyConstrained for s in comp.sketches)
assert all(int(x.healthState)==0 for x in comp.features)
d.activateRootComponent()
for prior in old:assert prior.deleteMe()
# Export all helper bodies, including hidden actuator/porous markers.
visibility=[(body,body.isVisible) for body in comp.bRepBodies]
for body,visible in visibility:body.isVisible=True
assert d.exportManager.execute(d.exportManager.createSTEPExportOptions(str(out/'cfd_helpers_traced.step'),comp))
for body,visible in visibility:body.isVisible=visible
report=dict(helper_component=comp.name,roles=roles,fully_constrained=True,features_healthy=True,
 parameters=[dict(name=p.name,expression=p.expression,comment=p.comment) for p in d.userParameters if p.name.startswith('CFD2_')],
 trace=dict(path=str(tracepath),sha256=hashlib.sha256(tracepath.read_bytes()).hexdigest(),data=trace),
 printed_occurrences=14,total_root_occurrences=root.occurrences.count,internal_ducts=2,fan_actuators=2,
 solver_status='Geometry ready for offline domain extraction; fan pressures and internal resistance assumed')
(out/'cfd_helpers_traced.json').write_text(json.dumps(report,indent=2))
assert d.exportManager.execute(d.exportManager.createFusionArchiveExportOptions(str(out/'Precision_5560_RevF_traced_CFD_helpers.f3d')))
result.update(report)
