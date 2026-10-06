"""Request a graceful, resumable stop for both authorized CFD continuations."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--mirror-root',type=Path,required=True)
    p.add_argument('--controller',type=Path,required=True)
    args=p.parse_args()
    targets=[]
    for name in ['revh_fourhour_08','revh_flowing_12']:
        targets.extend([args.root/name/'run-control.json',args.mirror_root/name/'run-control.json'])
    targets.append(args.controller/'control.json')
    for path in targets:
        control=json.loads(path.read_text())
        control.update(stop_requested=True,requested_utc=datetime.now(timezone.utc).isoformat())
        temp=path.with_suffix('.tmp');temp.write_text(json.dumps(control,indent=2)+'\n');temp.replace(path)
    print('Requested native checkpoint-and-stop for both simulations; the publisher will preserve a final cumulative video.')


if __name__=='__main__':main()
