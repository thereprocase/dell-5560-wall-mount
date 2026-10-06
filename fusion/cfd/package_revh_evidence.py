"""Publish compact, truthful evidence; raw meshes and solver fields stay local."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import zipfile
from datetime import datetime,timezone

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--case',type=Path,default=BASE/'runs/revh_transient_04')
args=parser.parse_args();case=args.case.resolve()
out=ROOT/'docs/simulation/revh-transient';out.mkdir(parents=True,exist_ok=True)

def read(name):
    p=case/name
    return p.read_text(errors='replace') if p.exists() else ''

def scrub(text):
    text=text.replace(str(ROOT).replace('\\','\\\\'),'REPOSITORY').replace(str(ROOT),'REPOSITORY').replace(str(ROOT).replace('\\','/'),'REPOSITORY')
    return re.sub(r'(?m)^(Host|PID)\s*:.*$',r'\1 : [local run]',text)

def copy_text(src,dst):
    if src.exists():(out/dst).write_text(scrub(src.read_text(errors='replace')),encoding='utf-8',newline='\n')

settings=json.loads(read('case_manifest.json'))
mesh_text=read('log.checkMesh.standard')
cells=re.search(r'^\s*cells:\s+(\d+)',mesh_text,re.M)
solver_logs=sorted(case.glob('log.pimpleFoam*'),key=lambda p:int(re.search(r'attempt(\d+)',p.name)[1]) if 'attempt' in p.name else 1)
solver_log=solver_logs[-1].name if solver_logs else 'log.pimpleFoam'
log=read(solver_log)
times=re.findall(r'^Time = ([\d.eE+-]+)',log,re.M)
completed=re.findall(r'^Time = ([\d.eE+-]+)\s*\n(?:(?!^Time = ).)*?ExecutionTime = ([\d.eE+-]+) s\s+ClockTime = ([\d.eE+-]+) s',log,re.M|re.S)
courant=re.findall(r'Courant Number mean: ([\d.eE+-]+) max: ([\d.eE+-]+)',log)
phases={p:json.loads(read('status.'+p+'.json')) if read('status.'+p+'.json') else {'state':'not_started'}
        for p in ['surface','mesh','zones','initialize','pilot']}
for phase in phases:
    for retry in sorted(case.glob('status.'+phase+'.attempt*.json'),key=lambda p:int(re.search(r'attempt(\d+)',p.name)[1])):
        phases[phase]=json.loads(retry.read_text())
summary={'updated_utc':datetime.now(timezone.utc).isoformat(),'geometry_revision':'H','case':case.name,
         'native_geometry_check':json.loads((BASE/'geometry_revh/native_step_probe_check.json').read_text())['pass'],
         'phases':{p:v['state'] for p,v in phases.items()},'cells':int(cells.group(1)) if cells else None,
         'requested_edge_cell_mm':.25,'requested_wake_cell_mm':.5,'requested_first_layer_mm':.06,
         'standard_mesh_ok':'Mesh OK.' in mesh_text,'expanded_mesh_ok':'Mesh OK.' in read('log.checkMesh.expanded'),
         'refinement_limit_hit':'reached limit' in read('log.snappyHexMesh'),
         'latest_started_time_s':float(times[-1]) if times else None,
         'latest_completed_time_s':float(completed[-1][0]) if completed else None,
         'completed_steps':len(completed),
         'solver_log_source':solver_log,
         'maximum_logged_Courant':max(float(b) for a,b in courant) if courant else None,
         'shedding_demonstrated':False,'lip_suction_demonstrated':False,
         'mesh_independence_demonstrated':False,'time_step_independence_demonstrated':False,'hardware_validated':False,
         'physics':'Isothermal transient SST URANS, four nominal 10 Pa constant-force actuators, traced laptop surrogate. No fan curves, grille/fin loss calibration or thermal solution.',
         'interpretation':'A short commissioning pilot does not establish settled flow, sustained shedding or a Bernoulli cause for pressure depression.'}
if read('quality-disposition.json'):summary['mesh_quality_disposition']=json.loads(read('quality-disposition.json'))
summary['Courant_note']='Maximum includes the mapped initial field before adaptive time-step adjustment; inspect the timestep log for actual advancement.'
coverage=re.findall(r'Extruding \d+ out of \d+ faces \(([\d.]+)%\)',read('log.snappyHexMesh'))
layer_cells=re.findall(r'Added (\d+) out of \d+ cells',read('log.snappyHexMesh'))
summary['reported_layer_coverage_percent']=float(coverage[-1]) if coverage else None
summary['reported_layer_cells']=int(layer_cells[-1]) if layer_cells else None
if read('commissioning-checkpoint-request.json'):
    summary['checkpoint_request']=json.loads(read('commissioning-checkpoint-request.json'))
    summary['intended_2ms_endpoint_completed']=bool(completed and float(completed[-1][0])>=.002-1e-12)
(out/'status.json').write_text(json.dumps(summary,indent=2)+'\n')
copy_text(case/'case_manifest.json','case-settings.json')
copy_text(BASE/'geometry_revh/native_step_probe_check.json','geometry-check.json')
for a,b in [('log.surfaceCheck','surface-check.txt'),('log.checkMesh.standard','mesh-check.txt'),
            ('log.checkMesh.expanded','mesh-check-expanded.txt')]:copy_text(case/a,b)
copy_text(case/'quality-disposition.json','quality-disposition.json')
copy_text(case/'commissioning-checkpoint-request.json','commissioning-checkpoint-request.json')
copy_text(case/solver_log,'solver-log.txt')
copy_text(case/'log.pimpleFoam','solver-log-attempt1.txt')
copy_text(case/'restart-attempt2.json','restart-attempt2.json')
for phase,data in phases.items():
    (out/('phase-'+phase+'.json')).write_text(scrub(json.dumps(data,indent=2))+'\n')
settings_dir=out/'dictionaries';settings_dir.mkdir(exist_ok=True)
for folder in ['system','constant']:
    for source in (case/folder).iterdir():
        if source.is_file():copy_text(source,'dictionaries/'+source.name)
copy_text(BASE/'REVH_TRANSIENT.md','METHOD.md')
inputs=[]
for p in [ROOT/'freecad/Precision_5560_Native.FCStd',ROOT/'freecad/Precision_5560_Native.step',
          ROOT/'profile_reconstruction.json',case/'constant/triSurface/fluid_boundary.stl',
          *sorted((case/'system').glob('*')),*sorted((case/'constant').glob('*'))]:
    if p.is_file():inputs.append({'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(out/'input-hashes.json').write_text(json.dumps(inputs,indent=2)+'\n')
if phases['pilot']['state']=='complete':
    samples=sorted(p for p in (case/'postProcessing').rglob('*') if p.is_file())
    archive=out/'commissioning-samples.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in samples:z.write(p,p.relative_to(case).as_posix())
    (out/'sample-hashes.json').write_text(json.dumps({'archive':archive.name,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
        'files':[{'path':p.relative_to(case).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in samples]},indent=2)+'\n')
rows=[('Rev H native / STEP geometry','Passed' if summary['native_geometry_check'] else 'Review required'),
      ('Surface check',phases['surface']['state']),('Mesh phase',phases['mesh']['state']),
      ('Volume cells',f"{summary['cells']:,}" if summary['cells'] else 'Not yet measured'),
      ('Standard / expanded mesh checks',f"{'Pass' if summary['standard_mesh_ok'] else 'Pending or failed'} / {'Pass' if summary['expanded_mesh_ok'] else 'Pending or failed'}"),
      ('Diagnostic restart',phases['pilot']['state']+'; original 2 ms endpoint not completed' if summary.get('checkpoint_request') else phases['pilot']['state']),
      ('Sustained vortex shedding','Not established'),('Laptop-lip suction','Not established'),
      ('Mesh / time-step independence','Not established'),('Hardware validation','Not established')]
table='\n'.join('| '+a+' | '+b+' |' for a,b in rows)
image='\n![Actual mesh sections through the duct and laptop lips](mesh-sections.png)\n' if (out/'mesh-sections.png').exists() else ''
quality=''
if summary.get('mesh_quality_disposition',{}).get('disposition')=='commissioning_only':
    q=summary['mesh_quality_disposition']
    quality=f"**Commissioning only.** The standard check passes, but expanded checks find {q['underdetermined_cells']:,} low-determinant cells, {q['low_weight_faces']} low-weight faces and {q['concave_cells']:,} concave cells. Defects include the lip regions. This mesh has not been accepted for validation. See [quality disposition](quality-disposition.json), [expanded check](mesh-check-expanded.txt) and [defect locations](mesh-defect-locations.json)."
readme=f'''# Revision H / transient airflow verification candidate

Updated {summary['updated_utc']}. This is a new study of the ducted Revision H assembly, separate from the earlier 836,278-cell Revision F exploration and the minimalist design.

| Check | Recorded status |
|---|---|
{table}
\n{quality}
{image}
The requested local cells are 0.25 mm at selected duct edges and front/hinge lips, with 0.5 mm wake and internal-passage refinement. Five wall layers are requested on printed and laptop surfaces, starting at 0.06 mm. Requested settings must not be mistaken for achieved quality or coverage.

`case-settings.json` records generation-time targets and initial gate flags. The current status, mesh review and check logs contain the achieved evidence.

The transient solver uses an adaptive Courant limit of 0.5, a maximum 25 microsecond step, and second-order momentum/time discretization. The original 2 ms pilot was curtailed; a parallel runtime dictionary-reload error prevented its requested checkpoint. The diagnostic restart targets 0.02 ms with fixed controls and every-step fields, probes and sections. This interval is far too short to establish mature flow or sustained shedding. Actual recorded timestamps and completion status govern interpretation. See the [latest solver log](solver-log.txt) and [restart record](restart-attempt2.json).

All fans remain nominal 10 Pa constant-force actuators. Laptop internals, grille resistance and fan operating points are uncalibrated. There is no temperature prediction. Negative pressure alone is not proof of a Bernoulli mechanism.

- [Machine-readable status](status.json)
- [Case settings and probe coordinates](case-settings.json)
- [Independent Rev H geometry and probe checks](geometry-check.json)
- [Method, acceptance criteria and GPU assessment](METHOD.md)
- [Input hashes](input-hashes.json)
- [Latest pilot diagnostics](pilot-review.json)
- [Startup video (MP4, four recorded frames)](pilot-sections.mp4)
- [Plot and animation provenance](animation-provenance.json)
- [Raw probes, local sections and diagnostics](commissioning-samples.zip) ([hashes](sample-hashes.json))

Raw meshes, partitioned fields and unsuccessful trials are retained locally in the CFD worktree. This compact publication does not contain the full solver output.
'''
(out/'README.md').write_text(readme,encoding='utf-8',newline='\n')
print(json.dumps(summary,indent=2))
