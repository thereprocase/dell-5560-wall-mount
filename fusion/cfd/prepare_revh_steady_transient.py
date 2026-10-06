"""Prepare a separate transient from a preserved steady-solver checkpoint.

The steady iteration count is NOT carried into physical time. Transient history
starts fresh; backward differencing uses its native initial Euler fallback.
The caller must assess whether the source field has settled before interpreting
this as established-flow dynamics. This script makes no convergence claim.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re
import shutil


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--steady',type=Path,required=True)
    parser.add_argument('--iteration',required=True)
    parser.add_argument('--template',type=Path,required=True)
    parser.add_argument('--case',type=Path,required=True)
    parser.add_argument('--mirror',type=Path,required=True)
    parser.add_argument('--outer-correctors',type=int,choices=[1,2,3],default=3)
    parser.add_argument('--benchmark-steps',type=int,default=0)
    parser.add_argument('--benchmark-dt-us',type=float,default=25.)
    args=parser.parse_args();source=args.steady.resolve();template=args.template.resolve();case=args.case.resolve()
    assert args.iteration.isdigit()
    assert digest(source/'constant/fvOptions')==digest(template/'constant/fvOptions')
    for name in ['points','faces','owner','neighbour','boundary']:
        assert digest(source/'constant/polyMesh'/name)==digest(template/'constant/polyMesh'/name)
    fields=['U','p','phi','k','omega','nut']
    assert all((source/args.iteration/name).is_file() for name in fields),'Reconstruct the chosen steady iteration first'
    case.mkdir(exist_ok=False)
    for name in ['constant','system']:shutil.copytree(template/name,case/name)
    hashes={}
    roots=[('',source/args.iteration,case/'0')]
    for rank in range(4):
        processor=f'processor{rank}'
        shutil.copytree(source/processor/'constant',case/processor/'constant')
        roots.append((processor+'/',source/processor/args.iteration,case/processor/'0'))
    for prefix,original,target in roots:
        target.mkdir()
        for field in fields:
            shutil.copy2(original/field,target/field)
            hashes[prefix+field]=digest(original/field)
    control=case/'system/controlDict';text=control.read_text().replace('startFrom latestTime;','startFrom startTime;')
    # The flowing field has a higher Courant number than the original quiet start.
    text=re.sub(r'deltaT\s+[^;]+;','deltaT .0000125;',text,count=1)
    if args.benchmark_steps:
        assert 1<=args.benchmark_steps<=20
        assert 0<args.benchmark_dt_us<=25
        dt=args.benchmark_dt_us*1e-6
        text=text.replace('adjustTimeStep yes;','adjustTimeStep no;')
        text=re.sub(r'deltaT\s+[^;]+;',f'deltaT {dt:.10f};',text,count=1)
        text=re.sub(r'endTime\s+[^;]+;',f'endTime {args.benchmark_steps*dt:.10f};',text,count=1)
        text=re.sub(r'writeControl\s+[^;]+;','writeControl timeStep;',text,count=1)
        text=re.sub(r'writeInterval\s+[^;]+;',f'writeInterval {args.benchmark_steps};',text,count=1)
    control.write_text(text)
    solution=case/'system/fvSolution'
    solution.write_text(solution.read_text().replace('nOuterCorrectors 3;',f'nOuterCorrectors {args.outer_correctors};'))
    (case/'case.foam').touch()
    meta=json.loads((source/'case_manifest.json').read_text())
    steady_status=json.loads((source/'run-status.json').read_text())
    meta.update(created_utc=datetime.now(timezone.utc).isoformat(),solver='pimpleFoam',initialization_kind='steady_solver',
                scope='Transient response from a same-Rev-H steady-solver checkpoint; provisional mesh; convergence of the initial field requires separate assessment.',
                transient_initialization={'steady_case':source.name,'steady_iteration':int(args.iteration),
                    'source_assessment':steady_status,
                    'physical_start_time_s':0,'old_time_fields_copied':False,'source_field_sha256':hashes,
                    'method':'Same mesh and forcing; reset physical clock; native backward-scheme initial Euler fallback. No quiescent fan startup is replayed.'},
                transient_controls={'initial_deltaT_s':args.benchmark_dt_us*1e-6 if args.benchmark_steps else 12.5e-6,
                                    'max_deltaT_s':25e-6,'max_Co':.5,'outer_correctors':args.outer_correctors,
                                    'pressure_correctors':2,'nonorthogonal_correctors':1},
                benchmark_steps=args.benchmark_steps,benchmark_dt_us=args.benchmark_dt_us if args.benchmark_steps else None)
    meta.pop('maximum_wall_seconds',None)
    meta.pop('steady_start',None)
    (case/'case_manifest.json').write_text(json.dumps(meta,indent=2)+'\n')
    quality=json.loads((template/'quality-disposition.json').read_text())
    quality.update(case=case.name,purpose='Transient from a separately assessed steady-solver initialization; exploratory evidence.')
    (case/'quality-disposition.json').write_text(json.dumps(quality,indent=2)+'\n')
    args.mirror.mkdir(exist_ok=False)
    for name in ['case_manifest.json','quality-disposition.json']:shutil.copy2(case/name,args.mirror/name)
    sampled=source/'postProcessing/edge_sections'/args.iteration
    if all((sampled/(side+'.vtp')).is_file() for side in ['right_section','left_section']):
        # These are the exact sampled initial fields, with the physical clock reset.
        initial_sample=args.mirror/'postProcessing/edge_sections/0'
        initial_sample.mkdir(parents=True)
        for side in ['right_section','left_section']:
            shutil.copy2(sampled/(side+'.vtp'),initial_sample/(side+'.vtp'))
    print(json.dumps({'case':str(case),'steady_iteration':args.iteration,'physical_start_s':0,
                      'outer_correctors':args.outer_correctors,'benchmark_steps':args.benchmark_steps}))


if __name__=='__main__':main()
