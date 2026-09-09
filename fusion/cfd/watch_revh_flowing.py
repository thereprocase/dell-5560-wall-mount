"""Prepare flowing-field videos after 20 minutes and at the remaining hourly deadlines."""
import argparse
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import subprocess
import time
from watch_revh_hourly import BASE,RENDER_PYTHON,wsl_path


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--case',type=Path,required=True)
    p.add_argument('--original',type=Path,required=True);p.add_argument('--wsl-case',required=True)
    args=p.parse_args();case=args.case.resolve();status=case/'flowing-artifacts.json';assert not status.exists()
    original=json.loads((args.original/'run-status.json').read_text())
    initial=json.loads((case/'run-status.json').read_text())
    origin=datetime.fromisoformat(original['started_utc']);start=datetime.fromisoformat(initial['started_utc'])
    deadlines=[start+timedelta(seconds=1200),origin+timedelta(seconds=10800),origin+timedelta(seconds=14400)]
    state={'state':'waiting','checkpoints':[],'deadlines_utc':[d.isoformat() for d in deadlines]}
    def save():
        state['updated_utc']=datetime.now(timezone.utc).isoformat();temp=status.with_suffix('.tmp')
        temp.write_text(json.dumps(state,indent=2)+'\n');temp.replace(status)
    def run(command,log):
        result=subprocess.run(command,cwd=BASE.parents[1],stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.IDLE_PRIORITY_CLASS)
        assert result.returncode==0,command
    save()
    try:
        for index,deadline in enumerate(deadlines,1):
            while True:
                solver=json.loads((case/'run-status.json').read_text())
                assert solver['state']!='failed','Flowing-field solver failed'
                if datetime.now(timezone.utc)>=deadline and (index<3 or solver['state']=='complete'):break
                time.sleep(5)
            state.update(state='rendering',current_checkpoint=index);save()
            output=case/'checkpoints'/f'checkpoint-{index:02d}';output.parent.mkdir(exist_ok=True)
            with (output.parent/f'checkpoint-{index:02d}.log').open('w') as log:
                run([RENDER_PYTHON,str(BASE/'render_revh_progress.py'),'--case',str(case),'--output',str(output),'--hour','0'],log)
                run(['wsl.exe','-e','python3',wsl_path(BASE/'collect_revh_diagnostics.py'),'--case',args.wsl_case,'--output',wsl_path(output)],log)
                run([RENDER_PYTHON,str(BASE/'plot_revh_history.py'),'--output',str(output)],log)
            report=json.loads((output/'progress.json').read_text())
            state['checkpoints'].append({'checkpoint':index,'ready_utc':datetime.now(timezone.utc).isoformat(),
                'source_frames':report['source_frames'],'last_time_s':report['last_time_s'],'path':str(output)})
            state['state']='waiting' if index<3 else 'complete';save();print(json.dumps(state['checkpoints'][-1]),flush=True)
    except Exception as error:
        state.update(state='failed',error=str(error));save();raise


if __name__=='__main__':main()
