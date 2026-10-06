from pathlib import Path
import sys,json
import FreeCAD as A,Part,MeshPart
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,A.getResourceDir()+'Mod/Assembly')
d=A.openDocument(str(ROOT/'FinishValidation.FCStd'));out=ROOT.parent/'docs';parts=[]
for o in d.getObject('InstalledAssembly').Group:
 if o.TypeId!='App::Link':continue
 key=o.InstanceKey
 for version,shape in [('after',o.Shape),('before',Part.read(str(ROOT.parent/'parts'/(key+'.step'))))]:
  mesh=MeshPart.meshFromShape(Shape=shape,LinearDeflection=.09,AngularDeflection=.12,Relative=False);mesh.write(str(out/'models'/version/(key+'.stl')))
 parts.append({'key':key,'label':o.Label,'volume':o.Shape.Volume,'frozen':'cradle' in key})
(out/'models/manifest.json').write_text(json.dumps(parts,indent=2))
print('Exported before/after showcase geometry for',len(parts),'parts',flush=True)
A.closeDocument(d.Name)
