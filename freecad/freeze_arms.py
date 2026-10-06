from pathlib import Path
import json,hashlib,shutil
import FreeCAD as App
ROOT=Path(__file__).resolve().parent
D=next(d for d in App.listDocuments().values() if d.FileName and Path(d.FileName).resolve()==(ROOT/'Precision_5560_Native.FCStd').resolve())
D.save(); frozen=ROOT/'frozen_print_arms'; frozen.mkdir(exist_ok=True)
manifest={'reason':'User started printing; no further arm/cradle geometry changes authorized.','parts':{}}
for o in D.Objects:
    if o.TypeId!='App::Link' and 'PartKey' in o.PropertiesList and 'cradle' in o.PartKey:
        path=frozen/(o.PartKey+'.brep')
        if path.exists(): raise RuntimeError('Existing print baseline must not be overwritten')
        o.Shape.exportBrep(str(path))
        o.addProperty('App::PropertyBool','PrintFrozen','Manufacturing'); o.PrintFrozen=True; o.setEditorMode('PrintFrozen',1)
        o.addProperty('App::PropertyString','ManufacturingNote','Manufacturing'); o.ManufacturingNote='PRINTING: geometry frozen. Change mating teal parts only.'; o.setEditorMode('ManufacturingNote',1)
        manifest['parts'][o.PartKey]={'source':o.Name,'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'volume':o.Shape.Volume}
(frozen/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
D.save(); shutil.copy2(D.FileName,ROOT/'BeforeRailFit.FCStd')
App.Console.PrintMessage('Both printed arms frozen; immutable geometry baselines saved.\n')
