"""Actual native geometry views of the cable groove and stationary tie anchors."""
from pathlib import Path
import hashlib,json
import FreeCAD as App,FreeCADGui as Gui
import Part
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'revh_cables/Precision_5560_RevH_Cable_Management_C1.FCStd'
OUT=ROOT/'docs/assets'


def run():
    sha=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    doc=next((d for d in App.listDocuments().values() if Path(d.FileName)==SOURCE),None)
    if doc is None:doc=App.openDocument(str(SOURCE))
    parts={o.InstanceKey:o.Shape.copy() for o in doc.Objects if o.TypeId=='App::Link' and hasattr(o,'InstanceKey')}
    untilt=App.Placement(App.Vector(0,67,-84),App.Rotation(App.Vector(1,0,0),45)).multiply(
        App.Placement(App.Vector(0,-70,104),App.Rotation())).inverse()
    local={}
    rendered=[]
    for key in ['06_right_fan_retainer','10_right_fan_tray','04_right_fan_duct']:
        s=parts[key].copy();s.Placement=untilt.multiply(s.Placement);local[key]=s
    def capture(name,selected,direction,crop=None,cover_travel=0,cable=False):
        show=App.newDocument('CableReview')
        for key,shape in selected.items():
            shape=shape.copy()
            if crop is not None:shape=shape.common(crop)
            if shape.isNull() or shape.Volume<1e-6:continue
            if cover_travel and 'fan_retainer' in key:shape.translate(App.Vector(0,cover_travel,0))
            obj=show.addObject('Part::Feature','Display'+key.replace('_',''));obj.Shape=shape
            obj.ViewObject.ShapeColor=(.96,.60,.21) if 'fan_retainer' in key else (.19,.62,.57) if 'fan_tray' in key else (.74,.82,.38) if 'push_pin' in key else (.32,.39,.43) if 'cradle' in key else (.14,.45,.50)
            obj.ViewObject.LineColor=(.1,.16,.18);obj.ViewObject.DisplayMode='Flat Lines'
        if cable:
            obj=show.addObject('Part::Feature','ReferenceCableEnvelope')
            obj.Shape=Part.makeCylinder(2,32,App.Vector(121,138.2,-116.5),App.Vector(1,0,0))
            obj.ViewObject.ShapeColor=(.67,.13,.20);obj.ViewObject.LineColor=(.35,.08,.12)
        show.recompute();view=Gui.activeDocument().activeView();view.setCameraType('Orthographic')
        back=App.Vector(*direction);back.normalize();right=App.Vector(0,0,1).cross(back);right.normalize();up=back.cross(right)
        view.getCameraNode().orientation.setValue(*App.Rotation(right,up,back,'ZXY').Q)
        view.fitAll();cam=view.getCameraNode();cam.height.setValue(cam.height.getValue()*1.22)
        Gui.updateGui();view.saveImage(str(OUT/name),1600,1100,'White');rendered.append(name);App.closeDocument(show.Name)
    capture('revh-cables-installed.png',parts,(1,1,.65))
    capture('revh-cables-tray.png',{'10_right_fan_tray':local['10_right_fan_tray']},(1,1,.9))
    crop=Part.makeBox(42,42,57,App.Vector(110,109,-150))
    capture('revh-cables-groove-open.png',local,(1,-1,.65),crop,22,True)
    capture('revh-cables-groove-closed.png',local,(1,1,.55),crop,0,True)
    coupons={key:doc.getObject(name).Shape.copy() for key,name in [
        ('06_right_fan_retainer','C1CableCoverCoupon'),('10_right_fan_tray','C1CableTrayCoupon'),('04_right_fan_duct','C1CableDuctCoupon')]}
    pins=[]
    for key,s in parts.items():
        if 'right_push_pin' in key:
            s=s.copy();s.Placement=untilt.multiply(s.Placement);pins.append(s)
    pin=max(pins,key=lambda s:s.BoundBox.Center.x)
    pin.translate(App.Vector(0,24,20));coupons['right_push_pin']=pin
    capture('revh-cables-coupon.png',coupons,(1,-1,.65),cover_travel=22,cable=True)
    App.setActiveDocument(doc.Name);Gui.activeDocument().activeView().viewAxonometric();Gui.activeDocument().activeView().fitAll();Gui.updateGui()
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==sha
    images={name:hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in rendered}
    (ROOT/'revh_cables/render-review.json').write_text(json.dumps({'native_sha256':sha,'images':images,
        'source_file_unchanged':True,'reference_cable_diameter_mm':4},indent=2)+'\n')
    App.Console.PrintMessage('H-C1 cable review renders saved; native source unchanged.\n')


if __name__=='__main__':run()
