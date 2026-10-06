from pathlib import Path
import random,json,math
from generate_case import read_triangles,combined_stl,cross,sub,dot
base=Path(__file__).resolve().parent;src=base/'geometry_traced_repaired'
patches={n:read_triangles(src/(n+'.stl')) for n in ['printed','laptop','noctua','wall_plane','ambient_openings']}
for exponent in (10,9,8):
 rng=random.Random(5560);mapping={};eps=10**-exponent
 for tris in patches.values():
  for tri in tris:
   for p in tri:
    if p in mapping:continue
    if any(abs(p[i]-v)<1e-12 for i,v in [(0,-.4),(0,.4),(1,0),(1,.45),(2,-.3),(2,.5)]):mapping[p]=p
    else:mapping[p]=tuple(v+eps*rng.uniform(-1,1) for v in p)
 moved={n:[tuple(mapping[p] for p in tri) for tri in tris] for n,tris in patches.items()}
 flips=0
 for n,tris in patches.items():
  for a,b in zip(tris,moved[n]):
   if dot(cross(sub(a[1],a[0]),sub(a[2],a[0])),cross(sub(b[1],b[0]),sub(b[2],b[0])))<=0:flips+=1
 path=src/f'fluid_stabilized_{exponent}.stl';path.write_text(combined_stl(moved))
 report={'seed':5560,'max_vertex_displacement_m':max(math.dist(p,q) for p,q in mapping.items()),'flipped_normals':flips,'method':'Bounded deterministic sub-micrometre perturbation of interior boundary vertices; domain planes fixed; manufacturing CAD unchanged'}
 path.with_suffix('.json').write_text(json.dumps(report,indent=2));print(exponent,report)
