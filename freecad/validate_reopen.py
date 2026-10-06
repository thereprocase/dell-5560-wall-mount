from pathlib import Path
import sys,json,hashlib
import FreeCAD as A,Part
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,A.getResourceDir()+'Mod/Assembly')
p=ROOT/'ValidationSnapshot.FCStd'; d=A.openDocument(str(p))
d.recompute(None,True,True)
a=d.getObject('InstalledAssembly'); links=[o for o in a.Group if o.TypeId=='App::Link']
joints=[j for g in a.Group if g.TypeId=='Assembly::JointGroup' for j in g.Group]
r={'snapshot_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'invalid_features':[o.Name for o in d.Objects if 'Invalid' in o.State],'underconstrained_sketches':[o.Name for o in d.Objects if o.TypeId=='Sketcher::SketchObject' and not o.FullyConstrained],'valid_solids':sum(o.Shape.isValid() and len(o.Shape.Solids)==1 for o in links),'joint_count':len(joints),'broken_joint_references':[j.Name for j in joints if hasattr(j,'Reference1') and (not j.Reference1[0] or not j.Reference2[0])]}
r['all_pass']=not r['invalid_features'] and not r['underconstrained_sketches'] and r['valid_solids']==14 and not r['broken_joint_references']
(ROOT/'reopen_validation.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
print(json.dumps(r),flush=True)
A.closeDocument(d.Name)
