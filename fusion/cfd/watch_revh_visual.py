"""Publish the running visual startup hourly and once after its deadline stop."""
import argparse
import ctypes
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

from snapshot_revh_visual import snapshot

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]
PAGE=ROOT/'docs/simulation/revh-transient/sequence'
PUBLIC='https://thereprocase.github.io/dell-5560-wall-mount/simulation/revh-transient/sequence/'
REPO='repos/thereprocase/dell-5560-wall-mount'
PYTHON='C:/Program Files/FreeCAD 1.1/bin/python.exe'


def now():return datetime.now(timezone.utc)


def write(path,data):
    temp=path.with_suffix('.tmp')
    temp.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8',newline='\n');temp.replace(path)


def update_readme(report,live):
    path=ROOT/'README.md';text=path.read_text(encoding='utf-8')
    active=live['state'] in ['running','writing_final_checkpoint']
    status=('The startup continuation is running until **4 p.m. Eastern on September 9, 2026**. '
            'Videos update automatically each hour, with a final update after the checkpoint and stop.' if active else
            'The startup continuation has stopped. Its native checkpoint and previous-step history are preserved for a later resume.')
    body=f'''## Rev H airflow videos - {'updating hourly' if active else 'recorded continuation'}

**Moving particles and trails, at 5× playback:**
[Startup]({PUBLIC}latest-tracers.mp4) ·
[Already flowing]({PUBLIC}flowing/latest-tracers.mp4).

{status}
The startup video covers **{report['last_time_s']*1000:.4f} ms** of simulated flow.
The separate flowing-air video remains at 68.0934 ms.

| Simulation | Original playback | 5× faster, 60 fps | Progress and archives |
|:--|:--|:--|:--|
| Startup | [MP4]({PUBLIC}latest.mp4) | [MP4]({PUBLIC}latest-5x.mp4) | [Startup page]({PUBLIC}) |
| Already flowing | [MP4]({PUBLIC}flowing/latest.mp4) | [MP4]({PUBLIC}flowing/latest-5x.mp4) | [Flowing page]({PUBLIC}flowing/) |

These stable links serve the latest published cumulative videos. All recorded
samples remain in the original playback. Particle views interpolate saved
in-plane velocity at 60 fps; they show projected 2D motion with fading trails.
The visual continuation begins at the old 38.3188 ms video endpoint and uses
fixed 80.93 microsecond steps, one step per 5× video frame, with 12 workers.
CFD runs at idle priority under a shared 28 GiB RAM cap. Full native fields are
saved every half hour and at the final stop. Earlier native branches and public
archives remain preserved. Timestep accuracy is deferred for this visual run;
the separate flowing-air sequence starts from an unconverged steady field.

'''
    text,n=re.subn(r'## Rev H airflow videos[^\n]*\n.*?(?=## MakerWorld preparation package)',lambda _:body,text,count=1,flags=re.S)
    assert n==1;path.write_text(text,encoding='utf-8',newline='\n')


def main():
    assert ctypes.windll.kernel32.SetPriorityClass(ctypes.c_void_p(-1),subprocess.IDLE_PRIORITY_CLASS)
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--case',type=Path,required=True)
    p.add_argument('--steady-case',type=Path,required=True)
    p.add_argument('--state-root',type=Path,required=True)
    p.add_argument('--until',required=True)
    p.add_argument('--resume',action='store_true')
    p.add_argument('--publish-now',action='store_true')
    args=p.parse_args();case=args.case.resolve();state_root=args.state_root.resolve()
    state_root.mkdir(parents=True,exist_ok=args.resume)
    deadline=datetime.fromisoformat(args.until.replace('Z','+00:00'));assert deadline.tzinfo
    status_path=state_root/'publisher-status.json';control_path=state_root/'control.json'
    if args.resume:state=json.loads(status_path.read_text())
    else:
        live=json.loads((case/'run-status.json').read_text());origin=datetime.fromisoformat(live['session_started_utc'])
        jobs=[]
        if args.publish_now:jobs.append(dict(due_utc=now().isoformat(),final=False,initial=True))
        due=origin+timedelta(hours=1)
        while due<deadline:
            jobs.append(dict(due_utc=due.isoformat(),final=False));due+=timedelta(hours=1)
        jobs.append(dict(due_utc=deadline.isoformat(),final=True))
        state=dict(started_utc=now().isoformat(),deadline_utc=deadline.isoformat(),state='waiting',jobs=jobs,publications=[])
        write(control_path,dict(stop_requested=False,deadline_utc=deadline.isoformat()))

    def save():state['updated_utc']=now().isoformat();write(status_path,state)

    def run(command,log,timeout=3600,check=True):
        result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',
                              timeout=timeout,creationflags=subprocess.IDLE_PRIORITY_CLASS|subprocess.CREATE_NO_WINDOW)
        log.write(result.stdout);log.write(result.stderr);log.flush()
        if check and result.returncode:raise RuntimeError(f'Command failed ({result.returncode}): {command[:3]}')
        return result

    def git(args,log,check=True):return run(['git',*args],log,180,check)
    def gh(args,log):return run(['wsl.exe','-e','gh','api',*args],log,180)

    def prepare(job,log):
        if job.get('source'):return Path(job['source'])
        live=snapshot(case,PAGE)
        job['snapshot']=live;save()
        output=state_root/(job['label']+'-render-'+now().strftime('%H%M%S'))
        presentation=case/'presentation'
        run([PYTHON,str(BASE/'render_revh_progress.py'),'--case',str(presentation),'--output',str(output),'--hour','0'],log)
        run([PYTHON,str(BASE/'compress_revh_video.py'),'--case',str(presentation),'--source',str(output),'--crf','30','--apply'],log)
        report=json.loads((output/'progress.json').read_text())
        report.update(visual_extension=live['visual_extension'],checkpoint_label='Final visual continuation' if job['final'] else 'Hourly visual continuation',
                      scope=live['scope'])
        write(output/'progress.json',report)
        public={k:live[k] for k in ['state','latest_physical_time_s','completed_steps','latest_deltaT_s','max_logged_Courant',
            'bounding_events','memory_peak_bytes','memory_limit_bytes','memory_events','cpu_workers','cpu_nice','scheduler',
            'authorized_deadline_utc','visual_extension','updated_utc','restart_checkpoint'] if k in live}
        write(output/'visual-run.json',public)
        job['source']=str(output);save();return output

    def publish(job):
        with (state_root/(job['label']+'-publication.log')).open('a',encoding='utf-8') as log:
            if not job.get('commit'):
                dirty=git(['diff','--name-only','-z'],log).stdout.split('\0')
                assert all(not p or p=='README.md' or p.startswith('docs/simulation/revh-transient/sequence/') for p in dirty),'Unexpected source changes; preserved for review'
                git(['fetch','origin'],log);git(['merge','--no-edit','origin/main'],log)
                source=prepare(job,log);target=PAGE/job['label']
                expected=json.loads((source/'progress.json').read_text())['video_sha256']
                if not target.exists():run([sys.executable,str(BASE/'stage_revh_checkpoint.py'),'--source',str(source),'--folder',job['label']],log)
                else:assert json.loads((target/'progress.json').read_text())['video_sha256']==expected
                shutil.copy2(source/'visual-run.json',target/'visual-run.json')
                run([sys.executable,str(BASE/'build_revh_sequence_page.py'),'--case',str(case/'presentation'),'--steady-case',str(args.steady_case)],log)
                report=json.loads((source/'progress.json').read_text());update_readme(report,job['snapshot'])
                server=subprocess.Popen([sys.executable,'-m','http.server','8890','--bind','127.0.0.1','--directory',str(ROOT/'docs')],
                    stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.IDLE_PRIORITY_CLASS|subprocess.CREATE_NO_WINDOW)
                try:
                    time.sleep(1);assert server.poll() is None,'Preview port unavailable'
                    run(['node',str(BASE/'review_revh_sequence.cjs'),'http://127.0.0.1:8890/simulation/revh-transient/sequence/',
                         str(state_root/(job['label']+'-local')),'--expected-sha',expected],log,300)
                finally:server.terminate();server.wait(timeout=15)
                git(['add','--','README.md','docs/simulation/revh-transient/sequence'],log)
                git(['diff','--cached','--check'],log)
                staged=git(['diff','--cached','--name-only','-z'],log).stdout.split('\0')
                assert all(not p or p=='README.md' or p.startswith('docs/simulation/revh-transient/sequence/') for p in staged)
                if any(staged):git(['-c','user.name=Repro','-c','user.email=thereprocase@users.noreply.github.com','commit','-m',f'Publish visual startup {job["label"]}'],log)
                for _ in range(3):
                    result=git(['push','--atomic','origin','HEAD:refs/heads/codex/cfd-tracer-videos','HEAD:refs/heads/main'],log,False)
                    if not result.returncode:break
                    git(['fetch','origin'],log);git(['merge','--no-edit','origin/main'],log)
                else:raise RuntimeError('Publication push failed; local commit preserved')
                job['commit']=git(['rev-parse','HEAD'],log).stdout.strip();job['expected_sha']=expected;save()
                gh(['--method','POST',REPO+'/pages/builds'],log)
            state['state']='verifying_deployment';save()
            for _ in range(90):
                build=json.loads(gh([REPO+'/pages/builds/latest'],log).stdout)
                if build['status']=='built':
                    git(['fetch','origin'],log)
                    if git(['merge-base','--is-ancestor',job['commit'],build['commit']],log,False).returncode==0:break
                if build['status']=='errored':raise RuntimeError('GitHub Pages build failed')
                time.sleep(10)
            else:raise RuntimeError('Pages deployment is still pending')
            run(['node',str(BASE/'review_revh_sequence.cjs'),PUBLIC+'?v='+job['commit'],
                 str(state_root/(job['label']+'-live')),'--expected-sha',job['expected_sha']],log,300)
            item=dict(label=job['label'],published_utc=now().isoformat(),commit=job['commit'],
                      last_time_s=job['snapshot']['latest_physical_time_s'],source_frames=job['snapshot']['complete_sample_frames'])
            state['publications'].append(item);job['state']='published';state['state']='complete' if job['final'] else 'waiting';save()
            print(json.dumps(item),flush=True)

    save()
    for job in state['jobs']:
        if job.get('state')=='published':continue
        while True:
            live=json.loads((case/'run-status.json').read_text());control=json.loads(control_path.read_text())
            stopped=live['state'] in ['complete','failed']
            if stopped or control.get('stop_requested'):
                job['final']=True
                if stopped:break
            elif now()>=datetime.fromisoformat(job['due_utc']) and not job['final']:break
            state['state']='waiting_for_final_checkpoint' if job['final'] and now()>=deadline else 'waiting';save();time.sleep(5)
        if not job.get('label'):
            job['label']=f'checkpoint-{max(int(p.name.split("-")[1]) for p in PAGE.glob("checkpoint-*"))+1:02d}'
        while job.get('state')!='published':
            try:
                state.update(state='publishing',current=job['label']);state.pop('error',None);save();publish(job)
            except Exception as exc:
                state.update(state='retrying_publication',error=repr(exc));job['last_error']=repr(exc);save()
                print(json.dumps({'publication_error':repr(exc),'retry_in_seconds':60}),flush=True);time.sleep(60)
        if job['final']:break


if __name__=='__main__':main()
