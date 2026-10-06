"""Run installed Windows OpenFOAM tools with preserved logs and explicit gates."""
from pathlib import Path
import argparse
import json
import os
import re
import subprocess
import shutil
import hashlib
import time
from datetime import datetime, timezone

BASE=Path(__file__).resolve().parent


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase',choices=['surface','mesh','zones','initialize','pilot','reconstruct','runtime-smoke','runtime-smoke-parallel'])
    parser.add_argument('--case',type=Path,default=BASE/'runs/revh_transient_01')
    parser.add_argument('--source-case',type=Path)
    parser.add_argument('--attempt',type=int,default=1,help='New attempt number preserves earlier phase logs')
    args=parser.parse_args()
    case=args.case.resolve()
    baram=Path(os.environ['LOCALAPPDATA'])/'Programs/BARAM-26.3.0'
    foam=baram/'solvers/openfoam'
    env=os.environ.copy()
    env['WM_PROJECT_DIR']=str(foam)
    env['PATH']=';'.join(str(p) for p in [baram/'solvers/mingw64/bin',baram/'solvers/mingw64/lib',foam/'bin',foam/'lib',foam/'lib/msmpi',Path('C:/Program Files/Microsoft MPI/Bin')])+';'+env['PATH']
    env['OMP_NUM_THREADS']='1'
    env['WINDIR']=env['SystemRoot']='C:\\Windows'
    env['USERPROFILE']=str(Path(env['LOCALAPPDATA']).parents[1])
    status={'phase':args.phase,'started_utc':datetime.now(timezone.utc).isoformat(),'state':'running','steps':[]}
    suffix='' if args.attempt==1 else '.attempt'+str(args.attempt)
    assert args.attempt>=1
    status_path=case/('status.'+args.phase+suffix+'.json')
    def save():status_path.write_text(json.dumps(status,indent=2)+'\n')
    if status_path.exists():raise RuntimeError('Preserve existing phase evidence: '+str(status_path))
    save()
    def run(tool,*arguments,parallel=False,label=None):
        name=label or tool
        log=case/('log.'+name+suffix)
        if log.exists():raise RuntimeError('Preserve existing log: '+str(log))
        command=[str(foam/'bin'/(tool+'.exe')),*arguments]
        if parallel:command=['C:/Program Files/Microsoft MPI/Bin/mpiexec.exe','-n','8',*command,'-parallel']
        print('RUN',name,flush=True)
        started=time.monotonic()
        with log.open('wb') as out:
            proc=subprocess.Popen(command,cwd=case,env=env,stdout=out,stderr=subprocess.STDOUT)
            status['active_tool']={'tool':tool,'pid':proc.pid,'log':log.name};save()
            proc.wait()
        status.pop('active_tool',None)
        entry={'tool':tool,'executable_sha256':hashlib.sha256((foam/'bin'/(tool+'.exe')).read_bytes()).hexdigest(),
               'arguments':arguments,'parallel':parallel,'log':log.name,'exit_code':proc.returncode,'wall_seconds':time.monotonic()-started}
        status['steps'].append(entry);save()
        text=log.read_text(errors='replace')
        print(name,proc.returncode,round(entry['wall_seconds'],1),'s',flush=True)
        if proc.returncode or 'FOAM FATAL' in text:raise RuntimeError('Failed '+name+'; see '+str(log))
        return text
    try:
        if args.phase in ['runtime-smoke','runtime-smoke-parallel']:
            assert json.loads((case/'case_manifest.json').read_text())['scope']=='runtime_smoke_only'
            run('blockMesh')
            text=run('checkMesh',label='checkMesh.standard')
            assert 'Mesh OK.' in text
            if args.phase=='runtime-smoke-parallel':
                run('decomposePar')
                run('pimpleFoam',parallel=True)
                run('reconstructPar','-latestTime')
            else:run('pimpleFoam')
        elif args.phase=='surface':
            text=run('surfaceCheck','-checkSelfIntersection','constant/triSurface/fluid_boundary.stl')
            assert 'Surface is closed' in text and 'Surface is not self-intersecting' in text, text[-3000:]
        elif args.phase=='mesh':
            assert json.loads((case/'status.surface.json').read_text())['state']=='complete'
            assert not (case/'constant/polyMesh').exists()
            run('blockMesh')
            run('decomposePar',label='decomposeMesh')
            run('snappyHexMesh','-overwrite',parallel=True)
            assert 'reached limit' not in (case/'log.snappyHexMesh').read_text(errors='replace'), 'Refinement limit prevented completion'
            run('reconstructParMesh','-constant',label='reconstructMesh')
            text=run('checkMesh','-constant',label='checkMesh.standard')
            assert 'Mesh OK.' in text,text[-5000:]
            assert re.search(r'Number of regions:\s+1(?:\s|$)',text), 'Expected one connected fluid region'
            run('checkMesh','-constant','-allGeometry','-allTopology',label='checkMesh.expanded')
        elif args.phase=='zones':
            assert json.loads((case/'status.mesh.json').read_text())['state']=='complete'
            run('topoSet')
        elif args.phase=='initialize':
            assert json.loads((case/'status.zones.json').read_text())['state']=='complete'
            assert args.source_case is not None, '--source-case is required'
            source=args.source_case.resolve()
            assert (source/'1200/U').is_file() and (source/'constant/polyMesh/points').is_file()
            shutil.copytree(case/'0',case/('initial_fields_before_mapping'+suffix))
            mapping_source=case/'mapping_source_1200'
            if not mapping_source.exists():
                shutil.copytree(source/'constant',mapping_source/'constant')
                shutil.copytree(source/'system',mapping_source/'system')
                (mapping_source/'1200').mkdir()
                for field in ['U','p','k','omega','nut']:
                    shutil.copy2(source/'1200'/field,mapping_source/'1200'/field)
            (case/'system/mapFieldsDict').write_text('FoamFile {version 2.0; format ascii; class dictionary; object mapFieldsDict;}\npatchMap (laptop laptop noctua noctua wall_plane wall_plane ambient_openings ambient_openings);\ncuttingPatches ();\n')
            run('mapFields',mapping_source.as_posix(),'-sourceTime','1200','-mapMethod','interpolate')
            status['initialization']={'source':str(source),'source_time':1200,'method':'interpolate','meaning':'Old Revision F fields mapped only to shorten startup; not a Revision H result. Uncovered cells retain initialized values.'}
        elif args.phase=='pilot':
            assert json.loads((case/'status.zones.json').read_text())['state']=='complete'
            quality=json.loads((case/'quality-disposition.json').read_text())
            assert quality['case']==case.name
            assert 'Mesh OK.' in (case/'log.checkMesh.standard').read_text(errors='replace')
            assert quality['disposition'] in ['commissioning_only','accepted']
            status['quality_disposition']=quality
            run('decomposePar','-force',label='decomposeSolve')
            run('pimpleFoam',parallel=True)
            run('reconstructPar','-latestTime',label='reconstructPilot')
        else:
            run('reconstructPar','-latestTime',label='reconstructLatest')
        status['state']='complete'
    except BaseException as exc:
        status['state']='failed';status['error']=str(exc)
        raise
    finally:
        status['finished_utc']=datetime.now(timezone.utc).isoformat();save()


if __name__=='__main__':main()
