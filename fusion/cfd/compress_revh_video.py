"""Encode smaller H.264 videos directly from cached, lossless plotted CFD frames.

The renderer and its cache remain unchanged. Every source state, timestamp,
frame count, image size, and playback interval is retained. --apply updates only
an unpublished checkpoint folder and preserves its initial encode alongside it.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time
from PIL import Image

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--case',type=Path,required=True)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--crf',type=int,default=30)
    p.add_argument('--apply',action='store_true')
    p.add_argument('--ffmpeg',default='F:/Code/gpu-offload/bin/ffmpeg.exe')
    args=p.parse_args();assert 19<=args.crf<=30
    report=json.loads((args.source/'progress.json').read_text())
    signature=hashlib.sha256((json.dumps(report['fixed_scales'],sort_keys=True)+
                             sha(BASE/'render_revh_progress.py')+
                             sha(ROOT/'docs/simulation/revh-transient/section-locator.png')).encode()).hexdigest()[:16]
    cache=args.case/'render-cache'/signature;assert cache.is_dir()
    paths=[]
    for t in report['physical_times_s']:
        digest=report['source_sha256'][str(t)]
        matches=list(cache.glob('*-'+digest[:10]+'.png'));assert len(matches)==1,(t,matches)
        paths.append(matches[0])
    counts=[round(duration*report['fps']) for duration in report['source_frame_duration_s']]
    assert sum(counts)==report['encoded_frames'] and len(paths)==report['source_frames']
    target=args.source/f'flow-crf{args.crf}-slow.mp4';assert not target.exists()
    width,height=report['fixed_scales']['size_px'];started=time.monotonic()
    command=[args.ffmpeg,'-hide_banner','-loglevel','error','-f','rawvideo','-pixel_format','rgb24',
             '-video_size',f'{width}x{height}','-framerate',str(report['fps']),'-i','pipe:0','-an',
             '-c:v','libx264','-threads','2','-preset','slow','-crf',str(args.crf),'-pix_fmt','yuv420p',
             '-g','30','-movflags','+faststart',str(target)]
    with (args.source/f'encoding-crf{args.crf}.log').open('w') as log:
        proc=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=log)
        try:
            for path,count in zip(paths,counts):
                with Image.open(path) as image:pixels=image.convert('RGB').tobytes()
                for _ in range(count):proc.stdin.write(pixels)
        finally:proc.stdin.close()
        assert proc.wait()==0
    original=args.source/'flow.mp4'
    result={'codec':'H.264','preset':'slow','crf':args.crf,'direct_from_lossless_plots':True,
            'source_frames_retained':len(paths),'encoded_frames_retained':sum(counts),
            'original_bytes':original.stat().st_size,'compressed_bytes':target.stat().st_size,
            'space_saved_fraction':1-target.stat().st_size/original.stat().st_size,
            'encoding_seconds':time.monotonic()-started,'video_sha256':sha(target)}
    if args.apply:
        assert 'docs' not in args.source.parts,'Never rewrite a published archive'
        assert target.stat().st_size<original.stat().st_size
        original.rename(args.source/'flow-before-compression.mp4');target.rename(original)
        report.update(video_sha256=result['video_sha256'],video_encoding=result)
        (args.source/'progress.json').write_text(json.dumps(report,indent=2)+'\n')
    (args.source/f'compression-crf{args.crf}.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
