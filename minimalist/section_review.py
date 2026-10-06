"""Report section stress demand under explicit screening loads; no load rating."""
from pathlib import Path
import json
import FreeCAD as App
import Part
from build import values
from validate import shapes

ROOT=Path(__file__).resolve().parent
reports={}
for path in sorted((ROOT/'presets').glob('*/M1.FCStd')):
    doc=App.openDocument(str(path))
    p={k:float(v) for k,v in values(doc).items()}
    arm=shapes(doc)['02_right_arm']
    force=3*9.81*2/2
    lever=p['wallGap']+p['laptopThickness']/2
    rows=[]
    # Each upright slice is treated as carrying the full per-arm force and
    # moment. This gross-section calculation omits local notch concentration,
    # creep, layer adhesion, fastener bearing, and uneven installation loads.
    for z in [1,12,26,47.2,50,52.8,74,98,122,146,170]:
        thick=.02
        slab=arm.common(Part.makeBox(50,100,thick,App.Vector(p['armOriginX']-40,-1,z-thick/2)))
        area=slab.Volume/thick
        center=sum(s.CenterOfMass.y*s.Volume for s in slab.Solids)/slab.Volume
        cz=sum(s.CenterOfMass.z*s.Volume for s in slab.Solids)/slab.Volume
        inertia=sum(s.MatrixOfInertia.A11+s.Volume*((s.CenterOfMass.y-center)**2+(s.CenterOfMass.z-cz)**2) for s in slab.Solids)/thick
        c=max(center-slab.BoundBox.YMin,slab.BoundBox.YMax-center)
        assert area>0 and inertia>0
        rows.append({'z_mm':z,'net_area_mm2':area,'Ixx_mm4':inertia,'extreme_fiber_mm':c,
                     'nominal_axial_plus_bending_MPa':force/area+force*lever*c/inertia})
    separation=p['armHeight']-34
    reports[path.parent.name]={'assumed_laptop_mass_kg':3,'vertical_acceleration_factor':2,
         'load_split':'equal between two arms','force_per_arm_N':force,'wall_to_load_mm':lever,
         'moment_per_arm_Nmm':force*lever,'anchor_center_spacing_mm':separation,
         'ideal_anchor_pair_tension_N':force*lever/separation,
         'upright_sections':rows,'peak_nominal_demand_MPa':max(r['nominal_axial_plus_bending_MPa'] for r in rows),
         'load_rating_established':False,
         'limits':'Beam screening demand only. No ASA allowable, creep duration, temperature, print anisotropy, stress concentration, shelf/fastener FEA, anchor strength or physical qualification was established.'}
    App.closeDocument(doc.Name)
(ROOT/'section-review.json').write_text(json.dumps(reports,indent=2)+'\n')
print({k:round(v['peak_nominal_demand_MPa'],3) for k,v in reports.items()},flush=True)
