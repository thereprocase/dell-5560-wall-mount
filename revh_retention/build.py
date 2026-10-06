"""Build removable Rev H retainers as stock FreeCAD features in a Save As copy.

Run run() in FreeCAD's GUI, or this file with FreeCAD's bundled Python. The
released Rev H document and all fourteen existing parts remain unchanged.
"""
from pathlib import Path
import hashlib
import json
import math
import shutil
import sys
import FreeCAD as App
import Part

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'minimalist'))
from native import Native
OUT = ROOT / 'revh_retention'
SOURCE = ROOT / 'freecad/Precision_5560_Native.FCStd'
TARGET = OUT / 'Precision_5560_RevH_Removable_Retainers.FCStd'


class RetainerNative(Native):
    def obj(self, kind, name, label):
        obj = super().obj(kind, 'R1' + name, label)
        obj.DesignFamily = 'Revision H removable retention R1'
        return obj

    def round_x(self, name, source, radius):
        self.doc.recompute()
        indices = []
        for i, edge in enumerate(source.Shape.Edges, 1):
            if len(edge.Vertexes) == 2:
                vector = edge.Vertexes[1].Point - edge.Vertexes[0].Point
                if abs(abs(vector.x) - edge.Length) < 1e-7:
                    indices.append(i)
        assert indices
        obj = self.obj('Part::Fillet', name, name)
        obj.Base = source
        obj.Edges = [(i, radius, radius) for i in indices]
        source.Visibility = obj.Visibility = False
        self.doc.recompute()
        assert obj.Shape.isValid() and len(obj.Shape.Solids) == 1
        return obj


def run():
    OUT.mkdir(exist_ok=True)
    sha = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    assert sha == json.loads((ROOT / 'print_release/manifest.json').read_text())['native_sha256']
    snapshot = ROOT / 'tmp/retention/RevH_Source_Snapshot.FCStd'
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE, snapshot)
    sys.path.insert(0, App.getResourceDir() + 'Mod/Assembly')
    for opened in list(App.listDocuments().values()):
        if Path(opened.FileName) == TARGET: App.closeDocument(opened.Name)
    doc = App.openDocument(str(snapshot))
    doc.saveAs(str(TARGET))
    before = {o.InstanceKey: o.Shape.copy() for o in doc.getObject('InstalledAssembly').Group
              if o.TypeId == 'App::Link'}
    assert len(before) == 14
    # Rev H's saved joint references use empty subelements that current FreeCAD
    # rejects. Preserve all native source features and installed link poses in
    # an ordinary App::Part; this add-on does not use the legacy joint solver.
    original_assembly = doc.getObject('InstalledAssembly')
    links = [o for o in original_assembly.Group if o.TypeId == 'App::Link']
    removed_joints = 0
    for joint_group in [o for o in original_assembly.Group if o.TypeId == 'Assembly::JointGroup']:
        for joint in list(joint_group.Group):
            doc.removeObject(joint.Name)
            removed_joints += 1
        doc.removeObject(joint_group.Name)
    baseline = doc.addObject('App::Part', 'BaselineAssembly')
    baseline.Label = 'Revision H — fourteen unchanged installed parts'
    for link in links:
        original_assembly.removeObject(link)
        baseline.addObject(link)
    doc.removeObject(original_assembly.Name)
    doc.recompute()
    provenance = doc.addObject('App::FeaturePython', 'RetentionProvenance')
    for name, value in [('Revision', 'H-R1 prototype'), ('SourcePath', 'freecad/Precision_5560_Native.FCStd'),
                        ('SourceSHA256', sha), ('Scope', 'Four removable add-on parts; all fourteen Rev H parts unchanged'),
                        ('Qualification', 'CAD and toolpath review only; fit, retention and strength require physical testing')]:
        provenance.addProperty('App::PropertyString', name, 'Provenance')
        setattr(provenance, name, value)
    # This metadata object has no proxy, geometry, or recompute dependency.
    group = doc.addObject('App::DocumentObjectGroup', 'RetentionFeatures')
    group.Label = 'H-R1 — editable sketches and stock Part features'
    n = RetainerNative(doc, group)
    c, x0, x1 = .3, 184.3, 189.3
    spine = n.prism('SideBarBlank', [(16,-53),(30,-53),(30,-36),(44.6,-31),(44.6,178),(16,178)], 'YZ', (x0,0,0), x1-x0)
    holes = []
    for index, (za, zb) in enumerate([(-9,32),(39,80),(87,128),(135,169)], 1):
        for suffix, points in [('A', [(21,za),(39.6,za),(39.6,zb-13)]),
                               ('B', [(21,za+13),(39.6,zb),(21,zb)])]:
            raw = n.prism('TrussWindow%d%s' % (index,suffix), points, 'YZ', (x0-.1,0,0), x1-x0+.2)
            holes.append(n.round_x('RoundedWindow%d%s' % (index,suffix), raw, 1.2))
    spine = n.cut('TriangulatedSideBar', spine, n.compound('TrussOpenings', holes))
    # Exact inward offset of the existing R1.5 rounded gusset window.
    m = 18/35
    offset = c * math.sqrt(1 + m*m)
    yback, ztop = 30+c, -15-c
    zbottom = m*(yback-30)-33+offset
    yfront = 30+(ztop+33-offset)/m
    raw = n.prism('WindowKeyBlank', [(yback,zbottom),(yfront,ztop),(yback,ztop)], 'YZ', (175.8,0,0), x1-175.8)
    tongue = n.round_x('RoundedWindowKey', raw, 1.5-c)
    guide_raw = n.prism('GuideWindowKeyBlank',[(43.3,5.3),(58.7,5.3),(58.7,17.7),(43.3,17.7)],'YZ',(175.3,0,0),x1-175.3)
    guide_key = n.round_x('RoundedGuideWindowKey',guide_raw,2.7)
    tab = n.box('DuctStop', 169.5,x1,36.3+c,42.6,-25,-20)
    upper = n.box('RailStop',173.4,x1,39+c,44.6,160,178)
    bar = n.fuse('JoinedSideRetainer', [spine,tongue,guide_key,tab,upper])
    hole = n.box('SquareKeeperSocket',172,175.6,37.8,41.4,-25.1,-19.9)
    right = n.cut('RightSideRetainer',bar,hole)
    right.Label = '16 — right removable side retainer'
    left = n.mirror('LeftSideRetainer',right)
    left.Label = '15 — left removable side retainer'
    # A keyed square peg keeps the eccentric catch foot facing the gusset.
    foot = n.box('KeeperCatchFoot',170.5,175.5,36.6,51.5,-29,-25.3)
    stem = n.box('KeeperSquareStem',172.3,175.3,38.1,41.1,-25.3,-19.7)
    crown = n.prism('KeeperInsertionRamp',[(37.7,-19.7),(37.7,-19.3),(38.3,-17.9),(40.9,-17.9),(41.5,-19.3),(41.5,-19.7)],'YZ',(172.3,0,0),3)
    peg = n.fuse('KeeperBlank',[foot,stem,crown])
    split = n.box('KeeperFlexSlot',172,175.6,39.1,40.1,-23.8,-17.5)
    pin = n.cut('RightKeeper',peg,split)
    pin.Label = '18 — right side-retainer keeper'
    left_pin = n.mirror('LeftKeeper',pin)
    left_pin.Label = '17 — left side-retainer keeper'
    # The short coupon tests the real printed arm, duct stop and keeper.
    cutoff = n.box('CouponUpperCut',160,195,10,70,23.1,190)
    coupon = n.cut('RightFitCoupon',right,cutoff)
    coupon.Label = 'TEST ONLY — right-arm two-window key and keeper coupon'
    assembly = doc.addObject('App::Part','RetentionAssembly')
    assembly.Label = 'H-R1 — four installed removable retainers'
    mapping = {'15_left_side_retainer':left,'16_right_side_retainer':right,
               '17_left_retainer_keeper':left_pin,'18_right_retainer_keeper':pin}
    for key,obj in mapping.items():
        obj.addProperty('App::PropertyString','RetentionPartKey','Manufacturing')
        obj.RetentionPartKey = key
        link = doc.addObject('App::Link','InstalledR1'+key)
        link.setLink(obj)
        link.Label = key.replace('_',' ')
        link.addProperty('App::PropertyString','InstanceKey','Manufacturing')
        link.InstanceKey = key
        assembly.addObject(link)
        obj.Visibility = False
        if App.GuiUp:
            color = (0.97,0.56,0.16) if 'side_retainer' in key else (0.35,0.80,0.35)
            obj.ViewObject.ShapeColor = color
            link.Visibility = True
    coupon.Visibility = False
    doc.recompute()
    sketches = [o for o in group.Group if o.TypeId == 'Sketcher::SketchObject']
    assert all(o.FullyConstrained for o in sketches)
    for key, obj in mapping.items():
        assert obj.Shape.isValid() and len(obj.Shape.Solids) == 1, key
    for obj in doc.getObject('BaselineAssembly').Group:
        if obj.TypeId == 'App::Link':
            s = before[obj.InstanceKey]
            assert obj.Shape.cut(s).Volume + s.cut(obj.Shape).Volume < .001
    report = {'revision':'H-R1 prototype','source_native_sha256':sha,
              'new_fully_constrained_sketches':len(sketches),'unchanged_original_parts':14,'legacy_invalid_joints_removed_from_copy':removed_joints,
              'parts':{key:{'volume_mm3':obj.Shape.Volume,'cad_ASA_g':obj.Shape.Volume*.00105}
                       for key,obj in mapping.items()}}
    if App.GuiUp:
        import FreeCADGui as Gui
        App.setActiveDocument(doc.Name)
        Gui.activeDocument().activeView().viewAxonometric()
        Gui.activeDocument().activeView().fitAll()
        Gui.updateGui()
    doc.recompute()
    doc.save()
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == sha
    report['native_sha256'] = hashlib.sha256(TARGET.read_bytes()).hexdigest()
    (OUT/'build-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('H-R1 native build complete:', report)
    return doc


if __name__ == '__main__': run()
