"""Native teal-only shroud refinement against frozen printed cradles."""
from pathlib import Path
import json,sys,shutil
import FreeCAD as App,FreeCADGui as Gui,Part,Sketcher
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT))
import native_ops as N
D=next(d for d in App.listDocuments().values() if d.FileName and Path(d.FileName).resolve()==(ROOT/'Precision_5560_Native.FCStd').resolve());App.setActiveDocument(D.Name)
if D.getObject('RailRefinement'): raise RuntimeError('Refinement already exists; edit it rather than rebuilding')
manifest=json.loads((ROOT/'frozen_print_arms/manifest.json').read_text())
def frozen_check():
    out={}
    for key,info in manifest['parts'].items():
        a=D.getObject(info['source']).Shape;b=Part.read(str(ROOT/'frozen_print_arms'/info['file']))
        ab=a.cut(b);ba=b.cut(a)
        assert ab.isValid() and ba.isValid() and abs(ab.Volume)+abs(ba.Volume)<1e-6,key
        out[key]=abs(ab.Volume)+abs(ba.Volume)
    return out
frozen_check();D.save();shutil.copy2(D.FileName,ROOT/'BeforeRailRefinement.FCStd')
D.openTransaction('Refine teal rail shrouds; printed arms frozen')
try:
    N.D=D;N.FAMILY='Rail fit revision';N.GROUP=D.addObject('App::DocumentObjectGroup','RailRefinement');N.GROUP.Label='Outlet rails - dust cover and frozen-arm fit'
    P=D.getObject('Parameters')
    P.mergeCells('A65:F65');P.set('A65','OUTLET RAIL FINISH | PRINTED ARMS FROZEN');P.setBackground('A65:F65',(.16,.29,.37));P.setForeground('A65:F65',(1,1,1))
    for row,alias,value,description in [(66,'railRoofThickness',2,'Top dust cover; central exhaust stays open'),(67,'railEdgeChamfer',.6,'Small exposed edge bevel')]:
        P.set('A'+str(row),alias);P.set('B'+str(row),str(value)+' mm');P.setAlias('B'+str(row),alias);P.set('C'+str(row),'mm');P.set('D'+str(row),description);P.set('E'+str(row),'Teal parts only');P.set('F'+str(row),'Input');P.setBackground('B'+str(row),(.79,.90,.98));P.setForeground('B'+str(row),(.03,.22,.42))
    P.set('A68','Frozen arm fit clearance');P.set('B68','0.30 mm');P.set('D68','Fixed profile from printed arm; lead-in preserves insertion');P.set('F68','Reference')
    P.set('A69','PRINT FREEZE');P.set('D69','Both gray cradles are printing. Do not alter shared arm dimensions.');P.setBackground('A69:F69',(1,.81,.50));P.setForeground('A69:F69',(.15,.12,.08))
    right=next(o for o in D.Objects if o.TypeId!='App::Link' and getattr(o,'PartKey','')=='08_right_outlet_rail')
    left=next(o for o in D.Objects if o.TypeId!='App::Link' and getattr(o,'PartKey','')=='07_left_outlet_rail')
    oldbase=right.Links[0]
    def box(x0,x1,y0,y1,z0,z1,label):
        sk=N.polygon([(x0,y0),(x1,y0),(x1,y1),(x0,y1)],(0,0,z0),label=label)
        return N.extrude(sk,z1-z0)
    # Exact frozen offset profile converted to native constrained sketch geometry.
    wire=Part.read(str(ROOT/'arm_clearance_profile.brep'))
    rot=App.Rotation(App.Vector(0,1,0),App.Vector(0,0,1),App.Vector(1,0,0),'ZXY')
    source_placement=App.Placement(App.Vector(182,0,0),rot)
    local=wire.copy();local.transformShape(source_placement.inverse().toMatrix())
    sk=N.new('Sketcher::SketchObject','Frozen arm contour + 0.30 mm');sk.Placement=App.Placement(App.Vector(139,0,0),rot)
    for e in local.Edges:
        if isinstance(e.Curve,Part.Line): g=Part.LineSegment(e.Vertexes[0].Point,e.Vertexes[-1].Point)
        elif isinstance(e.Curve,Part.Circle): g=Part.ArcOfCircle(e.Curve,e.FirstParameter,e.LastParameter)
        else: raise RuntimeError('Unsupported frozen outline curve')
        i=sk.addGeometry(g,False);sk.addConstraint(Sketcher.Constraint('Block',i))
    sk.addProperty('App::PropertyString','DatumNote','Manufacturing');sk.DatumNote='Fixed printing datum, 0.30 mm clearance; do not redrive from shared laptop dimensions.'
    pocket=N.extrude(sk,46)
    lead=box(139,185,-2,6.3,153.3,184.3,'Assembly lead-in over rear shoulder')
    pocket=pocket.union(lead)
    patch=box(180,184,0,26.3,154,198,'Continuous side cheek').cut(pocket)
    hole=N.circle(10,(162,-1,174),App.Rotation(App.Vector(0,0,1),App.Vector(0,1,0)))
    patch=patch.cut(N.extrude(hole,60))
    thickness=N.Expr(2,'Parameters.railRoofThickness / (1 mm)')
    roof=box(.2,184,0,28,232-thickness,232,'Dust cover behind exhaust slot')
    end=box(140,184,28,39,232-thickness,232,'Closed outer end window')
    result=N.Shape(oldbase).union(patch).union(roof).union(end)
    # Select long exposed top edges by geometry, not by stored edge numbers.
    edges=[]
    for i,e in enumerate(result.obj.Shape.Edges,1):
        b=e.BoundBox
        if abs(b.ZMin-232)<1e-6 and abs(b.ZMax-232)<1e-6 and e.Length>5:
            edges.append(i)
    chamfer=N.new('Part::Chamfer','Slender top-edge chamfer');chamfer.Base=result.obj
    chamfer.Edges=[(i,.6,.6) for i in edges]
    result=N.update(chamfer,[result.obj])
    right.Links=[result.obj]
    D.recompute()
    for o in N.GROUP.Group:o.Visibility=False
    right.Visibility=False;left.Visibility=False
    for o in D.getObject('InstalledAssembly').Group:
        if o.TypeId=='App::Link' and 'outlet_rail' in getattr(o,'InstanceKey',''):o.Visibility=True
    for o in N.GROUP.Group:
        v=o.ViewObject
        if hasattr(v,'ShapeColor'):v.ShapeColor=(.1,.55,.59)
        if hasattr(v,'LineColor'):v.LineColor=(.055,.07,.085)
        if hasattr(v,'LineWidth'):v.LineWidth=1.3
        if hasattr(v,'Deviation'):v.Deviation=.05
        if hasattr(v,'AngularDeflection'):v.AngularDeflection=5
    checks={'frozen_arms_difference':frozen_check(),'rail_parts':{}}
    for o in [right,left]:
        checks['rail_parts'][o.PartKey]={'valid':o.Shape.isValid(),'solids':len(o.Shape.Solids),'volume':o.Shape.Volume}
        assert o.Shape.isValid() and len(o.Shape.Solids)==1
    assert not [o.Name for o in D.Objects if 'Invalid' in o.State]
    checks['new_sketches_fully_constrained']=all(o.FullyConstrained for o in N.GROUP.Group if o.TypeId=='Sketcher::SketchObject')
    assert checks['new_sketches_fully_constrained']
    D.commitTransaction();D.save();shutil.copy2(D.FileName,ROOT/'RailValidation.FCStd')
    (ROOT/'rail_refinement_build.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
    Gui.updateGui();Gui.activeDocument().mdiViewsOfType('Gui::View3DInventor')[0].saveImage(str(ROOT/'rail_refinement_preview.png'),1920,1440,'Current')
    App.Console.PrintMessage('Teal rail refinement saved; both printed arms match frozen geometry.\n')
except Exception:
    D.abortTransaction();raise
