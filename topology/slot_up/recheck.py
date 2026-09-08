"""Conservative column-supported geometry and layer-aware screening, not slicer G-code.
Five top/bottom layers are modelled by intersecting neighbouring slices; each
slice is eroded 1.2 mm for walls. Remaining internal space gets 20% material.
"""
import sys,os,json,csv,subprocess
from pathlib import Path
import numpy as np
from scipy.ndimage import label
from shapely.geometry import box,GeometryCollection
from shapely.ops import unary_union
from render_model import load_study,read_ids,mesh_from_ids,draw

def index(m,e):
    return (e-1)%m.NX,((e-1)//m.NX)%m.NY,(e-1)//(m.NX*m.NY)

def close_columns(m,ids):
    full=set(m.grid()[1]);out=set(ids)
    for e in ids:
        i,j,k=index(m,e)
        out.update(m.en(i,j,z) for z in range(k+1))
    assert out<=full,'Projection would fill laptop void'
    return out

def layer_material(m,ids,out):
    slices=[];sparse=[];rows=[];scales={};cells={}
    for e in ids:
        i,j,k=index(m,e);cells[e]=box(2*i,2*j,2*i+2,2*j+2)
    for k in range(m.NZ):
        s=unary_union([cells[e] for e in ids if index(m,e)[2]==k])
        slices.extend([s]*10)
    empty=GeometryCollection()
    for l,s in enumerate(slices):
        core=s.buffer(-1.2,join_style=2)
        wall=s.area-core.area
        for d in range(1,6):
            core=core.intersection(slices[l-d] if l-d>=0 else empty)
            core=core.intersection(slices[l+d] if l+d<len(slices) else empty)
        sparse.append(core)
        skin=s.area-wall-core.area
        rows.append({'layer':l+1,'z_mm':round(.2*(l+1),3),'wall_mm2':wall,'skin_mm2':skin,'infill_envelope_mm2':core.area,'polymer_mm2':wall+skin+.2*core.area})
    for e in ids:
        k=index(m,e)[2]
        sparse_v=sum(sparse[l].intersection(cells[e]).area*.2 for l in range(k*10,(k+1)*10))
        solid_fraction=1-sparse_v/8
        # Screening homogenization: solid skins in parallel with infill E~rho^2.
        scale=solid_fraction+(1-solid_fraction)*.2**2
        scales[e]=round(max(.025,round(scale/.025)*.025),3)
    with out.open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    return sum(r['polymer_mm2']*.2 for r in rows),scales

def parse_dat(p):
    cases=[];current=None;mode=None
    for line in p.read_text().splitlines():
        if 'displacements (' in line:
            current={'max_loaded_displacement_mm':0.,'max_abs_stress_MPa':[0.]*6};cases.append(current);mode='u';continue
        if 'stresses (' in line:mode='s';continue
        if 'internal energy' in line:mode=None
        a=line.split()
        if not a or not a[0].isdigit() or current is None:continue
        try:
            if mode=='u' and len(a)==4:current['max_loaded_displacement_mm']=max(current['max_loaded_displacement_mm'],float(np.linalg.norm([float(v) for v in a[1:]])))
            if mode=='s' and len(a)>=8:current['max_abs_stress_MPa']=np.maximum(current['max_abs_stress_MPa'],np.abs([float(v) for v in a[2:8]])).tolist()
        except ValueError:pass
    assert len(cases)==3,(p,len(cases))
    assert all(max(c['max_abs_stress_MPa'])>0 for c in cases),'No stresses parsed'
    return cases

def main():
    folder=Path(sys.argv[1]).resolve();m=load_study(folder);out=folder/'results';out.mkdir(exist_ok=True)
    runtime=Path(__file__).resolve().parents[1]/'runtime'
    env={**os.environ,'LD_LIBRARY_PATH':str(runtime/'usr/lib/x86_64-linux-gnu'),'OMP_NUM_THREADS':'2','OPENBLAS_NUM_THREADS':'1'}
    report={'method':'Layer geometry approximation, not Orca toolpaths; orthotropic stiffness screening, not a strength rating','layer_mm':.2,'wall_mm':1.2,'top_bottom_layers':5,'infill':.2,'density_g_mm3':.00127,'stress_order':['xx','yy','zz','xy','xz','yz'],'cases':{}}
    trials={'envelope':set(m.grid()[1])}
    for name in ['v45','v30']:
        states=sorted((folder/'work'/name).glob('file*.csv'));trials[name]=read_ids(states[-1])
    for name,raw in trials.items():
        ids=close_columns(m,raw)
        mask=np.zeros((m.NZ,m.NY,m.NX),bool)
        for e in ids:
            i,j,k=index(m,e);mask[k,j,i]=True
        components=label(mask)[1];assert components==1,(name,components)
        mesh=mesh_from_ids(m,ids)
        if not mesh.is_watertight or not mesh.is_winding_consistent:raise RuntimeError('Invalid surface '+name)
        assert abs(mesh.volume-len(ids)*8)<1e-5
        mesh.export(out/(name+'_screening.stl'))
        draw(m,ids,out/(name+'_supported.png'),name+' — column-supported screening geometry')
        volume,scales=layer_material(m,ids,out/(name+'_layers.csv'))
        work=folder/'work'/('recheck_'+name);work.mkdir(exist_ok=True)
        m.deck(work/'check.inp',active=ids,scales=scales)
        with (work/'console.log').open('w') as log:
            subprocess.run([str(runtime/'usr/bin/ccx'),'-i','check'],cwd=work,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
        results=parse_dat(work/'check.dat')
        report['cases'][name]={'raw_elements':len(raw),'supported_elements':len(ids),'added_for_support':len(ids)-len(raw),'connected_components':components,'watertight':bool(mesh.is_watertight),'external_volume_mm3':float(mesh.volume),'surface_area_mm2':float(mesh.area),'estimated_polymer_mm3':volume,'estimated_pair_mass_g':2*volume*.00127,'loads':results}
        print(name,report['cases'][name],flush=True)
    (out/'screening.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':main()
