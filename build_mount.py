"""Revision F: glued keyed joints, shrouded cheeks and inclined 120 mm fan modules.
Millimetres. X width, Y out from wall, Z up. Four wall bolts are the only metal fasteners.
"""
from pathlib import Path
import json,math
import cadquery as cq
from base_geometry import box,cyl,yz_prism,fuse,bbox,roof_hole,tongue
import base_geometry as old
OUT=Path(__file__).resolve().parent;PARTS=OUT/'parts';PARTS.mkdir(exist_ok=True)
LAPTOP_W=344.4;LAPTOP_H=230.3;LAPTOP_T=20.;OUTLET_GAP=12.;OUTLET_Z=232.;RAMP_START_Z=198.
FAN_CX=70.;WALL_GAP=40.;WALL_HOLE_Z=(-36.,174.)
# Original tray coordinates converted into a fan plane whose normal points wallward/up.
def tilt(s):return s.translate((0,-70,104)).rotate((0,0,0),(1,0,0),45).translate((0,67,-84))
def untilt(s):return s.translate((0,-67,84)).rotate((0,0,0),(1,0,0),-45)
# Keyed lap joints: broad shoulders carry gravity; CA locks against pullout.
DUCT_KEYS=[(146,154,-59,-19),(167,175,-59,-19)]
RAIL_KEYS=[(143,152,156,164),(168,177,156,164)]
def tenons(spec,clear=0):
 items=[]
 for a,b,z0,z1 in spec:
  if clear:
   # Open-mouth mortise closes on a 45-degree roof in the side-print orientation.
   y0=14-clear;y1=26.6+clear
   pts=[(a-clear,y0),(b+clear,y0),(b+clear,y1),(a-clear-(y1-y0),y1)]
   top=z1+clear+(12.6 if spec is RAIL_KEYS else 0)
   items.append(cq.Workplane('XY',origin=(0,0,z0-clear)).polyline(pts).close().extrude(top-(z0-clear)))
  elif spec is RAIL_KEYS:
   items.append(yz_prism(a,b,[(14,z0),(26.6,z0),(26.6,z1+12.6),(14,z1)]))
  else:items.append(box(a,b,14,26.6,z0,z1))
 return items
def right_cradle():
 s=old.right_cradle()
 # Outer skin plus inward lip keep air behind the machine; ports remain outboard.
 skin=box(180,184,0,39,-10,153.7).edges('|X').fillet(2)
 lip=box(173.4,184,37,39,0,153.7)
 s=fuse(s,skin,lip)
 for t in tenons(DUCT_KEYS,.3)+tenons(RAIL_KEYS,.3):s=s.cut(t)
 return s.clean()

def wire(x0,x1,L,R):
 return cq.Wire.makePolygon([cq.Vector(x0,*L),cq.Vector(x1,*L),cq.Vector(x1,*R),cq.Vector(x0,*R)],close=True)
def loft_channel(inner=False):
 # A gentle wallward turn between the 45-degree fan plane and vertical rear gap.
 levels=[((23,-128),(111,-40)),((8,-80),(66,-28)),((4,-35),(42,-10)),((4,0),(40,0))]
 if inner:
  # Insets normal to each section; simple ruled skin, approximately 2 mm nominal.
  lev=[]
  for L,R in levels:
   dy,dz=R[0]-L[0],R[1]-L[1];n=math.hypot(dy,dz)
   lev.append(((L[0]+2*dy/n,L[1]+2*dz/n),(R[0]-2*dy/n,R[1]-2*dz/n)))
  levels=lev
 return cq.Solid.makeLoft([wire(3 if inner else 1,138 if inner else 140,L,R) for L,R in levels],ruled=True)
def right_duct():
 shell=cq.Workplane(obj=loft_channel()).cut(loft_channel(True))
 deck=old.box(1,140,4,136,-110,-104).edges('|Z').fillet(3).cut(old.cyl(58,8,(70,70,-111),(0,0,1)))
 deck=deck.cut(old.box(11,130,8,132,-107.6,-103.9))
 bosses=[old.box(a,b,122,136,-110,-97).edges('|Z').fillet(2) for a,b in [(1,11),(130,140)]]
 deck=fuse(deck,*bosses)
 for x in (5,135):
  deck=deck.cut(tongue(x,8.7,137,True)).cut(cyl(2.05,10,(x,128,-103)))
 s=fuse(shell,tilt(deck))
 # Full-depth joint saddle and two tenons. Sloped side buttress grows from inlet.
 saddle=box(139,175.5,26.3,36.3,-64,-12)
 ramp=cq.Workplane('XZ',origin=(0,36.3,0)).polyline([(136,-91),(175.5,-51.5),(175.5,-12),(136,-12)]).close().extrude(10)
 s=fuse(s,saddle,ramp,*tenons(DUCT_KEYS))
 # Keep the lower wall bolt accessible after assembly.
 s=s.cut(roof_hole(9,45,(162,8,-36),roof='+Z',bridge=4))
 return s.clean()
def right_tray():return tilt(old.right_tray())
def right_cap():return tilt(old.right_cap())
def right_rail(gap=12):
 # Lip-down printing, air-facing skin continues upward to hinge height.
 panel=box(.2,139,0,2,154,198)
 ramp=yz_prism(.2,180,[(0,196),(4,198),(40-gap,226),(40-gap,232),(37.6-gap,232),(37.6-gap,227),(0,201)])
 # A continuous thin air skin avoids the broad overhanging ceiling of a filled wedge.
 s=fuse(panel,ramp)
 arm=cq.Workplane('XZ',origin=(0,30.3,0)).polyline([(140,154),(184,154),(184,232),(180,232),(140,188)]).close().extrude(4)
 cheek=box(180,184,0,39,154,232)
 lip=box(173.4,184,37,39,154,232)
 link=box(136,184,0,4,226,232)
 end_rib=yz_prism(136,140,[(0,196),(4,198),(40-gap,226),(40-gap,232),(0,232)])
 s=fuse(s,arm,cheek,lip,link,end_rib,*tenons(RAIL_KEYS))
 s=s.cut(roof_hole(10,42,(162,-1,174),roof='-Z',bridge=4))
 s=s.cut(box(179.7,184.3,-.3,26.3,153.7,184.3))
 return s.clean()
def pin():
 # Split push-pin; print button down. 0.05-mm nominal radial interference at crown.
 head=cq.Workplane('XY').circle(4).extrude(2).edges('>Z').chamfer(.6)
 shaft=cq.Workplane('XY',origin=(0,0,2)).circle(2).extrude(10)
 barb=cq.Workplane('XY',origin=(0,0,12)).circle(2.1).workplane(offset=2).circle(1.6).loft()
 s=fuse(head,shaft,barb).cut(box(-.5,.5,-3,3,4,14.1))
 return s

def fan_reference(cx):return tilt(old.fan_reference(cx))
def laptop_reference():return old.laptop_reference()
def fastener_interfaces():return [dict(kind='wall_anchor',center=[x,10,z],axis=[0,-1,0],shaft_d_mm=7,driver_d_mm=16,head_plane_y=10) for x in (-162,162) for z in WALL_HOLE_Z]
def installed_pin(x):
 # Local pin button is outside the cap; shaft points toward the wall in old coordinates.
 return tilt(pin().rotate((0,0,0),(1,0,0),90).translate((x,146,-103)))
def build():
 rc=right_cradle().val();rd=right_duct().val();rr=right_rail().val();rt=right_tray().val();rp=right_cap().val()
 shapes={'01_left_cradle':rc.mirror('YZ'),'02_right_cradle':rc,'03_left_fan_duct':rd.mirror('YZ'),'04_right_fan_duct':rd,'05_left_fan_retainer':rp.mirror('YZ'),'06_right_fan_retainer':rp,'07_left_outlet_rail':rr.mirror('YZ'),'08_right_outlet_rail':rr,'09_left_fan_tray':rt.mirror('YZ'),'10_right_fan_tray':rt}
 for i,x in enumerate((5,135)):
  sp=installed_pin(x).val();shapes[f'{11+i*2:02}_left_push_pin']=sp.mirror('YZ');shapes[f'{12+i*2:02}_right_push_pin']=sp
 assy=cq.Assembly(name='Precision_5560_Wall_Mount_Rev_F')
 for n,s in shapes.items():
  print(n,'valid',s.isValid(),'solids',len(s.Solids()),flush=True)
  assert s.isValid() and len(s.Solids())==1,n
  cq.exporters.export(s,str(PARTS/f'{n}.step'));assy.add(s,name=n,color=cq.Color(.12,.5,.52) if any(k in n for k in ['duct','rail']) else cq.Color(.2,.25,.3))
 assy.export(str(OUT/'Precision_5560_Wall_Mount.step'))
 overlaps={}
 for i,(na,a) in enumerate(shapes.items()):
  for nb,b in list(shapes.items())[i+1:]:
   v=a.intersect(b).Volume()
   if v>1e-3:overlaps[f'{na} / {nb}']=v
 checks={'revision':'F','parts':{n:dict(volume_cm3=s.Volume()/1000,bbox=bbox(s)) for n,s in shapes.items()},'overlaps_mm3':overlaps,'wall_fasteners':fastener_interfaces(),'fan_axis':[0,-2**-.5,2**-.5]}
 lap=laptop_reference().val();fans=[fan_reference(x).val() for x in [-70,70]]
 checks['laptop_interference_mm3']={n:s.intersect(lap).Volume() for n,s in shapes.items()}
 checks['fan_interference_mm3']={n:max(s.intersect(f).Volume() for f in fans) for n,s in shapes.items()}
 checks['driver_interference_mm3']={str(f['center']):sum(cyl(8,180,tuple(f['center'])).val().intersect(s).Volume() for s in shapes.values()) for f in fastener_interfaces()}
 checks['lift_out_interference_mm3']=max(sum(s.intersect(lap.translate((0,0,d))).Volume() for s in shapes.values()) for d in (1,30,60,105,150))
 checks['step_reimport_solids']=len(cq.importers.importStep(str(OUT/'Precision_5560_Wall_Mount.step')).solids().vals())
 (OUT/'geometry_validation.json').write_text(json.dumps(checks,indent=2));print(json.dumps({k:v for k,v in checks.items() if k!='parts'},indent=2))
 ref=cq.Assembly(name='REFERENCE');ref.add(assy,name='HOLDER');ref.add(lap,name='LAPTOP_ENVELOPE',color=cq.Color(.7,.72,.74))
 for i,f in enumerate(fans):ref.add(f,name=f'FAN_{i}',color=cq.Color(.15,.15,.15))
 ref.export(str(OUT/'REFERENCE_Installed_Layout.step'))
 variant=OUT/'outlet_gap_variants';variant.mkdir(exist_ok=True)
 for g in [8,16]:
  r=right_rail(g).val()
  for side,s in [('left',r.mirror('YZ')),('right',r)]:cq.exporters.export(s,str(variant/f'{side}_outlet_rail_gap_{g}mm.step'))
 return shapes
if __name__=='__main__':build()
