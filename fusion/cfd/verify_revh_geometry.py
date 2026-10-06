"""Independent read-only snapshot / STEP check and intended probe locations."""
from pathlib import Path
import hashlib
import json
import shutil
import sys
import argparse
import FreeCAD as App
import Part

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--case',type=Path,default=BASE/'runs/revh_transient_04')
args=parser.parse_args()
sys.path.insert(0,App.getResourceDir()+'Mod/Assembly')
source=ROOT/'freecad/Precision_5560_Native.FCStd'
snapshot=ROOT/'freecad/ValidationSnapshot.FCStd'
if snapshot.exists():
    assert hashlib.sha256(snapshot.read_bytes()).digest()==hashlib.sha256(source.read_bytes()).digest(), 'Preserve differing snapshot'
else:shutil.copy2(source,snapshot)
doc=App.openDocument(str(snapshot))
try:
    links=[o for o in doc.getObject('InstalledAssembly').Group if o.TypeId=='App::Link']
    step=Part.read(str(ROOT/'freecad/Precision_5560_Native.step'))
    remaining=list(step.Solids)
    checks=[]
    for link in links:
        assert len(link.Shape.Solids)==1
        native=link.Shape.Solids[0]
        other=min(remaining,key=lambda s:(s.CenterOfMass-native.CenterOfMass).Length)
        remaining.remove(other)
        checks.append({'part':link.InstanceKey,'native_valid':native.isValid(),'native_solids':len(native.Solids),
                       'step_valid':other.isValid(),'centroid_delta_mm':(other.CenterOfMass-native.CenterOfMass).Length,
                       'relative_volume_delta':abs(other.Volume-native.Volume)/native.Volume})
    fluid=Part.read(str(BASE/'geometry_revh/fluid_source.brep'))
    case=json.loads((args.case/'case_manifest.json').read_text())
    probes=[{**p,'inside_CAD_fluid':fluid.isInside(App.Vector(*(v*1000 for v in p['point_m'])),1e-6,False)} for p in case['probes']]
    report={'native_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
            'revision_h_blends_present':all(doc.getObject(n) is not None for n in ['FlowInnerBlend','FlowOuterSupport']),
            'native_part_count':len(links),'step_solid_count':len(step.Solids),'parts':checks,'probes':probes,
            'comparison':'Independent saved native snapshot against installed-coordinate STEP: validity, solid count, centroid and volume. Not a pointwise equivalence proof.'}
    report['pass']=(len(links)==14 and len(step.Solids)==14 and not remaining and report['revision_h_blends_present']
        and all(p['native_valid'] and p['step_valid'] and p['native_solids']==1 and p['centroid_delta_mm']<.001 and p['relative_volume_delta']<1e-6 for p in checks)
        and all(p['inside_CAD_fluid'] for p in probes))
    (BASE/'geometry_revh/native_step_probe_check.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'pass':report['pass'],'part_count':len(links),'blends':report['revision_h_blends_present'],
                      'invalid_probes':[p for p in probes if not p['inside_CAD_fluid']]},indent=2),flush=True)
    assert report['pass']
finally:App.closeDocument(doc.Name)
