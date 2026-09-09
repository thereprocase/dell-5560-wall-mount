"""Freeze complete samples from the running visual branch for hourly rendering."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def snapshot(extension, page):
    extension=Path(extension);page=Path(page);presentation=extension/'presentation'
    live=json.loads((extension/'run-status.json').read_text())
    assert live['state'] in ['running','writing_final_checkpoint','complete','failed']
    assert live['latest_physical_time_s'] is not None
    base=json.loads((page/'hour-18/progress.json').read_text())
    detail=json.loads((page/'checkpoint-03/progress.json').read_text())['visual_extension']
    assert base['last_time_s']==detail['base_last_time_s']
    folders=sorted((p for p in (extension/'postProcessing/edge_sections').iterdir()
                    if p.is_dir() and not p.name.startswith('.')
                    and detail['base_last_time_s']+1e-11<float(p.name)<=live['latest_physical_time_s']+1e-12),
                   key=lambda p:float(p.name))
    assert folders
    for i,p in enumerate(folders):
        assert abs(float(p.name)-(detail['base_last_time_s']+(i+1)*detail['video_frame_step_s']))<1e-10,'Missing or mistimed visual frame'
    for t in base['physical_times_s']:
        folder=presentation/'postProcessing/edge_sections'/str(t)
        # The original spelling can contain insignificant trailing digits.
        if not folder.exists():
            folder=next(p for p in (presentation/'postProcessing/edge_sections').iterdir() if float(p.name)==t)
        assert sha(folder/'right_section.vtp')==base['source_sha256'][str(t)]
    for folder in folders:
        target=presentation/'postProcessing/edge_sections'/folder.name;target.mkdir(parents=True,exist_ok=True)
        for name in ['right_section.vtp','left_section.vtp']:
            assert (folder/name).read_bytes().rstrip().endswith(b'</VTKFile>')
            if not (target/name).exists():os.link(folder/name,target/name)
            assert sha(target/name)==sha(folder/name)
    times=base['physical_times_s']+[float(p.name) for p in folders]
    actual=sorted(float(p.name) for p in (presentation/'postProcessing/edge_sections').iterdir() if p.is_dir() and float(p.name)<=times[-1]+1e-12)
    assert actual==times
    detail['new_frames']=len(folders)
    state=dict(live,latest_physical_time_s=times[-1],complete_sample_frames=len(times),visual_extension=detail)
    manifest=json.loads((extension/'case_manifest.json').read_text());manifest['visual_extension']=detail
    for name,data in [('run-status.json',state),('case_manifest.json',manifest),('visual-extension.json',detail)]:
        (presentation/name).write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8',newline='\n')
    shutil.copy2(extension/'quality-disposition.json',presentation/'quality-disposition.json')
    return state


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--extension',type=Path,required=True);p.add_argument('--page',type=Path,required=True)
    args=p.parse_args();s=snapshot(args.extension,args.page)
    print(json.dumps({k:s[k] for k in ['state','latest_physical_time_s','complete_sample_frames']}))
