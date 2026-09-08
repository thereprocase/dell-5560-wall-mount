"""Resume or extend a saved Rev H transient with its native time history.

Examples after sourcing OpenFOAM v2412:
  python3 resume_revh.py --case CASE --mirror MIRROR --seconds 3600
  python3 resume_revh.py --case CASE --mirror MIRROR --until 2026-09-09T12:00:00Z

A running case is checkpointed with OpenFOAM's own signal before restarting.
Completed cases resume without replaying startup. Existing samples and logs stay
cumulative; idle time between completed sessions is excluded from wall accounting.
"""
import argparse
from datetime import datetime,timezone
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time
from revh_checkpoint import describe
from run_revh_wall_budget import workers,mirror_samples,lower_priority


def now():return datetime.now(timezone.utc)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case',type=Path,required=True)
    parser.add_argument('--mirror',type=Path,required=True)
    duration=parser.add_mutually_exclusive_group(required=True)
    duration.add_argument('--seconds',type=int)
    duration.add_argument('--until',help='An explicit ISO-8601 UTC deadline')
    args=parser.parse_args();case=args.case.resolve();mirror=args.mirror.resolve()
    lower_priority()
    assert case.name in ['revh_fourhour_08','revh_flowing_12'] and mirror.name==case.name
    assert os.environ.get('WM_PROJECT_VERSION')=='v2412'
    os.environ['HWLOC_COMPONENTS']='linux,stop';os.environ['OMP_NUM_THREADS']='1'
    deadline=datetime.fromisoformat(args.until.replace('Z','+00:00')) if args.until else None
    if deadline:assert deadline.tzinfo and (deadline-now()).total_seconds()>120
    else:assert 120<=args.seconds<=86400
    state=json.loads((case/'run-status.json').read_text());original_state=dict(state)
    assert state['state'] in ['running','complete']
    ranks=state.get('cpu_workers',4);assert ranks in [4,6,8]
    ids=workers(case);active=bool(ids)
    assert (active and state['state']=='running') or (not active and state['state']=='complete')
    event=case/'restart-events'/now().strftime('%Y%m%dT%H%M%SZ');event.mkdir(parents=True,exist_ok=False)
    for name in ['run-status.json','case_manifest.json','run-control.json']:
        if (case/name).exists():shutil.copy2(case/name,event/name)
    shutil.copy2(case/'system/controlDict',event/'controlDict')
    if active:
        assert len(ids)==ranks and ids==state['worker_pids']
        mpi=state['mpi_pid']
        parent=int(re.search(r'^PPid:\s+(\d+)',Path(f'/proc/{mpi}/status').read_text(),re.M)[1])
        command=Path(f'/proc/{parent}/cmdline').read_bytes().split(b'\0')
        assert any(item.endswith(b'/run_revh_wall_budget.py') for item in command)
        assert str(case).encode() in command
        for pid in ids:assert b'stopAtWriteNowSignal=12' in Path(f'/proc/{pid}/cmdline').read_bytes()
        os.kill(parent,signal.SIGTERM)
        for pid in ids:os.kill(pid,signal.SIGUSR2)
        state.update(state='writing_continuation_checkpoint',updated_utc=now().isoformat())
        for root in [case,mirror]:(root/'run-status.json').write_text(json.dumps(state,indent=2)+'\n')
        started=time.monotonic()
        while workers(case):
            assert time.monotonic()-started<180,'Checkpoint stop exceeded allowance'
            mirror_samples(case,mirror);time.sleep(2)
        mirror_samples(case,mirror)
        raw=(case/'log.pimpleFoam.fourhour').read_text()
        assert re.search(r'^End\s*$',raw,re.M),'Solver did not close its checkpoint cleanly'
    checkpoint=describe(case,ranks)
    for root in [case,mirror]:(root/'resume-checkpoint.json').write_text(json.dumps(checkpoint,indent=2)+'\n')
    (event/'checkpoint.json').write_text(json.dumps(checkpoint,indent=2)+'\n')
    shutil.copy2(case/'log.pimpleFoam.fourhour',event/'log.before-continuation')
    baseline=float(original_state['elapsed_seconds'])
    if active:baseline+=(now()-datetime.fromisoformat(original_state['updated_utc'])).total_seconds()
    remaining=(deadline-now()).total_seconds() if deadline else args.seconds
    assert remaining>60
    if deadline is None:
        from datetime import timedelta
        deadline=now()+timedelta(seconds=remaining)
    control=case/'system/controlDict'
    text=re.sub(r'startFrom\s+\w+;','startFrom latestTime;',control.read_text(),count=1)
    # v2412 disables gzip for binary output. Keep exact binary precision.
    text=re.sub(r'writeCompression\s+\w+;','writeCompression off;',text,count=1)
    control.write_text(text)
    state.update(state='restarting_from_checkpoint',resume_elapsed_seconds=baseline,
                 budget_seconds=math.ceil(baseline+remaining),cpu_workers=ranks,
                 authorized_deadline_utc=deadline.isoformat(),updated_utc=now().isoformat())
    for key in ['exit_code','finished_utc','stop_reason','stop_signal_utc','error']:state.pop(key,None)
    manifest=json.loads((case/'case_manifest.json').read_text())
    entry={'requested_utc':now().isoformat(),'from_state':original_state['state'],
           'checkpoint_time_s':checkpoint['physical_time_s'],'workers':ranks,
           'authorized_deadline_utc':deadline.isoformat(),'idle_between_sessions_excluded':True,
           'native_previous_step_fields_preserved':True}
    manifest.setdefault('continuation_sessions',[]).append(entry)
    manifest['checkpoint_compression']='Uncompressed native binary fields; OpenFOAM v2412 disables gzip for non-ascii output. Same precision and old-time history.'
    for root in [case,mirror]:
        (root/'case_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        (root/'run-status.json').write_text(json.dumps(state,indent=2)+'\n')
        (root/'run-control.json').write_text(json.dumps({'deadline_utc':deadline.isoformat(),'stop_requested':False},indent=2)+'\n')
    print(json.dumps({'continuation':entry,'event':str(event)}),flush=True)
    command=[sys.executable,str(Path(__file__).with_name('run_revh_wall_budget.py')),
             '--case',str(case),'--mirror',str(mirror),'--seconds',str(state['budget_seconds']),
             '--ranks',str(ranks),'--resume']
    raise SystemExit(subprocess.call(command))


if __name__=='__main__':main()
