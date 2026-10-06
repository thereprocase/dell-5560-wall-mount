"""Exercise actual Fusion regeneration and restore every nominal expression."""
import adsk.fusion as f
from pathlib import Path
import json
import traceback
d=None
for doc in app.documents:
    candidate=f.Design.cast(doc.products.itemByProductType('DesignProductType'))
    if candidate and candidate.attributes.itemByName('Dell5560','nativePort'):
        d=candidate;doc.activate();break
if not d:raise RuntimeError('Native model not open')

def audit():
    bodies={};issues=[];sketch_count=0
    for comp in d.allComponents:
        for feature in comp.features:
            if int(feature.healthState):issues.append({'feature':feature.name,'health':int(feature.healthState),'message':feature.errorOrWarningMessage})
        for sketch in comp.sketches:
            sketch_count+=1
            if not sketch.isFullyConstrained:issues.append({'sketch':sketch.name,'issue':'underconstrained'})
        for body in comp.bRepBodies:
            bodies[comp.name]=body.getPhysicalProperties(f.CalculationAccuracy.VeryHighCalculationAccuracy).volume*1000
    return {'volumes_mm3':bodies,'issues':issues,'sketch_count':sketch_count}

nominal=audit();checks=[]
tests=request.get('tests',[
    ['outletGap','8 mm'],['outletGap','16 mm'],
    ['pinHeadRadius','4.5 mm'],['pinSplitWidth','1.2 mm'],['pinSplitRoot','4.5 mm'],
    ['keyClearance','0.35 mm'],['TRAY_tray_height','38 mm'],
    ['ductSkin','2.2 mm'],['CRADLE_tine_height','96 mm']])
for name,expression in tests:
    p=d.userParameters.itemByName(name)
    entry={'parameter':name,'test_expression':expression}
    if not p:
        entry.update(passed=False,error='Missing parameter');checks.append(entry);continue
    original=p.expression
    try:
        p.expression=expression
        d.computeAll()
        state=audit();entry.update(state)
        changed=[n for n,v in state['volumes_mm3'].items() if abs(v-nominal['volumes_mm3'].get(n,v))>1e-5]
        entry.update(changed_components=changed,passed=not state['issues'] and bool(changed))
    except Exception:
        entry.update(passed=False,error=traceback.format_exc())
    finally:
        p.expression=original;d.computeAll()
    checks.append(entry)
restored=audit()
restoration=max([abs(v-nominal['volumes_mm3'][n]) for n,v in restored['volumes_mm3'].items()]+[0])
report={'nominal':nominal,'checks':checks,'restored':restored,'max_restore_volume_error_mm3':restoration,
        'passed':not nominal['issues'] and all(e['passed'] for e in checks) and not restored['issues'] and restoration<1e-4}
out=Path('F:/Code/dell-5560-wall-mount/fusion/output/native')
(out/request.get('report','parameter_checks.json')).write_text(json.dumps(report,indent=2))
result.update(passed=report['passed'],checks=[{k:e[k] for k in ('parameter','test_expression','passed')} for e in checks],restoration_error=restoration)
d.activateRootComponent();app.activeViewport.fit()
