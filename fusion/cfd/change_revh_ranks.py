"""Checkpoint and repartition the flowing CFD run without resetting physical time.

Preserve the original four-rank directories and solver log. Verify reconstructed
current and previous-step internal fields exactly after repartitioning. Keep the
original wall-time deadline and cumulative sampled output. A preparation failure
restores the four-rank checkpoint before continuing with the original rank count.
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

import numpy as np
from compare_cfd_fields import fields, digest
from run_revh_wall_budget import workers, mirror_samples


def utc():
    return datetime.now(timezone.utc).isoformat()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--case',type=Path,required=True)
    p.add_argument('--mirror',type=Path,required=True)
    p.add_argument('--ranks',type=int,choices=[6,8],required=True)
    p.add_argument('--benchmark',type=Path,required=True)
    args=p.parse_args();case=args.case.resolve();mirror=args.mirror.resolve()
    assert case.name=='revh_flowing_12' and mirror.name==case.name
    assert os.environ.get('WM_PROJECT_VERSION')=='v2412'
    os.environ['HWLOC_COMPONENTS']='linux,stop';os.environ['OMP_NUM_THREADS']='1'
    benchmark=json.loads(args.benchmark.read_text())
    candidate=benchmark['results'][str(args.ranks)]
    assert benchmark['state']=='complete' and candidate['field_check_passed']
    assert candidate['throughput_ratio']>=1.10 and candidate['max_Courant']<=.5
    assert not candidate['bounding_lines']
    state=json.loads((case/'run-status.json').read_text())
    manifest=json.loads((case/'case_manifest.json').read_text())
    assert state['state']=='running' and manifest['initialization_kind']=='steady_solver'
    assert state['elapsed_seconds']<state['budget_seconds']-600
    ids=workers(case);assert ids==state['worker_pids'] and len(ids)==4
    mpi=state['mpi_pid']
    parent=int(re.search(r'^PPid:\s+(\d+)',Path(f'/proc/{mpi}/status').read_text(),re.M)[1])
    command=Path(f'/proc/{parent}/cmdline').read_bytes().split(b'\0')
    assert any(item.endswith(b'/run_revh_wall_budget.py') for item in command)
    assert str(case).encode() in command
    for pid in ids:
        assert b'stopAtWriteNowSignal=12' in Path(f'/proc/{pid}/cmdline').read_bytes()
    archive=case/f'rank-handoff-{args.ranks}';archive.mkdir(exist_ok=False)
    for name in ['run-status.json','case_manifest.json']:
        shutil.copy2(case/name,archive/name)
    for name in ['controlDict','decomposeParDict']:
        shutil.copy2(case/'system'/name,archive/name)
    report={'started_utc':utc(),'from_ranks':4,'to_ranks':args.ranks,
            'original_deadline_unchanged':True,'benchmark_sha256':digest(args.benchmark),
            'benchmark_throughput_ratio':candidate['throughput_ratio']}

    def save_status(label):
        state.update(state=label,updated_utc=utc(),rank_change=report)
        for root in [case,mirror]:
            temp=root/'run-status.json.tmp'
            temp.write_text(json.dumps(state,indent=2)+'\n');temp.replace(root/'run-status.json')
        (archive/'handoff.json').write_text(json.dumps(report,indent=2)+'\n')

    def run(command,name,timeout=180):
        with (archive/name).open('w') as log:
            result=subprocess.run(command,cwd=case,stdout=log,stderr=subprocess.STDOUT,timeout=timeout)
        assert result.returncode==0,(command,result.returncode)

    # Retire only the old supervisor. Its MPI workers remain live and receive
    # OpenFOAM's own write-and-stop signal; a planned change is not a solver crash.
    os.kill(parent,signal.SIGTERM)
    for pid in ids:os.kill(pid,signal.SIGUSR2)
    save_status('writing_rank_checkpoint')
    stop_started=time.monotonic()
    while workers(case):
        assert time.monotonic()-stop_started<180,'Checkpoint stop exceeded allowance'
        mirror_samples(case,mirror);time.sleep(2)
    mirror_samples(case,mirror)
    raw=(case/'log.pimpleFoam.fourhour').read_text()
    assert re.search(r'^End\s*$',raw,re.M),'Solver did not finish its checkpoint cleanly'
    shutil.copy2(case/'log.pimpleFoam.fourhour',archive/'log.before-rank-change')
    times=[]
    for rank in range(4):
        numeric=[]
        for path in (case/f'processor{rank}').iterdir():
            if path.is_dir():
                try:numeric.append((float(path.name),path.name))
                except ValueError:pass
        times.append(max(numeric)[1])
    assert len(set(times))==1
    checkpoint=times[0]
    report.update(checkpoint_time_s=float(checkpoint),checkpoint_folder=checkpoint,
                  stopped_utc=utc(),old_supervisor_retired=True)
    save_status('repartitioning_checkpoint')
    moved=[];chosen=args.ranks
    try:
        run(['reconstructPar','-time',checkpoint],'log.reconstruct-before')
        names=['U','U_0','p','phi','phi_0','k','k_0','omega','omega_0','nut']
        before=fields(case,float(checkpoint),names)
        report['checkpoint_sha256']={name:digest(case/checkpoint/name) for name in names+['uniform/time']}
        for rank in range(4):
            folder=case/f'processor{rank}'
            assert folder.resolve().parent==case and archive.resolve().parent==case
            folder.rename(archive/folder.name);moved.append(folder.name)
        decomp=case/'system/decomposeParDict'
        decomp.write_text(re.sub(r'numberOfSubdomains\s+\d+;',f'numberOfSubdomains {args.ranks};',decomp.read_text()))
        control=case/'system/controlDict'
        control.write_text(re.sub(r'startFrom\s+\w+;','startFrom latestTime;',control.read_text(),count=1))
        run(['decomposePar','-time',checkpoint],'log.decompose-new')
        for rank in range(args.ranks):
            part=case/f'processor{rank}'/checkpoint
            assert all((part/name).is_file() for name in names)
            assert digest(part/'uniform/time')==report['checkpoint_sha256']['uniform/time']
        run(['reconstructPar','-time',checkpoint],'log.reconstruct-check')
        after=fields(case,float(checkpoint),names)
        report['internal_fields_exact_after_repartition']={name:bool(np.array_equal(before[name],after[name])) for name in names}
        assert all(report['internal_fields_exact_after_repartition'].values())
        assert digest(case/checkpoint/'uniform/time')==report['checkpoint_sha256']['uniform/time']
        report['native_time_history_preserved']=True
        manifest.setdefault('mpi_worker_history',[{'physical_time_s':0,'workers':4}]).append(
            {'physical_time_s':float(checkpoint),'workers':args.ranks,'changed_utc':utc(),
             'reason':'Measured CPU throughput improvement with unchanged field comparison',
             'native_time_history_preserved':True})
        manifest['cpu_workers']=args.ranks
    except Exception as error:
        report['repartition_error']=str(error);report['rolled_back_to_ranks']=4;chosen=4
        if len(moved)==4:
            failed=archive/'failed-new-partitions';failed.mkdir()
            for part in case.glob('processor[0-9]*'):
                assert part.resolve().parent==case
                part.rename(failed/part.name)
        for name in moved:(archive/name).rename(case/name)
        shutil.copy2(archive/'decomposeParDict',case/'system/decomposeParDict')
        text=(archive/'controlDict').read_text()
        (case/'system/controlDict').write_text(re.sub(r'startFrom\s+\w+;','startFrom latestTime;',text,count=1))
    report.update(finished_utc=utc(),resumed_ranks=chosen)
    state['cpu_workers']=chosen
    for root in [case,mirror]:
        (root/'case_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    save_status('restarting_after_rank_change')
    shutil.copy2(archive/'handoff.json',mirror/'rank-handoff.json')
    print(json.dumps(report,indent=2),flush=True)
    command=[sys.executable,str(Path(__file__).with_name('run_revh_wall_budget.py')),
             '--case',str(case),'--mirror',str(mirror),'--seconds',str(state['budget_seconds']),
             '--ranks',str(chosen),'--resume']
    raise SystemExit(subprocess.call(command))


if __name__=='__main__':main()
