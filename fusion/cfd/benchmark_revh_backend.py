"""Bounded CPU/CUDA commissioning comparison; run inside WSL OpenFOAM.

Preserves every case. Source meshes with recorded defects can be used ONLY to
compare solver implementations, never to assert validation or settled flow.
Source etc/bashrc first, then set HWLOC_COMPONENTS=linux,stop for this process.
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
import time


def run(case, command, label, timeout):
    log=case/('log.'+label)
    assert not log.exists(), 'Preserve earlier log: '+str(log)
    started=time.monotonic()
    with log.open('w') as out:
        proc=subprocess.Popen(command,cwd=case,stdout=out,stderr=subprocess.STDOUT,
                              stdin=subprocess.DEVNULL,start_new_session=True)
        try:code=proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid,signal.SIGKILL)
            proc.wait()
            raise RuntimeError('Timed out after '+str(timeout)+' seconds: '+label)
    elapsed=time.monotonic()-started
    print(label,code,round(elapsed,3),'seconds',flush=True)
    if code:raise RuntimeError('Nonzero exit: '+label)
    return {'command':command,'wall_seconds':elapsed,'exit_code':code}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--case',type=Path,required=True)
    p.add_argument('--backend',choices=['cpu','cuda-bj'],required=True)
    p.add_argument('--library',type=Path)
    p.add_argument('--steps',type=int,default=10)
    p.add_argument('--timeout',type=int,default=600)
    args=p.parse_args()
    assert os.name=='posix' and os.environ.get('WM_PROJECT_VERSION')=='v2412'
    assert 1<=args.steps<=100 and 1<=args.timeout<=3600
    source=args.source.resolve();case=args.case.resolve()
    case.mkdir(parents=True,exist_ok=False)
    state={'scope':'Backend commissioning benchmark only; source mesh is not accepted for validation.',
           'source':str(source),'backend':args.backend,'state':'preparing',
           'started_utc':datetime.now(timezone.utc).isoformat(),
           'ranks':4,'dt_s':1e-5,'steps':args.steps,'timeout_s':args.timeout,'phases':{}}
    def save():(case/'benchmark-status.json').write_text(json.dumps(state,indent=2)+'\n')
    save()
    try:
        for name in ['constant','system']:
            shutil.copytree(source/name,case/name)
        # Meshing leaves derived 0/ fields with obsolete blockMesh patches.
        # Only physical initial fields belong in the solve decomposition.
        (case/'0').mkdir()
        for name in ['U','p','k','omega','nut']:
            shutil.copy2(source/'0'/name,case/'0'/name)
        for name in ['case_manifest.json','log.checkMesh.standard','log.checkMesh.expanded']:
            if (source/name).exists():shutil.copy2(source/name,case/name)
        (case/'case.foam').touch()
        c=case/'system/controlDict';s=c.read_text()
        s=re.sub(r'endTime\s+[^;]+;',f'endTime {args.steps*1e-5:.10f};',s,count=1)
        s=re.sub(r'writeInterval\s+[^;]+;',f'writeInterval {args.steps*1e-5:.10f};',s,count=1)
        # Comparisons use one endpoint volume write and identical function objects.
        if args.backend=='cuda-bj':
            assert args.library and args.library.is_file()
            s+='\nlibs ("'+str(args.library.resolve())+'");\n'
        c.write_text(s)
        c=case/'system/decomposeParDict';s=c.read_text()
        c.write_text(re.sub(r'numberOfSubdomains\s+\d+;', 'numberOfSubdomains 4;',s))
        if args.backend=='cuda-bj':
            c=case/'system/fvSolution';s=c.read_text()
            old='p {solver GAMG; tolerance 1e-8; relTol .03; smoother GaussSeidel;}'
            assert old in s
            c.write_text(s.replace(old,'''p {solver GKOCG; executor cuda;
              tolerance 1e-8; relTol .03; maxIter 2000; verbose 0;
              forceHostBuffer true; ranksPerGPU 4; updateInitGuess true;
              scaling 1; adaptMinIter false; preconditionerCaching 0;
              preconditioner BJ;}'''))
        state['phases']['zones']=run(case,['topoSet'],'topoSet',180)
        # GPU source can be a prepared CPU case, retaining its exact partition.
        if (source/'processor0/constant/polyMesh').is_dir() and 'benchmark-status.json' in {q.name for q in source.iterdir()}:
            for rank in range(4):
                for name in ['0','constant']:
                    shutil.copytree(source/f'processor{rank}'/name,case/f'processor{rank}'/name)
            state['decomposition']='Copied exact CPU partition and initial fields'
        else:state['phases']['decompose']=run(case,['decomposePar'],'decomposePar',300)
        state['state']='running';save()
        with (case/'gpu-samples.csv').open('w') as out:
            sampler=subprocess.Popen(['nvidia-smi','--query-gpu=timestamp,index,memory.used,utilization.gpu',
                '--format=csv,noheader,nounits','-lms','500'],stdout=out,stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,start_new_session=True)
            try:
                state['phases']['solve']=run(case,['mpirun','--bind-to','none','-np','4','pimpleFoam','-parallel'],
                                             'pimpleFoam',args.timeout)
            finally:
                os.killpg(sampler.pid,signal.SIGTERM);sampler.wait(timeout=5)
        state['phases']['reconstruct']=run(case,['reconstructPar','-latestTime'],'reconstructPar',180)
        log=(case/'log.pimpleFoam').read_text(errors='replace')
        iterations=[int(n) for n in re.findall(r'Solving for p,.*?No Iterations (\d+)',log)]
        state.update(state='completed_pending_field_comparison',
                     reported_clock_times_s=[float(x) for x in re.findall(r'ClockTime = ([\d.]+) s',log)],
                     physical_times_s=[float(x) for x in re.findall(r'^Time = ([\d.e+-]+)',log,re.M)],
                     pressure_iterations_total=sum(iterations),pressure_iterations_max=max(iterations,default=0),
                     pressure_calls=len(iterations),bounding_events=len(re.findall(r'^bounding ',log,re.M)),
                     courant_max_values=[float(x) for x in re.findall(r'Courant Number mean: [^ ]+ max: ([\d.e+-]+)',log)])
    except BaseException as exc:
        state.update(state='failed',error=str(exc));raise
    finally:
        state['finished_utc']=datetime.now(timezone.utc).isoformat();save()
        print(json.dumps(state,indent=2),flush=True)


if __name__=='__main__':main()
