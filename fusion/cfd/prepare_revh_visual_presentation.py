"""Join an unchanged published CFD sample prefix to its fixed-step extension."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import shutil


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--original',type=Path,required=True)
    p.add_argument('--extension',type=Path,required=True)
    p.add_argument('--source-progress',type=Path,required=True)
    p.add_argument('--source-tracers',type=Path,required=True)
    args=p.parse_args()
    old=args.original;extension=args.extension;presentation=extension/'presentation'
    status=json.loads((extension/'visual-status.json').read_text())
    assert status['state']=='complete' and status['workers_stopped']
    source=json.loads(args.source_progress.read_text());tracers=json.loads(args.source_tracers.read_text())
    assert source['last_time_s']==status['video_tail_s']==tracers['last_time_s']
    assert tracers['video_sha256']==status['video_sha256']
    assert tracers['source_video_sha256']==source['video_sha256']
    presentation.mkdir(exist_ok=True)
    folders={float(p.name):p for p in (old/'postProcessing/edge_sections').iterdir() if p.is_dir() and p.name[0].isdigit()}
    def link_sample(folder):
        target=presentation/'postProcessing/edge_sections'/folder.name;target.mkdir(parents=True,exist_ok=True)
        for name in ['right_section.vtp','left_section.vtp']:
            if not (target/name).exists():os.link(folder/name,target/name)
            assert sha(target/name)==sha(folder/name)
        return target
    for t in source['physical_times_s']:
        folder=link_sample(folders[t]);assert sha(folder/'right_section.vtp')==source['source_sha256'][str(float(t))]
    new={float(p.name):p for p in (extension/'postProcessing/edge_sections').iterdir() if p.is_dir() and p.name[0].isdigit()}
    for t in status['new_sample_times_s']:link_sample(new[t])
    actual=sorted(float(p.name) for p in (presentation/'postProcessing/edge_sections').iterdir() if p.is_dir())
    assert actual==source['physical_times_s']+status['new_sample_times_s']
    for directory in (old/'render-cache').iterdir():
        if not directory.is_dir():continue
        target=presentation/'render-cache'/directory.name;target.mkdir(parents=True,exist_ok=True)
        for source_image in directory.glob('*.png'):
            if not (target/source_image.name).exists():os.link(source_image,target/source_image.name)
    detail=dict(base_last_time_s=source['last_time_s'],base_motion_frames=tracers['encoded_frames']-6,
                base_tracer_sha256=tracers['video_sha256'],base_arrow_sha256=source['video_sha256'],
                base_source_frames=source['source_frames'],base_progress_sha256=sha(args.source_progress),
                new_frames=status['requested_new_frames'],video_frame_step_s=status['coarse_deltaT_s'],
                timestep_accuracy='Deferred by user; fixed-step continuation for visualization.',
                replay_checkpoint_s=float(status['source_checkpoint']),replay_steps=status['replay_steps'])
    manifest=json.loads((old/'case_manifest.json').read_text())
    manifest.update(cpu_workers=12,ranks=12,visual_extension=detail,
                    current_native_case=Path(status['case']).name,
                    fixed_deltaT_s=status['coarse_deltaT_s'],adjustTimeStep=False,scope=status['scope'])
    state=json.loads((old/'run-status.json').read_text())
    coarse=status['phases']['coarse_visual_extension']
    state.update(case=Path(status['case']).name,state='complete',worker_pids=[],cpu_workers=12,
                 stop_reason='User requested a resumable stop',latest_physical_time_s=actual[-1],
                 latest_deltaT_s=status['coarse_deltaT_s'],latest_Courant=coarse['max_Courant'],
                 max_logged_Courant=coarse['max_Courant'],bounding_events=coarse['bounding_events'],
                 complete_sample_frames=len(actual),completed_steps=int(status['restart_checkpoint']['native_time_metadata']['index']),
                 elapsed_seconds=source['compute_elapsed_seconds_at_snapshot']+sum(v['wall_seconds'] for v in status['phases'].values()),
                 restart_checkpoint={k:status['restart_checkpoint'][k] for k in ['physical_time_s','mpi_ranks','verified_utc','native_previous_step_fields_preserved']},
                 visual_extension=detail,updated_utc=status['updated_utc'],finished_utc=status['updated_utc'],
                 session_started_utc=status['started_utc'],scope=status['scope'],cpu_nice=19,io_priority='idle',
                 wall_time_accounting='Prior published cumulative wall time plus replay and coarse continuation; idle time and branch preparation excluded.',
                 memory_limit_bytes=int(status['resource_limits']['memory.max']),memory_peak_bytes=status['memory_peak_bytes'])
    for key in ['mpi_pid','command','authorized_deadline_utc','resume_elapsed_seconds','stop_signal_utc']:state.pop(key,None)
    for name,data in [('case_manifest.json',manifest),('run-status.json',state),('visual-extension.json',detail)]:
        (presentation/name).write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8',newline='\n')
    shutil.copy2(old/'quality-disposition.json',presentation/'quality-disposition.json')
    print(json.dumps({'presentation':str(presentation),'source_frames':len(actual),'last_time_s':actual[-1]}))


if __name__=='__main__':main()
