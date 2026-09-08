"""Compare 4/6/8 MPI ranks while the independent four-rank startup run continues.

The flowing production workers are suspended only during timed solves and are
resumed in finally. An independent watchdog also resumes them after ten minutes.
Every candidate uses identical initial fields, numerics, mesh and output cadence.
This measures local throughput, not CFD validation.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time

import numpy as np
from compare_cfd_fields import fields, digest
from run_revh_wall_budget import workers


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--tag', default='14')
    p.add_argument('--resume', action='store_true')
    args = p.parse_args()
    assert re.fullmatch(r'[a-zA-Z0-9_-]+', args.tag)
    # Match the production CPU-only launch. Unrestricted hwloc discovery can
    # hang before MPI starts on this WSL/NVIDIA installation.
    os.environ['HWLOC_COMPONENTS'] = 'linux,stop'
    os.environ['OMP_NUM_THREADS'] = '1'
    root = args.root.resolve()
    source = root / 'revh_warm_outer2_11_dt12'
    production = root / 'revh_flowing_12'
    args.output.mkdir(exist_ok=args.resume)
    assert os.environ.get('WM_PROJECT_VERSION') == 'v2412'
    ids = workers(production)
    assert len(ids) == 4
    cases = {}
    report = {'created_utc': datetime.now(timezone.utc).isoformat(),
              'scope': __doc__, 'background_startup_ranks': 4,
              'paused_production_case': production.name, 'paused_pids': ids,
              'benchmark_steps': 4, 'deltaT_s': 12.5e-6, 'results': {},
              'environment': {'HWLOC_COMPONENTS': 'linux,stop', 'OMP_NUM_THREADS': '1'},
              'criteria': {'rms_relative': .001, 'maximum_relative': .01,
                           'absolute': 1e-6, 'minimum_throughput_gain': .10}}
    if args.resume:
        report = json.loads((args.output / 'rank-scaling.json').read_text())
        report['results'] = {int(k): v for k, v in report['results'].items()}
        assert set(report['results']) == {4, 6}
        report['resume_note'] = ('Eight-rank launch originally refused six physical-core slots. '
                                 'Retry uses --use-hwthread-cpus with binding still disabled; '
                                 'four startup plus eight benchmark workers fit twelve WSL threads.')

    def save():
        (args.output / 'rank-scaling.json').write_text(json.dumps(report, indent=2)+'\n')

    def run(command, case, name, timeout=210):
        with (case / name).open('w') as log:
            started = time.monotonic()
            proc = subprocess.Popen(command, cwd=case, stdout=log, stderr=subprocess.STDOUT,
                                    stdin=subprocess.DEVNULL, start_new_session=True)
            try:
                code = proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()
                raise
        assert code == 0, (command, code)
        return time.monotonic()-started

    for ranks in [4, 6, 8]:
        case = root / f'revh_rank_benchmark_{ranks}_{args.tag}'
        if args.resume:
            assert case.is_dir()
            assert digest(case / '0/U') == digest(source / '0/U')
            cases[ranks] = case
            continue
        case.mkdir(exist_ok=False)
        for name in ['constant', 'system', '0']:
            shutil.copytree(source / name, case / name)
        control = case / 'system/controlDict'
        text = re.sub(r'endTime\s+[^;]+;', 'endTime .00005;', control.read_text(), count=1)
        text = re.sub(r'writeInterval\s+[^;]+;', 'writeInterval 4;', text, count=1)
        control.write_text(text)
        decomposition = case / 'system/decomposeParDict'
        decomposition.write_text(re.sub(r'numberOfSubdomains\s+\d+;',
                                       f'numberOfSubdomains {ranks};', decomposition.read_text()))
        if ranks == 4:
            for rank in range(4):
                for name in ['constant', '0']:
                    shutil.copytree(source / f'processor{rank}' / name,
                                    case / f'processor{rank}' / name)
        else:
            run(['decomposePar'], case, 'log.decompose', 180)
        cases[ranks] = case
        print(f'Prepared {ranks} ranks', flush=True)

    # Preserve a watchdog outside this process group, including against an
    # interrupted launcher. It verifies the exact case before sending CONT.
    watchdog_code = ('import os,signal,time; from pathlib import Path; time.sleep(600); '
                     f'case=Path({str(production)!r}); ids={ids!r}; '
                     '[os.kill(p,signal.SIGCONT) for p in ids '
                     'if Path(f"/proc/{p}/cwd").exists() and Path(f"/proc/{p}/cwd").resolve()==case]')
    watchdog = subprocess.Popen([sys.executable, '-c', watchdog_code], start_new_session=True,
                                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    assert workers(production) == ids
    paused = time.monotonic()
    try:
        for pid in ids:
            os.kill(pid, signal.SIGSTOP)
        report['production_suspended_utc'] = datetime.now(timezone.utc).isoformat()
        save()
        for ranks, case in cases.items():
            if ranks in report['results']:
                continue
            print(f'Timing {ranks} ranks with four background workers', flush=True)
            logname = 'log.benchmark-threads' if args.resume else 'log.benchmark'
            seconds = run(['mpirun', '--use-hwthread-cpus', '--bind-to', 'none', '-np', str(ranks),
                           'pimpleFoam', '-parallel'], case, logname)
            raw = (case / logname).read_text()
            clock = [float(v) for v in re.findall(r'ClockTime = ([\d.eE+-]+) s', raw)]
            assert len(clock) == 4
            result = {'wall_seconds': seconds, 'clock_seconds': clock,
                      'seconds_per_step_after_first': (clock[-1]-clock[0])/3,
                      'max_Courant': max(map(float, re.findall(r'Courant Number mean: [^ ]+ max: ([\d.eE+-]+)', raw))),
                      'bounding_lines': re.findall(r'^bounding .*$', raw, re.M)}
            report['results'][ranks] = result
            save()
            print(json.dumps({'ranks': ranks, **result}), flush=True)
    finally:
        for pid in ids:
            if pid in workers(production):
                os.kill(pid, signal.SIGCONT)
        watchdog.terminate()
        watchdog.wait()
        report.setdefault('production_pause_segments_seconds', []).append(time.monotonic()-paused)
        if args.resume and len(report['production_pause_segments_seconds']) == 1:
            report['production_pause_segments_seconds'].insert(0, report['production_pause_seconds'])
        report['production_pause_seconds'] = sum(report['production_pause_segments_seconds'])
        report['production_resumed_utc'] = datetime.now(timezone.utc).isoformat()
        save()
        print('Production workers resumed', flush=True)

    for ranks, case in cases.items():
        run(['reconstructPar', '-time', '.00005'], case, 'log.reconstruct', 180)
    reference = fields(cases[4], .00005)
    hashes = {}
    for rel in [f'0/{name}' for name in ['U', 'p', 'phi', 'k', 'omega', 'nut']] + [
            'constant/polyMesh/points', 'constant/polyMesh/faces', 'constant/fvOptions',
            'system/fvSchemes', 'system/fvSolution', 'system/controlDict']:
        values = [digest(case / rel) for case in cases.values()]
        assert len(set(values)) == 1, rel
        hashes[rel] = values[0]
    report['identical_input_sha256'] = hashes
    for ranks in [6, 8]:
        comparison = {}
        for name, b in fields(cases[ranks], .00005).items():
            a = reference[name]
            rms = float(np.sqrt(np.mean((b-a)**2)))
            maximum = float(np.max(np.abs(b-a)))
            comparison[name] = {'rms_error': rms, 'max_abs_error': maximum,
                                'pass': bool(np.isfinite(b).all() and
                                             rms <= 1e-6+.001*np.sqrt(np.mean(a*a)) and
                                             maximum <= 1e-6+.01*np.max(np.abs(a)))}
        result = report['results'][ranks]
        result['fields'] = comparison
        result['field_check_passed'] = all(v['pass'] for v in comparison.values())
        result['throughput_ratio'] = report['results'][4]['seconds_per_step_after_first']/result['seconds_per_step_after_first']
    report['state'] = 'complete'
    save()
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
