"""Copy the latest complete steady plane pair into an immutable local snapshot."""
import argparse
import json
from pathlib import Path
import shutil


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case',type=Path,required=True)
    parser.add_argument('--mirror',type=Path,required=True)
    args=parser.parse_args()
    state=json.loads((args.case/'run-status.json').read_text())
    folders=sorted((args.case/'postProcessing/edge_sections').iterdir(),key=lambda p:int(p.name))
    selected=None
    for folder in folders:
        if int(folder.name)>state['latest_iteration']:continue
        files=[folder/(name+'.vtp') for name in ['right_section','left_section']]
        if all(p.is_file() and p.read_bytes()[-128:].rstrip().endswith(b'</VTKFile>') for p in files):selected=folder
    assert selected is not None,'No complete sampled plane pair'
    target=args.mirror/('iteration-'+selected.name)
    target.mkdir(exist_ok=False)
    for name in ['right_section.vtp','left_section.vtp']:shutil.copy2(selected/name,target/name)
    (target/'captured-status.json').write_text(json.dumps(state,indent=2)+'\n')
    print(json.dumps({'iteration':int(selected.name),'snapshot':str(target),'converged':state['converged']}))


if __name__=='__main__':main()
