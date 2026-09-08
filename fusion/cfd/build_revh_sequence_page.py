"""Build the existing GitHub Pages report from immutable hourly CFD artifacts."""
import argparse
from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[2]
PAGE=ROOT/'docs/simulation/revh-transient/sequence'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case',type=Path,required=True)
    args=parser.parse_args()
    state=json.loads((args.case/'run-status.json').read_text())
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
    for hour in range(1,5):
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
        shutil.copy2(source/'flow.mp4',PAGE/'latest.mp4')
        (PAGE/'latest.json').write_text(json.dumps({k:latest[k] for k in ['_folder','created_utc','last_time_s','source_frames','video_sha256']},indent=2)+'\n',encoding='utf-8',newline='\n')
        # Keep the already-shared early MP4 URL working as a current alias.
        if latest['_folder']!='early':
            (PAGE/'early').mkdir(exist_ok=True)
            for name in ['flow.mp4','poster.png','first-frame.png','progress.json']:
                shutil.copy2(source/name,PAGE/'early'/name)
    ms=(latest['last_time_s'] if latest else state.get('latest_physical_time_s') or 0)*1000
    heading='Four hours of airflow, recorded.' if state['state']=='complete' else 'Four-hour airflow run.'
    video='''<div class="pending"><strong>The solver is running.</strong><p>The first hourly video is due around 1:12 p.m. Eastern on 8 September, plus rendering and publication time.</p></div>'''
    if latest:
        hour=latest['hour_checkpoint']
        folder=latest['_folder']
        title=f'Hour {hour}: latest cumulative video' if hour else 'Latest requested checkpoint'
        video=f'''<h2>{title}</h2>
<figure><video id="flow-video" controls playsinline preload="metadata" poster="{folder}/poster.png" aria-describedby="video-caption"><source src="{folder}/flow.mp4" type="video/mp4"><a href="{folder}/flow.mp4">Open the MP4</a>.</video>
<figcaption id="video-caption">{latest['source_frames']} actual sampled states, from {latest['first_time_s']*1000:.4f} to {ms:.4f} ms. Playback lasts {latest['video_duration_s']:.2f} seconds at {latest['playback_slowdown']:.0f}× slow motion, rounded to 30 fps, with a half-second final hold. No intermediate CFD states are generated. <a href="{folder}/flow.mp4">Open or download this video</a>.</figcaption></figure>'''
        if (PAGE/folder/'history.png').exists():
            video+=f'<figure><a href="{folder}/history.png"><img src="{folder}/history.png" alt="Recorded pressure, velocity and numerical diagnostics against physical time" loading="lazy"></a><figcaption>Recorded histories through this video checkpoint. Pressure uses the assumed air density of 1.2 kg/m³.</figcaption></figure>'
    rows=[]
    for number,r in enumerate(adhoc,1):
        folder=r['_folder']
        rows.append(f'<tr><th scope="row">Requested checkpoint {number}</th><td>{r["compute_elapsed_seconds_at_snapshot"]/3600:.3f} h</td><td>{r["last_time_s"]*1000:.4f} ms</td><td>{r["source_frames"]}</td><td><a href="{folder}/flow.mp4">MP4</a> · <a href="{folder}/progress.json">Provenance</a></td></tr>')
    byhour={r['hour_checkpoint']:r for r in reports}
    for hour in range(1,5):
        r=byhour.get(hour)
        if r:
            links=f'<a href="hour-{hour}/flow.mp4">MP4</a> · <a href="hour-{hour}/poster.png">Last frame</a> · <a href="hour-{hour}/progress.json">Provenance</a>'
            if (PAGE/f'hour-{hour}'/'diagnostics.json').exists():links+=f' · <a href="hour-{hour}/diagnostics.json">Diagnostics</a>'
            rows.append(f'<tr><th scope="row">Hour {hour}</th><td>{r["compute_elapsed_seconds_at_snapshot"]/3600:.3f} h</td><td>{r["last_time_s"]*1000:.4f} ms</td><td>{r["source_frames"]}</td><td>{links}</td></tr>')
        else:rows.append(f'<tr><th scope="row">Hour {hour}</th><td>Due about {hour}:12 p.m. EDT</td><td>Pending</td><td>—</td><td>Not yet published</td></tr>')
    status=escape(state['state'].replace('_',' '))
    steady_note=''
    steady_case=args.case.parent/'revh_steady_09'
    if (steady_case/'run-status.json').is_file():
        steady=json.loads((steady_case/'run-status.json').read_text())
        steady_public={k:v for k,v in steady.items() if k not in ['worker_pids','mpi_pid']}
        (PAGE/'steady-run-status.json').write_text(json.dumps(steady_public,indent=2)+'\n',encoding='utf-8',newline='\n')
        (PAGE/'steady-case_manifest.json').write_text((steady_case/'case_manifest.json').read_text(),encoding='utf-8',newline='\n')
        convergence='The numerical convergence policy is satisfied.' if steady.get('converged') else 'Numerical convergence has not been established.'
        steady_note=f'''<h2>Parallel steady-state initialization</h2><p>A separate four-worker steady-state solve began at 1:03 p.m. Eastern, using the same Revision H geometry and fan forcing. At this publication snapshot it has completed {steady['completed_iterations']} iterations; its state is {escape(steady['state'].replace('_',' '))}. {convergence}</p><p>These iterations are numerical adjustments, not elapsed fluid time. The purpose is to prepare a settled starting field for another transient shedding run. Residuals, pressure and velocity stability, conservation and recent turbulence bounding are checked before accepting that field. The startup videos above remain the original transient record.</p><ul class="links"><li><a href="steady-run-status.json">Steady-solver diagnostics</a></li><li><a href="steady-case_manifest.json">Initialization and convergence policy</a></li></ul>'''
        images=sorted((PAGE/'steady').glob('iteration-*/images.json'),key=lambda p:int(p.parent.name.split('-')[-1]))
        if images:
            info=json.loads(images[-1].read_text());directory=images[-1].parent.relative_to(PAGE).as_posix()
            steady_note+=f'<section id="steady-images"><h2>Steady-solver images with velocity arrows</h2><p>Actual sampled fields at iteration {info["iteration"]}. This snapshot is still unconverged; the arrows show local in-plane velocity.</p>'
            for filename,label in [('speed-arrows.png','Speed and flow direction'),('pressure-arrows.png','Static pressure and flow direction')]:
                steady_note+=f'<figure><a href="{directory}/{filename}"><img src="{directory}/{filename}" alt="{label} on the actual Rev H air path and two lip sections" loading="lazy"></a><figcaption>{label}. <a href="{directory}/{filename}">Open the full-size arrow image</a>.</figcaption></figure>'
            steady_note+=f'<p><a href="{directory}/vorticity-arrows.png">Vorticity with velocity arrows</a> · <a href="{directory}/images.json">Image provenance</a> · <a href="{directory}/right-section.vtp">Raw sampled section</a></p></section>'
    html=f'''<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Four-hour Rev H flow run · Precision 5560 mount</title>
<style>
:root{{color-scheme:light;--ink:#162c36;--muted:#536772;--line:#d9e2e5;--accent:#17686b}}*{{box-sizing:border-box}}body{{margin:0;background:#f5f7f7;color:var(--ink);font:17px/1.6 system-ui,sans-serif}}main{{max-width:1240px;margin:auto;padding:38px 24px 64px}}a{{color:var(--accent);text-underline-offset:3px}}nav,.small{{font-size:14px;color:var(--muted)}}nav{{margin-bottom:34px}}h1{{font-size:clamp(34px,5vw,58px);line-height:1.08;letter-spacing:-.035em;margin:12px 0 24px}}h2{{font-size:26px;line-height:1.3;margin:36px 0 15px}}p{{max-width:900px}}.eyebrow{{font-size:12px;text-transform:uppercase;letter-spacing:.12em;font-weight:750}}.lede{{font-size:20px;color:var(--muted)}}.notice{{border-left:4px solid #a5661b;background:#fff3df;padding:17px 22px;margin:25px 0}}.metrics{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}}.metric,.pending{{padding:20px;background:white;border:1px solid var(--line)}}.metric strong{{display:block;font-size:28px}}.metric span{{font-size:14px;color:var(--muted)}}.pending{{margin-top:26px}}figure{{margin:24px 0;background:white;border:1px solid var(--line);padding:10px}}video,img{{display:block;width:100%;height:auto}}video{{background:#e8edf0}}figcaption{{padding:12px 8px;font-size:14px;color:var(--muted)}}table{{border-collapse:collapse;width:100%;background:white;font-size:15px}}th,td{{text-align:left;padding:13px;border-bottom:1px solid var(--line);vertical-align:top}}.table-wrap{{overflow-x:auto}}.links{{display:flex;flex-wrap:wrap;gap:10px 22px;list-style:none;padding:0}}footer{{border-top:1px solid var(--line);padding-top:18px;margin-top:34px}}@media(max-width:620px){{main{{padding:24px 16px 44px}}.metrics{{grid-template-columns:1fr}}th,td{{padding:9px}}}}
</style><main>
<nav><a href="../">← Revision H study and GPU benchmark</a> · <a href="../../../">Mount designs</a></nav>
<div class="eyebrow">Revision H · 8 September 2026 · {status}</div>
<h1>{heading}</h1>
<p class="lede">A four-hour CPU solve, with an actual-sample video published each hour. Close-ups follow the duct outlet, front laptop lip and hinge discharge. <a href="latest.mp4">Open the latest MP4</a>.</p>
<div class="notice"><strong>Exploratory startup on a provisional mesh.</strong> This run does not yet establish periodic vortex shedding or settled lip suction. Mesh and timestep independence remain untested.</div>
<div class="metrics"><div class="metric"><strong>{ms:.4f} ms</strong><span>physical time at latest {'video' if latest else 'status'} checkpoint</span></div><div class="metric"><strong>{latest['source_frames'] if latest else 0}</strong><span>actual CFD states in the latest published video</span></div><div class="metric"><strong>≤ 25 µs</strong><span>adaptive timestep · Courant limit 0.5</span></div></div>
{video}
<h2>Hourly checkpoints</h2>
<p>Started at <time datetime="2026-09-08T16:12:29Z">12:12 p.m. Eastern</time>; the four-hour compute limit is about 4:12 p.m. Eastern. Videos are cumulative and use every completed section sample available at their capture time. Earlier hourly files stay unchanged.</p>
<div class="table-wrap"><table><thead><tr><th scope="col">Checkpoint</th><th scope="col">Compute elapsed</th><th scope="col">Physical time</th><th scope="col">Sampled states</th><th scope="col">Files</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<h2>How to read the video</h2>
<p>The locator shows where the sections lie on the actual installed CAD. The whole air path is coloured by speed. Close-ups show static pressure and signed vorticity at X = +111 mm; arrows show the in-plane velocity. Black lines are CAD surfaces and grey areas are solid or unsampled. Pressure, speed and vorticity scales stay fixed across all four hourly videos. The physical timestamp is the simulation time; playback is deliberately slowed.</p>
<p>Moving vorticity can reveal shear layers and vortices. A pressure depression near the lip would need to persist after startup before interpretation. A negative pressure alone does not identify a Bernoulli mechanism, and three apparent cycles would not establish converged shedding statistics.</p>
<h2>What is being computed</h2>
<p>This continuation uses the focused 3,193,565-cell Revision H mesh, with 0.25 mm targets in the sampled lip strips, and four CPU workers. It restarts at 0.1 ms from the same-geometry CPU benchmark, preserving the solver's time history. That benchmark started from quiet air. The older 18.2-million-cell, four-frame pilot is a separate record.</p>
<p>The standard mesh check passes, but expanded checks identify four low-determinant cells and 71,820 concave cells; wall-layer coverage remains poor. Four nominal 10 Pa fan actuators drive isothermal SST URANS flow. Fan curves, grille resistance and laptop passages remain approximate. This is not an experimentally validated flow or temperature prediction.</p>
<p>Complete planes at X = ±111 mm are saved every two solver steps, normally 50 µs apart. Full fields are checkpointed every half-hour of wall time. The solver records pressure and velocity probes, field bounds and ambient flux each step. A verified signal handler writes a final checkpoint at the four-hour limit.</p>
{steady_note}
<ul class="links"><li><a href="run-status.json">Dated run status</a></li><li><a href="case_manifest.json">Inputs and solver settings</a></li><li><a href="quality-disposition.json">Mesh disposition</a></li><li><a href="../#gpu-benchmark">CPU/GPU evidence</a></li></ul>
<footer class="small">Published status snapshot: {escape(public['published_snapshot_utc'])}. This static page updates with each published checkpoint; it is not a live solver connection. Raw fields and all sampled planes remain preserved locally.</footer>
</main></html>
'''
    (PAGE/'index.html').write_text(html,encoding='utf-8',newline='\n')
    print(json.dumps({'page':str(PAGE),'published_hours':[r['hour_checkpoint'] for r in reports],'solver_state':state['state']}))


if __name__=='__main__':main()
