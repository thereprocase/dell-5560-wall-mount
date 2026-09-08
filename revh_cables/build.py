"""Add stock native cable features to a Save As of the preserved H-R1 model.

The four replacement prints are the two fan covers and the two fan trays.
All arm, duct, rail and H-R1 retention geometry stays unchanged.
"""
from pathlib import Path
import hashlib
import json
import shutil
import sys
import FreeCAD as App
import Part

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'revh_cables'
SOURCE=ROOT/'revh_retention/Precision_5560_RevH_Removable_Retainers.FCStd'
TARGET=OUT/'Precision_5560_RevH_Cable_Management_C1.FCStd'
sys.path.insert(0,str(ROOT/'minimalist'))
from native import Native


class CableNative(Native):
    def obj(self,kind,name,label):
        obj=super().obj(kind,'C1'+name,label)
        obj.DesignFamily='Revision H cable management C1'
        return obj

    def round_axis(self,name,source,radius,axis):
        self.doc.recompute()
        indices=[]
        for i,edge in enumerate(source.Shape.Edges,1):
            if len(edge.Vertexes)==2 and isinstance(edge.Curve,Part.Line):
                delta=edge.Vertexes[1].Point-edge.Vertexes[0].Point
                if abs(abs(getattr(delta,axis))-edge.Length)<1e-7:indices.append(i)
        assert indices,(name,axis)
        obj=self.obj('Part::Fillet',name,name)
        obj.Base=source;obj.Edges=[(i,radius,radius) for i in indices]
        source.Visibility=obj.Visibility=False
        self.doc.recompute()
        assert obj.Shape.isValid() and len(obj.Shape.Solids)==1,name
        return obj

    def common(self,name,source,tool):
        obj=self.obj('Part::Common',name,name)
        obj.Base=source;obj.Tool=tool;obj.Refine=True
        source.Visibility=tool.Visibility=obj.Visibility=False
        return obj


def fan_placement():
    return App.Placement(App.Vector(0,67,-84),App.Rotation(App.Vector(1,0,0),45)).multiply(
        App.Placement(App.Vector(0,-70,104),App.Rotation()))


def run():
    OUT.mkdir(exist_ok=True)
    source_sha=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    assert source_sha==json.loads((ROOT/'revh_retention/release-report.json').read_text())['native_sha256']
    snapshot=ROOT/'tmp/cables/H_R1_Source.FCStd'
    snapshot.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(SOURCE,snapshot)
    for doc in list(App.listDocuments().values()):
        if Path(doc.FileName)==TARGET:App.closeDocument(doc.Name)
    doc=App.openDocument(str(snapshot));doc.saveAs(str(TARGET));App.setActiveDocument(doc.Name)
    doc.Label='Precision 5560 / Rev H-C1 cable management prototype'
    links={o.InstanceKey:o for o in doc.Objects if o.TypeId=='App::Link' and hasattr(o,'InstanceKey')}
    assert len(links)==18
    before={k:o.Shape.copy() for k,o in links.items()}
    group=doc.addObject('App::DocumentObjectGroup','CableFeatures')
    group.Label='H-C1 / edge cable groove and external tie lugs'
    n=CableNative(doc,group)
    tilt=fan_placement();untilt=tilt.inverse()
    cap_source=links['06_right_fan_retainer'].getLinkedObject()
    tray_source=links['10_right_fan_tray'].getLinkedObject()
    for key,obj in [('06_right_fan_retainer',cap_source),('10_right_fan_tray',tray_source)]:
        assert before[key].cut(obj.Shape).Volume+obj.Shape.cut(before[key]).Volume<.001
    cap=n.move('OriginalCapLocal',cap_source,tuple(untilt.Base),untilt.Rotation)
    tray=n.move('OriginalTrayLocal',tray_source,tuple(untilt.Base),untilt.Rotation)
    # Close the previous connector-trapping hole with the original face skin.
    # The added pad is flush to the front face; its back overlaps that skin.
    patch=n.box('OldCableHoleFacePatch',116,128,141.3,144,-116,-105)
    cap=n.fuse('CapClosedFormerHole',[cap,patch])
    # Cut through the OUTBOARD edge and open REAR mating face. The stationary
    # tray closes the rear of the groove when the cover is installed.
    groove=n.box('CableGrooveBlank',122,142,130,140.7,-120,-113)
    groove=n.round_axis('CableGrooveRoundedFloor',groove,1.2,'x')
    cap=n.cut('CapWithLayInCableGroove',cap,groove)
    # Two external anchors on the stationary tray, clear of the fan envelope.
    # A 45-degree underside grows each lug from the existing grille-down base.
    lugs=[]
    for name,y in [('Front',119),('Rear',51)]:
        profile=[(137,-146),(140,-146),(148,-138),(148,-129),(137,-129)]
        lug=n.prism(name+'TieLugBlank',profile,'XZ',(0,y+6,0),12)
        # Parallel-to-Z corners of the thick upper pad receive modest rounds;
        # full profile rounds would alter the precisely controlled print slope.
        slot=n.box(name+'TieSlotBlank',142,146,y-2.75,y+2.75,-148,-127)
        slot=n.round_axis(name+'TieSlotRounded',slot,.8,'z')
        lug=n.cut(name+'TieLug',lug,slot)
        lugs.append(lug)
    tray=n.fuse('TrayWithCableTieLugs',[tray]+lugs)
    right_cap=n.move('RightCableCover',cap,tuple(tilt.Base),tilt.Rotation)
    left_cap=n.mirror('LeftCableCover',right_cap)
    right_tray=n.move('RightCableTray',tray,tuple(tilt.Base),tilt.Rotation)
    left_tray=n.mirror('LeftCableTray',right_tray)
    mapping={'05_left_fan_retainer':left_cap,'06_right_fan_retainer':right_cap,
             '09_left_fan_tray':left_tray,'10_right_fan_tray':right_tray}
    doc.recompute()
    for key,source in mapping.items():
        source.addProperty('App::PropertyString','PartKey','Identity');source.PartKey=key
        source.Label=key.replace('_',' ')+' / H-C1 source'
        link=links[key];link.setLink(source);link.LinkTransform=True;link.LinkPlacement=App.Placement()
        link.Label=key.replace('_',' ')+' / H-C1 cable routing'
        if App.GuiUp:
            source.ViewObject.ShapeColor=(.96,.60,.21) if 'retainer' in key else (.19,.62,.57)
            source.ViewObject.LineColor=(.12,.17,.19);source.ViewObject.DisplayMode='Flat Lines'
        source.Visibility=False;link.Visibility=True
    # Coupon pieces are true sections of the final cover/tray and unchanged
    # duct corner. Together with one original pin they reproduce the latch,
    # mating seam, cable groove and front tie lug without printing whole trays.
    duct_source=links['04_right_fan_duct'].getLinkedObject()
    duct_local=n.move('OriginalDuctLocal',duct_source,tuple(untilt.Base),untilt.Rotation)
    crop=n.box('CableCouponCrop',118,149,111,145,-147,-95)
    # Keep the complete latch and dovetail, but omit the unrelated inner roof
    # ledge whose free cropped end would create a coupon-only overhang.
    duct_crop=n.box('CableDuctCouponCrop',129,149,111,145,-147,-95)
    coupons={
        'cover':n.common('CableCoverCoupon',cap,crop),
        'tray':n.common('CableTrayCoupon',tray,crop),
        'duct':n.common('CableDuctCoupon',duct_local,duct_crop),
    }
    doc.getObject('BaselineAssembly').Label='Rev H-C1 / fourteen installed base parts, four cable replacements'
    doc.getObject('RetentionProvenance').Scope='H-R1 construction history; C1 replaces covers 05/06 and trays 09/10 only'
    meta=doc.addObject('App::FeaturePython','CableProvenance')
    for name,value in [('Revision','H-C1 prototype'),('SourcePath','revh_retention/Precision_5560_RevH_Removable_Retainers.FCStd'),
                       ('SourceSHA256',source_sha),('Scope','Four replacement cover/tray prints; arms, air ducts, rails and H-R1 retainers unchanged'),
                       ('Qualification','Native geometry and toolpath candidate; physical cable fit and tie-lug strength require testing')]:
        meta.addProperty('App::PropertyString',name,'Provenance');setattr(meta,name,value)
    doc.recompute()
    errors=[o.Name for o in doc.Objects if 'Invalid' in o.State or 'Error' in o.State]
    assert not errors,errors
    report={'revision':'H-C1 prototype','source_native_sha256':source_sha,'changed_parts':{},'unchanged_parts':{},
            'native_errors':errors,'groove_nominal':{'outer_wall_height_mm':7,'floor_y':140.7,'rear_mate_y':135.7,'corner_radius_mm':1.2},
            'tie_lugs':{'per_tray':2,'outer_x_mm':148,'local_y_centers_mm':[119,51],'slot_mm':[4,5.5],'slot_corner_radius_mm':.8}}
    for key,link in links.items():
        s=link.Shape
        assert s.isValid() and len(s.Solids)==1,key
        added=s.cut(before[key]).Volume;removed=before[key].cut(s).Volume
        record={'added_mm3':added,'removed_mm3':removed,'volume_mm3':s.Volume}
        if key in mapping:
            assert added+removed>.01,key
            report['changed_parts'][key]=record
        else:
            assert added+removed<.001,(key,added,removed)
            report['unchanged_parts'][key]=record
    sketches=[o for o in group.Group if o.TypeId=='Sketcher::SketchObject']
    assert all(o.FullyConstrained for o in sketches)
    report['new_fully_constrained_sketches']=len(sketches)
    report['coupon_solids']={name:len(obj.Shape.Solids) for name,obj in coupons.items()}
    assert all(count==1 for count in report['coupon_solids'].values()),report['coupon_solids']
    for o in group.Group:o.Visibility=False
    for o in links.values():o.Visibility=True
    doc.recompute();doc.save()
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==source_sha
    report['native_sha256']=hashlib.sha256(TARGET.read_bytes()).hexdigest()
    (OUT/'build-report.json').write_text(json.dumps(report,indent=2)+'\n')
    if App.GuiUp:
        import FreeCADGui as Gui
        Gui.activeDocument().activeView().viewAxonometric();Gui.activeDocument().activeView().fitAll();Gui.updateGui()
    App.Console.PrintMessage('H-C1 cable model saved: four replacement prints; fourteen other installed parts unchanged.\n')
    return doc


if __name__=='__main__':run()
