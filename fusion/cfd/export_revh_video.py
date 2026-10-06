"""Convert the published CFD frames to a slow, seekable H.264 video.

Requires Pillow and an FFmpeg executable with libx264. Example:
python fusion/cfd/export_revh_video.py --ffmpeg /path/to/ffmpeg
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from PIL import Image, ImageSequence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ffmpeg', default='ffmpeg')
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[2] / 'docs/simulation/revh-transient')
    args = parser.parse_args()
    out = args.output.resolve()
    provenance_path = out / 'animation-provenance.json'
    provenance = json.loads(provenance_path.read_text(encoding='utf-8'))
    source = out / 'pilot-sections.gif'
    with Image.open(source) as gif:
        frames = [frame.convert('RGB').copy() for frame in ImageSequence.Iterator(gif)]
    times = provenance['physical_times_s']
    assert len(frames) == len(times) >= 2, 'Each recorded time needs one source frame'
    intervals = [b - a for a, b in zip(times, times[1:])]
    assert min(intervals) > 0
    assert len({frame.size for frame in frames}) == 1
    width, height = frames[0].size
    assert width % 2 == height % 2 == 0, 'H.264 yuv420p needs even dimensions'

    # Preserve relative physical spacing, rounded to 30 fps, with the shortest
    # interval shown for two seconds. Hold the final sample for three seconds.
    # Repeated encoded frames are holds, never interpolated CFD observations.
    fps = 30
    slowdown = 2.0 / min(intervals)
    starts = [round((t - times[0]) * slowdown * fps) for t in times]
    counts = [b - a for a, b in zip(starts, starts[1:])] + [3 * fps]
    video = out / 'pilot-sections.mp4'
    command = [args.ffmpeg, '-hide_banner', '-loglevel', 'error', '-y',
               '-f', 'rawvideo', '-pixel_format', 'rgb24',
               '-video_size', f'{width}x{height}', '-framerate', str(fps),
               '-i', 'pipe:0', '-an', '-c:v', 'libx264', '-threads', '4',
               '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p',
               '-g', str(fps), '-movflags', '+faststart', str(video)]
    with subprocess.Popen(command, stdin=subprocess.PIPE) as encoder:
        try:
            for frame, count in zip(frames, counts):
                pixels = frame.tobytes()
                for _ in range(count):
                    encoder.stdin.write(pixels)
        finally:
            encoder.stdin.close()
        if encoder.wait():
            raise RuntimeError('FFmpeg video encoding failed')
    frames[0].save(out / 'pilot-sections-poster.png')
    provenance['video'] = {
        'file': video.name,
        'source': source.name,
        'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'sha256': hashlib.sha256(video.read_bytes()).hexdigest(),
        'codec': 'H.264', 'pixel_format': 'yuv420p',
        'width': width, 'height': height, 'frames_per_second': fps,
        'source_frame_count': len(frames),
        'encoded_frame_count': sum(counts),
        'duration_s': sum(counts) / fps,
        'target_playback_slowdown': slowdown,
        'source_frame_start_s': [start / fps for start in starts],
        'source_frame_duration_s': [count / fps for count in counts],
        'presentation': 'User-controlled playback; no autoplay or automatic looping. Physical intervals are uniformly slowed and rounded to 30 fps; the final sample is held for 3 seconds. Original timestamps and fixed colour scales are preserved. No motion interpolation or additional simulation samples.'
    }
    provenance_path.write_text(json.dumps(provenance, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(provenance['video'], indent=2))


if __name__ == '__main__':
    main()
