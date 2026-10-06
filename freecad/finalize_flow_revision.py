from pathlib import Path
import FreeCAD as A
ROOT=Path(__file__).resolve().parent
D=next(d for d in A.listDocuments().values() if d.FileName and Path(d.FileName).resolve()==(ROOT/'Precision_5560_Native.FCStd').resolve())
for name,value in getattr(A,'_flow_review_visibility',{}).items():D.getObject(name).Visibility=value
for name in ['audit_airway_continuity.py','finalize_fit_review.py']:
 p=ROOT/name;exec(compile(p.read_text(encoding='utf-8'),str(p),'exec'),{'__file__':str(p),'__name__':'__main__'})
