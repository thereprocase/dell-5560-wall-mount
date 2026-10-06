from pathlib import Path
import sys,json,hashlib
import FreeCAD as A,Part,Import,MeshPart
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,A.getResourceDir()+'Mod/Assembly')
d=A.openDocument(str(ROOT/'FinishValidation.FCStd'))
a=d.getObject('InstalledAssembly');links=[o for o in a.Group if o.TypeId=='App::Link']
out=ROOT/'print_refinements';out.mkdir(exist_ok=True)
manifest={}
for o in links:
 if any(word in o.InstanceKey for word in ['outlet_rail','fan_duct','fan_tray']):
  p=out/(o.InstanceKey+'.step');Import.export([o],str(p))
  # Explicit tessellation instead of inheriting viewport quality.
  mesh=MeshPart.meshFromShape(Shape=o.Shape,LinearDeflection=.05,AngularDeflection=.0872665,Relative=False)
  mesh.write(str(out/(o.InstanceKey+'.stl')))
  manifest[o.InstanceKey]={'step':p.name,'stl':o.InstanceKey+'.stl','valid':o.Shape.isValid(),'solids':len(o.Shape.Solids),'volume_mm3':o.Shape.Volume}
Import.export(links,str(ROOT/'Precision_5560_Native.step'))
(out/'manifest.json').write_text(json.dumps({'parts':manifest,'orientation':'Installed assembly coordinates; orient for printing according to source notes.','arms':'Frozen; no replacement arm files generated.'},indent=2),encoding='utf-8')
print('Exported',len(manifest),'revised components and full STEP assembly',flush=True);A.closeDocument(d.Name)
