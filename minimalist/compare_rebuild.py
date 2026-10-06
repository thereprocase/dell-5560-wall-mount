"""Compare a clean native reconstruction against the delivered 20-part model."""
from pathlib import Path
import sys,json,hashlib
import FreeCAD as A
root=Path(__file__).resolve().parent
sys.path.insert(0,str(root))
from validate import shapes
source=root/'Laptop_Wall_Mount_Minimalist.FCStd'
import shutil
snapshot=root/'scratch/DeliveredCompare.FCStd';shutil.copy2(source,snapshot)
a=A.openDocument(str(snapshot));b=A.openDocument(str(root/'scratch/Rebuilt_M1.FCStd'))
x,y=shapes(a),shapes(b)
report={'source_native_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'parts':{}}
for key in x:
 delta=x[key].cut(y[key]).Volume+y[key].cut(x[key]).Volume
 report['parts'][key]={'symmetric_difference_mm3':delta,'pass':delta<.01}
assert all(v['pass'] for v in report['parts'].values())
A.closeDocument(a.Name);A.closeDocument(b.Name)
(root/'rebuild-shape-comparison.json').write_text(json.dumps(report,indent=2)+'\n')
print('Clean source rebuild matches all 20 delivered solids within 0.01 mm3',flush=True)
