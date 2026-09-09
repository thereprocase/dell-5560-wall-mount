"""Continue a paused native startup checkpoint in an isolated, bounded MPI trial."""
import argparse
from datetime import datetime, timezone
import json
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


def utc():
    return datetime.now(timezone.utc).isoformat()


def verify_finished(source, case, mirror, report):
    """Verify an exited trial without restarting it, including checkpoint overshoot."""
    assert not workers(case)
    initial = report['source_checkpoint']
    count = mirror_samples(case, mirror)
    log_path = case/'log.pimpleFoam.trial'
    raw = log_path.read_text()
    assert re.search(r'^End\s*$', raw, re.M) and 'Finalising parallel run' in raw
    assert not re.search(r'=\s*[-+]?(?:nan|inf)\b', raw, re.I)
    checkpoint = describe(case, report['ranks'])
    times = sorted(float(p.name) for p in (mirror/'postProcessing/edge_sections').iterdir() if p.is_dir())
    # The signal is processed at a timestep boundary. Its native write-and-stop
    # can complete another sampled step before exit; preserve that evidence.
    assert report['requested_new_samples'] <= count <= report['requested_new_samples']+1
    if count > report['requested_new_samples']:
        assert abs(times[-1]-checkpoint['physical_time_s']) < 1e-12
    unchanged = describe(source, 4)
    assert unchanged['field_sha256'] == initial['field_sha256']
    assert unchanged['mesh_sha256'] == initial['mesh_sha256']
    clocks = list(map(float, re.findall(r'ClockTime = ([\d.eE+-]+) s', raw)))
    dts = list(map(float, re.findall(r'^deltaT = ([\d.eE+-]+)', raw, re.M)))
    finish = datetime.fromtimestamp(log_path.stat().st_mtime, timezone.utc)
    sample_hashes = {p.relative_to(mirror).as_posix(): sha(p)
                     for p in (mirror/'postProcessing/edge_sections').rglob('*.vtp')}
    report.update(state='complete', updated_utc=utc(), worker_count=0,
                  new_samples=count, solver_steps=len(clocks),
                  additional_samples_during_native_stop=count-report['requested_new_samples'],
                  solve_clock_seconds=clocks[-1],
                  seconds_per_step_after_first=(clocks[-1]-clocks[0])/(len(clocks)-1),
                  physical_times_s=times, sample_sha256=sample_hashes,
                  max_Courant=max(map(float,re.findall(r'Courant Number mean: [^ ]+ max: ([\d.eE+-]+)',raw))),
                  final_deltaT_s=dts[-1],
                  bounding_events=len(re.findall(r'^bounding ',raw,re.M)),
                  restart_checkpoint=checkpoint,
                  continued_time_s=checkpoint['physical_time_s']-initial['physical_time_s'],
                  solver_finished_utc=finish.isoformat(), verified_utc=utc(),
                  elapsed_since_preparation_started_s=(finish-datetime.fromisoformat(report['started_utc'])).total_seconds())
    for name in ['case_manifest.json', 'quality-disposition.json', log_path.name]:
        shutil.copy2(case/name, mirror/name)
    for root in [case, mirror]:
        (root/'resume-checkpoint.json').write_text(json.dumps(checkpoint,indent=2)+'\n')
        (root/'trial-status.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in
                      ['source_checkpoint','restart_checkpoint','input_sha256','sample_sha256']}),flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--case', type=Path, required=True)
    p.add_argument('--mirror', type=Path, required=True)
    p.add_argument('--ranks', type=int, required=True)
    p.add_argument('--samples', type=int, required=True)
    p.add_argument('--verify-only', action='store_true', help='Verify an already-exited trial without running CFD')
    args = p.parse_args()
    source, case, mirror = (v.resolve() for v in (args.source, args.case, args.mirror))
    assert source.name == 'revh_fourhour_08'
    assert case.parent == source.parent and case != source
    assert args.ranks == 12 and args.samples == 5
    assert os.environ.get('WM_PROJECT_VERSION') == 'v2412'
    assert not workers(source)
    if args.verify_only:
        assert case.is_dir() and mirror.is_dir()
        report = json.loads((case/'trial-status.json').read_text())
        assert report['ranks'] == args.ranks and report['requested_new_samples'] == args.samples
        verify_finished(source, case, mirror, report)
        return
    assert not case.exists() and not mirror.exists()
    lower_priority()
    os.environ['HWLOC_COMPONENTS'] = 'linux,stop'
    os.environ['OMP_NUM_THREADS'] = '1'
    for name in ['DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY']:
        os.environ.pop(name, None)
    started = time.monotonic()
    initial = describe(source, 4)
    saved = initial['time_folder']
    case.mkdir()
    mirror.mkdir(parents=True)
    report = dict(started_utc=utc(), state='copying_checkpoint', source_case=str(source),
                  case=str(case), ranks=args.ranks, requested_new_samples=args.samples,
                  source_checkpoint=initial, cpu_nice=os.getpriority(os.PRIO_PROCESS, 0),
                  io_priority='idle', original_case_unchanged=True)

    def save(state=None, **updates):
        if state:
            report['state'] = state
        report.update(updated_utc=utc(), total_wall_seconds=time.monotonic()-started, **updates)
        for root in [case, mirror]:
            temp = root/'trial-status.json.tmp'
            temp.write_text(json.dumps(report, indent=2)+'\n')
            temp.replace(root/'trial-status.json')
        print(json.dumps({k:v for k,v in report.items() if k not in
                          ['source_checkpoint', 'restart_checkpoint', 'input_sha256']}), flush=True)

    def command(cmd, label, timeout=300):
        save(label)
        with (case/('log.'+label)).open('w') as log:
            proc = subprocess.Popen(cmd, cwd=case, stdout=log, stderr=subprocess.STDOUT,
                                    stdin=subprocess.DEVNULL, start_new_session=True)
            try:
                result = proc.wait(timeout=timeout)
            except BaseException:
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()
                raise
        assert result == 0, (label, result)

    save()
    for name in ['constant', 'system']:
        shutil.copytree(source/name, case/name)
    for name in ['case_manifest.json', 'quality-disposition.json']:
        shutil.copy2(source/name, case/name)
    for rank in range(4):
        for name in ['constant', saved]:
            shutil.copytree(source/f'processor{rank}'/name, case/f'processor{rank}'/name)
    copied = describe(case, 4)
    assert copied['field_sha256'] == initial['field_sha256']
    assert copied['mesh_sha256'] == initial['mesh_sha256']
    command(['reconstructPar', '-time', saved], 'reconstruct_before')
    before = fields(case, float(saved), NATIVE_FIELDS)
    time_hash = sha(case/saved/'uniform/time')
    archive = case/'original-four-rank-checkpoint'
    archive.mkdir()
    for rank in range(4):
        part = case/f'processor{rank}'
        assert part.resolve().parent == case and archive.resolve().parent == case
        part.rename(archive/part.name)
    decomposition = case/'system/decomposeParDict'
    decomposition.write_text(re.sub(r'numberOfSubdomains\s+\d+;',
                                   f'numberOfSubdomains {args.ranks};', decomposition.read_text()))
    command(['decomposePar', '-time', saved], 'decompose_12')
    repartitioned = describe(case, args.ranks)
    assert repartitioned['native_time_metadata'] == initial['native_time_metadata']
    command(['reconstructPar', '-time', saved], 'reconstruct_check')
    after = fields(case, float(saved), NATIVE_FIELDS)
    identical = {name: bool(np.array_equal(before[name], after[name])) for name in NATIVE_FIELDS}
    assert all(identical.values()) and sha(case/saved/'uniform/time') == time_hash
    del before, after
    # Solver settings and sample cadence are unchanged; only decomposition differs.
    inputs = ['system/controlDict', 'system/fvSchemes', 'system/fvSolution',
              'constant/fvOptions', 'constant/transportProperties', 'constant/turbulenceProperties']
    hashes = {name: sha(case/name) for name in inputs}
    assert all(hashes[name] == sha(source/name) for name in inputs)
    report.update(internal_fields_exact_after_repartition=identical,
                  native_time_history_preserved=True, input_sha256=hashes,
                  preparation_seconds=time.monotonic()-started)
    solve_started = time.monotonic()
    log_path = case/'log.pimpleFoam.trial'
    stopped = None
    last_notice = 0
    solve = ['mpirun', '--use-hwthread-cpus', '--bind-to', 'none', '-np', str(args.ranks),
             'pimpleFoam', '-parallel', '-opt-switch', 'stopAtWriteNowSignal=12']
    with log_path.open('w') as log:
        proc = subprocess.Popen(solve, cwd=case, stdout=log, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL, start_new_session=True)
        save('running', mpi_pid=proc.pid)
        try:
            while proc.poll() is None:
                elapsed = time.monotonic()-solve_started
                count = mirror_samples(case, mirror)
                raw = log_path.read_text(errors='replace')
                clocks = list(map(float, re.findall(r'ClockTime = ([\d.eE+-]+) s', raw)))
                ids = workers(case)
                if stopped is None and (count >= args.samples or elapsed >= 1200):
                    assert len(ids) == args.ranks, 'Unexpected worker count at checkpoint stop'
                    for pid in ids:
                        assert b'stopAtWriteNowSignal=12' in Path(f'/proc/{pid}/cmdline').read_bytes()
                        os.kill(pid, signal.SIGUSR2)
                    stopped = elapsed
                    report['stop_reason'] = 'Five new sampled states saved' if count >= args.samples else 'Trial wall-time backstop'
                if stopped is not None and elapsed-stopped > 180:
                    raise TimeoutError('Native checkpoint stop exceeded 180 seconds')
                if elapsed-last_notice >= 15:
                    save('writing_checkpoint' if stopped else 'running',
                         new_samples=count, solver_steps=len(clocks), solve_seconds=elapsed,
                         worker_count=len(ids), seconds_per_step_after_first=(clocks[-1]-clocks[0])/(len(clocks)-1) if len(clocks)>1 else None)
                    last_notice = elapsed
                time.sleep(.5)
        finally:
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()
    assert proc.returncode == 0
    report.update(solve_seconds=time.monotonic()-solve_started, exit_code=proc.returncode)
    verify_finished(source, case, mirror, report)


if __name__ == '__main__':
    main()
