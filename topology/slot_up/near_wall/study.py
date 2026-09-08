"""3D slot-inclusive fanless mount search. Coordinates: x=wall distance,
y=height, z=print height / inward reach from the laptop's outer side.
Units mm/N/MPa. Explicit laptop void; distributed contact-surface loads.
"""
import os,sys,json,shutil,subprocess
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent
H=2.; NX,NY,NZ=18,48,6

def en(i,j,k):return 1+i+NX*(j+NY*k)
def nid(i,j,k):return 1+i+(NX+1)*(j+(NY+1)*k)
def grid():
    nodes={nid(i,j,k):(H*i,H*j,H*k) for k in range(NZ+1) for j in range(NY+1) for i in range(NX+1)}
    elements={};keep=set()
    for k in range(NZ):
        for j in range(NY):
            for i in range(NX):
                x,y,z=H*(i+.5),H*(j+.5),H*(k+.5)
                if 8<x<28 and y>6 and z>4:continue # laptop insertion volume
                e=en(i,j,k)
                elements[e]=[nid(i,j,k),nid(i+1,j,k),nid(i+1,j+1,k),nid(i,j+1,k),nid(i,j,k+1),nid(i+1,j,k+1),nid(i+1,j+1,k+1),nid(i,j+1,k+1)]
                if (x<10 and (6<y<24 or 72<y<96)) or (4<x<36 and y<6) or (6<x<8 and y>6) or (28<x<30 and y>6) or (10<x<26 and 74<y<86 and z<4):keep.add(e)
    return nodes,elements,keep

def elastic(scale=1):
    return '*ELASTIC,TYPE=ENGINEERING CONSTANTS\n'+','.join(str(x) for x in [1800*scale,1800*scale,900*scale,.3,.3,.3,690*scale,345*scale])+'\n'+str(345*scale)

def deck(path,active=None,scales=None):
    nodes,els,keep=grid()
    if active is not None:els={e:ns for e,ns in els.items() if e in active}
    used=set(n for ns in els.values() for n in ns)
    def lines_ids(ids):
        ids=sorted(ids);return [','.join(map(str,ids[k:k+16])) for k in range(0,len(ids),16)]
    lines=['*HEADING','Slot-up 3D topology; assumed orthotropic PETG; ideal wall supports','*ORIENTATION,NAME=PRINT_FRAME','1,0,0,0,1,0','*NODE']
    lines += [f'{n},{x},{y},{z}' for n,(x,y,z) in nodes.items() if n in used]
    lines+=['*ELEMENT,TYPE=C3D8,ELSET=ALL']+[str(e)+','+','.join(map(str,ns)) for e,ns in els.items()]
    for name,ids in [('DESIGN',set(els)-keep),('KEEP',set(els)&keep)]:lines+=['*ELSET,ELSET='+name]+lines_ids(ids)
    if scales is None:
        lines+=['*MATERIAL,NAME=PETG',elastic(.5),'*SOLID SECTION,ELSET=ALL,MATERIAL=PETG,ORIENTATION=PRINT_FRAME']
    else:
        for s in sorted(set(scales.values())):
            name='M'+str(int(s*1000));lines+=['*ELSET,ELSET='+name]+lines_ids([e for e in els if scales[e]==s])
            lines+=['*MATERIAL,NAME='+name,elastic(s),f'*SOLID SECTION,ELSET={name},MATERIAL={name},ORIENTATION=PRINT_FRAME']
    groups={
      'SUPPORT':[n for n in used if nodes[n][0]==0 and (10<=nodes[n][1]<=20 or 80<=nodes[n][1]<=90)],
      'SEAT':[n for n in used if nodes[n][1]==6 and 10<=nodes[n][0]<=26 and 6<=nodes[n][2]<=10],
      'FRONT':[n for n in used if nodes[n][0]==28 and 80<=nodes[n][1]<=90 and 6<=nodes[n][2]<=10],
      'SIDE':[n for n in used if nodes[n][2]==4 and 12<=nodes[n][0]<=24 and 76<=nodes[n][1]<=84]}
    assert len(groups['SEAT'])==27 and len(groups['FRONT'])==18
    # SIDE face is part of the design space. Keep its loaded strips explicitly.
    assert groups['SIDE']
    groups['MONITOR']=set(groups['SEAT']+groups['FRONT']+groups['SIDE'])
    for name,ids in groups.items():lines+=['*NSET,NSET='+name]+lines_ids(ids)
    lines+=['*BOUNDARY','SUPPORT,1,3']
    cases=[{'SEAT':(0,-73.575,0)}, {'SEAT':(0,-24.525,0),'FRONT':(30,0,0)}, {'SEAT':(0,-24.525,0),'SIDE':(0,0,-20)}]
    for loads in cases:
        lines+=['*STEP','*STATIC','*CLOAD,OP=NEW']
        for name,f in loads.items():
            for d,v in enumerate(f,1):
                if v:lines += [f'{n},{d},{v/len(groups[name])}' for n in groups[name]]
        lines+=['*NODE PRINT,NSET=MONITOR','U','*EL PRINT,ELSET=ALL','S,ENER','*NODE FILE','U','*EL FILE','S','*END STEP']
    Path(path).write_text('\n'.join(lines)+'\n')
    return groups

def run():
    runtime=ROOT.parents[1]/'runtime';work=ROOT/'work';work.mkdir(exist_ok=True)
    beso=runtime/'beso';ccx=runtime/'usr/bin/ccx'
    # Protect narrow contact strips on the cheek so optimization cannot delete loads.
    for ratio in [.45,.3]:
        case=work/f'v{int(ratio*100)}';case.mkdir(exist_ok=True)
        if (case/'console.log').exists():raise RuntimeError('Existing case: '+str(case))
        for p in beso.glob('beso_*.py'):shutil.copy2(p,case/p.name)
        # Upstream casting filter preallocates sectors incompletely for negative transformed coordinates.
        fp=case/'beso_filters.py';fs=fp.read_text();start=fs.index('def prepare2s_casting(')
        fs=fs[:start]+fs[start:].replace('sector_elm[tuple(sector_centre)].append(en)','sector_elm.setdefault(tuple(sector_centre), []).append(en)')
        fp.write_text(fs)
        deck(case/'bracket.inp')
        conf=f'''path={str(case)!r}
path_calculix={str(ccx)!r}
file_name='bracket.inp'
for name in ['DESIGN','KEEP']:
 domain_optimized[name]=name=='DESIGN'
 domain_density[name]=[1e-6,1]
 domain_material[name]={[elastic(.5e-6),elastic(.5)]!r}
 domain_FI[name]=[]
 domain_orientation[name]=['PRINT_FRAME','PRINT_FRAME']
mass_goal_ratio={ratio}
filter_list=[['simple',4.],['casting',.5,(0,0,1)]]
optimization_base='stiffness'
cpu_cores=2
sensitivity_averaging=True
mass_addition_ratio=.01
mass_removal_ratio=.04
ratio_type='absolute'
iterations_limit=50
tolerance=.001
displacement_graph=[['MONITOR','total']]
save_iteration_results=1
save_solver_files='dat'
save_resulting_format='csv vtk'
'''
        (case/'beso_conf.py').write_text(conf)
        env={**os.environ,'LD_LIBRARY_PATH':str(runtime/'usr/lib/x86_64-linux-gnu'),'OMP_NUM_THREADS':'2','OPENBLAS_NUM_THREADS':'1','MPLBACKEND':'Agg','PYTHONUNBUFFERED':'1'}
        with (case/'console.log').open('w') as f:r=subprocess.run([sys.executable,str(case/'beso_main.py')],cwd=case,env=env,stdout=f,stderr=subprocess.STDOUT)
        if r.returncode:raise RuntimeError('BESO failure: '+str(case))
        print('Completed',case.name,flush=True)

if __name__=='__main__':run()
