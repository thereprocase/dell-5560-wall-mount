"""Bounded six-step correction-count comparison on identical flowing fields.

The predeclared short-run acceptance is 0.1% RMS and 1% maximum field error,
plus 1e-6 absolute tolerance, against three outer correctors. It is only a
coupling-cost check, not time-step, mesh, or long-time statistical convergence.
"""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
import numpy as np
from compare_cfd_fields import fields,digest


def run(command,case,logname,timeout=900):
    started=time.monotonic()
    with (case/logname).open('w') as log:
        proc=subprocess.Popen(command,cwd=case,stdout=log,stderr=subprocess.STDOUT,
                              stdin=subprocess.DEVNULL,start_new_session=True)
        try:code=proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid,signal.SIGTERM)
            try:proc.wait(timeout=20)
            except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
            raise
    assert code==0,f'{logname} exited {code}'
    return time.monotonic()-started


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--mirror-root',type=Path,required=True)
    p.add_argument('--dt-us',type=float,default=25.)
    p.add_argument('--tag',default='')
    args=p.parse_args();base=Path(__file__).resolve().parent
    assert re.fullmatch(r'[a-zA-Z0-9_-]*',args.tag)
    end_time=6*args.dt_us*1e-6
    cases={};timings={};diagnostics={}
    output=args.mirror_root/('revh_correction_benchmark'+args.tag);output.mkdir(exist_ok=False)
    criteria={'rms_relative':.001,'maximum_relative':.01,'absolute':1e-6,
              'maximum_Courant':.5,'maximum_boundary_flux_ratio':1e-4,
              'scope':f'Six physical steps at {args.dt_us} microseconds. Short-run coupling check only.'}
    (output/'criteria.json').write_text(json.dumps(criteria,indent=2)+'\n')
    for outer,name in [(3,'revh_warm_outer3_10'),(2,'revh_warm_outer2_11')]:
        case=args.root/(name+args.tag);mirror=args.mirror_root/(name+args.tag)
        subprocess.run([sys.executable,str(base/'prepare_revh_steady_transient.py'),
            '--steady',str(args.root/'revh_steady_09'),'--iteration','300',
            '--template',str(args.root/'revh_fourhour_08'),'--case',str(case),'--mirror',str(mirror),
            '--outer-correctors',str(outer),'--benchmark-steps','6','--benchmark-dt-us',str(args.dt_us)],check=True)
        print(f'Running {outer} outer correctors',flush=True)
        timings[outer]=run(['mpirun','--bind-to','none','-np','4','pimpleFoam','-parallel'],case,'log.benchmark')
        raw=(case/'log.benchmark').read_text()
        num=r'[-+]?(?:\d*\.)?\d+(?:[eE][-+]?\d+)?'
        co=[float(v) for v in re.findall(r'Courant Number mean: [^ ]+ max: ('+num+')',raw)]
        net=[float(v) for v in re.findall(r'sum\(ambient_openings\) of phi = ('+num+')',raw)]
        total=[float(v) for v in re.findall(r'sumMag\(ambient_openings\) of phi = ('+num+')',raw)]
        diagnostics[outer]={'maximum_Courant':max(co),'maximum_flux_ratio':max(abs(a)/b for a,b in zip(net,total)),
                            'bounding_lines':re.findall(r'^bounding .*$',raw,re.M)}
        run(['reconstructPar','-time',f'{end_time:.10f}'],case,'log.reconstruct')
        cases[outer]=case
        print(json.dumps({'outer_correctors':outer,'wall_seconds':timings[outer],'diagnostics':diagnostics[outer]}),flush=True)
    identical={}
    for rel in [f'constant/polyMesh/{name}' for name in ['points','faces','owner','neighbour','boundary','cellZones']]+[f'0/{name}' for name in ['U','p','phi','k','omega','nut']]+['constant/fvOptions','constant/transportProperties','constant/turbulenceProperties','system/fvSchemes','system/controlDict']:
        pair=[digest(cases[n]/rel) for n in [3,2]]
        assert pair[0]==pair[1],rel
        identical[rel]=pair[0]
    reference,candidate=[fields(cases[n],end_time) for n in [3,2]]
    comparison={}
    for name,a in reference.items():
        b=candidate[name];error=b-a
        rms=float(np.sqrt(np.mean(error**2)));max_error=float(np.max(np.abs(error)))
        ref_rms=float(np.sqrt(np.mean(a**2)));ref_max=float(np.max(np.abs(a)))
        finite=bool(np.isfinite(a).all() and np.isfinite(b).all())
        comparison[name]={'finite':finite,'reference_rms':ref_rms,'reference_max_abs':ref_max,
            'error_rms':rms,'max_abs_error':max_error,
            'pass':finite and rms<=1e-6+.001*ref_rms and max_error<=1e-6+.01*ref_max}
    accepted=all(v['pass'] for v in comparison.values()) and all(d['maximum_Courant']<=.5 and d['maximum_flux_ratio']<=1e-4 for d in diagnostics.values())
    report={'created_utc':datetime.now(timezone.utc).isoformat(),'physical_duration_s':end_time,
        'source_steady_iteration':300,'criteria':criteria,'wall_seconds':timings,'diagnostics':diagnostics,
        'identical_input_sha256':identical,'fields':comparison,'accepted':accepted,
        'speedup_ratio':timings[3]/timings[2],'scope':__doc__}
    (output/'comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':main()
