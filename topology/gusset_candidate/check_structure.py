"""Mesh the exact perforated CAD; screen orthotropic, layer-weighted PETG.
Idealized clamps act only on the washer-bearing annuli, not the whole wall pad.
"""
from pathlib import Path
import sys,os,json,pickle,subprocess,math
import numpy as np,gmsh
from shapely import contains_xy
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'results';WORK=ROOT/'work';WORK.mkdir(exist_ok=True)
h=float(sys.argv[1]) if len(sys.argv)>1 else 2.5
case=WORK/('fea_'+str(h));case.mkdir(exist_ok=True)
gmsh.initialize();gmsh.option.setNumber('General.Terminal',0);gmsh.model.add('curved_mount');gmsh.model.occ.importShapes(str(OUT/'left.step'));gmsh.model.occ.synchronize()
gmsh.option.setNumber('Mesh.MeshSizeMin',.65);gmsh.option.setNumber('Mesh.MeshSizeMax',h);gmsh.option.setNumber('Mesh.MeshSizeFromCurvature',10);gmsh.option.setNumber('Mesh.Algorithm3D',1);gmsh.option.setNumber('General.NumThreads',2)
gmsh.model.mesh.generate(3)
tags,coords,_=gmsh.model.mesh.getNodes();coords=np.array(coords).reshape(-1,3);lookup={int(t):i+1 for i,t in enumerate(tags)}
types,etags,enodes=gmsh.model.mesh.getElements(3);ix=list(types).index(4);elems=np.array([[lookup[int(n)] for n in row] for row in np.array(enodes[ix]).reshape(-1,4)])
gmsh.write(str(case/'mesh.msh'));gmsh.finalize()
tet=coords[elems-1];vol=np.abs(np.linalg.det(tet[:,1:]-tet[:,0,None,:]))/6
assert vol.min()>1e-10
with (WORK/'layer_regions.pkl').open('rb') as f:regions=pickle.load(f)
# Five representative interior points estimate local solid/core coverage.
cent=tet.mean(axis=1);samples=np.stack([cent,*[.6*cent+.4*tet[:,k] for k in range(4)]],axis=1)
flat=samples.reshape(-1,3);layer=np.clip((flat[:,2]/.2).astype(int),0,len(regions['cores'])-1);sparse=np.zeros(len(flat),bool)
for l in np.unique(layer):
    take=layer==l;sparse[take]=contains_xy(regions['cores'][l],flat[take,0],flat[take,1])
solid=1-sparse.reshape(-1,5).mean(axis=1);scales=np.round(solid+(1-solid)*.04,3)
a=math.radians(4.198081958929171);c,s=math.cos(a),math.sin(a)
x,y,z=coords.T;lx=20+c*(x-20)-s*(y-6);ly=6+s*(x-20)+c*(y-6)
groups={}
groups['FIX']=np.flatnonzero((abs(x-4)<.02)&(((y-18)**2+(z-12)**2<7.5**2)|((y-132)**2+(z-12)**2<7.5**2)))+1
groups['SEAT']=np.flatnonzero((abs(ly-6)<.02)&(lx>22)&(lx<40)&(z>5.4)&(z<14.8))+1
groups['FRONT']=np.flatnonzero((abs(lx-42)<.02)&(ly>85)&(ly<114)&(z>5.4)&(z<14.8))+1
groups['REAR']=np.flatnonzero((abs(lx-20)<.02)&(ly>49)&(ly<63)&(z>5.4)&(z<14.8))+1
groups['SIDE']=np.flatnonzero((abs(z-4.8)<.02)&(lx>23)&(lx<40)&(ly>30)&(ly<125))+1
assert all(len(v)>=3 for v in groups.values()),{k:len(v) for k,v in groups.items()}
def ids(v):return [','.join(map(str,v[i:i+16])) for i in range(0,len(v),16)]
lines=['*HEADING','Curved CAD, washer-seat clamps, assumed orthotropic PETG','*ORIENTATION,NAME=PRINT','1,0,0,0,1,0','*NODE']+[f'{i},{p[0]:.10g},{p[1]:.10g},{p[2]:.10g}' for i,p in enumerate(coords,1)]
lines+=['*ELEMENT,TYPE=C3D4,ELSET=ALL']+[str(i)+','+','.join(map(str,ns)) for i,ns in enumerate(elems,1)]
for scale in np.unique(scales):
    name='M'+str(round(scale*1000));lines+=['*ELSET,ELSET='+name]+ids((np.flatnonzero(scales==scale)+1).tolist())
    lines+=['*MATERIAL,NAME='+name,'*ELASTIC,TYPE=ENGINEERING CONSTANTS',f'{1800*scale},{1800*scale},{900*scale},.3,.3,.3,{690*scale},{345*scale}',str(345*scale),f'*SOLID SECTION,ELSET={name},MATERIAL={name},ORIENTATION=PRINT']
for name,ns in groups.items():lines+=['*NSET,NSET='+name]+ids(ns.tolist())
monitor=np.unique(np.concatenate(list(groups.values()))).tolist();lines+=['*NSET,NSET=MONITOR']+ids(monitor)+['*BOUNDARY','FIX,1,3']
means={name:coords[ns-1].mean(axis=0) for name,ns in groups.items()}
xcom=20+c*11+s*115.15;gripy=6-s*11+c*190
cases=[]
for W,F,side in [(73.575,0,0),(24.525,30,0),(24.525,0,-20)]:
    # Balance gravity's extra lever arm from the lean, and an outward pull
    # 190 mm up the laptop, with front/rear normal reactions.
    yf,yr=means['FRONT'][1],means['REAR'][1]
    front=(W*(xcom-means['SEAT'][0])+F*(gripy-yr))/(yf-yr)
    loads={'SEAT':(0,-W,0),'FRONT':(front,0,0),'REAR':(F-front,0,0)}
    if side:loads['SIDE']=(0,0,side)
    cases.append(loads);lines+=['*STEP','*STATIC','*CLOAD,OP=NEW']
    for name,forces in loads.items():
        for d,f in enumerate(forces,1):
            if f:lines += [f'{n},{d},{f/len(groups[name])}' for n in groups[name]]
    lines+=['*NODE PRINT,NSET=MONITOR','U','*EL PRINT,ELSET=ALL','S','*END STEP']
(case/'check.inp').write_text('\n'.join(lines)+'\n')
runtime=ROOT.parent/'runtime';env={**os.environ,'LD_LIBRARY_PATH':str(runtime/'usr/lib/x86_64-linux-gnu'),'OMP_NUM_THREADS':'2','OPENBLAS_NUM_THREADS':'1'}
with (case/'console.log').open('w') as f:subprocess.run([str(runtime/'usr/bin/ccx'),'-i','check'],cwd=case,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
sys.path.insert(0,str(ROOT.parent/'slot_up'));from recheck import parse_dat
report={'mesh_size_mm':h,'nodes':len(coords),'tetrahedra':len(elems),'mesh_volume_mm3':float(vol.sum()),'group_nodes':{k:len(v) for k,v in groups.items()},'group_centres_mm':{k:v.tolist() for k,v in means.items()},'loads_N':cases,'responses':parse_dat(case/'check.dat'),'assumptions':['C3D4 linear tetrahedra; mesh refinement comparison required','Ideal fully fixed washer-bearing annuli; no anchor or friction rating','XY E=1800 MPa, Z E=900 MPa; directional shear scaled consistently','Element solid fraction from five sample points in 0.2 mm shell/core slices; infill stiffness factor 0.04','Outward pull moment balanced for a grip 190 mm above laptop base','Side case applies 20 N across the cheek contact region, not a full two-bracket contact simulation']}
(OUT/('structure_'+str(h)+'.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
