"""Reopen, perturb a real native parameter, restore, and add a native fit coupon."""
from pathlib import Path
import json
import FreeCAD as App, Part, MeshPart
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'results'
doc=App.openDocument(str(OUT/'Fanless_Curved.FCStd'))
body=doc.getObject('FinishedBracket');sheet=doc.getObject('Parameters');v=body.Shape.Volume
for row in [5,6,7,8,15,16,17,18,19]:sheet.set('C'+str(row),'Reference only; edit geometry recipe')
sheet.set('C4','Tool offsets only; pad outline in recipe')
sheet.set('B9','7.4 mm');doc.recompute();changed=body.Shape.Volume
assert body.Shape.isValid() and changed<v
sheet.set('B9','7 mm');doc.recompute()
assert abs(body.Shape.Volume-v)<1e-5
for name in ['FitCoupon','CouponClip']:
    if doc.getObject(name):doc.removeObject(name)
clip=doc.addObject('Part::Box','CouponClip');clip.Length=80;clip.Width=42;clip.Height=26;clip.Placement.Base=App.Vector(-1,-2,-1)
coupon=doc.addObject('Part::Common','FitCoupon');coupon.Base=body;coupon.Tool=clip;coupon.Label='Fit coupon — lower seat and wall fastener';doc.recompute()
assert coupon.Shape.isValid() and len(coupon.Shape.Solids)==1
for o in [clip,coupon]:o.Visibility=False
body.Visibility=True
doc.save()
coupon.Shape.exportStep(str(OUT/'fit_coupon.step'))
MeshPart.meshFromShape(Shape=coupon.Shape,LinearDeflection=.06,AngularDeflection=.12,Relative=False).write(str(OUT/'fit_coupon.stl'))
r={'reopened_valid':body.Shape.isValid(),'nominal_volume_mm3':v,'hole_7_4mm_volume_mm3':changed,'nominal_restored':abs(body.Shape.Volume-v)<1e-5,'coupon_valid':coupon.Shape.isValid(),'coupon_volume_mm3':coupon.Shape.Volume}
(OUT/'reopen_validation.json').write_text(json.dumps(r,indent=2)+'\n');print(r)
