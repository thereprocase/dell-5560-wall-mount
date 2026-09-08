"""Stage a separate physical-time video initialized from an assessed flowing field.

No network writes: the existing GitHub Pages review and commit workflow follows.
The reset physical clock is never merged with the quiet-start video's timeline.
"""
import argparse
from datetime import datetime,timezone
from html import escape
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[2]
PAGE=ROOT/'docs/simulation/revh-transient/sequence/flowing'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--case',type=Path,required=True)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--checkpoint',type=int,required=True)
    args=p.parse_args();manifest=json.loads((args.case/'case_manifest.json').read_text())
    assert manifest['initialization_kind']=='steady_solver'
    report=json.loads((args.source/'progress.json').read_text())
    assert report['initialization_kind']=='steady_solver' and report['case']==args.case.name
    assert not report['preview_subsampled'] and report['source_frames']==report['source_sample_count_available']
    assert hashlib.sha256((args.source/'flow.mp4').read_bytes()).hexdigest()==report['video_sha256']
    diagnostics=json.loads((args.source/'diagnostics.json').read_text())
    assert abs(diagnostics['through_time_s']-report['last_time_s'])<1e-12
    target=PAGE/f'checkpoint-{args.checkpoint:02d}';target.mkdir(parents=True,exist_ok=False)
    for name in ['flow.mp4','poster.png','first-frame.png','progress.json','diagnostics.json','history.png']:
        shutil.copy2(args.source/name,target/name)
    shutil.copytree(args.source/'diagnostic-raw',target/'diagnostic-raw')
    for name in ['case_manifest.json','quality-disposition.json']:shutil.copy2(args.case/name,PAGE/name)
    state=json.loads((args.case/'run-status.json').read_text())
    public={k:v for k,v in state.items() if k not in ['mpi_pid','worker_pids','command']}
    public['published_snapshot_utc']=datetime.now(timezone.utc).isoformat()
    (PAGE/'run-status.json').write_text(json.dumps(public,indent=2)+'\n',encoding='utf-8')
    checkpoints=[]
    for path in PAGE.glob('checkpoint-*/progress.json'):
        r=json.loads(path.read_text());r['_folder']=path.parent.name;checkpoints.append(r)
    checkpoints.sort(key=lambda r:r['last_time_s']);latest=checkpoints[-1];folder=latest['_folder']
    shutil.copy2(PAGE/folder/'flow.mp4',PAGE/'latest.mp4')
    (PAGE/'latest.json').write_text(json.dumps({k:latest[k] for k in ['_folder','created_utc','last_time_s','source_frames','video_sha256']},indent=2)+'\n',encoding='utf-8')
    rows=[]
    for r in checkpoints:
        d=r['_folder'];rows.append(f'<tr><th>{escape(d)}</th><td>{r["last_time_s"]*1000:.4f} ms</td><td>{r["source_frames"]}</td><td><a href="{d}/flow.mp4">Video</a> · <a href="{d}/progress.json">Provenance</a> · <a href="{d}/diagnostics.json">Diagnostics</a></td></tr>')
    iteration=manifest['transient_initialization']['steady_iteration']
    outer=manifest['transient_controls']['outer_correctors']
    html=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Rev H transient from flowing air</title><style>
*{{box-sizing:border-box}}body{{margin:0;color:#162c36;background:#f5f7f7;font:17px/1.6 system-ui,sans-serif}}main{{max-width:1240px;margin:auto;padding:32px 24px 64px}}a{{color:#17686b;text-underline-offset:3px}}h1{{font-size:clamp(34px,5vw,56px);line-height:1.1;letter-spacing:-.03em}}h2{{font-size:26px}}p{{max-width:940px}}figure{{margin:26px 0;padding:10px;background:white;border:1px solid #d9e2e5}}video,img{{display:block;width:100%;height:auto}}figcaption{{font-size:14px;padding:12px 8px;color:#536772}}.notice{{padding:18px 22px;background:#fff3df;border-left:4px solid #a5661b}}table{{width:100%;border-collapse:collapse;background:white}}th,td{{text-align:left;padding:12px;border-bottom:1px solid #d9e2e5}}.table{{overflow-x:auto}}footer,nav{{font-size:14px;color:#536772}}footer{{margin-top:34px;border-top:1px solid #d9e2e5;padding-top:18px}}@media(max-width:620px){{main{{padding:24px 16px}}th,td{{padding:8px}}}}
</style><main><nav><a href="../">← Original startup and steady arrow images</a> · <a href="../../">Revision H study</a></nav>
<h1>Air is already moving in the first frame.</h1>
<p>This separate transient begins with the flowing field from steady-solver iteration {iteration}. Its clock starts at zero for this sequence. It is not appended to the original quiet-start simulation.</p>
<div class="notice"><strong>The starting field is not converged.</strong> These are physical transient samples after switching from the steady solver; initial adjustment remains. The provisional mesh and timestep have not passed an independence study. Periodic shedding, settled lip suction and temperature benefits are not established.</div>
<h2>Latest recorded flow</h2><figure><video id="flow-video" controls playsinline preload="metadata" poster="{folder}/poster.png"><source src="{folder}/flow.mp4" type="video/mp4"><a href="{folder}/flow.mp4">Open video</a></video>
<figcaption>{latest['source_frames']} actual CFD states, from {latest['first_time_s']*1000:.4f} to {latest['last_time_s']*1000:.4f} ms after flowing-field initialization. {latest['video_duration_s']:.2f} seconds of playback at {latest['playback_slowdown']:.0f}× slow motion, rounded to 30 fps, with a half-second final hold. No intermediate CFD states are generated. <a href="latest.mp4">Open the latest MP4</a>.</figcaption></figure>
<figure><a href="{folder}/history.png"><img src="{folder}/history.png" alt="Pressure, speed, boundary flow and Courant histories against physical transient time" loading="lazy"></a><figcaption>Recorded probe histories. A steady-solver iteration is not counted as elapsed fluid time.</figcaption></figure>
<h2>Preserved checkpoints</h2><div class="table"><table><thead><tr><th>Checkpoint</th><th>Transient time</th><th>Actual states</th><th>Files</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<h2>How this run is initialized</h2><p>The geometry, mesh and fan forcing match the original Revision H case. Velocity, pressure and turbulence fields are copied from the saved steady iterate; old transient history is not copied. The backward time scheme uses its native initial Euler fallback. The solver uses four CPU workers, {outer} outer correction passes, an initial 12.5 µs step, a maximum 25 µs step and an adaptive Courant target of 0.5.</p>
<p>Arrows show sampled in-plane velocity at X = +111 mm. Colour limits are fixed within this sequence: speed 0–6 m/s, pressure ±12 Pa and vorticity ±2000/s. The original startup sequence retains its own scales. Grey areas are solid or unsampled; black lines are CAD surfaces.</p>
<p><a href="case_manifest.json">Initialization provenance and settings</a> · <a href="quality-disposition.json">Mesh limitations</a> · <a href="run-status.json">Dated solver status</a> · <a href="../correction-check/">Short correction-count comparison</a></p>
<footer>Published {escape(public['published_snapshot_utc'])}. Solver state at publication: {escape(state['state'])}. This page is a published checkpoint, not a live connection.</footer></main></html>'''
    (PAGE/'index.html').write_text(html,encoding='utf-8',newline='\n')
    print(json.dumps({'page':str(PAGE),'checkpoint':folder,'source_frames':latest['source_frames'],'last_time_s':latest['last_time_s']}))


if __name__=='__main__':main()
