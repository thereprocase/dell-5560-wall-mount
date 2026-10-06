"""Conforming Gmsh triangulation of the geometrically checked STEP boundary."""
from pathlib import Path
import json, math
from collections import Counter
import sys,os
sys.path.insert(0,str(Path(__file__).resolve().parent/'vendor/downloads/gmsh_api'))
os.environ['PATH']='C:/Program Files/FreeCAD 1.1/bin;'+os.environ.get('PATH','')
import gmsh
import FreeCAD as App, Part
from prepare_installed_domain import write_stl
base=Path(__file__).resolve().parent
src=base/'geometry_traced_repaired';out=base/'geometry_traced_gmsh';out.mkdir(exist_ok=True)
meta=json.loads((src/'geometry_manifest.json').read_text());cad=Part.read(str(src/'fluid.step'))
faces=cad.Faces;centres=[f.CenterOfMass for f in faces];available=set(range(len(faces)))
gmsh.initialize();gmsh.option.setNumber('General.NumThreads',8)
gmsh.model.occ.importShapes(str(src/'fluid.step'));gmsh.model.occ.synchronize()
entities=gmsh.model.getEntities(2);owners={};matches=[]
assert len(entities)==len(faces),(len(entities),len(faces))
for dim,tag in entities:
 c=App.Vector(*gmsh.model.occ.getCenterOfMass(dim,tag))
 i=min(available,key=lambda k:(centres[k]-c).Length)
 assert (centres[i]-c).Length<.001
 available.remove(i);owners[tag]=meta['boundary_faces'][i]['patch'];matches.append(dict(gmsh_surface=tag,cad_face=i))
gmsh.option.setNumber('Mesh.MeshSizeMin',.05);gmsh.option.setNumber('Mesh.MeshSizeMax',5)
gmsh.option.setNumber('Mesh.MeshSizeFromCurvature',64);gmsh.option.setNumber('Mesh.MeshSizeFromPoints',0)
gmsh.option.setNumber('Mesh.Algorithm',6)
gmsh.model.mesh.generate(2)
nodeids,coords,_=gmsh.model.mesh.getNodes();vertices=[App.Vector(*coords[i:i+3]) for i in range(0,len(coords),3)]
index={int(n):i for i,n in enumerate(nodeids)}
orient={abs(t):1 if t>0 else -1 for dim,t in gmsh.model.getBoundary(gmsh.model.getEntities(3),combined=True,oriented=True,recursive=False)}
facets=[];groups={p:[] for p in ('printed','laptop','noctua','wall_plane','ambient_openings')}
for dim,tag in entities:
 types,tags,nodes=gmsh.model.mesh.getElements(dim,tag)
 for typ,ids in zip(types,nodes):
  assert typ==2,typ
  for i in range(0,len(ids),3):
   tri=[index[int(x)] for x in ids[i:i+3]]
   # Gmsh mesh orientation is checked globally below.
   groups[owners[tag]].append(len(facets));facets.append(tri)
edges=Counter();winding=Counter()
for tri in facets:
 for a,b in zip(tri,tri[1:]+tri[:1]):edges[tuple(sorted((a,b)))]+=1;winding[tuple(sorted((a,b)))]+=1 if a<b else -1
qa=dict(triangles=len(facets),vertices=len(vertices),open_edges=sum(v==1 for v in edges.values()),nonmanifold=sum(v>2 for v in edges.values()),winding_errors=sum(v!=0 for v in winding.values()))
print(json.dumps(qa),flush=True)
gmsh.write(str(out/'surface.msh'))
assert qa['open_edges']==0 and qa['nonmanifold']==0 and qa['winding_errors']==0
for name,ids in groups.items():write_stl(out/(name+'.stl'),name,facets,vertices,ids)
with (out/'fluid_boundary.stl').open('w') as f:
 for name in groups:f.write((out/(name+'.stl')).read_text())
(out/'surface_qa.json').write_text(json.dumps(dict(qa=qa,gmsh_version=gmsh.__version__,source=str(src/'fluid.step'),matches=matches,check='OpenFOAM self-intersection check still required'),indent=2))
gmsh.finalize()
