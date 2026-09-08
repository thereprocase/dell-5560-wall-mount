"""Compare like-for-like screening cases; do not convert stiffness into a strength rating."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parent
old=ROOT.parent/'cad_candidate/results';new=ROOT/'results'
rows=[]
for h in ['1.8','1.2']:
    before=json.loads((old/('structure_'+h+'.json')).read_text())
    after=json.loads((new/('structure_'+h+'.json')).read_text())
    for name,a,b in zip(['downward','outward_grab','side'],before['responses'],after['responses']):
        u,v=a['max_loaded_displacement_mm'],b['max_loaded_displacement_mm']
        rows.append({'mesh_mm':float(h),'case':name,'before_mm':u,'gusseted_mm':v,'displacement_reduction_percent':100*(1-v/u),'before_peak_absolute_component_MPa':max(a['max_abs_stress_MPa']),'gusseted_peak_absolute_component_MPa':max(b['max_abs_stress_MPa'])})
mass=json.loads((new/'layer_validation.json').read_text())['orca_pair_mass_g']
r={'baseline':'../cad_candidate','pair_mass_g':mass,'added_pair_mass_g':mass-50.28,'cases':rows,'conclusion':'Gussets improve screened stiffness; peak grab stress remains essentially unchanged and mesh-sensitive. No strength rating.'}
(new/'comparison.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
