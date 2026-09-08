"""Independently check installed retention geometry and export oriented print files."""
from pathlib import Path
import hashlib
import importlib.util
import json
import shutil
import sys
import FreeCAD as App
import Part

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'revh_retention'
SOURCE=OUT/'Precision_5560_RevH_Removable_Retainers.FCStd'
sys.path.insert(0,str(ROOT/'minimalist'))
from export import write_shape, mesh_for, sha


def shifted(s, delta):
    shape=s.copy();shape.translate(App.Vector(*delta));return shape


def oriented(key,shape,center=(128,128)):
    s=shape.copy()
    if 'retainer_keeper' not in key:
        s.rotate(App.Vector(),App.Vector(0,1,0),-90 if 'left' in key else 90)
        s.rotate(App.Vector(),App.Vector(0,0,1),90)
        pose='flat outboard face down; long axis along plate Y'
    else: pose='catch foot down; split tip up'
    b=s.BoundBox
    s.translate(App.Vector(center[0]-(b.XMin+b.XMax)/2,center[1]-(b.YMin+b.YMax)/2,-b.ZMin))
    return s,pose


def main():
    snapshot=ROOT/'tmp/retention/ExportSnapshot.FCStd';shutil.copy2(SOURCE,snapshot)
    print('Open native snapshot',flush=True)
    d=App.openDocument(str(snapshot))
    # Force native recomputation, including the fillets and constrained sketches.
    for obj in d.Objects:
        if hasattr(obj,'Shape'):obj.touch()
    d.recompute()
    print('Native recompute complete',flush=True)
    errors=[o.Name for o in d.Objects if 'Invalid' in o.State or 'Error' in o.State]
    assert not errors,errors
    h={o.InstanceKey:o.Shape.copy() for o in d.getObject('BaselineAssembly').Group if o.TypeId=='App::Link'}
    r={o.InstanceKey:o.Shape.copy() for o in d.getObject('RetentionAssembly').Group if o.TypeId=='App::Link'}
    assert len(h)==14 and len(r)==4
    oldpath=ROOT/'tmp/retention/HValidation.FCStd';shutil.copy2(ROOT/'freecad/Precision_5560_Native.FCStd',oldpath)
    sys.path.insert(0,App.getResourceDir()+'Mod/Assembly')
    old=App.openDocument(str(oldpath))
    oldparts={o.InstanceKey:o.Shape for o in old.getObject('InstalledAssembly').Group if o.TypeId=='App::Link'}
    report={'revision':'H-R1 prototype','native_sha256':sha(SOURCE),'original_native_sha256':sha(ROOT/'freecad/Precision_5560_Native.FCStd'),
            'scope':'CAD geometry and sampled rigid motion; no physical strength, creep, retention-force or fit qualification',
            'unchanged_h_parts':{},'new_parts':{},'clearances':{},'motions':{},'keeper_fit':{
                'square_stem_mm':3.0,'square_socket_mm':3.6,'nominal_clearance_per_side_mm':.3,
                'split_crown_width_mm':3.8,'insertion_deflection_each_finger_mm':.1,
                'head_to_shoulder_endplay_mm':.6,'catch_foot_to_arm_gap_mm':.5}}
    for key,s in h.items():
        diff=s.cut(oldparts[key]).Volume+oldparts[key].cut(s).Volume
        assert diff<.001,(key,diff)
        report['unchanged_h_parts'][key]={'symmetric_difference_mm3':diff,'volume_mm3':s.Volume}
    frozen=json.loads((ROOT/'freecad/frozen_print_arms/manifest.json').read_text())
    for key,row in frozen['parts'].items():
        s=Part.read(str(ROOT/'freecad/frozen_print_arms'/row['file']))
        assert hashlib.sha256((ROOT/'freecad/frozen_print_arms'/row['file']).read_bytes().replace(b'\r\n',b'\n')).hexdigest()==row['sha256']
        diff=s.cut(h[key]).Volume+h[key].cut(s).Volume
        assert diff<.001
        report['unchanged_h_parts'][key]['frozen_print_arm_difference_mm3']=diff
        report['unchanged_h_parts'][key]['frozen_brep_sha256_lf_text']=row['sha256']
    App.closeDocument(old.Name)
    print('All 14 original parts and frozen arms match',flush=True)
    for key,s in r.items():
        assert s.isValid() and len(s.Solids)==1
        report['new_parts'][key]={'valid':True,'solids':1,'volume_mm3':s.Volume,'cad_ASA_g':s.Volume*.00105}
        contacts={}
        for other,p in {**h,**r}.items():
            if other==key:continue
            volume=s.common(p).Volume
            assert volume<.001,(key,other,volume)
            if ('left' in key)==('left' in other):
                contacts[other]={'interference_mm3':volume,'distance_mm':s.distToShape(p)[0]}
        report['clearances'][key]=contacts
    # Original native laptop envelope plus the existing wall-driver cylinders.
    laptop=d.getObject('LaptopEnvelope').Shape
    envelope_report={}
    for key,s in r.items():
        assert s.common(laptop).Volume<.001
        envelope_report[key]={'laptop_clearance_mm':s.distToShape(laptop)[0]}
        for x in [-162,162]:
            for z in [-36,174]:
                driver=Part.makeCylinder(9,80,App.Vector(x,-1,z),App.Vector(0,1,0))
                assert s.common(driver).Volume<.001
    report['laptop_and_existing_wall_driver_clearance']=envelope_report
    print('Four added solids, assembled clearances and driver access pass',flush=True)
    # Fit at rest, free removal when unlocked, and positive catches when locked.
    for side,sign in [('left',-1),('right',1)]:
        find=lambda parts,word:next(s for k,s in parts.items() if side in k and word in k)
        arm,duct,rail=find(h,'cradle'),find(h,'fan_duct'),find(h,'outlet_rail')
        bar,pin=find(r,'side_retainer'),find(r,'retainer_keeper')
        rows={}
        for name,s,other,axis,distances in [
            ('duct_forward_stop',duct,bar,(0,1,0),[0,.3,.5,1,2]),
            ('rail_forward_stop',rail,bar,(0,1,0),[0,.3,.5,1,2]),
            ('bar_forward_window_stop',bar,arm,(0,1,0),[0,.3,.5,1,2]),
            ('locked_bar_outboard_stop',bar.fuse(pin),arm,(sign,0,0),[0,.5,1,2,5])]:
            measured={str(dist):shifted(s,tuple(v*dist for v in axis)).common(other).Volume for dist in distances}
            assert measured['0']<.001
            assert measured[str(distances[-1])]>1,(side,name,measured)
            rows[name]={'travel_mm_to_interference_mm3':measured}
        # Sample the full sideways bar path with the keeper removed.
        for travel in [0,.3,.5,1,2,4,8,12,16,20,25,30]:
            moved=shifted(bar,(sign*travel,0,0))
            for key,s in h.items():assert moved.common(s).Volume<.001,(side,'bar removal',travel,key)
        rows['unlocked_bar_removal']={'axis':'outboard X','sampled_travel_mm':30,'interference_mm3':0,'samples':12}
        # The released crown flexes through the socket. Its insertion/removal
        # interference is intentional; the body must clear all existing parts.
        for travel in [0,.3,.6,1,2,4,6,8,12,16]:
            moved=shifted(pin,(0,0,-travel))
            for key,s in h.items():assert moved.common(s).Volume<.001,(side,'keeper removal',travel,key)
        rows['keeper_removal']={'axis':'downward Z','sampled_travel_mm':16,'existing_part_interference_mm3':0,
                                'requires_split_crown_flex':True,'samples':10}
        # The seated key resists rotation of the long bar in its own plane.
        rotation=[]
        for angle in [-2,-1,-.5,.5,1,2]:
            moved=bar.copy();moved.rotate(App.Vector(sign*180,43,-22),App.Vector(1,0,0),angle)
            rotation.append({'angle_deg':angle,'arm_interference_mm3':moved.common(arm).Volume})
        assert rotation[0]['arm_interference_mm3']>1 and rotation[-1]['arm_interference_mm3']>1
        rows['window_rotation_stops']=rotation
        report['motions'][side]=rows
        print(side,'sampled service and stop motions pass',flush=True)
    # Challenge combined outboard tilt and side clearance. The lower heel
    # bears against the original arm before the wider top stop loses overlap.
    # This finite CAD grid is a screening check, not a proof of all 6-DOF paths.
    arm=h['02_right_cradle'];bar=r['16_right_side_retainer'];pin=r['18_right_retainer_keeper']
    rail=h['08_right_outlet_rail'];tilt=[]
    for angle in [0,.5,1,1.5,2,2.5,3,4]:
        for xmove in [0,.25,.5,.75,1]:
            for float_z in [-.3,0,.3]:
                moved=bar.copy();moved_pin=shifted(pin,(0,0,float_z))
                for s in [moved,moved_pin]:
                    s.rotate(App.Vector(174,43,-27),App.Vector(0,1,0),angle)
                    s.translate(App.Vector(xmove,0,0))
                overlap=moved.common(arm).Volume+moved_pin.common(arm).Volume
                if overlap<.001:
                    stop=moved.common(shifted(rail,(0,2,0))).Volume
                    assert stop>1,('tilt loses rail overlap',angle,xmove,float_z,stop)
                    tilt.append({'outboard_tilt_deg':angle,'translation_x_mm':xmove,'keeper_float_z_mm':float_z,
                                 'rail_stop_overlap_at_2mm_withdrawal_mm3':stop})
    report['outboard_tilt_screen']={'grid_samples':120,'clear_samples':len(tilt),
            'largest_clear_sampled_tilt_deg':max(t['outboard_tilt_deg'] for t in tilt),
            'all_clear_samples_retain_rail_at_2mm_attempted_forward_motion':True,'clear_poses':tilt}
    print('Outboard tilt and keeper endplay grid passes',flush=True)
    report['new_fully_constrained_sketches']=sum(o.TypeId=='Sketcher::SketchObject' and o.FullyConstrained for o in d.getObject('RetentionFeatures').Group)
    report['native_errors']=errors
    printout=OUT/'print';printout.mkdir(exist_ok=True)
    manifest={'revision':'H-R1 prototype','native_sha256':sha(SOURCE),'units':'mm','standard_3mf_contains_slicer_settings':False,'parts':{},'plates':{}}
    for key,s in sorted(r.items()):
        placed,pose=oriented(key,s)
        manifest['parts'][key]=write_shape(printout,key,placed,pose)
        print(key,'STEP / mesh / plate checks pass',flush=True)
    allplaced=[]
    for key,s in sorted(r.items()):
        center=(75 if 'left' in key else 180,128) if 'side_retainer' in key else (128,100 if 'left' in key else 150)
        allplaced.append(oriented(key,s,center)[0])
    # Check part-to-part brim spacing before serializing the combined plate.
    for i,s in enumerate(allplaced):
        for p in allplaced[i+1:]:assert s.distToShape(p)[0]>16
    manifest['plates']['00_four_retainer_parts']=write_shape(printout,'00_four_retainer_parts',Part.makeCompound(allplaced),'all four add-on parts; replaces individual files 15-18',4)
    coupon=d.getObject('R1RightFitCoupon').Shape
    couponparts=[oriented('right_coupon',coupon,(105,128))[0],oriented('18_right_retainer_keeper',r['18_right_retainer_keeper'],(155,128))[0]]
    manifest['plates']['01_right_arm_fit_test']=write_shape(printout,'01_right_arm_fit_test',Part.makeCompound(couponparts),'TEST ONLY: short right-arm key plus keeper; do not install as the complete retainer',2)
    manifest['total_cad_ASA_g']=sum(s.Volume*.00105 for s in r.values())
    (printout/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    meshout=ROOT/'docs/models/retainers';meshout.mkdir(parents=True,exist_ok=True)
    scene={'revision':'H-R1 prototype','native_sha256':sha(SOURCE),'parts':[]}
    for key,s in sorted(r.items()):
        mesh_for(s).write(str(meshout/(key+'.stl')))
        scene['parts'].append({'id':key,'file':key+'.stl','side':'left' if 'left' in key else 'right','type':'bar' if 'side_retainer' in key else 'keeper'})
    (meshout/'manifest.json').write_text(json.dumps(scene,indent=2)+'\n')
    assert sha(SOURCE)==report['native_sha256']
    App.closeDocument(d.Name)
    print('H-R1 verification and print exports PASS',flush=True)


if __name__=='__main__':main()
