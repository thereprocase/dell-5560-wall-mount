"""Publish installed meshes from each independently recomputed native preset."""
from pathlib import Path
import json
import FreeCAD as App
import MeshPart
from presets import PRESETS
from validate import shapes
from export import sha

ROOT=Path(__file__).resolve().parent
out=ROOT.parent/'docs/models/minimalist'
manifest={'presets':{},'dam_index_range':[0,8],'rung_pitch_mm':12}
for name,preset in PRESETS.items():
    source=ROOT/'presets'/name/'M1.FCStd'
    doc=App.openDocument(str(source))
    folder=out/name;folder.mkdir(parents=True,exist_ok=True)
    rows=[]
    for key,shape in sorted(shapes(doc).items()):
        mesh=MeshPart.meshFromShape(Shape=shape,LinearDeflection=.07,AngularDeflection=.15,Relative=False)
        mesh.write(str(folder/(key+'.stl')))
        rows.append({'key':key,'volume_mm3':shape.Volume})
    manifest['presets'][name]={**preset,'native_sha256':sha(source),'parts':rows,'exported_dam_index':8}
    App.closeDocument(doc.Name)
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Published six native-derived installed scenes',flush=True)
