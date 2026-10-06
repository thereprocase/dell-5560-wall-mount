"""Create and verify a 5x playback companion to an immutable CFD checkpoint.

The original video and every recorded CFD sample remain preserved. The 60 fps
companion selects existing frames; it does not interpolate new flow states.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import uuid

FFMPEG = Path('F:/Code/gpu-offload/bin/ffmpeg.exe')
SPEED = 5
FPS = 60


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command):
    options = {}
    if os.name == 'nt':
        options['creationflags'] = subprocess.IDLE_PRIORITY_CLASS | subprocess.CREATE_NO_WINDOW
    return subprocess.run(command, check=True, capture_output=True, text=True, **options)


def probe(path, ffmpeg):
    return json.loads(run([str(ffmpeg.with_name('ffprobe.exe' if os.name == 'nt' else 'ffprobe')),
                          '-v', 'error', '-select_streams', 'v:0', '-count_frames',
                          '-show_entries', 'stream=codec_name,pix_fmt,width,height,r_frame_rate,duration,nb_read_frames',
                          '-of', 'json', str(path)]).stdout)['streams'][0]


def make_fast_video(page, latest, ffmpeg=FFMPEG):
    page = Path(page)
    source = page / latest['_folder'] / 'flow.mp4'
    source_sha = sha(source)
    assert source_sha == latest['video_sha256'], 'Source checkpoint hash mismatch'
    target = page / 'latest-5x.mp4'
    manifest = page / 'latest-5x.json'
    if target.is_file() and manifest.is_file():
        cached = json.loads(manifest.read_text(encoding='utf-8'))
        if (cached['source_video_sha256'] == source_sha and cached['speed_multiplier'] == SPEED
                and cached['fps'] == FPS and cached['video_sha256'] == sha(target)):
            return cached
    source_info = probe(source, ffmpeg)
    original_duration = float(source_info['duration'])
    with tempfile.TemporaryDirectory(prefix='.fast-video-', dir=page) as temp:
        output = Path(temp) / 'flow.mp4'
        command = [str(ffmpeg), '-hide_banner', '-loglevel', 'error', '-threads', '2',
                   '-i', str(source), '-an', '-filter_threads', '1',
                   '-vf', f'setpts=(PTS-STARTPTS)/{SPEED},fps={FPS}',
                   '-c:v', 'libx264', '-threads', '2', '-preset', 'slow', '-crf', '26',
                   '-pix_fmt', 'yuv420p', '-g', str(FPS), '-movflags', '+faststart',
                   '-metadata', 'title=Revision H airflow - 5x faster playback',
                   '-metadata', 'comment=Recorded CFD states only; 5x the original video playback rate; no interpolation.',
                   str(output)]
        run(command)
        info = probe(output, ffmpeg)
        duration = float(info['duration'])
        assert info['codec_name'] == 'h264' and info['pix_fmt'] == 'yuv420p'
        assert (info['width'], info['height']) == (source_info['width'], source_info['height'])
        assert info['r_frame_rate'] == f'{FPS}/1'
        assert abs(duration - original_duration / SPEED) <= 1 / FPS + 1e-6
        assert abs(int(info['nb_read_frames']) / FPS - duration) <= 1e-6
        # Decode the complete file with errors made fatal before replacing the alias.
        run([str(ffmpeg), '-hide_banner', '-loglevel', 'error', '-xerror', '-threads', '2',
             '-i', str(output), '-f', 'null', '-'])
        report = {
            'created_utc': datetime.now(timezone.utc).isoformat(),
            'source_checkpoint': latest['_folder'],
            'source_video': f"{latest['_folder']}/flow.mp4",
            'source_video_sha256': source_sha,
            'source_video_duration_s': original_duration,
            'source_encoded_frames': int(source_info['nb_read_frames']),
            'source_cfd_states': latest['source_frames'],
            'first_time_s': latest['first_time_s'],
            'last_time_s': latest['last_time_s'],
            'speed_multiplier': SPEED,
            'playback_slowdown': latest['playback_slowdown'] / SPEED,
            'fps': FPS,
            'encoded_frames': int(info['nb_read_frames']),
            'video_duration_s': duration,
            'video_sha256': sha(output),
            'video_bytes': output.stat().st_size,
            'size_px': [info['width'], info['height']],
            'encoding': {'codec': 'H.264', 'crf': 26, 'preset': 'slow'},
            'timing': 'Original presentation timestamps divided by 5, then rounded to 60 fps. Final hold also shortened by 5.',
            'sampling': 'Existing video frames selected at 60 fps; no blending or generated intermediate CFD states. Full sample sequence retained in the original video.',
            'verification': 'Source SHA-256 checked; dimensions, frame rate, decoded frame count and duration checked; complete error-fatal decode passed.',
        }
        # Create publication files directly under PAGE so Windows inherits the
        # repository ACL, rather than retaining TemporaryDirectory's private ACL.
        token = uuid.uuid4().hex
        staged_video = page / f'.latest-5x-{token}.mp4'
        staged_manifest = page / f'.latest-5x-{token}.json'
        try:
            shutil.copyfile(output, staged_video)
            staged_manifest.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
            staged_video.replace(target)
            staged_manifest.replace(manifest)
        finally:
            staged_video.unlink(missing_ok=True)
            staged_manifest.unlink(missing_ok=True)
    return report


def fast_video_html(report, folder):
    version = report['video_sha256'][:12]
    return f'''<h3>5× faster playback</h3>
<figure><video id="flow-video-fast" controls playsinline preload="metadata" poster="{folder}/poster.png"><source src="latest-5x.mp4?v={version}" type="video/mp4"><a href="latest-5x.mp4">Open the 5× MP4</a></video>
<figcaption>The same recorded interval in {report['video_duration_s']:.2f} seconds at 60 fps: five times the original playback speed, still approximately {report['playback_slowdown']:.0f}× slower than physical time. Frames are selected without interpolation; the original video retains every recorded state. <a href="latest-5x.mp4">Open or download the latest 5× MP4</a> · <a href="latest-5x.json">Timing and provenance</a>.</figcaption></figure>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--page', type=Path, required=True)
    parser.add_argument('--ffmpeg', type=Path, default=FFMPEG)
    args = parser.parse_args()
    latest = json.loads((args.page / 'latest.json').read_text(encoding='utf-8'))
    full = json.loads((args.page / latest['_folder'] / 'progress.json').read_text(encoding='utf-8'))
    full['_folder'] = latest['_folder']
    print(json.dumps(make_fast_video(args.page, full, args.ffmpeg)))


if __name__ == '__main__':
    main()
