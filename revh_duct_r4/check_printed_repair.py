"""Check a depth-limited drill envelope in the historical printed duct geometry."""
from pathlib import Path
import json,sys,os,math
if sys.platform=='win32':
 sys.path.insert(0,'C:/Program Files/FreeCAD 1.1/lib');dll=os.add_dll_directory('C:/Program Files/FreeCAD 1.1/bin')
import FreeCAD as A,Part
import socket_fix
O=Path(__file__).resolve().parent
D=A.openDocument(str(O/'baseline/Precision_5560_RevH_Current.FCStd'))
objects=socket_fix.installed(D);base=D.getObject('D3EndWallRootR1').Shape
crown=D.getObject('PinCrown').Shape.cut(D.getObject('PinShaft').Shape)
original=Part.makeCompound([D.getObject(n).Shape for n in socket_fix.TOOL_NAMES])
out={'diameter_mm':4.1,'maximum_tip_depth_from_socket_face_mm':6.0,'original_blind_depth_mm':7.7,'physical_result':None,'cases':[]}
for angle in [90,118,135]:
 radius=2.05;height=radius/math.tan(math.radians(angle/2));tools=[]
 for x in [5,135]:
  tools.append(Part.makeCylinder(radius,6.1-height,A.Vector(x,135.8,-103),A.Vector(0,-1,0)))
  tools.append(Part.makeCone(radius,0,height,A.Vector(x,129.7+height,-103),A.Vector(0,-1,0)))
 tool=Part.makeCompound(tools);local=base.cut(tool)
 assert local.isValid() and len(local.Solids)==1
 outside=base.cut(local).cut(original).Volume;assert outside<1e-6,outside
 right=local.copy();right.Placement=D.getObject('D3RightDuct').Placement.multiply(right.Placement)
 reflection=A.Matrix();reflection.A11=-1
 left=right.transformGeometry(reflection)
 row={'drill_point_angle_degrees':angle,'full_diameter_depth_mm':6-height,'tip_to_blind_bottom_mm':1.7,'removed_outside_original_bores_mm3':outside,'pins':{}}
 for key in socket_fix.PIN_KEYS:
  pin=objects[key];duct=left if 'left' in key else right;mask=crown.copy();mask.Placement=pin.LinkPlacement.multiply(mask.Placement)
  samples=[]
  for distance in [0,.2,.5,1,2,3,5,8,12]:
   p=pin.Shape.copy();m=mask.copy();v=A.Vector(0,distance/math.sqrt(2),distance/math.sqrt(2));p.translate(v);m.translate(v)
   contact=p.common(duct);unintended=contact.cut(m).Volume
   assert unintended<1e-6,(angle,key,distance,unintended)
   if distance==0:assert .005<contact.Volume<.2,(angle,key,contact.Volume)
   samples.append({'outward_mm':distance,'crown_contact_mm3':contact.Volume,'outside_crown_mm3':unintended})
  row['pins'][key]=samples
 out['cases'].append(row);print('Repair envelope passed: '+str(angle)+' degree point',flush=True)
out['passed']=True
(O/'printed-repair-validation.json').write_text(json.dumps(out,indent=2)+'\n')
A.closeDocument(D.Name)
