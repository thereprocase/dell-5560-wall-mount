"""Headless BESO/CalculiX fanless bracket study. Units: mm, N, MPa.

Run with BESO_SOURCE and CCX pointing to pinned BESO checkout and CalculiX.
This is a side-profile concept study, not an installation-rated bracket.
"""
import os, json, shutil, subprocess, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
H = 2.0
NX, NY = 30, 45
THICKNESS = 10.0

def grid():
    nodes = {1+j*(NX+1)+i: (i*H,j*H,0) for j in range(NY+1) for i in range(NX+1)}
    elements = {}
    fixed = set()
    for j in range(NY):
        for i in range(NX):
            e=1+j*NX+i; n=1+j*(NX+1)+i
            elements[e]=(n,n+1,n+NX+2,n+NX+1)
            if (i<5 and (j<7 or j>=34)) or (i>=17 and j>=40): fixed.add(e)
    return nodes,elements,fixed

def deck(filename, active=None, modulus=None):
    nodes,elements,fixed=grid()
    if active is not None: elements={e:ns for e,ns in elements.items() if e in active}
    used={n for ns in elements.values() for n in ns}
    lines=['*HEADING','Fanless topology concept; mm N MPa; ideal fixed interfaces','*NODE']
    lines += [f'{n}, {x}, {y}, {z}' for n,(x,y,z) in nodes.items() if n in used]
    lines += ['*ELEMENT,TYPE=CPS4,ELSET=ALL']+[str(e)+','+','.join(map(str,ns)) for e,ns in elements.items()]
    for name,es in [('DESIGN',set(elements)-fixed),('KEEP',set(elements)&fixed)]:
        lines += ['*ELSET,ELSET='+name]
        ids=sorted(es)
        lines += [','.join(map(str,ids[k:k+16])) for k in range(0,len(ids),16)]
    if modulus is None:
        lines += ['*MATERIAL,NAME=PETG_EQ','*ELASTIC','1000.,0.35','*SOLID SECTION,ELSET=ALL,MATERIAL=PETG_EQ',str(THICKNESS)]
    else:
        # Binned through-thickness effective stiffness; not a resolved slicer toolpath.
        for E in sorted(set(modulus.values())):
            es=[e for e in elements if modulus[e]==E];name='M'+str(int(E))
            lines += ['*ELSET,ELSET='+name]
            lines += [','.join(map(str,es[k:k+16])) for k in range(0,len(es),16)]
            lines += ['*MATERIAL,NAME='+name,'*ELASTIC',f'{E},0.35',f'*SOLID SECTION,ELSET={name},MATERIAL={name}',str(THICKNESS)]
    supports=[n for n in used if nodes[n][0]==0 and (nodes[n][1]<=12 or nodes[n][1]>=70)]
    loads=[n for n in used if nodes[n][1]==90 and 38<=nodes[n][0]<=58]
    assert len(loads)==11 and len(supports)>4
    lines += ['*NSET,NSET=SUPPORT','\n'.join(','.join(map(str,sorted(supports)[k:k+16])) for k in range(0,len(supports),16)),'*NSET,NSET=LOAD',','.join(map(str,sorted(loads))),'*BOUNDARY','SUPPORT,1,2']
    for fx,fy in [(30.,-2.5*9.81*3),(50.,30.)]:
        lines += ['*STEP','*STATIC','*CLOAD,OP=NEW']
        lines += [f'{n},1,{fx/len(loads)}\n{n},2,{fy/len(loads)}' for n in sorted(loads)]
        lines += ['*NODE PRINT,NSET=LOAD','U','*EL PRINT,ELSET=ALL','S,ENER','*NODE FILE','U','*EL FILE','S','*END STEP']
    Path(filename).write_text('\n'.join(lines)+'\n')

def run():
    beso=Path(os.environ['BESO_SOURCE']).resolve();ccx=Path(os.environ['CCX']).resolve()
    work=ROOT/'work';work.mkdir(exist_ok=True)
    provenance={'beso_commit':subprocess.check_output(['git','-C',str(beso),'rev-parse','HEAD'],text=True).strip(),
                'ccx_version':subprocess.run([str(ccx),'-v'],text=True,capture_output=True).stdout.strip(),
                'python':sys.version,'numpy':np.__version__}
    (work/'environment.json').write_text(json.dumps(provenance,indent=2))
    for ratio in [.4,.25]:
        case=work/f'v{int(ratio*100):02}';case.mkdir(exist_ok=True)
        if (case/'console.log').exists(): raise RuntimeError(f'Refusing to overwrite {case}')
        for p in beso.glob('beso_*.py'):shutil.copy2(p,case/p.name)
        deck(case/'bracket.inp')
        config=f'''path = {str(case)!r}
path_calculix = {str(ccx)!r}
file_name = 'bracket.inp'
for name in ['DESIGN','KEEP']:
    domain_optimized[name] = name == 'DESIGN'
    domain_density[name] = [1e-6,1.0]
    domain_thickness[name] = [10.,10.]
    domain_material[name] = ['*ELASTIC\\n0.001,0.35','*ELASTIC\\n1000.,0.35']
    domain_FI[name] = []
mass_goal_ratio = {ratio}
filter_list = [['simple',4.0]]
optimization_base = 'stiffness'
cpu_cores = 2
sensitivity_averaging = True
mass_addition_ratio = .01
mass_removal_ratio = .04
ratio_type = 'absolute'
iterations_limit = 55
tolerance = .001
displacement_graph = [['LOAD','total']]
save_iteration_results = 1
save_solver_files = 'dat'
save_resulting_format = 'csv vtk'
'''
        (case/'beso_conf.py').write_text(config)
        with (case/'console.log').open('w') as f:
            r=subprocess.run([sys.executable,str(case/'beso_main.py')],cwd=case,env={**os.environ,'MPLBACKEND':'Agg','OMP_NUM_THREADS':'2','OPENBLAS_NUM_THREADS':'1'},stdout=f,stderr=subprocess.STDOUT)
        if r.returncode:raise RuntimeError(f'BESO failed: {case}/console.log')
        print('Completed',case.name,flush=True)

if __name__=='__main__':run()
