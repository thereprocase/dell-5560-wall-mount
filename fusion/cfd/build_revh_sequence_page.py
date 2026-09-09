"""Build the existing GitHub Pages report from immutable hourly CFD artifacts."""
from gridline_html import apply_gridline
import argparse
from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path
import shutil
from make_revh_fast_video import make_fast_video, fast_video_html
from publish_revh_tracers import make_tracer_video, tracer_video_html

ROOT=Path(__file__).resolve().parents[2]
PAGE=ROOT/'docs/simulation/revh-transient/sequence'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case',type=Path,required=True)
    parser.add_argument('--steady-case',type=Path)
    args=parser.parse_args()
    state=json.loads((args.case/'run-status.json').read_text())
    visual=state.get('visual_extension')
    paused=state['state']=='complete' and bool(state.get('restart_checkpoint'))
    pause_note=''
    if paused:
        restart_ms=state['restart_checkpoint']['physical_time_s']*1000
        pause_note=f'<p class="notice"><strong>Simulation paused.</strong> The native restart checkpoint is preserved at {restart_ms:.4f} ms, with previous-step history. The videos below use the existing recorded samples. Automatic hourly publication is paused.</p>'
    elif visual and state['state'] in ['running','writing_final_checkpoint'] and state.get('authorized_deadline_utc'):
        from zoneinfo import ZoneInfo
        deadline=datetime.fromisoformat(state['authorized_deadline_utc']).astimezone(ZoneInfo('America/New_York'))
        pause_note=f'<p class="notice"><strong>Simulation running.</strong> Automatic hourly video updates are enabled through {deadline.strftime("%I:%M %p %Z on %B %d, %Y")}. A final update follows the native checkpoint and stop. These links always serve the latest published video.</p>'
    step_metric='<strong>≤ 25 µs</strong><span>adaptive timestep · Courant limit 0.5</span>'
    visual_note=''
    if visual:
        step_metric=f'<strong>{visual["video_frame_step_s"]*1e6:.2f} µs</strong><span>fixed step in the new visual extension · one sample per 60 fps video frame</span>'
        visual_note=f'<p class="notice"><strong>Visual continuation from {visual["base_last_time_s"]*1000:.4f} ms.</strong> The original video is followed by {visual["new_frames"]} new samples using fixed {visual["video_frame_step_s"]*1e6:.2f} µs steps and 12 workers. This prioritizes temporal progress and appearance; timestep accuracy will be assessed later. The earlier checkpoints remain available.</p>'
    PAGE.mkdir(parents=True,exist_ok=True)
    public={k:v for k,v in state.items() if k not in ['mpi_pid','worker_pids','command']}
    public['published_snapshot_utc']=datetime.now(timezone.utc).isoformat()
    (PAGE/'run-status.json').write_text(json.dumps(public,indent=2)+'\n',encoding='utf-8',newline='\n')
    for name in ['case_manifest.json','quality-disposition.json']:
        (PAGE/name).write_text((args.case/name).read_text(),encoding='utf-8',newline='\n')
    reports=[]
    adhoc=[]
    for directory in sorted(PAGE.glob('checkpoint-*')):
        if (directory/'progress.json').is_file():
            report=json.loads((directory/'progress.json').read_text())
            assert not report['preview_subsampled']
            report['_folder']=directory.name
            adhoc.append(report)
    early=PAGE/'early/progress.json'
    if not adhoc and early.is_file():
        report=json.loads(early.read_text());report['_folder']='early';adhoc.append(report)
    planned_hours=(max([int(p.name.split('-')[1]) for p in PAGE.glob('hour-*')],default=18)
                   if visual else max(4,int(state['budget_seconds']//3600)))
    for hour in range(1,planned_hours+1):
        path=PAGE/f'hour-{hour}'/'progress.json'
        if path.is_file():
            report=json.loads(path.read_text())
            assert not report['preview_subsampled']
            assert report['hour_checkpoint']==hour
            report['_folder']=f'hour-{hour}'
            reports.append(report)
    latest=max(reports+adhoc,key=lambda r:r['last_time_s']) if reports or adhoc else None
    if latest:
        source=PAGE/latest['_folder']
        if visual and (source/'visual-run.json').is_file():
            visual_note=visual_note.removesuffix('</p>')+f' <a href="{latest["_folder"]}/visual-run.json">Run timings, resource use and restart record</a>.</p>'
        fast=make_fast_video(PAGE,latest)
        tracers=make_tracer_video(PAGE,latest,args.case)
        shutil.copy2(source/'flow.mp4',PAGE/'latest.mp4')
        (PAGE/'latest.json').write_text(json.dumps({k:latest[k] for k in ['_folder','created_utc','last_time_s','source_frames','video_sha256']},indent=2)+'\n',encoding='utf-8',newline='\n')
        # Keep the already-shared early MP4 URL working as a current alias.
        if latest['_folder']!='early':
            (PAGE/'early').mkdir(exist_ok=True)
            for name in ['flow.mp4','poster.png','first-frame.png','progress.json']:
                shutil.copy2(source/name,PAGE/'early'/name)
    ms=(latest['last_time_s'] if latest else state.get('latest_physical_time_s') or 0)*1000
    heading='Revision H airflow, recorded.' if state['state']=='complete' else 'Revision H airflow run.'
    video='''<div class="pending"><strong>The solver is running.</strong><p>The first hourly video is due around 1:12 p.m. Eastern on 8 September, plus rendering and publication time.</p></div>'''
    if latest:
        hour=latest['hour_checkpoint']
        folder=latest['_folder']
        title=latest.get('checkpoint_label',f'Hour {hour}: latest cumulative video' if hour else 'Latest requested checkpoint')
        video=f'''<h2>{title}</h2>
<figure><video id="flow-video" controls playsinline preload="metadata" poster="{folder}/poster.png" aria-describedby="video-caption"><source src="{folder}/flow.mp4" type="video/mp4"><a href="{folder}/flow.mp4">Open the MP4</a>.</video>
<figcaption id="video-caption">{latest['source_frames']} actual sampled states, from {latest['first_time_s']*1000:.4f} to {ms:.4f} ms. Playback lasts {latest['video_duration_s']:.2f} seconds at {latest['playback_slowdown']:.0f}× slow motion, rounded to 30 fps, with a half-second final hold. No intermediate CFD states are generated. <a href="{folder}/flow.mp4">Open or download this video</a>.</figcaption></figure>'''
        video=tracer_video_html(tracers)+video+fast_video_html(fast,folder)
        if (PAGE/folder/'history.png').exists():
            video+=f'<figure><a href="{folder}/history.png"><img src="{folder}/history.png" alt="Recorded pressure, velocity and numerical diagnostics against physical time" loading="lazy"></a><figcaption>Recorded histories through this video checkpoint. Pressure uses the assumed air density of 1.2 kg/m³.</figcaption></figure>'
    rows=[]
    for number,r in enumerate(adhoc,1):
        folder=r['_folder']
        rows.append(f'<tr><th scope="row">Requested checkpoint {number}</th><td>{r["compute_elapsed_seconds_at_snapshot"]/3600:.3f} h</td><td>{r["last_time_s"]*1000:.4f} ms</td><td>{r["source_frames"]}</td><td><a href="{folder}/flow.mp4">MP4</a> · <a href="{folder}/progress.json">Provenance</a></td></tr>')
    byhour={r['hour_checkpoint']:r for r in reports}
    for hour in range(1,planned_hours+1):
        r=byhour.get(hour)
        if r:
            links=f'<a href="hour-{hour}/flow.mp4">MP4</a> · <a href="hour-{hour}/poster.png">Last frame</a> · <a href="hour-{hour}/progress.json">Provenance</a>'
            diagnostic='diagnostics.json.gz' if (PAGE/f'hour-{hour}'/'diagnostics.json.gz').is_file() else 'diagnostics.json'
            if (PAGE/f'hour-{hour}'/diagnostic).exists():links+=f' · <a href="hour-{hour}/{diagnostic}">Diagnostics{ " (gzip)" if diagnostic.endswith(".gz") else ""}</a>'
            rows.append(f'<tr><th scope="row">Hour {hour}</th><td>{r["compute_elapsed_seconds_at_snapshot"]/3600:.3f} h</td><td>{r["last_time_s"]*1000:.4f} ms</td><td>{r["source_frames"]}</td><td>{links}</td></tr>')
        elif state['state']!='complete':rows.append(f'<tr><th scope="row">Hour {hour}</th><td>Scheduled hourly checkpoint</td><td>Pending</td><td>—</td><td>Not yet published</td></tr>')
    status='paused' if paused else escape(state['state'].replace('_',' '))
    steady_note=''
    steady_case=args.steady_case or args.case.parent/'revh_steady_09'
    if (steady_case/'run-status.json').is_file():
        steady=json.loads((steady_case/'run-status.json').read_text())
        steady_public={k:v for k,v in steady.items() if k not in ['worker_pids','mpi_pid']}
        (PAGE/'steady-run-status.json').write_text(json.dumps(steady_public,indent=2)+'\n',encoding='utf-8',newline='\n')
        (PAGE/'steady-case_manifest.json').write_text((steady_case/'case_manifest.json').read_text(),encoding='utf-8',newline='\n')
        convergence='The numerical convergence policy is satisfied.' if steady.get('converged') else 'Numerical convergence has not been established.'
        steady_note=f'''<h2>Parallel steady-state initialization</h2><p>A separate four-worker steady-state solve began at 1:03 p.m. Eastern, using the same Revision H geometry and fan forcing. At this publication snapshot it has completed {steady['completed_iterations']} iterations; its state is {escape(steady['state'].replace('_',' '))}. {convergence}</p><p>These iterations are numerical adjustments, not elapsed fluid time. The purpose is to prepare a settled starting field for another transient shedding run. Residuals, pressure and velocity stability, conservation and recent turbulence bounding are checked before accepting that field. The startup videos above remain the original transient record.</p><ul class="links"><li><a href="steady-run-status.json">Steady-solver diagnostics</a></li><li><a href="steady-case_manifest.json">Initialization and convergence policy</a></li></ul>'''
        if (PAGE/'steady/history-final.json').is_file():
            steady_note+='<p>The one-hour preparation stopped without meeting the steady convergence policy. Its flowing field is suitable only as a provisional transient initialization, with initial adjustment still to be observed. <a href="steady/history-final.png">See the final convergence history</a> · <a href="steady/history-final.json">Recorded history data</a>.</p>'
        images=sorted((PAGE/'steady').glob('iteration-*/images.json'),key=lambda p:int(p.parent.name.split('-')[-1]))
        if images:
            info=json.loads(images[-1].read_text());directory=images[-1].parent.relative_to(PAGE).as_posix()
            steady_note+=f'<section id="steady-images"><h2>Steady-solver images with velocity arrows</h2><p>Actual sampled fields at iteration {info["iteration"]}. This snapshot is still unconverged; the arrows show local in-plane velocity.</p>'
            for filename,label in [('speed-arrows.png','Speed and flow direction'),('pressure-arrows.png','Static pressure and flow direction')]:
                steady_note+=f'<figure><a href="{directory}/{filename}"><img src="{directory}/{filename}" alt="{label} on the actual Rev H air path and two lip sections" loading="lazy"></a><figcaption>{label}. <a href="{directory}/{filename}">Open the full-size arrow image</a>.</figcaption></figure>'
            steady_note+=f'<p><a href="{directory}/vorticity-arrows.png">Vorticity with velocity arrows</a> · <a href="{directory}/images.json">Image provenance</a> · <a href="{directory}/right-section.vtp">Raw sampled section</a></p></section>'
            measurement=images[-1].parent/'section-flow.json'
            if measurement.is_file():
                measured=json.loads(measurement.read_text())
                ratios=[v['upward_channel_at_Z20']['net_flux_m2_s']/v['front_opening']['net_flux_m2_s'] for v in measured['results'].values()]
                steady_note+=f'<h2>Flow at the front opening</h2><p>At these two sampled side sections, upward channel flow is {min(ratios):.1f}–{max(ratios):.1f} times the net outward flow through the front opening. Both inward and outward flow occur across that opening. This is a line integral per unit span, not a full-width leakage fraction or a conservative three-dimensional flow split. The field remains unconverged.</p><p>Some outward flow could help cool the outer shell if it sweeps a warmer surface. This isothermal airflow model has no battery or heat-transfer solution, so it cannot quantify that benefit. A small smooth divider extension is a possible later comparison; the current geometry is unchanged.</p><p><a href="{directory}/section-flow.json">Opening-flow measurements and exact section definitions</a> · <a href="{directory}/left-section.vtp">Left sampled section</a></p>'
    flowing_note=''
    flowing_intro=''
    if (PAGE/'flowing/index.html').is_file():
        flowing_note='<h2>Transient from an already flowing field</h2><p>A separate recorded sequence begins with the steady-solver field. Its physical clock starts at zero, and initial adjustment remains because the source field is unconverged. <a href="flowing/">Watch the flowing-field transient</a>.</p>'
        flowing_intro='<p class="lede"><strong>Start with moving air:</strong> <a href="flowing/">Watch the separate transient initialized from the flowing field</a>. Its clock and checkpoints are kept separate from the original startup below.</p>'
    elif (PAGE/'flowing-first-frame.png').is_file():
        flowing_note='<h2>Transient from an already flowing field</h2><p>A separate four-worker transient began at 2:08 p.m. Eastern from steady iteration 400. It starts with moving air, and its physical clock resets to zero. Initial adjustment remains because the source field is unconverged. Its first video is being accumulated. <a href="flowing-first-frame.png">View the exact starting frame</a> · <a href="correction-check/">See the short correction-count comparison</a>.</p>'
    wider=PAGE/'steady/opening-flow-400/opening-flow.json'
    if wider.is_file():
        measurement=json.loads(wider.read_text());front=measurement['results']['front_mouth'];up=measurement['results']['upward_channel']
        steady_note+=f'<h2>Across the central 280 mm</h2><p>A wider integration through the actual sampled fluid gives {front["positive_flow_L_s"]:.2f} L/s outward and {front["negative_flow_L_s"]:.2f} L/s inward at the front opening: {front["net_flow_L_s"]:.2f} L/s net outward. The upward passage cut carries {up["net_flow_L_s"]:.2f} L/s net. These defined open cuts do not form a closed device flow balance; they are an unconverged model snapshot, not measured fan delivery.</p><p><a href="steady/opening-flow-400/opening-flow.png">See how the flow varies across the width</a> · <a href="steady/opening-flow-400/opening-flow.json">Surface-integral data and exact bounds</a>.</p>'
    html=f'''<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Rev H flow continuation · Precision 5560 mount</title>
<style>
:root{{color-scheme:light;--ink:#162c36;--muted:#536772;--line:#d9e2e5;--accent:#17686b}}*{{box-sizing:border-box}}body{{margin:0;background:#f5f7f7;color:var(--ink);font:17px/1.6 system-ui,sans-serif}}main{{max-width:1240px;margin:auto;padding:38px 24px 64px}}a{{color:var(--accent);text-underline-offset:3px}}nav,.small{{font-size:14px;color:var(--muted)}}nav{{margin-bottom:34px}}h1{{font-size:clamp(34px,5vw,58px);line-height:1.08;letter-spacing:-.035em;margin:12px 0 24px}}h2{{font-size:26px;line-height:1.3;margin:36px 0 15px}}p{{max-width:900px}}.eyebrow{{font-size:12px;text-transform:uppercase;letter-spacing:.12em;font-weight:750}}.lede{{font-size:20px;color:var(--muted)}}.notice{{border-left:4px solid #a5661b;background:#fff3df;padding:17px 22px;margin:25px 0}}.metrics{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}}.metric,.pending{{padding:20px;background:white;border:1px solid var(--line)}}.metric strong{{display:block;font-size:28px}}.metric span{{font-size:14px;color:var(--muted)}}.pending{{margin-top:26px}}figure{{margin:24px 0;background:white;border:1px solid var(--line);padding:10px}}video,img{{display:block;width:100%;height:auto}}video{{background:#e8edf0}}figcaption{{padding:12px 8px;font-size:14px;color:var(--muted)}}table{{border-collapse:collapse;width:100%;background:white;font-size:15px}}th,td{{text-align:left;padding:13px;border-bottom:1px solid var(--line);vertical-align:top}}.table-wrap{{overflow-x:auto}}.links{{display:flex;flex-wrap:wrap;gap:10px 22px;list-style:none;padding:0}}footer{{border-top:1px solid var(--line);padding-top:18px;margin-top:34px}}@media(max-width:620px){{main{{padding:24px 16px 44px}}.metrics{{grid-template-columns:1fr}}th,td{{padding:9px}}}}
</style><main>
<nav><a href="../">← Revision H study and GPU benchmark</a> · <a href="../../../">Mount designs</a></nav>
<div class="eyebrow">Revision H · 8 September 2026 · {status}</div>
<h1>{heading}</h1>
<p class="lede">Recorded airflow around the duct outlet, front laptop lip and hinge discharge. Moving particles follow the saved velocity fields; original arrow videos preserve the sampled states. <a href="latest-tracers.mp4">Open the moving-particle MP4</a>.</p>
{pause_note}
{visual_note}
{flowing_intro}
<div class="notice"><strong>Exploratory startup on a provisional mesh.</strong> This run does not yet establish periodic vortex shedding or settled lip suction. Mesh and timestep independence remain untested.</div>
<div class="metrics"><div class="metric"><strong>{ms:.4f} ms</strong><span>physical time at latest {'video' if latest else 'status'} checkpoint</span></div><div class="metric"><strong>{latest['source_frames'] if latest else 0}</strong><span>actual CFD states in the latest published video</span></div><div class="metric">{step_metric}</div></div>
{video}
<h2>Hourly checkpoints</h2>
<p>Started at <time datetime="2026-09-08T16:12:29Z">12:12 p.m. Eastern on September 8</time>. The original videos are cumulative and use every completed section sample available at their capture time. Earlier hourly files stay unchanged. Restart fields and their previous-step history are preserved for later continuation.</p>
<div class="table-wrap"><table><thead><tr><th scope="col">Checkpoint</th><th scope="col">Compute elapsed</th><th scope="col">Physical time</th><th scope="col">Sampled states</th><th scope="col">Files</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<h2>How to read the video</h2>
<p>The locator shows where the sections lie on the actual installed CAD. The whole air path is coloured by speed. Close-ups show static pressure and signed vorticity at X = +111 mm; arrows show the in-plane velocity. Black lines are CAD surfaces and grey areas are solid or unsampled. Pressure, speed and vorticity scales stay fixed across the hourly videos. The physical timestamp is the simulation time; playback is deliberately slowed.</p>
<p>Moving vorticity can reveal shear layers and vortices. A pressure depression near the lip would need to persist after startup before interpretation. A negative pressure alone does not identify a Bernoulli mechanism, and three apparent cycles would not establish converged shedding statistics.</p>
<h2>What is being computed</h2>
<p>The original startup uses the focused 3,193,565-cell Revision H mesh, with 0.25 mm targets in the sampled lip strips, and four CPU workers. It restarted at 0.1 ms from the same-geometry CPU benchmark, preserving the solver's time history. That benchmark started from quiet air. The older 18.2-million-cell, four-frame pilot is a separate record.</p>
<p>The standard mesh check passes, but expanded checks identify four low-determinant cells and 71,820 concave cells; wall-layer coverage remains poor. Four nominal 10 Pa fan actuators drive isothermal SST URANS flow. Fan curves, grille resistance and laptop passages remain approximate. This is not an experimentally validated flow or temperature prediction.</p>
<p>In the original adaptive run, complete planes at X = ±111 mm were saved every two solver steps, up to 50 µs apart. The new fixed-step visual extension saves each step. Full fields retain native binary precision and previous-step history for continuation. OpenFOAM disables gzip for binary fields; a separate lossless compression trial saved only about 5%. The solver records pressure and velocity probes, field bounds and ambient flux each step. New diagnostic downloads use lossless gzip; MP4 compression retains every plotted flow state.</p>
{steady_note}
{flowing_note}
<ul class="links"><li><a href="run-status.json">Dated run status</a></li><li><a href="case_manifest.json">Inputs and solver settings</a></li><li><a href="quality-disposition.json">Mesh disposition</a></li><li><a href="../#gpu-benchmark">CPU/GPU evidence</a></li></ul>
<footer class="small">Published status snapshot: {escape(public['published_snapshot_utc'])}. This static page updates with each published checkpoint; it is not a live solver connection. Raw fields and all sampled planes remain preserved locally.</footer>
</main></html>
'''
    (PAGE/'index.html').write_text(apply_gridline(html, PAGE/'index.html'),encoding='utf-8',newline='\n')
    print(json.dumps({'page':str(PAGE),'published_hours':[r['hour_checkpoint'] for r in reports],'solver_state':state['state']}))


if __name__=='__main__':main()
