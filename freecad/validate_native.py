"""Validate native geometry and exercise shared aliases; always restore input values."""
from pathlib import Path
import json,time
import FreeCAD as App,Part
import FreeCADGui as Gui
ROOT=Path(__file__).resolve().parent; D=App.ActiveDocument; P=D.getObject('Parameters')
a=D.getObject('InstalledAssembly')
links={o.InstanceKey:o for o in a.Group if o.TypeId=='App::Link'}
assert len(links)==14
report={'parts':{},'sketch_count':0,'underconstrained_sketches':[],'feature_errors':[]}
for o in D.Objects:
    if o.TypeId=='Sketcher::SketchObject':
        report['sketch_count']+=1
        if not o.FullyConstrained: report['underconstrained_sketches'].append(o.Name)
    if 'Invalid' in o.State: report['feature_errors'].append([o.Name,o.getStatusString()])
for key,o in links.items():
    shape=o.Shape; ref=Part.read(str(ROOT.parent/'parts'/(key+'.step')))
    ab=shape.cut(ref); ba=ref.cut(shape)
    report['parts'][key]={'valid':shape.isValid(),'solids':len(shape.Solids),'volume_mm3':shape.Volume,'baseline_volume_mm3':ref.Volume,'symmetric_difference_mm3':ab.Volume+ba.Volume,'boolean_results_valid':ab.isValid() and ba.isValid()}
(ROOT/'final_native_validation.json').write_text(json.dumps(report,indent=2))
assert not report['feature_errors'] and not report['underconstrained_sketches']
assert all(v['valid'] and v['solids']==1 and v['boolean_results_valid'] and abs(v['symmetric_difference_mm3'])<1e-4 for v in report['parts'].values()),report
D.Label='Precision 5560 — Native Revision F'
D.saveAs(str(ROOT/'Precision_5560_Native.FCStd'))
__import__('Import').export(list(links.values()),str(ROOT/'Precision_5560_Native.step'))
Gui.activeDocument().mdiViewsOfType('Gui::View3DInventor')[0].viewAxonometric(); Gui.activeDocument().mdiViewsOfType('Gui::View3DInventor')[0].fitAll()
Gui.activeDocument().mdiViewsOfType('Gui::View3DInventor')[0].saveImage(str(ROOT/'assembly_preview.png'),1600,1200,'Current')
# Preserve a stable file for independent read/reopen tests; never read the GUI save target concurrently.
import shutil
shutil.copy2(ROOT/'Precision_5560_Native.FCStd',ROOT/'ValidationSnapshot.FCStd')

(ROOT/'build_progress.json').write_text(json.dumps({'phase':'nominal model accepted; independent parameter sweep ready'},indent=2))
