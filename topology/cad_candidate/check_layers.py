"""Audit every 0.2 mm slice and preserve shell/core polygons for FEA mapping."""
from pathlib import Path
import json,pickle,csv,math
import numpy as np,trimesh
from shapely.geometry import GeometryCollection
from shapely.ops import unary_union
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'results';WORK=ROOT/'work';WORK.mkdir(exist_ok=True)
mesh=trimesh.load_mesh(OUT/'left.stl',process=True)
assert mesh.is_watertight and mesh.is_winding_consistent
heights=np.arange(.1,24,.2)+.0001 # avoid a slice exactly tangent to the 8.5 mm hole bottom
paths=mesh.section_multiplane([0,0,0],[0,0,1],heights)
slices=[unary_union(p.polygons_full) if p is not None else GeometryCollection() for p in paths]
cores=[];rows=[]
for l,s in enumerate(slices):
    core=s.buffer(-1.2,join_style=2)
    for d in range(1,6):
        core=core.intersection(slices[l-d] if l>=d else GeometryCollection())
        core=core.intersection(slices[l+d] if l+d<len(slices) else GeometryCollection())
    cores.append(core)
    expansion=s.difference(slices[l-1].buffer(.2*math.tan(math.radians(30))+.025)) if l else GeometryCollection()
    rows.append({'layer':l+1,'z_mm':float(heights[l]),'area_mm2':s.area,'sparse_core_mm2':core.area,'estimated_polymer_mm2':s.area-.8*core.area,'beyond_30deg_support_mm2':expansion.area})
with (OUT/'layers.csv').open('w') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
with (WORK/'layer_regions.pkl').open('wb') as f:pickle.dump({'slices':slices,'cores':cores,'heights':heights},f)
gcode=(ROOT/'orca/plate_1.gcode').read_text()
import re
mass=float(re.search(r'; filament used \[g\] = ([\d.]+)',gcode).group(1))
report={'mesh_watertight':bool(mesh.is_watertight),'mesh_volume_mm3':float(mesh.volume),'orca_pair_mass_g':mass,'geometric_pair_mass_g':2*sum(r['estimated_polymer_mm2']*.2 for r in rows)*.00127,'maximum_beyond_30deg_support_mm2':max(r['beyond_30deg_support_mm2'] for r in rows),'total_beyond_30deg_support_mm2':sum(r['beyond_30deg_support_mm2'] for r in rows),'support_audit_tolerance_mm':.025,'sample_plane_offset_mm':.0001,'layers':len(rows),'notes':'Geometric support audit uses successive mesh slices, with 0.025 mm chord/tessellation allowance. Infill skins naturally span the infill; this audit concerns external shape support.'}
(OUT/'layer_validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

# Independent perturbation: bracket the exact tangency, then check the next layer.
probe=mesh.section_multiplane([0,0,0],[0,0,1],[8.4999,8.5001,8.7001])
polys=[unary_union(p.polygons_full) for p in probe]
report['tangent_crosscheck']={'areas_mm2':[p.area for p in polys], 'next_layer_unsupported_mm2':[polys[2].difference(p.buffer(.2*math.tan(math.radians(30))+.025)).area for p in polys[:2]]}
assert max(report['tangent_crosscheck']['next_layer_unsupported_mm2'])<1e-5
(OUT/'layer_validation.json').write_text(json.dumps(report,indent=2)+'\n')
