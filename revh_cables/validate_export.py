"""Check cable capture/service paths, unchanged parts and print exchange files."""
from pathlib import Path
import hashlib
import io
import json
import shutil
import sys
import zipfile
import FreeCAD as App
import Part

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'revh_cables'
SOURCE=OUT/'Precision_5560_RevH_Cable_Management_C1.FCStd'
BASELINE=ROOT/'revh_retention/Precision_5560_RevH_Removable_Retainers.FCStd'
CHANGED=['05_left_fan_retainer','06_right_fan_retainer','09_left_fan_tray','10_right_fan_tray']
sys.path.insert(0,str(ROOT/'minimalist'))
from export import write_shape as export_shape,mesh_for,sha


def write_shape(path,key,shape,pose,expected_solids=1):
    # Preserve already reviewed geometry archives when only ZIP timestamps
    # differ, so unchanged full plates retain their exact slicer-input hashes.
    archive=path/(key+'.3mf')
    old=archive.read_bytes() if archive.exists() else None
    record=export_shape(path,key,shape,pose,expected_solids)
    if old is not None:
        with zipfile.ZipFile(io.BytesIO(old)) as a,zipfile.ZipFile(archive) as b:
            equal=set(a.namelist())==set(b.namelist()) and all(a.read(k)==b.read(k) for k in a.namelist())
        if equal:
            archive.write_bytes(old);record['sha256']['.3mf']=sha(archive)
    return record


def tilt():
    return App.Placement(App.Vector(0,67,-84),App.Rotation(App.Vector(1,0,0),45)).multiply(
        App.Placement(App.Vector(0,-70,104),App.Rotation()))


def shifted(shape,delta):
    s=shape.copy();s.translate(App.Vector(*delta));return s


def placed_local(shape,kind,center=(128,128)):
    s=shape.copy()
    if kind in ['cover','duct_coupon']:s.rotate(App.Vector(),App.Vector(1,0,0),-90)
    b=s.BoundBox
    s.translate(App.Vector(center[0]-(b.XMin+b.XMax)/2,center[1]-(b.YMin+b.YMax)/2,-b.ZMin))
    return s


def main():
    temp=ROOT/'tmp/cables';temp.mkdir(parents=True,exist_ok=True)
    snapshot=temp/'ValidationSnapshot.FCStd';shutil.copy2(SOURCE,snapshot)
    d=App.openDocument(str(snapshot))
    for obj in d.Objects:
        if hasattr(obj,'Shape'):obj.touch()
    d.recompute()
    errors=[o.Name for o in d.Objects if 'Invalid' in o.State or 'Error' in o.State]
    assert not errors,errors
    sketches=[o for o in d.getObject('CableFeatures').Group if o.TypeId=='Sketcher::SketchObject']
    assert all(o.FullyConstrained for o in sketches)
    parts={o.InstanceKey:o.Shape.copy() for o in d.Objects if o.TypeId=='App::Link' and hasattr(o,'InstanceKey')}
    old=App.openDocument(str(BASELINE))
    before={o.InstanceKey:o.Shape.copy() for o in old.Objects if o.TypeId=='App::Link' and hasattr(o,'InstanceKey')}
    assert set(parts)==set(before) and len(parts)==18
    report={'revision':'H-C1 prototype','native_sha256':sha(SOURCE),'baseline_native_sha256':sha(BASELINE),
            'native_errors':errors,'new_fully_constrained_sketches':len(sketches),
            'scope':'Native geometric support and sampled motions only; physical fit, cable abrasion and tie-lug strength untested',
            'unchanged_parts':{},'replaced_parts':{},'clearances':{},'cable_service':{},'tray_removal':{}}
    for key,s in parts.items():
        assert s.isValid() and len(s.Solids)==1,key
        difference=s.cut(before[key]).Volume+before[key].cut(s).Volume
        record={'difference_mm3':difference,'volume_mm3':s.Volume}
        if key in CHANGED:
            assert difference>1,key
            report['replaced_parts'][key]=record
        else:
            assert difference<.001,(key,difference)
            report['unchanged_parts'][key]=record
    print('Four replacement solids; fourteen others unchanged',flush=True)
    App.closeDocument(old.Name)
    for key in CHANGED:
        s=parts[key];contacts={}
        for other,p in parts.items():
            if key==other:continue
            volume=s.common(p).Volume if s.BoundBox.intersect(p.BoundBox) else 0
            assert volume<.001,(key,other,volume)
            if ('left' in key)==('left' in other):contacts[other]={'overlap_mm3':volume,'gap_mm':s.distToShape(p)[0]}
        assert s.common(d.getObject('LaptopEnvelope').Shape).Volume<.001
        report['clearances'][key]=contacts
    print('Installed cover/tray clearances and laptop envelope pass',flush=True)
    local={}
    for key,s in parts.items():
        s=s.copy();s.Placement=tilt().inverse().multiply(s.Placement);local[key]=s
    for side,sign in [('right',1),('left',-1)]:
        find=lambda term:next(k for k in local if side in k and term in k)
        cap_key,tray_key,duct_key=find('fan_retainer'),find('fan_tray'),find('fan_duct')
        cap,tray,duct=local[cap_key],local[tray_key],local[duct_key]
        cable=Part.makeCylinder(2,26,App.Vector(sign*122,138.2,-116.5),App.Vector(sign,0,0))
        gaps={}
        for key,s in local.items():
            overlap=cable.common(s).Volume if cable.BoundBox.intersect(s.BoundBox) else 0
            assert overlap<.001,(side,'cable',key,overlap)
            if key in [cap_key,tray_key,duct_key]:gaps[key]=s.distToShape(cable)[0]
        assert min(gaps.values())>=.499
        cap_rows=[]
        for travel in [0,.3,1,2,4,8,12,20,30]:
            moved=shifted(cap,(0,travel,0))
            assert moved.common(cable).Volume<.001,(side,'cover crosses stationary cable',travel)
            for key,s in local.items():
                if key==cap_key or 'push_pin' in key:continue
                overlap=moved.common(s).Volume if moved.BoundBox.intersect(s.BoundBox) else 0
                assert overlap<.001,(side,'cover removal',travel,key,overlap)
            cap_rows.append(travel)
        # A short cable cross section is bounded on all four sides in service.
        # The narrow normal mating clearance is not treated as a fluid seal.
        section=Part.makeCylinder(2,1,App.Vector(sign*138,138.2,-116.5),App.Vector(sign,0,0))
        attempts={}
        for name,delta in [('rear',(0,-2,0)),('front',(0,2,0)),('up',(0,0,3)),('down',(0,0,-3))]:
            moved=shifted(section,delta)
            overlap=moved.common(cap).Volume+moved.common(tray).Volume
            assert overlap>.1,(side,'unbounded tunnel',name,overlap)
            attempts[name]=overlap
        # With the cover alone, the wire can leave through its open mating face.
        for travel in [0,1,2,4,6,8,12]:
            moved=shifted(section,(0,-travel,0))
            assert moved.common(cap).Volume<.001,(side,'not an open groove',travel)
        straps=[]
        for y in [119,51]:
            strap=Part.makeBox(1.5,3.6,25,App.Vector(143.25 if sign==1 else -144.75,y-1.8,-150))
            for key,s in local.items():
                overlap=strap.common(s).Volume if strap.BoundBox.intersect(s.BoundBox) else 0
                assert overlap<.001,(side,'tie tail access',y,key,overlap)
            straps.append({'local_y_mm':y,'tail_cross_section_mm':[1.5,3.6],'entry_and_exit_clear':True})
        report['cable_service'][side]={'checked_round_cable_diameter_mm':4,'installed_gaps_mm':gaps,
            'cover_removed_with_wire_stationary':True,'cover_local_y_travel_samples_mm':cap_rows,
            'closed_tunnel_stop_overlaps_mm3':attempts,'wire_lays_in_from_open_mating_face':True,'tie_slots':straps}
        tray_rows=[]
        for travel in [0,.3,1,5,10,20,40,80,120,150]:
            moved=shifted(tray,(0,travel,0))
            for key,s in local.items():
                if key in [cap_key,tray_key] or 'push_pin' in key:continue
                overlap=moved.common(s).Volume if moved.BoundBox.intersect(s.BoundBox) else 0
                assert overlap<.001,(side,'tray removal',travel,key,overlap)
            tray_rows.append(travel)
        fan=Part.makeBox(120,120,27,App.Vector(10 if sign==1 else -130,10,-138))
        # New geometry must remain outside the conservative fan frame box.
        for key in [cap_key,tray_key]:
            assert local[key].common(fan).Volume<.001,(side,'fan envelope',key)
        report['tray_removal'][side]={'local_y_travel_samples_mm':tray_rows,'cover_and_pins_removed':True,
                                   'fan_box_mm':[120,120,27],'interference_mm3':0}
        print(side,'cable capture, open-edge lay-in, tie access and removal paths pass',flush=True)
    printout=OUT/'print';printout.mkdir(exist_ok=True)
    manifest={'revision':'H-C1 prototype','native_sha256':sha(SOURCE),'units':'mm',
              'standard_3mf_contains_slicer_settings':False,'parts':{},'plates':{}}
    for key in CHANGED:
        kind='cover' if 'retainer' in key else 'tray'
        s=placed_local(local[key],kind)
        pose='broad front face down; edge groove opens upward' if kind=='cover' else 'grille down; tie-lug undersides rise at 45 degrees'
        manifest['parts'][key]=write_shape(printout,key,s,pose)
        print(key,'STEP/mesh/bed checks pass',flush=True)
    covers=[placed_local(local[key],'cover',(128,y)) for key,y in [('05_left_fan_retainer',78),('06_right_fan_retainer',172)]]
    assert covers[0].distToShape(covers[1])[0]>16
    manifest['plates']['20_both_cable_covers']=write_shape(printout,'20_both_cable_covers',Part.makeCompound(covers),
        'both covers together; replaces individual cover files 05 and 06',2)
    coupon=[]
    for name,objname,kind,center in [
        ('cover','C1CableCoverCoupon','cover',(65,115)),
        ('tray','C1CableTrayCoupon','tray',(125,115)),
        ('duct','C1CableDuctCoupon','duct_coupon',(185,115)),
        ('pin','PinBody','pin',(125,175))]:
        s=placed_local(d.getObject(objname).Shape,kind,center)
        assert s.isValid() and len(s.Solids)==1,name
        coupon.append(s)
    for i,s in enumerate(coupon):
        for other in coupon[i+1:]:assert s.distToShape(other)[0]>16
    manifest['plates']['00_cable_fit_coupon']=write_shape(printout,'00_cable_fit_coupon',Part.makeCompound(coupon),
        'TEST ONLY: duct coupon front mating face down; cover/tray/pin in full-part print directions',4)
    manifest['total_cad_ASA_g']=sum(parts[k].Volume*.00105 for k in CHANGED)
    manifest['added_cad_ASA_g']=sum((parts[k].Volume-before[k].Volume)*.00105 for k in CHANGED)
    (printout/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    sceneout=ROOT/'docs/models/cables';sceneout.mkdir(parents=True,exist_ok=True)
    scene={'revision':'H-C1 prototype','native_sha256':sha(SOURCE),'parts':[]}
    for key in CHANGED:
        mesh_for(parts[key]).write(str(sceneout/(key+'.stl')))
        scene['parts'].append({'id':key,'file':key+'.stl','side':'left' if 'left' in key else 'right',
                               'type':'cover' if 'retainer' in key else 'tray'})
    (sceneout/'manifest.json').write_text(json.dumps(scene,indent=2)+'\n')
    assert sha(SOURCE)==report['native_sha256']
    assert sha(BASELINE)==report['baseline_native_sha256']
    App.closeDocument(d.Name)
    print('H-C1 validation and exports PASS',flush=True)


if __name__=='__main__':main()
