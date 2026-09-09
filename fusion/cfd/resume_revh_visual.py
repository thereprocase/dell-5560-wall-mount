"""Resume the saved fixed-step visual branch until an explicit UTC deadline."""
import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from revh_checkpoint import describe
from run_revh_wall_budget import lower_priority, workers


def write(path, data):
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data,indent=2)+'\n')
    temporary.replace(path)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--case',type=Path,required=True)
    p.add_argument('--mirror',type=Path,required=True)
    p.add_argument('--until',required=True)
    args=p.parse_args();lower_priority()
    case=args.case.resolve();mirror=args.mirror.resolve()
    assert case.name=='revh_visual_81us_20260909_a3' and mirror.name==case.name
    assert not workers(case) and os.environ.get('WM_PROJECT_VERSION')=='v2412'
    now=datetime.now(timezone.utc);deadline=datetime.fromisoformat(args.until.replace('Z','+00:00'))
    remaining=(deadline-now).total_seconds();assert 120<remaining<86400
    saved=json.loads((case/'resume-checkpoint.json').read_text());actual=describe(case,12)
    for key in ['field_sha256','mesh_sha256','native_time_metadata']:assert saved[key]==actual[key],key
    manifest=json.loads((case/'case_manifest.json').read_text())
    dt=manifest['fixed_deltaT_s'];assert abs(dt-80.930025e-6)<1e-12
    event=case/'restart-events'/now.strftime('%Y%m%dT%H%M%SZ');event.mkdir(parents=True)
    for name in ['resume-checkpoint.json','case_manifest.json','run-status.json','run-control.json']:
        if (case/name).exists():shutil.copy2(case/name,event/name)
    shutil.copy2(case/'system/controlDict',event/'controlDict')
    text=(case/'system/controlDict').read_text()
    for key,value in {'startFrom':'latestTime','stopAt':'endTime','endTime':'10',
                      'deltaT':format(dt,'.17g'),'adjustTimeStep':'no','maxDeltaT':format(dt,'.17g'),
                      'writeControl':'clockTime','writeInterval':'1800','purgeWrite':'0',
                      'writeCompression':'off','timePrecision':'14'}.items():
        text,n=re.subn(r'\b'+key+r'\s+[^;]+;',key+' '+value+';',text,count=1);assert n==1,key
    text,n=re.subn(r'(edge_sections\s*\{.*?writeInterval\s+)\d+;',lambda m:m[1]+'1;',text,count=1,flags=re.S);assert n==1
    (case/'system/controlDict').write_text(text)
    log=case/'log.pimpleFoam.fourhour'
    previous=json.loads((mirror/'presentation/run-status.json').read_text())
    if (case/'run-status.json').exists():previous=json.loads((case/'run-status.json').read_text())
    assert previous['state']=='complete'
    baseline=previous['elapsed_seconds'];budget=math.ceil(baseline+remaining)
    if not log.exists():log.touch()
    logged=len(re.findall(r'^ExecutionTime = ',log.read_text(),re.M))
    state=dict(previous,state='restarting_from_checkpoint',cpu_workers=12,
               budget_seconds=budget,resume_elapsed_seconds=baseline,resume_from_s=actual['physical_time_s'],
               completed_steps_before_log=int(actual['native_time_metadata']['index'])-logged,
               authorized_deadline_utc=deadline.isoformat(),updated_utc=now.isoformat())
    for key in ['finished_utc','stop_reason','stop_signal_utc','error','exit_code']:state.pop(key,None)
    entry=dict(requested_utc=now.isoformat(),checkpoint_time_s=actual['physical_time_s'],workers=12,
               authorized_deadline_utc=deadline.isoformat(),fixed_deltaT_s=dt,native_previous_step_fields_preserved=True)
    manifest.setdefault('continuation_sessions',[]).append(entry)
    for root in [case,mirror]:
        write(root/'case_manifest.json',manifest);write(root/'run-status.json',state)
        write(root/'run-control.json',dict(deadline_utc=deadline.isoformat(),stop_requested=False))
    write(event/'verified-checkpoint.json',actual)
    os.environ['HWLOC_COMPONENTS']='linux,stop';os.environ['OMP_NUM_THREADS']='1'
    for name in ['DISPLAY','WAYLAND_DISPLAY','XAUTHORITY']:os.environ.pop(name,None)
    print(json.dumps(entry),flush=True)
    raise SystemExit(subprocess.call([sys.executable,str(Path(__file__).with_name('run_revh_wall_budget.py')),
        '--case',str(case),'--mirror',str(mirror),'--seconds',str(budget),'--ranks','12','--resume']))


if __name__=='__main__':main()
