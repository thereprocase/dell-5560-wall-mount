"""Prepare each hourly video locally while the four-hour solver is running.

Artifacts are staged in the ignored case mirror. Publishing remains a separate
reviewed step, so a failed render cannot change the public checkpoint page.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import subprocess
import time

BASE=Path(__file__).resolve().parent
RENDER_PYTHON='C:/Program Files/FreeCAD 1.1/bin/python.exe'


def wsl_path(path):
    path=path.resolve()
    return '/mnt/'+path.drive[0].lower()+'/'+path.as_posix()[3:]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case',type=Path,required=True)
    parser.add_argument('--wsl-case',required=True)
    args=parser.parse_args();case=args.case.resolve()
    status_file=case/'hourly-artifacts.json'
    assert not status_file.exists(),'An hourly watcher already has a state file'
    state={'started_utc':datetime.now(timezone.utc).isoformat(),'state':'waiting','hours':[]}
    def save():
        state['updated_utc']=datetime.now(timezone.utc).isoformat()
        temp=status_file.with_suffix('.tmp');temp.write_text(json.dumps(state,indent=2)+'\n');temp.replace(status_file)
    def run(command,log):
        result=subprocess.run(command,cwd=BASE.parents[1],stdout=log,stderr=subprocess.STDOUT,
                              creationflags=subprocess.IDLE_PRIORITY_CLASS)
        if result.returncode:raise RuntimeError('Artifact command failed: '+str(command[1]))
    save()
    try:
        for hour in range(1,5):
            while True:
                solver=json.loads((case/'run-status.json').read_text())
                if solver['state']=='failed':raise RuntimeError('Solver failed; inspect final status before further hourly rendering')
                if solver['elapsed_seconds']>=hour*3600 and (hour<4 or solver['state']=='complete'):break
                time.sleep(5)
            state.update(state='rendering',current_hour=hour);save()
            output=case/'hourly'/f'hour-{hour}'
            output.parent.mkdir(exist_ok=True)
            log_path=output.parent/f'hour-{hour}-preparation.log'
            with log_path.open('w') as log:
                run([RENDER_PYTHON,str(BASE/'render_revh_progress.py'),'--case',str(case),'--output',str(output),'--hour',str(hour)],log)
                run(['wsl.exe','-e','python3',wsl_path(BASE/'collect_revh_diagnostics.py'),'--case',args.wsl_case,'--output',wsl_path(output)],log)
                run([RENDER_PYTHON,str(BASE/'plot_revh_history.py'),'--output',str(output)],log)
            report=json.loads((output/'progress.json').read_text())
            assert not report['preview_subsampled'] and report['hour_checkpoint']==hour
            assert report['source_frames']>=2
            assert hashlib.sha256((output/'flow.mp4').read_bytes()).hexdigest()==report['video_sha256']
            state['hours'].append({'hour':hour,'ready_utc':datetime.now(timezone.utc).isoformat(),
                                   'path':str(output),'source_frames':report['source_frames'],
                                   'physical_time_s':report['last_time_s'],'video_duration_s':report['video_duration_s']})
            state['state']='ready' if hour==4 else 'waiting';save()
            print(json.dumps(state['hours'][-1]),flush=True)
        state['state']='complete';save()
    except Exception as error:
        state.update(state='failed',error=str(error));save();raise


if __name__=='__main__':main()
