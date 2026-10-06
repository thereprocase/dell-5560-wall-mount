from pathlib import Path
import json,sys
import FreeCAD as A,Part
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,A.getResourceDir()+'Mod/Assembly')
d=A.openDocument(str(Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'RailValidation.FCStd'))
a=d.getObject('InstalledAssembly');links={o.InstanceKey:o for o in a.Group if o.TypeId=='App::Link'}
rails={k:o.Shape for k,o in links.items() if 'outlet_rail' in k}
refs=Part.read(str(ROOT.parent/'REFERENCE_Installed_Layout.step')).Solids
lap=next(q for q in refs if q.BoundBox.XLength>300)
r={'invalid_features':[o.Name for o in d.Objects if 'Invalid' in o.State],'underconstrained_sketches':[o.Name for o in d.Objects if o.TypeId=='Sketcher::SketchObject' and not o.FullyConstrained],'arms':{},'rails':{}}
def overlap(a,b):
 c=a.common(b);assert c.isValid();return c.Volume
for key,info in json.loads((ROOT/'frozen_print_arms/manifest.json').read_text())['parts'].items():
 x=d.getObject(info['source']).Shape;y=Part.read(str(ROOT/'frozen_print_arms'/info['file']));ab=x.cut(y);ba=y.cut(x);assert ab.isValid() and ba.isValid();r['arms'][key]=abs(ab.Volume)+abs(ba.Volume)
for k,s in rails.items():
 side='left' if 'left' in k else 'right';cradle=next(o.Shape for key,o in links.items() if side in key and 'cradle' in key)
 c={'valid':s.isValid(),'solids':len(s.Solids),'laptop_overlap':overlap(s,lap),'other_part_overlaps':{},'insertion_samples':{}}
 for key,o in links.items():
  if key!=k:
   v=overlap(s,o.Shape)
   if v>1e-5:c['other_part_overlaps'][key]=v
 for y in [0,.3,1,3,5,10,20,40,60]:
  q=s.copy();q.translate(A.Vector(0,y,0));c['insertion_samples'][str(y)]=overlap(q,cradle)
 x=162 if side=='right' else -162;c['driver_overlap']=overlap(s,Part.makeCylinder(8,60,A.Vector(x,-1,174),A.Vector(0,1,0)))
 r['rails'][k]=c
r['all_pass']=not r['invalid_features'] and not r['underconstrained_sketches'] and all(v<1e-6 for v in r['arms'].values()) and all(c['valid'] and c['solids']==1 and c['laptop_overlap']<1e-5 and c['driver_overlap']<1e-5 and not c['other_part_overlaps'] and all(v<1e-5 for v in c['insertion_samples'].values()) for c in r['rails'].values())
(ROOT/'rail_refinement_validation.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r),flush=True)
A.closeDocument(d.Name)
