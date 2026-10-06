"""Small fit samples cut directly from the released native mating geometry."""
from pathlib import Path
import json
import FreeCAD as App
import Part
from build import values
from validate import shapes
from export import export, orient, write_shape, sha

ROOT=Path(__file__).resolve().parent
source=ROOT/'presets/5560/M1.FCStd'
doc=App.openDocument(str(source))
p={k:float(v) for k,v in values(doc).items()}
s=shapes(doc)
x,y,z=p['armOriginX'],p['ladderY'],p['damAttachZ']
tool=Part.makeBox(40,16,37,App.Vector(x-35,y-9,z-6))
parts={
    '01_coupon_right_arm':s['02_right_arm'].common(tool),
    '02_coupon_dam_carriage':s['08_right_dam'].common(tool),
    '03_coupon_right_key':s['12_right_dam_key'],
    '04_coupon_keeper':s['16_right_dam_keeper'],
    '07_coupon_cap_pin':s['18_right_cap_pin_1'],
}
# Capture one complete retainer socket and its mating cap in fan-local axes.
center=App.Vector(x-p['fanOffsetX'],p['fanCenterY'],p['fanCenterZ'])
localtool=Part.makeBox(11,19,13,App.Vector(-p['fanWidth']/2-p['fitClearance']-9,p['fanWidth']/2+p['fitClearance']-11,-p['fanThickness']-p['fanFrameWall']+9.5))
localtool.rotate(App.Vector(),App.Vector(1,0,0),45)
localtool.translate(center)
parts['05_coupon_fan_cage']=s['04_right_fan_cage'].common(localtool)
parts['06_coupon_fan_cap']=s['06_right_fan_cap'].common(localtool)
# Keep the full supporting side rail below the hanger. A short Y/Z crop can
# create artificial floating starts that do not exist in the complete cradle.
hanger_tool=Part.makeBox(15,400,400,App.Vector(x-25,-100,-250))
parts['08_coupon_fan_cage_hanger']=s['04_right_fan_cage'].common(hanger_tool)
out=ROOT/'coupons';out.mkdir(exist_ok=True)
for suffix in ('.stl','.step','.3mf'):
    obsolete=out/('02_coupon_right_key'+suffix)
    if obsolete.exists():obsolete.unlink()
report={'source_native_sha256':sha(source),'parts':{},'purpose':'Fit samples only; not a load test or substitute assembly'}
placed=[]
for i,(key,shape) in enumerate(sorted(parts.items())):
    # The arm sample needs only the flat face orientation; its short coupon
    # does not need the complete arm's diagonal/cutter placement search.
    orientation_key='08_right_dam' if 'dam_carriage' in key else key.replace('_arm','_key')
    center=(107,210) if key=='04_coupon_keeper' else (191,145) if 'hanger' in key else (65+(i%4)*42,85+(i//4)*65)
    printshape,pose=orient(orientation_key,shape,center)
    report['parts'][key]=write_shape(out,key,printshape,pose)
    placed.append(printshape)
report['plate']=write_shape(out,'00_fit_coupon_plate',Part.makeCompound(placed),'8 fit samples; do not also print the individual alternatives',len(placed))
(out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
App.closeDocument(doc.Name)
print('Eight native-derived fit samples and combined plate exported',flush=True)
