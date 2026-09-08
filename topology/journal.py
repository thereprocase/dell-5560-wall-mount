"""One-command progress entry; --push also commits/pushes on authenticated desktops.
Cloud publication uses publish_in_cloud.js with the connected GitHub app.
"""
import argparse,json,datetime,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
URL='https://github.com/thereprocase/dell-5560-wall-mount/blob/cloud-topo/topology/JOURNAL.md'
p=argparse.ArgumentParser();p.add_argument('--title',required=True);p.add_argument('--note-file',required=True);p.add_argument('--image',action='append',default=[]);p.add_argument('--include',action='append',default=[]);p.add_argument('--push',action='store_true');a=p.parse_args()
entries_path=ROOT/'topology/journal_entries.json'
entries=json.loads(entries_path.read_text()) if entries_path.exists() else []
entry={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),'title':a.title,'note':Path(a.note_file).read_text(),'images':a.image}
for image in a.image+a.include:
    f=(ROOT/image).resolve();f.relative_to(ROOT)
    if not f.is_file():raise FileNotFoundError(f)
entries.insert(0,entry);entries_path.write_text(json.dumps(entries,indent=2)+'\n')
lines=['# Cloud topology journal','Latest update first. Images show actual geometry unless labeled as reference images or diagrams. Click a GitHub image to open it separately.','']
for e in entries:
    lines += ['## '+e['title'],e['utc'],'',e['note'],'']
    for im in e['images']:lines += [f'![{e["title"]}](../{im})','']
(ROOT/'topology/JOURNAL.md').write_text('\n'.join(lines))
paths=['topology/JOURNAL.md','topology/journal_entries.json',*a.image,*a.include]
manifest=ROOT/'topology/publish_manifest.json';manifest.write_text(json.dumps({'paths':paths,'message':a.title},indent=2)+'\n')
if a.push:
    subprocess.run(['git','add','--',*paths],cwd=ROOT,check=True)
    subprocess.run(['git','commit','-m',a.title],cwd=ROOT,check=True)
    subprocess.run(['git','push','origin','HEAD:cloud-topo'],cwd=ROOT,check=True)
print(URL)
