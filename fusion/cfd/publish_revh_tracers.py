"""Refresh moving-tracer companions as part of normal checkpoint publication."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import uuid
from make_revh_fast_video import FFMPEG, probe, run, sha

BASE = Path(__file__).resolve().parent
RENDER_PYTHON = 'C:/Program Files/FreeCAD 1.1/bin/python.exe'


def make_tracer_video(page, latest, case):
    page, case = Path(page), Path(case)
    renderer = BASE / 'render_revh_tracers.py'
    renderer_sha = hashlib.sha256(renderer.read_text(encoding='utf-8').encode()).hexdigest()
    target = page / 'latest-tracers.mp4'
    manifest = page / 'latest-tracers.json'
    if target.is_file() and manifest.is_file():
        cached = json.loads(manifest.read_text(encoding='utf-8'))
        if (cached.get('renderer_sha256') == renderer_sha
                and cached['source_video_sha256'] == latest['video_sha256']
                and cached['video_sha256'] == sha(target)):
            return cached
    parent = case / 'render-tracers'
    parent.mkdir(exist_ok=True)
    stem = f"{latest['_folder']}-{latest['video_sha256'][:12]}-{renderer_sha[:12]}"
    output = parent / stem
    if output.exists() and not (output / 'tracers.json').exists():
        output = parent / (stem + '-' + uuid.uuid4().hex[:8])
    if not output.exists():
        options = {}
        if os.name == 'nt':
            options['creationflags'] = subprocess.IDLE_PRIORITY_CLASS | subprocess.CREATE_NO_WINDOW
        command = [RENDER_PYTHON, str(renderer), '--case', str(case), '--page', str(page),
                   '--checkpoint', latest['_folder'], '--output', str(output)]
        with (parent / (output.name + '.log')).open('w', encoding='utf-8') as log:
            subprocess.run(command, check=True, stdout=log, stderr=subprocess.STDOUT, timeout=1800, **options)
    report = json.loads((output / 'tracers.json').read_text(encoding='utf-8'))
    assert not report['preview'] and report['samples_read_and_hash_verified'] == latest['source_frames']
    assert report['source_video_sha256'] == latest['video_sha256']
    assert abs(report['last_time_s'] - latest['last_time_s']) < 1e-12
    assert report['video_sha256'] == sha(output / 'tracers.mp4')
    assert all(c['integrated_travel_mm'] > 0 and c['integrated_particle_steps'] > 0 for c in report['clouds'])
    info = probe(output / 'tracers.mp4', FFMPEG)
    assert info['codec_name'] == 'h264' and info['pix_fmt'] == 'yuv420p'
    assert info['r_frame_rate'] == '60/1' and [info['width'], info['height']] == [1800, 1100]
    assert int(info['nb_read_frames']) == report['encoded_frames']
    assert abs(float(info['duration']) - report['video_duration_s']) < .001
    run([str(FFMPEG), '-hide_banner', '-loglevel', 'error', '-xerror', '-threads', '2',
         '-i', str(output / 'tracers.mp4'), '-f', 'null', '-'])
    report.update(renderer_sha256=renderer_sha,
                  verification='All used CFD samples hash checked; complete source interval integrated; particle movement recorded; full video decode, dimensions, frame count and duration checked.')
    token = uuid.uuid4().hex
    for source, destination in [(output / 'tracers.mp4', target),
                                (output / report['last_frame_file'], page / 'latest-tracers.png')]:
        temporary = page / ('.tracers-' + token + destination.suffix)
        shutil.copyfile(source, temporary)
        temporary.replace(destination)
    temporary = page / ('.tracers-' + token + '.json')
    temporary.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    temporary.replace(manifest)
    return report


def tracer_video_html(report):
    version = report['video_sha256'][:12]
    return f'''<h2>Follow the moving air</h2>
<figure><video id="flow-video-tracers" controls playsinline preload="metadata" poster="latest-tracers.png?v={version}"><source src="latest-tracers.mp4?v={version}" type="video/mp4"><a href="latest-tracers.mp4">Open the moving-tracer MP4</a></video>
<figcaption>Moving particles and fading trails follow the saved in-plane velocity over the pressure field, through {report['last_time_s']*1000:.4f} ms. {report['video_duration_s']:.2f} seconds at 60 fps and five times the original playback speed. This is a projected 2D visualization with interpolation between recorded samples, not a reconstruction of full 3D particle paths. <a href="latest-tracers.mp4">Open or download the latest moving-tracer MP4</a> · <a href="latest-tracers.json">Method and provenance</a>.</figcaption></figure>'''
