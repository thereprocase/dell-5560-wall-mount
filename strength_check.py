"""Revision F hand calculation, not FEA or a certified load rating.
All geometry is mm, forces N, stresses MPa. Regenerates the check note + JSON.
"""
from pathlib import Path
import json, math
import numpy as np

OUT=Path(__file__).resolve().parent
G=9.81; FACTOR=3.; MASS_LAPTOP=2.5; MASS_TOTAL=6.; MASS_FAN_MODULE=1.
PULL=50.; E=1000.; LIMIT=5.; SHEAR_LIMIT=2.; K=1.5

def run():
    geo=json.loads((OUT/'geometry_validation.json').read_text())
    assert geo['revision']=='F'
    results={}
    def result(name,stress,**extra):
        results[name]={'stress_MPa':stress,'screen_limit_MPa':LIMIT,'margin_to_screen_limit':LIMIT/stress,**extra}
    # Net section properties include every designed void and asymmetry.
    profiles=json.loads((OUT/'section_properties.json').read_text())
    F=MASS_LAPTOP*G*FACTOR/2
    R=PULL*230.3/(2*88.)
    totalW=MASS_TOTAL*G*FACTOR
    Tgravity=totalW*75/(2*210)
    Tpull=(PULL/2)*(232.3+36)/210
    T=Tgravity+Tpull
    for name,key,force,end in [('shelf_3g','shelf',F,64),('tines_50N_hinge_pull','tine',R,90),('rear_rail_combined','rear',T,174)]:
        v=profiles[key]; z=np.array([p['station_mm'] for p in v])
        S=np.array([p['effective_section_modulus_mm3'] for p in v])*.9
        I=np.array([p['effective_inertia_mm4'] for p in v])*.9
        stress=K*force*(end-z)/S
        result(name,float(stress.max()),force_N=force,maximum_at_station_mm=float(z[stress.argmax()]),
               sampled_span_deflection_mm=float(np.trapezoid(force*(end-z)**2/(E*I),z)),
               method='CAD net sections; unsymmetric bending; 10% section allowance')
    # Unreinforced tail above the spine: use conservative 20 mm free length.
    result('rear_rail_upper_tail',K*T*20/(44*10**2/6))
    # Two 8 x 40 mm tenons, 21 mm apart, carry a 1 kg fan module at 3g.
    D=MASS_FAN_MODULE*G*FACTOR;ex=91.;ey=65.
    key_vertical=D/2+D*ex/21
    result('duct_key_lower_shoulder_bearing',key_vertical/(8*12.6),force_N=key_vertical)
    shear=K*key_vertical/(8*40)
    results['duct_key_root_shear']={'stress_MPa':shear,'screen_limit_MPa':SHEAR_LIMIT,'margin_to_screen_limit':SHEAR_LIMIT/shear}
    # Saddle root: retain 10 mm thickness; use only 40 mm net height.
    result('duct_saddle_root_bending',K*D*ex/(10*40**2/6))
    ledge=K*6*(.25*G*FACTOR/2)*10/(20*7**2)
    result('fan_support_ledge',ledge)
    rail_key_force=.4*G*FACTOR/2+.4*G*FACTOR*100/25
    result('rail_key_lower_shoulder_bearing',rail_key_force/(9*12.6))
    # Printed pin: only half the 4 mm shaft section credited because of split.
    pin_demand=.5*G*FACTOR/2
    pin_shear=pin_demand/(.5*math.pi*4**2/4)
    results['split_pin_shear']={'stress_MPa':pin_shear,'screen_limit_MPa':SHEAR_LIMIT,'margin_to_screen_limit':SHEAR_LIMIT/pin_shear}
    # Fan-tray dovetails: 0.5 kg tray/fan allowance, only 20 mm of each rail credited.
    tray_load=.5*G*FACTOR
    result('tray_dovetail_bearing',tray_load/(2*20*1.5))
    results['tray_dovetail_root_shear']={'stress_MPa':tray_load/(2*20*3),
        'screen_limit_MPa':SHEAR_LIMIT,'margin_to_screen_limit':SHEAR_LIMIT/(tray_load/(2*20*3))}
    # Wall screw bearing; conservatively only two screws carry vertical shear.
    wall_shear=math.hypot(totalW/2,D*ex/210)
    result('wall_hole_bearing',wall_shear/(7*10))
    washer_shear=T/(math.pi*16*10)
    results['wall_washer_punching']={'stress_MPa':washer_shear,'screen_limit_MPa':SHEAR_LIMIT,
        'margin_to_screen_limit':SHEAR_LIMIT/washer_shear}
    # Demand only; unknown anchor, wall material, and insert pullout are not rated.
    fasteners={'upper_wall_anchor_tension_N':T,'conservative_wall_anchor_shear_N':wall_shear,
               'duct_joint_outward_couple_force_N':D*ey/40,
               'duct_key_peak_vertical_reaction_N':key_vertical,
               'printed_pin_retention_demand_N':pin_demand,
               'CA_bond_strength_qualified':False,
               'CA_note':'Fixed joints require a qualified adhesive bond for outward retention. Shoulder bearing does not establish glue pullout strength.'}
    volume=sum(p['volume_cm3'] for p in geo['parts'].values())
    estimated_total=MASS_LAPTOP+volume*1.07/1000+.5+.15
    assert estimated_total<=MASS_TOTAL,'total mass allowance too low'
    assert all(v['margin_to_screen_limit']>=1 for v in results.values()),results
    data={'revision':'F','method':'Hand beam, bearing, bolt-group and anchor-demand screening; no FEA',
          'assumptions':{'laptop_mass_kg':MASS_LAPTOP,'total_installed_mass_kg':MASS_TOTAL,
                         'fan_module_mass_kg_each':MASS_FAN_MODULE,'gravity_multiplier':FACTOR,
                         'outward_pull_at_hinge_N':PULL,'normal_stress_screen_MPa':LIMIT,
                         'shear_stress_screen_MPa':SHEAR_LIMIT,'effective_modulus_MPa':E,
                         'local_stress_multiplier':K,'critical_print_sections':'100% infill, sound fusion; cradle printed on side'},
          'estimated_solid_print_assembly_mass_kg':estimated_total,'components':results,
          'fastener_demands':fasteners,'smallest_screen_margin':min(v['margin_to_screen_limit'] for v in results.values()),
          'status':'Meets stated analytical screen; conditional on print quality and the stated model. Physical proof pending.'}
    (OUT/'strength_check.json').write_text(json.dumps(data,indent=2))
    rows='\n'.join(f'| {k.replace("_"," ")} | {v["stress_MPa"]:.2f} | {v["screen_limit_MPa"]:.1f} | {v["margin_to_screen_limit"]:.2f} |' for k,v in results.items())
    note=f"""# Revision F — limited structural screen

The printed sections meet the stated bending, bearing and shear screen.
Minimum ratio to an assumed stress limit: **{data['smallest_screen_margin']:.2f}**.
The CA bonds and printed-pin pullout have not been qualified; this is not a
complete assembly load rating or FEA.

## Assumptions and method

2.5 kg laptop; 6 kg installed assembly; 1 kg per fan module; 3× gravity;
50 N outward hinge pull. Normal/bearing limit 5 MPa; shear limit 2 MPa;
effective modulus 1,000 MPa; local multiplier 1.5. These are chosen screening
values, not measured warm ASA strengths. Print on the supplied faces with
100% infill in the remaining solid sections. Designed cavities remain empty.

The exported cradle geometry supplies net section properties every 0.5 mm,
including hollow sections and unsymmetric bending. A 10% section allowance
remains. The rear-section extraction ignores added cheek stiffness. The check
does not resolve torsion, buckling, fatigue, impact or long-term creep.

The duct uses two 8 × 40 mm keys with 12.6 mm engagement, 21 mm apart. Their
lower shoulders carry vertical load and the moment from the sideways fan
offset. The saddle retains a 10 mm root with at least 40 mm net height. The
rail keys are 9 mm wide, 25 mm apart. Their sloped leading faces print without
unsupported ledges. The four split pins retain fan caps and carry no laptop load.

| Case | Stress MPa | Assumed limit MPa | Ratio |
|---|---:|---:|---:|
{rows}

## Joint demands that still need physical qualification

- Each duct: {D*ey/40:.1f} N outward couple demand for the stated 3g fan-module case.
  CA locks the keyed lap against withdrawal. The plastic shoulder calculation
  establishes neither adhesive peel resistance nor warm bond durability.
- Each printed pin: {pin_demand:.1f} N retention demand. The shear check passes;
  frictional pullout, repeated use and creep remain untested. Test the coupon.
- Each upper wall anchor: {T:.1f} N tension; conservative carrying-anchor shear
  {wall_shear:.1f} N. Select toggle bolts for the actual wall and those loads.

Four Ø7 mm wall holes remain at X=±162, Z=−36/+174 mm. All four bolt axes remain
normal to the wall, with clear Ø16 mm room-side tool corridors. No other metal
fasteners or heat-set inserts are required.

Estimated installed mass, including conservative laptop/fan/hardware allowances:
{estimated_total:.2f} kg. No service temperature or physical load rating is claimed.

Regenerate with build_mount.py, section_properties.py, then strength_check.py.
"""
    (OUT/'Strength_and_Installation_Check.md').write_text(note)
    print(json.dumps({'revision':'F','minimum_screen_ratio':data['smallest_screen_margin'],'components':results},indent=2))

if __name__=='__main__':run()
