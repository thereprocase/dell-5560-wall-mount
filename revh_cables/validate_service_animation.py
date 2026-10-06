"""Check the viewer's pin parking and complete cover withdrawal poses."""
from pathlib import Path
import hashlib,json,sys
import FreeCAD as App
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'revh_cables';SOURCE=OUT/'Precision_5560_RevH_Cable_Management_C1.FCStd'
sys.path.insert(0,str(OUT))
from validate_export import tilt,shifted

def main():
    digest=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    d=App.openDocument(str(SOURCE))
    local={}
    for o in d.Objects:
        if o.TypeId!='App::Link' or not hasattr(o,'InstanceKey'):continue
        s=o.Shape.copy();s.Placement=tilt().inverse().multiply(s.Placement);local[o.InstanceKey]=s
    pin_keys=[k for k in local if 'push_pin' in k]
    cover_keys=[k for k in local if 'fan_retainer' in k]
    assert len(pin_keys)==4 and len(cover_keys)==2
    parked={k:shifted(local[k],(0,24,20)) for k in pin_keys}
    count=0
    for key in pin_keys:
        for up in [0,5,10,15,20]:
            moved=shifted(local[key],(0,24,up))
            for other,s in local.items():
                if other==key:continue
                if moved.BoundBox.intersect(s.BoundBox):
                    assert moved.common(s).Volume<.001,('pin parking',key,up,other)
                count+=1
    for travel in [0,1,5,10,15,20,25,30,35]:
        moved_covers={k:shifted(local[k],(0,travel,0)) for k in cover_keys}
        for key,moved in moved_covers.items():
            for other,s in {**local,**parked,**moved_covers}.items():
                if other==key:continue
                if moved.BoundBox.intersect(s.BoundBox):
                    assert moved.common(s).Volume<.001,('cover withdrawal',key,travel,other)
                count+=1
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==digest
    (OUT/'service-animation-review.json').write_text(json.dumps({'native_sha256':digest,'pass':True,
        'pin_axial_withdrawal_mm':24,'pin_parking_local_z_samples_mm':[0,5,10,15,20],
        'cover_local_y_samples_mm':[0,1,5,10,15,20,25,30,35],'pair_checks':count,
        'scope':'Sampled rigid poses after original split pins clear the sockets; split-crown flex and continuous physical handling are not simulated.'},indent=2)+'\n')
    App.closeDocument(d.Name)
    print('Pin parking and complete cover animation poses PASS',flush=True)

if __name__=='__main__':main()
