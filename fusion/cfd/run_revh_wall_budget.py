"""Run CPU CFD within a wall budget; mirror complete samples for live videos.

Use OpenFOAM's per-process stopAtWriteNowSignal. No dictionary reloads or
global installation changes. Signal only the verified workers in this
fresh case. The fallback terminates only this runner's process descendants.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time
from revh_checkpoint import describe as describe_checkpoint


def utc():return datetime.now(timezone.utc).isoformat()


def lower_priority():
    # A shared slice caps all concurrent CFD work together, including children.
    # A scope keeps the current environment, cwd and terminal connection.
    if '/cfd.slice/' not in Path('/proc/self/cgroup').read_text():
        os.execvp('systemd-run', ['systemd-run','--user','--scope','--quiet',
                                '--slice=cfd.slice','--',sys.executable,*sys.argv])
    os.setpriority(os.PRIO_PROCESS,0,19)
    os.sched_setscheduler(0,os.SCHED_IDLE,os.sched_param(0))
    subprocess.run(['ionice','-c','3','-p',str(os.getpid())],check=True)


def workers(case):
    result=[]
    for path in Path('/proc').iterdir():
        if not path.name.isdigit():continue
        try:
            if (path/'comm').read_text().strip()=='pimpleFoam' and (path/'cwd').resolve()==case:
                result.append(int(path.name))
        except (OSError,ProcessLookupError):pass
    return sorted(result)


def mirror_samples(case,mirror):
    source=case/'postProcessing/edge_sections';target=mirror/'postProcessing/edge_sections'
    target.mkdir(parents=True,exist_ok=True)
    if not source.is_dir():return 0
    for folder in sorted(source.iterdir()):
        if not folder.is_dir() or (target/folder.name).exists():continue
        files=[folder/(n+'.vtp') for n in ['right_section','left_section']]
        if not all(p.is_file() and p.read_bytes()[-128:].rstrip().endswith(b'</VTKFile>') for p in files):continue
        temp=target/('.'+folder.name+'.partial');temp.mkdir(exist_ok=True)
        for path in files:shutil.copy2(path,temp/path.name)
        temp.rename(target/folder.name)
    return len([p for p in target.iterdir() if p.is_dir() and not p.name.startswith('.')])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--case',type=Path,required=True)
    p.add_argument('--mirror',type=Path,required=True)
    p.add_argument('--seconds',type=int,default=14400)
    p.add_argument('--ranks',type=int,choices=[4,6,8],default=4)
    p.add_argument('--resume',action='store_true',help='Continue a deliberately checkpointed run within its original deadline')
    args=p.parse_args();case=args.case.resolve();mirror=args.mirror.resolve()
    lower_priority()
    assert 5<=args.seconds<=31*86400
    assert os.environ.get('WM_PROJECT_VERSION')=='v2412'
    log_path=case/'log.pimpleFoam.fourhour'
    assert log_path.exists() if args.resume else not log_path.exists()
    manifest=json.loads((case/'case_manifest.json').read_text())
    warm=manifest.get('initialization_kind')=='steady_solver'
    state={'case':case.name,'state':'starting','started_utc':utc(),
           'budget_seconds':args.seconds,'hourly_updates_due_seconds':[n*3600 for n in range(1,5)],
           'scope':('Exploratory transient from a steady-solver iterate; initial field is not claimed converged.' if warm
                    else 'Extended exploratory startup; mesh and timestep independence not established.'),
           'initialization_kind':manifest.get('initialization_kind','native_transient_startup')}
    elapsed_before=0
    if args.resume:
        previous=json.loads((case/'run-status.json').read_text())
        assert previous['state'] in ['restarting_after_rank_change','restarting_from_checkpoint']
        assert previous['budget_seconds']==args.seconds and not workers(case)
        state.update(previous)
        state.pop('error',None)
        elapsed_before=previous.get('resume_elapsed_seconds',(datetime.now(timezone.utc)-datetime.fromisoformat(state['started_utc'])).total_seconds())
        assert elapsed_before<args.seconds
    started=time.monotonic()-elapsed_before;last_notice=elapsed_before;stop_sent=None;sample_count=0
    session_started=datetime.now(timezone.utc)
    state['session_started_utc']=session_started.isoformat()
    state['wall_time_accounting']='Cumulative supervised wall time; idle gaps between completed sessions are excluded.'
    command=['mpirun','--use-hwthread-cpus','--bind-to','none','-np',str(args.ranks),'pimpleFoam','-parallel','-opt-switch','stopAtWriteNowSignal=12']
    state['cpu_workers']=args.ranks
    state['cpu_nice']=os.getpriority(os.PRIO_PROCESS,0)
    state['io_priority']='idle'
    with log_path.open('a' if args.resume else 'w') as log:
        proc=subprocess.Popen(command,cwd=case,stdout=log,stderr=subprocess.STDOUT,
                              stdin=subprocess.DEVNULL,start_new_session=True)
        state.update(state='running',mpi_pid=proc.pid,command=command)
        while True:
            elapsed=time.monotonic()-started
            raw=log_path.read_text(errors='replace')
            entries=re.findall(r'^Time = ([\d.eE+-]+)\s*\n(.*?)(?=^Time = |\Z)',raw,re.M|re.S)
            complete=[(t,body) for t,body in entries if 'ExecutionTime =' in body]
            co=re.findall(r'Courant Number mean: [^ ]+ max: ([\d.eE+-]+)',raw)
            dt=re.findall(r'^deltaT = ([\d.eE+-]+)',raw,re.M)
            ids=workers(case)
            reason=None
            effective_budget=args.seconds
            control_path=case/'run-control.json'
            if control_path.is_file():
                control=json.loads(control_path.read_text())
                if control.get('deadline_utc'):
                    deadline=datetime.fromisoformat(control['deadline_utc'].replace('Z','+00:00'))
                    effective_budget=elapsed_before+(deadline-session_started).total_seconds()
                    state['authorized_deadline_utc']=deadline.isoformat()
                if control.get('stop_requested'):reason='User requested a resumable stop'
            state['budget_seconds']=effective_budget
            if elapsed>=effective_budget:reason='Requested wall-time budget reached'
            if min(shutil.disk_usage(root).free for root in [case,mirror])<5*1024**3:
                reason='Checkpointing before available disk falls below 5 GiB'
            if complete:
                tail=complete[-1][1]
                if re.search(r'=\s*[-+]?(?:nan|inf)\b',tail,re.I):reason='Non-finite field diagnostic'
                speed=re.findall(r'max\(mag\(U\)\) = ([\d.eE+-]+)',tail)
                if speed and float(speed[-1])>100:reason='Velocity exceeds 100 m/s commissioning guard'
            if reason and stop_sent is None and len(ids)==args.ranks:
                # Only workers have the handler; never send USR2 to mpirun.
                for pid in ids:os.kill(pid,signal.SIGUSR2)
                stop_sent=elapsed
                state.update(state='writing_final_checkpoint',stop_reason=reason,stop_signal_utc=utc(),worker_pids=ids)
            if stop_sent is not None and elapsed-stop_sent>180 and proc.poll() is None:
                for pid in workers(case):os.kill(pid,signal.SIGKILL)
                os.killpg(proc.pid,signal.SIGKILL)
                state.update(state='failed',error='Graceful stop exceeded 180-second checkpoint allowance')
            try:sample_count=mirror_samples(case,mirror)
            except OSError as exc:state['mirror_warning']=str(exc)
            state.update(updated_utc=utc(),elapsed_seconds=round(elapsed,2),
                         completed_steps=len(complete),latest_physical_time_s=float(complete[-1][0]) if complete else None,
                         latest_deltaT_s=float(dt[-1]) if dt else None,
                         latest_Courant=float(co[-1]) if co else None,
                         max_logged_Courant=max(map(float,co),default=None),
                         bounding_events=len(re.findall(r'^bounding ',raw,re.M)),
                         complete_sample_frames=sample_count,worker_pids=ids)
            code=proc.poll()
            if code is not None:
                state.update(state='complete' if code==0 and stop_sent is not None else 'failed',
                             exit_code=code,finished_utc=utc())
                if code==0 and stop_sent is None:state['error']='Exited before wall-budget stop'
                if state['state']=='complete':
                    try:
                        checkpoint=describe_checkpoint(case,args.ranks)
                        for root in [case,mirror]:
                            (root/'resume-checkpoint.json').write_text(json.dumps(checkpoint,indent=2)+'\n')
                        state['restart_checkpoint']={k:checkpoint[k] for k in ['physical_time_s','mpi_ranks','verified_utc','native_previous_step_fields_preserved']}
                    except Exception as error:
                        state.update(state='failed',error='Final restart checkpoint verification: '+str(error))
            for root in [case,mirror]:
                tmp=root/'run-status.json.tmp';tmp.write_text(json.dumps(state,indent=2)+'\n');tmp.replace(root/'run-status.json')
            if elapsed-last_notice>=60 or code is not None:
                print(json.dumps({k:state.get(k) for k in ['state','elapsed_seconds','completed_steps','latest_physical_time_s','latest_Courant','complete_sample_frames']}),flush=True)
                last_notice=elapsed
            if code is not None:break
            time.sleep(5)
    shutil.copy2(log_path,mirror/log_path.name)
    if state['state']!='complete':raise SystemExit(1)


if __name__=='__main__':main()
