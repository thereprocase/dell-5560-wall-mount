"""Start the assessed flowing-field transient inside the original four-hour deadline."""
import argparse
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import subprocess
import sys


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True);p.add_argument('--mirror-root',type=Path,required=True)
    args=p.parse_args();base=Path(__file__).resolve().parent
    original=args.root/'revh_fourhour_08';steady=args.root/'revh_steady_09'
    status=json.loads((original/'run-status.json').read_text())
    assert status['state']=='running'
    assessment=json.loads((steady/'run-status.json').read_text())
    assert assessment['state']=='complete' and assessment['exit_code']==0
    comparison=args.mirror_root/'revh_correction_benchmark_dt12/comparison.json'
    check=json.loads(comparison.read_text());assert check['accepted']
    case=args.root/'revh_flowing_12';mirror=args.mirror_root/case.name
    subprocess.run([sys.executable,str(base/'prepare_revh_steady_transient.py'),'--steady',str(steady),
        '--iteration','400','--template',str(original),'--case',str(case),'--mirror',str(mirror),
        '--outer-correctors','2'],check=True)
    deadline=datetime.fromisoformat(status['started_utc'])+timedelta(seconds=status['budget_seconds'])
    seconds=int((deadline-datetime.now(timezone.utc)).total_seconds());assert 300<seconds<=14400
    manifest=json.loads((case/'case_manifest.json').read_text())
    manifest.update(maximum_wall_seconds=seconds,overall_compute_deadline_utc=deadline.isoformat(),
        correction_count_assessment={'comparison':str(comparison.name),'passed':True,
            'scope':'Six-step field comparison at 12.5 microseconds; not temporal or spatial independence.',
            'timing_caveat':'Competing workload changed between measurements; the wall-time ratio is not an isolated speed benchmark.'},
        initial_field_disposition='Use the last complete sampled full-field checkpoint, iteration 400 of 403. The steady convergence policy was not satisfied; this is a provisional flowing initialization.')
    for root in [case,mirror]:
        (root/'case_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        (root/'correction-comparison.json').write_text(comparison.read_text())
    print(json.dumps({'case':str(case),'seconds':seconds,'deadline_utc':deadline.isoformat(),
        'steady_iteration':400,'source_converged':assessment['converged'],'outer_correctors':2}),flush=True)
    subprocess.run([sys.executable,str(base/'run_revh_wall_budget.py'),'--case',str(case),
        '--mirror',str(mirror),'--seconds',str(seconds)],check=True)


if __name__=='__main__':main()
