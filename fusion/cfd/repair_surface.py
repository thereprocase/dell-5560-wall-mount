"""Repair CAD tessellation seams by reloading topology; validate geometry face by face."""
import json, math, shutil
from pathlib import Path
import FreeCAD as App, Part, MeshPart
from prepare_installed_domain import export_surface, mesh_report
base=Path(__file__).resolve().parent
source=base/'geometry_traced_v1';out=base/'geometry_traced_repaired'
out.mkdir(exist_ok=True)
original=Part.read(str(source/'fluid_source.brep'))
reference=json.loads((source/'geometry_manifest.json').read_text())
trials=[]
for label,file in [('brep_reload','fluid_source.brep'),('step_reload','fluid.step')]:
 candidate=Part.read(str(source/file))
 mesh=MeshPart.meshFromShape(Shape=candidate,LinearDeflection=.1,AngularDeflection=.15,Relative=False,Segments=True)
 qa=mesh_report(mesh);trials.append(dict(method=label,mesh=qa))
 print(label,json.dumps(qa),flush=True)
 if qa['boundary_edges']==0 and qa['nonmanifold_edges']==0 and not qa['freecad_self_intersections']:break
else:raise RuntimeError('No closed triangulation candidate')
assert candidate.isValid() and candidate.isClosed() and len(candidate.Solids)==1
assert len(original.Faces)==len(candidate.Faces)
original_faces=original.Faces
centres=[face.CenterOfMass for face in original_faces]
remaining=set(range(len(original_faces)));owners=[];maxdist=0;maxarea=0;maxcentre=0;pairs=[]
for j,face in enumerate(candidate.Faces):
 if j%100==0:print("Comparing face",j,flush=True)
 centre=face.CenterOfMass
 i=min(remaining,key=lambda idx:(centres[idx]-centre).Length)
 other=original_faces[i];remaining.remove(i)
 cd=(other.CenterOfMass-centre).Length;ad=abs(other.Area-face.Area)
 assert cd<.001 and ad<max(.001,face.Area*1e-7),(j,i,cd,ad)
 # Bidirectional boundary-vertex and projected-interior samples on paired faces.
 distances=[]
 for a,b in [(face,other),(other,face)]:
  pts=[v.Point for v in a.Vertexes]
  pts.append(a.distToShape(Part.Vertex(a.CenterOfMass))[1][0][0])
  for pt in pts:distances.append(Part.Vertex(pt).distToShape(b)[0])
 dist=max(distances);assert dist<.001,(j,i,dist)
 maxdist=max(maxdist,dist);maxarea=max(maxarea,ad);maxcentre=max(maxcentre,cd)
 owners.append(reference['boundary_faces'][i]['patch'])
 pairs.append(dict(candidate_face=j,source_face=i,max_sample_distance_mm=dist,area_delta_mm2=ad))
assert not remaining
vol_delta=abs(candidate.Volume-original.Volume)
assert vol_delta<original.Volume*1e-6
report=dict(method=label,trials=trials,paired_faces=len(pairs),maximum_bidirectional_sample_distance_mm=maxdist,
 maximum_face_centroid_delta_mm=maxcentre,maximum_face_area_delta_mm2=maxarea,volume_delta_mm3=vol_delta,
 validation_tolerance_mm=.001,surface_deflection_mm=.1,comparison='Bidirectional per-face geometric samples, centroid and area; no claim of exact coincident Boolean equality',pairs=pairs)
qa=export_surface(candidate,owners,out,.1)
assert qa['boundary_edges']==0 and qa['nonmanifold_edges']==0 and qa['freecad_self_intersections']==0
candidate.exportStep(str(out/'fluid.step'))
shutil.copytree(source/'zones',out/'zones',dirs_exist_ok=True)
reference['surface_mesh']=qa;reference['geometry_ready']=True;reference['repair']=report
reference['boundary_faces']=[dict(index=j,patch=owner) for j,owner in enumerate(owners)]
reference['solver_case_ready']=False
(out/'geometry_manifest.json').write_text(json.dumps(reference,indent=2))
with (out/'fluid_boundary.stl').open('w') as f:
 for name in ('printed','laptop','noctua','wall_plane','ambient_openings'):f.write((out/(name+'.stl')).read_text())
print(json.dumps({k:v for k,v in report.items() if k not in ('pairs','trials')},indent=2),flush=True)
