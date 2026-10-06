"""Rebuild the current video endpoint, then extend at one solver step per frame."""
import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import time
import numpy as np
from compare_cfd_fields import fields
from revh_checkpoint import describe, sha, NATIVE_FIELDS
from run_revh_wall_budget import lower_priority, workers, mirror_samples


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--video-report',type=Path,required=True)
    p.add_argument('--case',type=Path,required=True)
    p.add_argument('--mirror',type=Path,required=True)
    p.add_argument('--frames',type=int,required=True)
    args=p.parse_args()
    lower_priority()
    source,case,mirror=(p.resolve() for p in [args.source,args.case,args.mirror])
    assert source.name=='revh_fourhour_08' and case.parent==source.parent and case!=source
    assert not case.exists() and not mirror.exists() and not workers(source)
    assert os.environ.get('WM_PROJECT_VERSION')=='v2412' and 1<=args.frames<=6000
    os.environ['HWLOC_COMPONENTS']='linux,stop';os.environ['OMP_NUM_THREADS']='1'
    for name in ['DISPLAY','WAYLAND_DISPLAY','XAUTHORITY']:os.environ.pop(name,None)
    video=json.loads(args.video_report.read_text())
    tail=float(video['last_time_s']);dt=1/(video['fps']*video['playback_slowdown'])
    checkpoints=sorted((float(p.name),p.name) for p in (source/'processor0').iterdir()
                       if p.is_dir() and p.name[0].isdigit())
    saved=max(t for t in checkpoints if t[0]<=tail)[1]
    original=describe(source,4)
    case.mkdir();mirror.mkdir(parents=True)
    started=time.monotonic()
    report=dict(state='copying',started_utc=datetime.now(timezone.utc).isoformat(),
                source_case=str(source),case=str(case),source_checkpoint=saved,
                video_tail_s=tail,video_sha256=video['video_sha256'],
                coarse_deltaT_s=dt,video_fps=video['fps'],playback_slowdown=video['playback_slowdown'],
                requested_new_frames=args.frames,ranks=12,visualization_only=True,
                scope='User requested temporal progress and appearance; timestep accuracy deferred.',
                phases={})
    cgroup=Path('/sys/fs/cgroup')/Path('/proc/self/cgroup').read_text().strip().split('::')[1].lstrip('/')
    slice_group=next(x for x in [cgroup,*cgroup.parents] if x.name=='cfd.slice')
    report['resource_limits']={name:((slice_group/name).read_text().strip() if (slice_group/name).exists() else None)
                               for name in ['memory.max','memory.high','memory.swap.max','cpu.weight','io.weight']}
    report['nice']=os.getpriority(os.PRIO_PROCESS,0);report['scheduler']=os.sched_getscheduler(0)

    def save(state=None):
        if state:report['state']=state
        report['updated_utc']=datetime.now(timezone.utc).isoformat()
        report['wall_seconds']=time.monotonic()-started
        report['memory_current_bytes']=int((cgroup/'memory.current').read_text())
        report['memory_peak_bytes']=int((cgroup/'memory.peak').read_text())
        report['memory_events']=(cgroup/'memory.events').read_text()
        for root in [case,mirror]:
            temp=root/'visual-status.json.tmp';temp.write_text(json.dumps(report,indent=2)+'\n');temp.replace(root/'visual-status.json')
        print(json.dumps({k:v for k,v in report.items() if k not in ['phases','restart_checkpoint','initial_checkpoint']}),flush=True)

    def run(command,label,timeout=1500):
        save(label);begin=time.monotonic();notice=begin
        log_path=case/('log.'+label)
        with log_path.open('w') as log:
            proc=subprocess.Popen(command,cwd=case,stdout=log,stderr=subprocess.STDOUT,
                                  stdin=subprocess.DEVNULL,start_new_session=True)
            try:
                while proc.poll() is None:
                    if time.monotonic()-begin>timeout:raise TimeoutError(label)
                    if time.monotonic()-notice>=20:
                        raw=log_path.read_text(errors='replace')
                        clocks=list(map(float,re.findall(r'ClockTime = ([\d.eE+-]+) s',raw)))
                        report['phase_progress']={'phase':label,'steps':len(clocks),'elapsed_s':time.monotonic()-begin,
                                                  'seconds_per_step_after_first':(clocks[-1]-clocks[0])/(len(clocks)-1) if len(clocks)>1 else None}
                        save();notice=time.monotonic()
                    time.sleep(.5)
            finally:
                if proc.poll() is None:
                    os.killpg(proc.pid,signal.SIGTERM)
                    try:proc.wait(timeout=15)
                    except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
        assert proc.returncode==0,(label,proc.returncode)
        return log_path,time.monotonic()-begin

    for name in ['constant','system']:shutil.copytree(source/name,case/name)
    for name in ['case_manifest.json','quality-disposition.json']:shutil.copy2(source/name,case/name)
    for rank in range(4):
        for name in ['constant',saved]:shutil.copytree(source/f'processor{rank}'/name,case/f'processor{rank}'/name)
    initial=describe(case,4);report['initial_checkpoint']=initial
    for relative,digest in initial['field_sha256'].items():assert sha(source/relative)==digest
    run(['reconstructPar','-time',saved],'reconstruct_before',300)
    before=fields(case,float(saved),NATIVE_FIELDS)
    archive=case/'original-four-rank-checkpoint';archive.mkdir()
    for rank in range(4):
        part=case/f'processor{rank}';assert part.resolve().parent==case
        part.rename(archive/part.name)
    decomp=case/'system/decomposeParDict'
    decomp.write_text(re.sub(r'numberOfSubdomains\s+\d+;','numberOfSubdomains 12;',decomp.read_text()))
    run(['decomposePar','-time',saved],'decompose_12',300)
    run(['reconstructPar','-time',saved],'reconstruct_check',300)
    after=fields(case,float(saved),NATIVE_FIELDS)
    report['repartition_comparison']={n:{
        'exact':bool(np.array_equal(before[n],after[n])),
        'finite':bool(np.isfinite(before[n]).all() and np.isfinite(after[n]).all()),
        'max_abs_difference':float(np.max(np.abs(before[n]-after[n]))),
        'reference_max_abs':float(np.max(np.abs(before[n])))} for n in NATIVE_FIELDS}
    assert all(v['finite'] for v in report['repartition_comparison'].values())
    assert describe(case,12)['native_time_metadata']==initial['native_time_metadata']
    del before,after
    report['repartition_exact']=all(v['exact'] for v in report['repartition_comparison'].values())
    template=(case/'system/controlDict').read_text()
    solver=['mpirun','--use-hwthread-cpus','--bind-to','none','-np','12','pimpleFoam','-parallel']

    def phase(label,end,step,count,start_index,sample_interval):
        text=template
        settings={'startFrom':'latestTime','stopAt':'endTime','endTime':format(end,'.17g'),
                  'deltaT':format(step,'.17g'),'adjustTimeStep':'no','maxDeltaT':format(step,'.17g'),
                  'writeControl':'timeStep','writeInterval':str(start_index+count),'timePrecision':'14'}
        for key,value in settings.items():
            text,n=re.subn(r'\b'+key+r'\s+[^;]+;',key+' '+value+';',text,count=1);assert n==1,key
        text=re.sub(r'(edge_sections\s*\{.*?writeInterval\s+)\d+;',lambda m:m[1]+str(sample_interval)+';',text,count=1,flags=re.S)
        text=text.replace('executeInterval 2;','executeInterval 1;')
        (case/'system/controlDict').write_text(text)
        shutil.copy2(case/'system/controlDict',case/('controlDict.'+label))
        log,wall=run(solver,label,1800)
        raw=log.read_text();clocks=list(map(float,re.findall(r'ClockTime = ([\d.eE+-]+) s',raw)))
        assert re.search(r'^End\s*$',raw,re.M) and len(clocks)==count
        assert not re.search(r'=\s*[-+]?(?:nan|inf)\b',raw,re.I)
        checkpoint=describe(case,12)
        assert abs(checkpoint['physical_time_s']-end)<1e-11
        report['phases'][label]=dict(steps=count,deltaT_s=step,end_time_s=end,wall_seconds=wall,
            clock_seconds=clocks[-1],seconds_per_step_after_first=(clocks[-1]-clocks[0])/(len(clocks)-1) if len(clocks)>1 else None,
            max_Courant=max(map(float,re.findall(r'Courant Number mean: [^ ]+ max: ([\d.eE+-]+)',raw))),
            bounding_events=len(re.findall(r'^bounding ',raw,re.M)))
        return checkpoint

    initial_value=float(initial['native_time_metadata']['value'])
    fine_count=max(1,round((tail-initial_value)/float(initial['native_time_metadata']['deltaT'])))
    report['replay_steps']=fine_count
    replay=phase('replay_to_video_tail',tail,(tail-initial_value)/fine_count,fine_count,
                 int(initial['native_time_metadata']['index']),int(initial['native_time_metadata']['index'])+fine_count)
    report['tail_checkpoint']=replay['time_folder']
    coarse_start=float(replay['native_time_metadata']['value'])
    final=phase('coarse_visual_extension',coarse_start+args.frames*dt,dt,args.frames,
                int(replay['native_time_metadata']['index']),1)
    mirror_samples(case,mirror)
    new_times=sorted(float(p.name) for p in (mirror/'postProcessing/edge_sections').iterdir()
                     if p.is_dir() and float(p.name)>tail+1e-11)
    assert len(new_times)==args.frames
    assert all(abs(t-(tail+(i+1)*dt))<1e-11 for i,t in enumerate(new_times))
    assert describe(source,4)['field_sha256']==original['field_sha256'] and not workers(case)
    report.update(new_sample_times_s=new_times,restart_checkpoint=final,workers_stopped=True)
    manifest=json.loads((case/'case_manifest.json').read_text())
    manifest.update(cpu_workers=12,ranks=12,current_native_case=case.name,
                    fixed_deltaT_s=dt,adjustTimeStep=False,
                    visual_continuation_from_s=tail,scope=report['scope'])
    (case/'case_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    for root in [case,mirror]:(root/'resume-checkpoint.json').write_text(json.dumps(final,indent=2)+'\n')
    for name in ['case_manifest.json','quality-disposition.json','controlDict.replay_to_video_tail','controlDict.coarse_visual_extension',
                 'log.replay_to_video_tail','log.coarse_visual_extension']:shutil.copy2(case/name,mirror/name)
    save('complete')


if __name__=='__main__':main()
