"""Reopen the saved archive, keeping exactly one production-model tab."""
import adsk.core as c
import adsk.fusion as f
from pathlib import Path
import json
out=Path('F:/Code/dell-5560-wall-mount/fusion/output/native')
d=f.Design.cast(app.activeProduct)
if not d.attributes.itemByName('Dell5560','assembled'):raise RuntimeError('Wrong document')
path=out/'Precision_5560_RevF_native.f3d'
assert d.exportManager.execute(d.exportManager.createFusionArchiveExportOptions(str(path)))
options=app.importManager.createFusionArchiveImportOptions(str(path))
old=app.activeDocument
old.close(False)
doc=app.importManager.importToNewDocument(options)
if not doc:raise RuntimeError('Could not reopen archive')
d=f.Design.cast(app.activeProduct)
root=d.rootComponent
issues=[{'name':x.name,'message':x.errorOrWarningMessage} for comp in d.allComponents for x in comp.features if int(x.healthState)]
sketches=[s for comp in d.allComponents for s in comp.sketches]
report={'reopened':True,'native_parametric':d.designType==f.DesignTypes.ParametricDesignType,
        'occurrences':root.occurrences.count,'joints':root.asBuiltJoints.count,
        'sketches':len(sketches),'all_fully_constrained':all(s.isFullyConstrained for s in sketches),
        'parameters':d.userParameters.count,'issues':issues}
assert report['occurrences']==14 and report['joints']==13 and report['all_fully_constrained'] and not issues
(out/'archive_reopen.json').write_text(json.dumps(report,indent=2))
result.update(report)
