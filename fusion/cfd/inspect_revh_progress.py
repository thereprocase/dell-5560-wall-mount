"""Read one compact snapshot of the local CFD run; changes nothing."""
from pathlib import Path
import argparse
import json
import re
from datetime import datetime,timezone

BASE=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--case',type=Path,default=BASE/'runs/revh_transient_04')
args=parser.parse_args();case=args.case.resolve()
result={'case':case.name}
for phase in ['surface','mesh','zones','initialize','pilot']:
    p=case/f'status.{phase}.json'
    retries=sorted(case.glob('status.'+phase+'.attempt*.json'),key=lambda p:int(re.search(r'attempt(\d+)',p.name)[1]))
    if retries:p=retries[-1]
    if p.exists():
        state=json.loads(p.read_text());result[phase]=state['state']
        if 'active_tool' in state:result['active_tool']=state['active_tool']
        if 'error' in state:result[phase+'_error']=state['error']
p=case/'log.snappyHexMesh'
if p.exists():
    raw=p.read_text(errors='replace')
    for name,pattern in [('morph_pass',r'Morph iteration (\d+)'),('layer_pass',r'Layer addition iteration (\d+)'),
                         ('layer_coverage_percent',r'Extruding \d+ out of \d+ faces \(([\d.]+)%\)'),
                         ('layer_cells',r'Added (\d+) out of \d+ cells'),
                         ('latest_logged_mesh_cells',r'cells:(\d+)')]:
        matches=re.findall(pattern,raw)
        if matches:result[name]=float(matches[-1]) if name.endswith('percent') else int(matches[-1])
    result['refinement_limit_hit']='reached limit' in raw
    result['mesher_ended']='Finished meshing in =' in raw
    result['mesh_log_updated_utc']=datetime.fromtimestamp(p.stat().st_mtime,timezone.utc).isoformat()
p=case/'log.pimpleFoam'
solver_logs=sorted(case.glob('log.pimpleFoam*'),key=lambda p:int(re.search(r'attempt(\d+)',p.name)[1]) if 'attempt' in p.name else 1)
if solver_logs:p=solver_logs[-1]
if p.exists():
    raw=p.read_text(errors='replace');times=re.findall(r'^Time = ([\d.eE+-]+)',raw,re.M)
    result['latest_started_time_s']=float(times[-1]) if times else None
    done=re.findall(r'^Time = ([\d.eE+-]+)\s*\n(?:(?!^Time = ).)*?ExecutionTime = ([\d.eE+-]+) s\s+ClockTime = ([\d.eE+-]+) s',raw,re.M|re.S)
    result['completed_steps']=len(done)
    if done:result['latest_completed_step']={'time_s':float(done[-1][0]),'wall_s':float(done[-1][2])}
    result['solver_ended']=bool(re.search(r'^End\s*$',raw,re.M))
try:
    import psutil
    result['available_RAM_GiB']=round(psutil.virtual_memory().available/2**30,1)
except ImportError:pass
print(json.dumps(result,indent=2))
