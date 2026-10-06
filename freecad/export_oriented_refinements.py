from pathlib import Path
import json,sys
import FreeCAD as A,Part,MeshPart,Mesh
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,A.getResourceDir()+'Mod/Assembly')
d=A.openDocument(str(ROOT/'FinishValidation.FCStd'))
p=A.Placement(A.Vector(0,67,-84),A.Rotation(A.Vector(1,0,0),45)).multiply(A.Placement(A.Vector(0,-70,104),A.Rotation()))
out=ROOT/'print_refinements_oriented';out.mkdir(exist_ok=True);manifest={}
for o in d.getObject('InstalledAssembly').Group:
 if o.TypeId!='App::Link' or not any(t in o.InstanceKey for t in ['fan_duct','fan_tray','outlet_rail']):continue
 s=o.Shape.copy()
 if 'outlet_rail' in o.InstanceKey:s.rotate(A.Vector(),A.Vector(1,0,0),180);orientation='lip down'
 else:s.Placement=p.inverse().multiply(s.Placement);orientation='inlet down' if 'fan_duct' in o.InstanceKey else 'grille down'
 b=s.BoundBox;s.translate(A.Vector(128-(b.XMin+b.XMax)/2,128-(b.YMin+b.YMax)/2,-b.ZMin));b=s.BoundBox
 assert b.XMin>=8 and b.YMin>=8 and b.XMax<=248 and b.YMax<=248 and b.ZMax<=256
 assert b.XMin-8>=18 or b.YMin-8>=28
 m=MeshPart.meshFromShape(Shape=s,LinearDeflection=.05,AngularDeflection=.0872665,Relative=False)
 vertices,faces=m.Topology
 vertices=[A.Vector(round(v.x,7),round(v.y,7),round(v.z,7)) for v in vertices]
 triangles=[[vertices[i] for i in f] for f in faces]
 triangles=[t for t in triangles if (t[1]-t[0]).cross(t[2]-t[0]).Length>1e-12]
 m=Mesh.Mesh(triangles)
 m.removeDuplicatedPoints();m.removeDuplicatedFacets();m.fixDegenerations();m.harmonizeNormals()
 # OCC tessellated two shared 0.01-mm seams with unequal subdivisions.
 # Split only existing long boundary edges at existing collinear boundary vertices.
 from collections import Counter
 for repair_pass in range(3):
  if m.isSolid():break
  vv,ff=m.Topology;counts=Counter(tuple(sorted((f[i],f[(i+1)%3]))) for f in ff for i in range(3))
  boundary={i for e,c in counts.items() if c==1 for i in e};rebuilt=[];splits=0
  for f in ff:
   replacement=None
   for j in range(3):
    a,b,c=f[j],f[(j+1)%3],f[(j+2)%3]
    if counts[tuple(sorted((a,b)))]!=1:continue
    delta=vv[b]-vv[a];length2=delta.dot(delta)
    if length2<1e-12:continue
    inner=[]
    for k in boundary-{a,b,c}:
     t=(vv[k]-vv[a]).dot(delta)/length2
     if 1e-5<t<1-1e-5 and (vv[k]-(vv[a]+delta*t)).Length<1e-5:inner.append((t,k))
    if inner:
     ids=[a]+[k for t,k in sorted(inner)]+[b]
     replacement=[(ids[q],ids[q+1],c) for q in range(len(ids)-1)];splits+=len(inner);break
   rebuilt.extend(replacement if replacement else [f])
  if not splits:break
  m=Mesh.Mesh([[vv[i] for i in f] for f in rebuilt]);m.harmonizeNormals()
 assert m.isSolid(),o.InstanceKey
 m.write(str(out/(o.InstanceKey+'.stl')))
 manifest[o.InstanceKey]={'orientation':orientation,'dimensions_mm':[s.BoundBox.XLength,s.BoundBox.YLength,s.BoundBox.ZLength],'closed_mesh':True,'8mm_brim_and_cutter_clear':True}
(out/'manifest.json').write_text(json.dumps({'machine':'P1S','nozzle_mm':.4,'layer_mm':.2,'material':'ASA','arms':'Frozen; not regenerated','slicing':'Toolpaths not validated','parts':manifest},indent=2))
print('Oriented revised STLs:',len(manifest),flush=True)
A.closeDocument(d.Name)
