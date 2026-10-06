"""Measure lossless compression on one immutable native checkpoint partition."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile
import time


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();args.output.mkdir(exist_ok=False);os.nice(10)
    plain=args.output/'checkpoint.tar'
    with tarfile.open(plain,'w') as archive:archive.add(args.source,arcname=args.source.name)
    raw=plain.read_bytes();expected=hashlib.sha256(raw).hexdigest();results={}
    for label,command in [('gzip-9',['gzip','-9','-c',str(plain)]),
                          ('zstd-19',['zstd','-19','-T1','-q','-c',str(plain)])]:
        target=args.output/('checkpoint.tar.gz' if label=='gzip-9' else 'checkpoint.tar.zst')
        started=time.monotonic()
        with target.open('wb') as stream:subprocess.run(command,stdout=stream,check=True,timeout=180)
        seconds=time.monotonic()-started
        decoded=gzip.decompress(target.read_bytes()) if label=='gzip-9' else subprocess.check_output(['zstd','-d','-q','-c',str(target)])
        assert hashlib.sha256(decoded).hexdigest()==expected
        results[label]={'bytes':target.stat().st_size,'compression_seconds':seconds,
                        'space_saved_fraction':1-target.stat().st_size/len(raw),
                        'exact_uncompressed_sha256_verified':expected}
    report={'source':str(args.source),'uncompressed_tar_bytes':len(raw),'results':results,
            'scope':'One saved partition; observed ratio only, not a guarantee for all future fields.'}
    (args.output/'compression.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':main()
