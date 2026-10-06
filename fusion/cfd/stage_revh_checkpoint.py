"""Stage a reviewed-source CFD checkpoint without replacing earlier archives."""
import argparse
import hashlib
import gzip
import json
from pathlib import Path
import re
import shutil

PAGE=Path(__file__).resolve().parents[2]/'docs/simulation/revh-transient/sequence'
FILES=['flow.mp4','poster.png','first-frame.png','progress.json','history.png','diagnostics.json','diagnostic-raw']


def copy(source,target):
    target.mkdir(exist_ok=False)
    compressed={}
    def pack(original,destination):
        raw=original.read_bytes();data=gzip.compress(raw,compresslevel=9,mtime=0)
        assert gzip.decompress(data)==raw
        destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(data)
        compressed[destination.relative_to(target).as_posix()]={
            'uncompressed_sha256':hashlib.sha256(raw).hexdigest(),
            'compressed_sha256':hashlib.sha256(data).hexdigest(),
            'uncompressed_bytes':len(raw),'compressed_bytes':len(data)}
    for name in FILES:
        path=source/name
        if name=='diagnostics.json' and path.is_file():pack(path,target/'diagnostics.json.gz')
        elif name=='diagnostic-raw' and path.is_dir():
            for original in path.iterdir():
                assert original.is_file();pack(original,target/name/(original.name+'.gz'))
        elif path.is_dir():shutil.copytree(path,target/name)
        elif path.is_file():shutil.copy2(path,target/name)
    if compressed:
        (target/'diagnostic-compression.json').write_text(json.dumps({
            'method':'Lossless gzip level 9; every decompressed byte verified before staging.',
            'files':compressed},indent=2)+'\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--folder',required=True)
    args=parser.parse_args()
    assert re.fullmatch(r'(hour-\d{1,3}|checkpoint-\d{2})',args.folder)
    report=json.loads((args.source/'progress.json').read_text())
    assert not report['preview_subsampled']
    assert report['source_frames']==report['source_sample_count_available']
    assert hashlib.sha256((args.source/'flow.mp4').read_bytes()).hexdigest()==report['video_sha256']
    if (args.source/'diagnostics.json').exists():
        diagnostics=json.loads((args.source/'diagnostics.json').read_text())
        assert diagnostics['through_time_s']==report['last_time_s']
    if not (PAGE/'checkpoint-01').exists() and (PAGE/'early/progress.json').exists():
        copy(PAGE/'early',PAGE/'checkpoint-01')
    copy(args.source,PAGE/args.folder)
    print(json.dumps({'archive':args.folder,'source_frames':report['source_frames'],'through_ms':report['last_time_s']*1000}))


if __name__=='__main__':main()
