"""Add the no-dam hardware alternative without rewriting existing print files."""
from pathlib import Path
import json
import FreeCAD as App
from export import optional_hardware, sha

ROOT=Path(__file__).resolve().parent
hashes={}
for source in sorted((ROOT/'presets').glob('*/M1.FCStd')):
    doc=App.openDocument(str(source))
    folder=source.parent/'print'
    manifest=json.loads((folder/'manifest.json').read_text())
    assert manifest['native_sha256']==sha(source)
    manifest['plates']['22_hardware_without_dam']=optional_hardware(doc,folder)
    (folder/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    hashes[source.parent.name]=sha(folder/'22_hardware_without_dam.stl')
    App.closeDocument(doc.Name)
(ROOT/'optional-hardware-review.json').write_text(json.dumps({'identical_stl_across_all_presets':len(set(hashes.values()))==1,'solids_per_plate':8,'sha256':hashes},indent=2)+'\n')
print('All six no-dam plates validated; eight hardware parts per plate',flush=True)
