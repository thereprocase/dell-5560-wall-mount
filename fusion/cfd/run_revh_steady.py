"""Prepare and monitor an independent four-worker same-Rev-H steady solve.

Iteration numbers are not physical times and must never be rendered as a flow
movie. A converged result may initialize a separate transient shedding case.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import time

NUMBER=r'[-+]?(?:\d*\.)?\d+(?:[eE][-+]?\d+)?'


def utc():return datetime.now(timezone.utc).isoformat()


def workers(case):
    result=[]
    for path in Path('/proc').iterdir():
        if not path.name.isdigit():continue
        try:
            if (path/'comm').read_text().strip()=='simpleFoam' and (path/'cwd').resolve()==case:result.append(int(path.name))
        except OSError:pass
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--source-time',required=True)
    parser.add_argument('--case',type=Path,required=True)
    parser.add_argument('--mirror',type=Path,required=True)
    parser.add_argument('--seconds',type=int,default=3600)
    args=parser.parse_args();source=args.source.resolve();case=args.case.resolve();mirror=args.mirror.resolve()
    assert os.environ.get('WM_PROJECT_VERSION')=='v2412'
    assert 60<=args.seconds<=3600
    case.mkdir(exist_ok=False);mirror.mkdir(exist_ok=False)
    for name in ['constant','system']:shutil.copytree(source/name,case/name)
    hashes={}
    for rank in range(4):
        processor=f'processor{rank}'
        shutil.copytree(source/processor/'constant',case/processor/'constant')
        initial=case/processor/'0';initial.mkdir()
        for field in ['U','p','phi','k','omega','nut']:
            src=source/processor/args.source_time/field
            assert src.stat().st_size>100
            shutil.copy2(src,initial/field)
            hashes[f'{processor}/{field}']=hashlib.sha256(src.read_bytes()).hexdigest()
    control=(case/'system/controlDict').read_text()
    functions='functions {'+control.split('functions {',1)[1]
    functions=functions.replace('executeInterval 2;','executeInterval 25;').replace('writeInterval 2;','writeInterval 25;')
    header='FoamFile {version 2.0; format ascii; class dictionary; object controlDict;}\n'
    (case/'system/controlDict').write_text(header+'''application simpleFoam;
startFrom startTime; startTime 0; stopAt endTime; endTime 5000; deltaT 1;
writeControl timeStep; writeInterval 100; purgeWrite 0;
writeFormat binary; writePrecision 10; writeCompression off;
timeFormat general; timePrecision 10; runTimeModifiable false;
'''+functions)
    schemes=(case/'system/fvSchemes').read_text().replace('default backward;','default steadyState;')
    for field in ['U','k','omega']:schemes=schemes.replace(f'div(phi,{field}) Gauss',f'div(phi,{field}) bounded Gauss')
    (case/'system/fvSchemes').write_text(schemes)
    (case/'system/fvSolution').write_text('''FoamFile {version 2.0; format ascii; class dictionary; object fvSolution;}
solvers {
 p {solver GAMG; tolerance 1e-8; relTol .03; smoother GaussSeidel;}
 "(U|k|omega)" {solver smoothSolver; smoother symGaussSeidel; tolerance 1e-8; relTol .05;}
}
SIMPLE {nNonOrthogonalCorrectors 1; consistent no; momentumPredictor yes;}
relaxationFactors {fields {p .3;} equations {U .5; k .5; omega .5;}}
''')
    (case/'case.foam').touch()
    manifest=json.loads((source/'case_manifest.json').read_text())
    manifest.update(scope='Steady-solver initialization study on the same provisional mesh. Iterations are not physical time.',
                    steady_start={'source_case':source.name,'source_time_s':float(args.source_time),'processor_field_sha256':hashes},
                    solver='simpleFoam',ranks=4,maximum_wall_seconds=args.seconds,
                    convergence_policy={'minimum_iterations':200,'window_iterations':50,
                        'max_initial_residuals':{'p':1e-5,'U':1e-6,'k':1e-5,'omega':1e-5},
                        'probe_window_relative_range':.005,'net_to_absolute_boundary_flux':1e-5,
                        'recent_turbulence_bounding_events':0})
    for root in [case,mirror]:(root/'case_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    state={'case':case.name,'state':'running','started_utc':utc(),'budget_seconds':args.seconds,'converged':False,'completed_iterations':0}
    path=case/'log.simpleFoam';started=time.monotonic();signal_at=None;last_notice=0
    with path.open('w') as log:
        proc=subprocess.Popen(['mpirun','--bind-to','none','-np','4','simpleFoam','-parallel','-opt-switch','stopAtWriteNowSignal=12'],
                              cwd=case,stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)
        state['mpi_pid']=proc.pid
        while True:
            elapsed=time.monotonic()-started;raw=path.read_text(errors='replace')
            blocks=re.findall(r'^Time = ('+NUMBER+r')\s*\n(.*?)(?=^Time = |\Z)',raw,re.M|re.S)
            complete=[(t,b) for t,b in blocks if 'ExecutionTime =' in b and 'sumMag(ambient_openings)' in b]
            reason=None
            if elapsed>=args.seconds:reason='Steady preparation wall budget reached'
            if complete:
                tail=complete[-1][1]
                if re.search(r'=\s*[-+]?(?:nan|inf)\b',tail,re.I):reason='Non-finite diagnostic'
                speed=re.findall(r'max\(mag\(U\)\) = ('+NUMBER+')',tail)
                if speed and float(speed[-1])>100:reason='Velocity exceeds 100 m/s guard'
                recent='\n'.join(b for _,b in complete[-50:])
                residuals={name:[float(x) for x in re.findall(r'Solving for '+name+r', Initial residual = ('+NUMBER+')',recent)] for name in ['p','Ux','Uy','Uz','k','omega']}
                residual_max={k:max(v) for k,v in residuals.items() if v}
                net=re.findall(r'sum\(ambient_openings\) of phi = ('+NUMBER+')',recent)
                absolute=re.findall(r'sumMag\(ambient_openings\) of phi = ('+NUMBER+')',recent)
                flux_ratio=max((abs(float(a))/max(float(b),1e-30) for a,b in zip(net,absolute)),default=math.inf)
                variation={}
                for field in ['p','U']:
                    probe=case/'postProcessing/probes/0'/field
                    if not probe.exists():continue
                    rows=[[float(v) for v in re.findall(NUMBER,line)][1:] for line in probe.read_text().splitlines() if line.strip() and not line.startswith('#')][-50:]
                    if len(rows)==50 and len({len(r) for r in rows})==1:
                        columns=list(zip(*rows));scale=max(1,max(abs(v) for row in rows for v in row))
                        variation[field]=max(max(c)-min(c) for c in columns)/scale
                limits={'p':1e-5,'Ux':1e-6,'Uy':1e-6,'Uz':1e-6,'k':1e-5,'omega':1e-5}
                converged=(len(complete)>=200 and len(residual_max)==6 and all(residual_max[k]<=v for k,v in limits.items())
                           and len(variation)==2 and max(variation.values())<=.005 and flux_ratio<=1e-5
                           and not re.search(r'^bounding ',recent,re.M))
                if converged:reason='Residuals, probes and conservation satisfy the convergence policy';state['converged']=True
                state.update(last_50_max_initial_residuals=residual_max,probe_window_relative_range=variation,
                             last_50_max_flux_ratio=flux_ratio,latest_max_speed_m_s=float(speed[-1]) if speed else None)
            ids=workers(case)
            if reason and signal_at is None and len(ids)==4:
                for pid in ids:os.kill(pid,signal.SIGUSR2)
                signal_at=elapsed;state.update(state='writing_final_checkpoint',stop_reason=reason)
            if signal_at is not None and elapsed-signal_at>180 and proc.poll() is None:
                for pid in workers(case):os.kill(pid,signal.SIGKILL)
                os.killpg(proc.pid,signal.SIGKILL);state['error']='Graceful stop timed out'
            code=proc.poll()
            state.update(updated_utc=utc(),elapsed_seconds=round(elapsed,2),completed_iterations=len(complete),
                         latest_iteration=int(float(complete[-1][0])) if complete else None,
                         bounding_events=len(re.findall(r'^bounding ',raw,re.M)),worker_pids=ids)
            if code is not None:state.update(state='complete' if code==0 else 'failed',exit_code=code,finished_utc=utc())
            for root in [case,mirror]:
                temp=root/'run-status.json.tmp';temp.write_text(json.dumps(state,indent=2)+'\n');temp.replace(root/'run-status.json')
            if elapsed-last_notice>=60 or code is not None:
                print(json.dumps({k:state.get(k) for k in ['state','elapsed_seconds','completed_iterations','latest_max_speed_m_s','converged']}),flush=True);last_notice=elapsed
            if code is not None:break
            time.sleep(5)
    shutil.copy2(path,mirror/path.name)
    if state['state']=='failed':raise SystemExit(1)


if __name__=='__main__':main()
