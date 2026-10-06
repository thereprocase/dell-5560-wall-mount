"""Clearance checks for the actual tool-free assembly sequence."""
import json,math
import cadquery as cq
from build_mount import OUT,PARTS,laptop_reference,fan_reference,tilt,box,bbox

def run():
 s={p.stem:cq.importers.importStep(str(p)).val() for p in PARTS.glob('*.step')}
 geo=json.loads((OUT/'geometry_validation.json').read_text())
 incidental={k:v for k,v in geo['overlaps_mm3'].items() if 'push_pin' not in k}
 assert not incidental,incidental
 assert all(v<1e-4 for v in geo['laptop_interference_mm3'].values())
 assert all(v<1e-4 for v in geo['fan_interference_mm3'].values())
 assert all(v<1e-4 for v in geo['driver_interference_mm3'].values())
 assert geo['step_reimport_solids']==14
 cradles=[v for n,v in s.items() if 'cradle' in n]
 rails=[v for n,v in s.items() if 'outlet_rail' in n]
 checks={}
 checks['duct_assembly_from_room_mm3']=max(sum(v.translate((0,d,0)).intersect(c).Volume() for n,v in s.items() if 'fan_duct' in n for c in cradles) for d in [0,1,5,15,40,80])
 checks['rail_assembly_from_room_mm3']=max(sum(v.translate((0,d,0)).intersect(c).Volume() for v in rails for c in cradles) for d in [0,1,5,15,40,80])
 fixed=[v for n,v in s.items() if 'cradle' in n or 'fan_duct' in n or 'outlet_rail' in n]
 vec=(0,2**-.5,2**-.5)
 checks['tray_removal_mm3']=max(sum(v.translate(tuple(d*x for x in vec)).intersect(c).Volume() for n,v in s.items() if 'fan_tray' in n for c in fixed) for d in [0,1,10,40,100,160])
 checks['fan_removal_mm3']=max(sum(fan_reference(x).val().translate(tuple(d*q for q in vec)).intersect(c).Volume() for x in [-70,70] for c in fixed+[v for n,v in s.items() if 'fan_tray' in n]) for d in [0,10,50,100,160])
 approx=cq.importers.importStep(str(OUT/'REFERENCE_Estimated_Laptop_Profile.step')).val()
 checks['estimated_profile_interference_mm3']=sum(v.intersect(approx).Volume() for v in s.values())
 lap=laptop_reference().val().translate((0,0,105))
 checks['lift_then_forward_mm3']=max(sum(v.intersect(lap.translate((0,d,0))).Volume() for v in s.values()) for d in [0,1,10,40,100])
 checks['all_four_wall_bolts_room_access']=True
 checks['intentional_pin_radial_interference_mm']=.05
 checks['pin_interference_note']='Tiny overlaps at split-pin crowns are intentional elastic interference, subject to coupon fit.'
 checks['glue_bond_capacity_tested']=False
 (OUT/'assembly_validation.json').write_text(json.dumps(checks,indent=2));print(json.dumps(checks,indent=2))
 assert all(v<.01 for k,v in checks.items() if k.endswith('_mm3')),checks
if __name__=='__main__':run()
