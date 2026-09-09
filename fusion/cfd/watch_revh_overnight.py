"""Render, verify, and publish authorized hourly CFD checkpoints through a deadline.

This Windows controller uses the existing GitHub Pages repository. Each archive
is immutable. It verifies every video locally before commit, handles concurrent
main-branch updates without force pushing, and verifies the exact deployed video
hash afterward. A publication failure preserves work and leaves solvers running.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import subprocess
import sys
import time
from watch_revh_hourly import BASE,RENDER_PYTHON,wsl_path

ROOT=BASE.parents[1]
PAGE=ROOT/'docs/simulation/revh-transient/sequence'
PUBLIC='https://thereprocase.github.io/dell-5560-wall-mount/simulation/revh-transient/sequence/'
REPO='repos/thereprocase/dell-5560-wall-mount'
WSL_ROOT='/home/repro/code/dell5560-cfd-gpu-20260908'


def now():return datetime.now(timezone.utc)


def main():
    import ctypes
    if not ctypes.windll.kernel32.SetPriorityClass(ctypes.c_void_p(-1),subprocess.IDLE_PRIORITY_CLASS):
        raise OSError('Could not set the CFD publisher to Idle priority')
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--until',required=True)
    p.add_argument('--state-root',type=Path,default=BASE/'runs/revh_overnight_16')
    p.add_argument('--resume',action='store_true')
    args=p.parse_args();state_root=args.state_root.resolve();state_root.mkdir(parents=True,exist_ok=args.resume)
    status_path=state_root/'overnight-status.json';control_path=state_root/'control.json'
    deadline=datetime.fromisoformat(args.until.replace('Z','+00:00'));assert deadline.tzinfo and deadline>now()
    cases={'startup':BASE/'runs/revh_fourhour_08','flowing':BASE/'runs/revh_flowing_12'}
    origin=datetime.fromisoformat(json.loads((cases['startup']/'run-status.json').read_text())['started_utc'])
    if args.resume:
        state=json.loads(status_path.read_text())
    else:
        last_hour=max(int(path.name.split('-')[1]) for path in PAGE.glob('hour-*') if (path/'progress.json').is_file())
        last_flow=max(int(path.name.split('-')[1]) for path in (PAGE/'flowing').glob('checkpoint-*'))
        next_final=max(int(path.name.split('-')[1]) for path in PAGE.glob('checkpoint-*'))+1
        if origin+timedelta(hours=last_hour+1)<now()-timedelta(minutes=5):origin=now()-timedelta(hours=last_hour)
        jobs=[];hour=last_hour+1;flow=last_flow+1
        while origin+timedelta(hours=hour)<deadline:
            jobs.append({'label':f'hour-{hour}','hour':hour,'flow_checkpoint':flow,
                         'due_utc':(origin+timedelta(hours=hour)).isoformat(),'final':False})
            hour+=1;flow+=1
        jobs.append({'label':f'checkpoint-{next_final:02d}','hour':0,'flow_checkpoint':flow,
                     'due_utc':deadline.isoformat(),'final':True})
        state={'started_utc':now().isoformat(),'deadline_utc':deadline.isoformat(),'state':'waiting','jobs':jobs,'publications':[]}
        control_path.write_text(json.dumps({'deadline_utc':deadline.isoformat(),'stop_requested':False},indent=2)+'\n')

    def save():
        state['updated_utc']=now().isoformat();temp=status_path.with_suffix('.tmp')
        temp.write_text(json.dumps(state,indent=2)+'\n');temp.replace(status_path)

    def run(command,log,timeout=1800,check=True):
        result=subprocess.run(command,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,
                              encoding='utf-8',errors='replace',timeout=timeout,
                              creationflags=subprocess.IDLE_PRIORITY_CLASS|subprocess.CREATE_NO_WINDOW)
        log.write(result.stdout);log.write(result.stderr);log.flush()
        if check and result.returncode:raise RuntimeError(f'Command failed ({result.returncode}): {command[:3]}')
        return result

    def git(arguments,log,check=True):return run(['git',*arguments],log,120,check)
    def gh(arguments,log):return run(['wsl.exe','-e','gh','api',*arguments],log,120)

    def prepare(kind,job):
        case=cases[kind]
        if job.get('sources',{}).get(kind):return job['sources'][kind]
        parent=case/'overnight';parent.mkdir(exist_ok=True)
        attempt=1
        while (parent/f'{job["label"]}-attempt-{attempt}').exists():attempt+=1
        output=parent/f'{job["label"]}-attempt-{attempt}'
        with (parent/f'{job["label"]}-attempt-{attempt}.log').open('w',encoding='utf-8') as log:
            run([RENDER_PYTHON,str(BASE/'render_revh_progress.py'),'--case',str(case),'--output',str(output),'--hour',str(job['hour'] if kind=='startup' else 0)],log)
            run(['wsl.exe','-e','nice','-n','19','ionice','-c','3','python3',wsl_path(BASE/'collect_revh_diagnostics.py'),'--case',WSL_ROOT+'/'+case.name,'--output',wsl_path(output)],log)
            run([RENDER_PYTHON,str(BASE/'plot_revh_history.py'),'--output',str(output)],log)
            run([RENDER_PYTHON,str(BASE/'compress_revh_video.py'),'--case',str(case),'--source',str(output),'--crf','30','--apply'],log)
        if job['final']:
            path=output/'progress.json';report=json.loads(path.read_text())
            report['checkpoint_label']='Final scheduled checkpoint' if not job.get('user_stop') else 'Stopped checkpoint'
            path.write_text(json.dumps(report,indent=2)+'\n')
        return str(output)

    def review(kind,base,folder,expected,log):
        command=['node',str(BASE/'review_revh_sequence.cjs'),base,str(folder),'--expected-sha',expected]
        if kind=='flowing':command.append('--no-early-alias')
        run(command,log,300)

    save()
    try:
        for job in state['jobs']:
            if job.get('state')=='published':continue
            while True:
                control=json.loads(control_path.read_text())
                statuses={kind:json.loads((case/'run-status.json').read_text()) for kind,case in cases.items()}
                assert not any(s['state']=='failed' for s in statuses.values()),'A CFD solver requires attention'
                if control.get('stop_requested'):
                    job.update(final=True,user_stop=True,hour=0)
                    job['label']=f'checkpoint-{max(int(path.name.split("-")[1]) for path in PAGE.glob("checkpoint-*"))+1:02d}'
                    job['flow_checkpoint']=max(int(path.name.split('-')[1]) for path in (PAGE/'flowing').glob('checkpoint-*'))+1
                    if all(s['state']=='complete' for s in statuses.values()):break
                elif now()>=datetime.fromisoformat(job['due_utc']):
                    if not job['final'] or all(s['state']=='complete' and s.get('restart_checkpoint') for s in statuses.values()):break
                time.sleep(5)
            state.update(state='preparing',current=job['label']);job['state']='preparing';save()
            with (state_root/(job['label']+'-publication.log')).open('a',encoding='utf-8') as log:
                changed=git(['diff','--name-only','-z'],log).stdout.split('\0')
                assert all(not path or path.startswith('docs/simulation/revh-transient/sequence/') for path in changed),'Unexpected source edits; preserve them for review'
                git(['fetch','origin'],log);git(['merge','--no-edit','origin/main'],log)
                with ThreadPoolExecutor(max_workers=2) as pool:
                    futures={kind:pool.submit(prepare,kind,job) for kind in cases}
                    for kind,future in futures.items():job.setdefault('sources',{})[kind]=future.result();save()
                startup_source=Path(job['sources']['startup']);flow_source=Path(job['sources']['flowing'])
                target=PAGE/job['label']
                if target.exists():
                    assert json.loads((target/'progress.json').read_text())['video_sha256']==json.loads((startup_source/'progress.json').read_text())['video_sha256']
                else:run([RENDER_PYTHON,str(BASE/'stage_revh_checkpoint.py'),'--source',str(startup_source),'--folder',job['label']],log)
                run([RENDER_PYTHON,str(BASE/'publish_revh_flowing_checkpoint.py'),'--case',str(cases['flowing']),'--source',str(flow_source),'--checkpoint',str(job['flow_checkpoint']),'--reuse'],log)
                run([RENDER_PYTHON,str(BASE/'build_revh_sequence_page.py'),'--case',str(cases['startup'])],log)
                expected={kind:json.loads((Path(job['sources'][kind])/'progress.json').read_text())['video_sha256'] for kind in cases}
                for kind in cases:
                    suffix='flowing/' if kind=='flowing' else ''
                    review(kind,'http://127.0.0.1:8881/simulation/revh-transient/sequence/'+suffix,
                           state_root/(job['label']+'-'+kind+'-local'),expected[kind],log)
                git(['add','-u','--','docs/simulation/revh-transient/sequence'],log)
                git(['add','--',str(target.relative_to(ROOT)),str((PAGE/'flowing'/f'checkpoint-{job["flow_checkpoint"]:02d}').relative_to(ROOT))],log)
                git(['diff','--cached','--check'],log)
                staged=git(['diff','--cached','--name-only','-z'],log).stdout.split('\0')
                assert all(not path or path.startswith('docs/simulation/revh-transient/sequence/') for path in staged)
                if any(staged):git(['-c','user.name=Repro','-c','user.email=thereprocase@users.noreply.github.com','commit','-m',f'Publish cumulative CFD {job["label"]} checkpoints'],log)
                for attempt in range(3):
                    pushed=git(['push','--atomic','origin','HEAD:refs/heads/codex/cfd-revh-transient','HEAD:refs/heads/main'],log,False)
                    if pushed.returncode==0:break
                    git(['fetch','origin'],log);git(['merge','--no-edit','origin/main'],log)
                else:raise RuntimeError('Atomic publication push failed after preserving and merging concurrent work')
                commit=git(['rev-parse','HEAD'],log).stdout.strip();job['commit']=commit;save()
                gh(['--method','POST',REPO+'/pages/builds'],log)
                deployed=False
                for _ in range(30):
                    build=json.loads(gh([REPO+'/pages/builds/latest'],log).stdout)
                    if build['status']=='built':
                        if build['commit']==commit:deployed=True;break
                        git(['fetch','origin'],log)
                        if git(['merge-base','--is-ancestor',commit,build['commit']],log,False).returncode==0:deployed=True;break
                    if build['status']=='errored':raise RuntimeError('GitHub Pages build failed')
                    time.sleep(10)
                assert deployed,'Pages deployment did not include the committed checkpoint'
                for kind in cases:
                    suffix='flowing/' if kind=='flowing' else ''
                    review(kind,PUBLIC+suffix+'?v='+commit,state_root/(job['label']+'-'+kind+'-live'),expected[kind],log)
                publication={'label':job['label'],'published_utc':now().isoformat(),'commit':commit}
                for kind in cases:
                    report=json.loads((Path(job['sources'][kind])/'progress.json').read_text())
                    publication[kind]={key:report[key] for key in ['source_frames','last_time_s','video_duration_s','video_sha256']}
                job['state']='published';state['publications'].append(publication)
                state['state']='complete' if job['final'] else 'waiting';save();print(json.dumps(publication),flush=True)
                if job['final']:break
    except Exception as error:
        state.update(state='failed',error=str(error));save();raise


if __name__=='__main__':main()
