"""Build the fanless candidate using stock FreeCAD Sketcher/Part features.
Run with FreeCAD's bundled Python. Coordinates: x=wall distance, y=up,
z=print height/inward from outer cheek. Saved FCStd needs no custom proxy.
"""
from pathlib import Path
import math,json,hashlib
import FreeCAD as App,Part,Sketcher,MeshPart

ROOT=Path(__file__).resolve().parent;OUT=ROOT/'results';OUT.mkdir(exist_ok=True)
doc=App.newDocument('Fanless_Curved_Candidate')
sheet=doc.addObject('Spreadsheet::Sheet','Parameters');sheet.Label='Design parameters — mm'
params={'Web':4.8,'ContactReach':16.,'PadReach':24.,'WallThickness':8.,'SlotWidth':22.,'RearDatum':20.,'SeatHeight':6.,'Tilt':4.198081958929171,'HoleDiameter':7.,'WasherDiameter':15.,'ToolDiameter':16.,'HoleLower':18.,'HoleUpper':132.,'CounterboreDepth':4.,'LipHeight':126.,'LaptopWidth':344.4,'LaptopHeight':230.3,'LaptopThickness':20.,'SideClearance':.5}
for row,(name,value) in enumerate(params.items(),1):
    sheet.set('A'+str(row),name);sheet.set('B'+str(row),str(value)+(' deg' if name=='Tilt' else ' mm'));sheet.setAlias('B'+str(row),name)

for row,(name,value) in enumerate(params.items(),1):
    sheet.set('C'+str(row),'Native expression' if name in ['Web','ContactReach','PadReach','HoleDiameter','WasherDiameter','ToolDiameter','HoleLower','HoleUpper','WallThickness','CounterboreDepth'] else 'Reference only; edit geometry recipe')
sheet.setColumnWidth('C',300)
sheet.setColumnWidth('A',190);sheet.setColumnWidth('B',110)
geometry=doc.addObject('App::DocumentObjectGroup','Construction');geometry.Label='Editable profiles and native operations'
def add(kind,name):
    o=doc.addObject(kind,name);geometry.addObject(o);return o
def hide(*objects):
    for o in objects:o.Visibility=False
def check(o):
    doc.recompute()
    if o.Shape.isNull() or not o.Shape.isValid():raise RuntimeError('Invalid feature '+o.Name)
    return o
def transform(p):
    x,y=p;a=math.radians(params['Tilt']);c,s=math.cos(a),math.sin(a)
    xr=20+c*(x-20)+s*(y-6);yr=6-s*(x-20)+c*(y-6)
    blend=min(1,max(0,(x-10)/8))
    return (x+blend*(xr-x),y+blend*(yr-y))
def v(p):return App.Vector(*p,0)
def sketch(name,start,segments,tilt=True,z=0):
    sk=add('Sketcher::SketchObject',name);sk.Placement.Base.z=z
    sk.addProperty('App::PropertyString','EditingNotes');sk.EditingNotes='Editable cubic control points; profile curves are not fully constrained. Depths and screw tools use named parameters.'
    def point(p):return v(transform(p) if tilt else p)
    current=start
    for seg in segments:
        if len(seg)==2:
            end=seg;geo=Part.LineSegment(point(current),point(end))
        else:
            p1,p2,end=seg;geo=Part.BSplineCurve();geo.buildFromPolesMultsKnots([point(current),point(p1),point(p2),point(end)],[4,4],[0.,1.],False,3)
        sk.addGeometry(geo,False);current=end
    doc.recompute();return sk
def polygon(name,points,tilt=False,z=0):return sketch(name,points[0],points[1:]+[points[0]],tilt,z)
def extrude(name,sk,length,alias=None):
    o=add('Part::Extrusion',name);o.Base=sk;o.DirMode='Normal';o.LengthFwd=length;o.Solid=True
    if alias:o.setExpression('LengthFwd','Parameters.'+alias)
    check(o);hide(sk);return o
def join(name,items):
    o=add('Part::MultiFuse',name);o.Shapes=items;o.Refine=True;check(o);hide(*items);return o
def cut(name,base,tool):
    o=add('Part::Cut',name);o.Base=base;o.Tool=tool;o.Refine=True;check(o);hide(base,tool);return o

outer=sketch('OuterSilhouette',(0,4),[(0,140),((0,148),(8,148),(8,140)),((10,116),(28,113),(43,123)),((48,129),(51,125),(49,117)),((47,83),(49,36),(50,10)),((50,2),(46,0),(38,0)),(4,0),((1.8,0),(0,1.8),(0,4))])
web=extrude('SideWeb',outer,params['Web'],'Web')
lo=sketch('LowerOpening',(10,18),[((10,13),(13,12),(19,12)),(33,12),((40,12),(42,16),(37,24)),((29,38),(20,53),(14,62)),((11,66),(9,65),(9,59)),(9,24),((9,22),(9,20),(10,18))])
hi=sketch('UpperOpening',(11,83),[((23,69),(35,45),(42,31)),((44,27),(45,29),(45,35)),(43,108),((43,114),(41,117),(36,117)),((25,118),(17,123),(12,132)),((10,135),(9,132),(9,125)),(9,90),((9,87),(10,85),(11,83))])
windows=join('WindowTools',[extrude('LowerWindowCut',lo,6),extrude('UpperWindowCut',hi,6)])
web=cut('OpenSideWeb',web,windows)
seat=sketch('SeatProfile',(16,0),[(38,0),((46,0),(50,2),(50,6)),(20,6),((17,6),(16,3),(16,0))])
seat=extrude('BottomSeat',seat,params['ContactReach'],'ContactReach')
lip=sketch('FrontRailProfile',(42,6),[(42,119),(44,126),((48,129),(51,125),(49,117)),((47,83),(49,36),(50,10)),(50,4),(42,4),(42,6)])
lip=extrude('FrontRetentionRail',lip,params['ContactReach'],'ContactReach')
rear_lo=polygon('LowerRearContact',[(16,2),(20,2),(20,20),(17,20)],tilt=True)
rear_hi=sketch('UpperRearContact',(15,46),[(18,46),((20,46),(20,48),(20,50)),(20,63),((20,68),(15,68),(15,63)),(15,46)])
contacts=[extrude('LowerContact',rear_lo,params['ContactReach'],'ContactReach'),extrude('UpperContact',rear_hi,params['ContactReach'],'ContactReach')]
contact_limit=extrude('ContactEnvelope',outer,params['ContactReach'],'ContactReach')
upper_clipped=add('Part::Common','UpperContactClipped');upper_clipped.Base=contacts[1];upper_clipped.Tool=contact_limit;upper_clipped.Refine=True;check(upper_clipped);hide(contacts[1],contact_limit);contacts[1]=upper_clipped
pads=[]
for label,cy in [('Lower',params['HoleLower']),('Upper',params['HoleUpper'])]:
    sk=sketch(label+'WallPadProfile',(0,cy-10),[(0,cy+10),((0,cy+12),(2,cy+12),(4,cy+12)),(8,cy+9),(8,cy-9),(4,cy-12),((2,cy-12),(0,cy-12),(0,cy-10))],False)
    sk.setExpression('Placement.Base.y','Parameters.Hole'+label+' - '+str(cy)+' mm')
    pads.append(extrude(label+'WallPad',sk,params['PadReach'],'PadReach'))
upper_rib=sketch('UpperSweepingRib',(6,139),[((10,114),(28,112),(43,122)),(46,115),((30,104),(12,106),(6,127)),(6,139)])
upper_rib=extrude('UpperBrace',upper_rib,params['Web'],'Web')
# Nested curved sections form print-bed-supported, inward-tapering buttresses.
# All contact gussets remain outside the normal 22 mm laptop slot.
def oval(name,cx,cy,rx,ry,z,tilt):
    k=.5522847498307936
    return sketch(name,(cx+rx,cy),[
        ((cx+rx,cy+k*ry),(cx+k*rx,cy+ry),(cx,cy+ry)),
        ((cx-k*rx,cy+ry),(cx-rx,cy+k*ry),(cx-rx,cy)),
        ((cx-rx,cy-k*ry),(cx-k*rx,cy-ry),(cx,cy-ry)),
        ((cx+k*rx,cy-ry),(cx+rx,cy-k*ry),(cx+rx,cy))],tilt,z)
gussets=[]
for name,base,tip,height,tilted in [
    ('RearUpperTab',(14,58,6,26),(18,57,1.5,8),14,True),
    ('RearLowerTab',(15,18,5,17),(18,12,1.5,7),14,True),
    ('FrontUpperTab',(48,104,6,24),(46,108,3,11),14,True),
    ('FrontLowerTab',(48,28,6,23),(46,25,3,11),14,True),
    ('UpperWallPad',(7,126,7,20),(4,132,3,8),22,False),
    ('LowerWallPad',(7,22,7,21),(4,18,3,8),22,False)]:
    bottom=oval(name+'GussetRoot',*base,0,tilted)
    top=oval(name+'GussetTip',*tip,height,tilted)
    loft=add('Part::Loft',name+'Gusset');loft.Sections=[bottom,top]
    loft.Solid=True;loft.Ruled=True;check(loft)
    hide(bottom,top);gussets.append(loft)
body=join('JoinedBracket',[web,seat,lip,upper_rib,*contacts,*pads,*gussets])

# Small top edge chamfers contract material as printing proceeds; no bed-side fillet.
top_edges=[]
for i,e in enumerate(body.Shape.Edges,1):
    if abs(e.BoundBox.ZMin-e.BoundBox.ZMax)<1e-5 and any(abs(e.BoundBox.ZMin-z)<1e-5 for z in [16,24]):top_edges.append((i,.6,.6))
ch=add('Part::Chamfer','ContactTopChamfers');ch.Base=body;ch.Edges=top_edges
doc.recompute()
if ch.Shape.isNull() or not ch.Shape.isValid():
    doc.removeObject(ch.Name);raise RuntimeError('Contact chamfer failed; rebuild source geometry')
hide(body);body=ch

def roof_tool(name,cy,r,x0,length):
    # Circle plus tangent 60° roof; its apex requires no horizontal bridge.
    sk=add('Sketcher::SketchObject',name+'Profile')
    sk.Placement=App.Placement(App.Vector(x0,cy,12),App.Rotation(App.Vector(0,0,1),App.Vector(1,0,0)))
    # Sketch u maps to -z, v maps to y. Apex is therefore negative u.
    q=r*math.sqrt(3)/2
    # circular lower arc, completed by the two roof lines
    sk.addGeometry(Part.Arc(App.Vector(-r/2,-q,0),App.Vector(r,0,0),App.Vector(-r/2,q,0)),False)
    sk.addGeometry(Part.LineSegment(App.Vector(-r/2,q,0),App.Vector(-2*r,0,0)),False)
    sk.addGeometry(Part.LineSegment(App.Vector(-2*r,0,0),App.Vector(-r/2,-q,0)),False)
    alias='HoleDiameter' if name.endswith('BoltHole') else 'WasherDiameter' if name.endswith('WasherRecess') else 'ToolDiameter'
    radius_expr='Parameters.'+alias+' / 2'
    constraints=[Sketcher.Constraint('Coincident',0,3,-1,1),Sketcher.Constraint('Radius',0,r),Sketcher.Constraint('DistanceX',0,1,-r/2),Sketcher.Constraint('DistanceX',0,2,-r/2),Sketcher.Constraint('Coincident',1,1,0,2),Sketcher.Constraint('Coincident',2,2,0,1),Sketcher.Constraint('Coincident',1,2,2,1),Sketcher.Constraint('DistanceX',1,2,-2*r),Sketcher.Constraint('DistanceY',1,2,0.)]
    for c in constraints:sk.addConstraint(c)
    for i,expr in [(1,radius_expr),(2,'-('+radius_expr+') / 2'),(3,'-('+radius_expr+') / 2'),(7,'-2 * ('+radius_expr+')')]:sk.setExpression('Constraints['+str(i)+']',expr)
    sk.setExpression('Placement.Base.y','Parameters.Hole'+('Lower' if cy==18 else 'Upper'))
    sk.setExpression('Placement.Base.z','Parameters.PadReach / 2')
    if name.endswith('WasherRecess'):sk.setExpression('Placement.Base.x','Parameters.WallThickness - Parameters.CounterboreDepth')
    elif name.endswith('DriverCorridor'):sk.setExpression('Placement.Base.x','Parameters.WallThickness')
    obj=extrude(name,sk,length)
    if name.endswith('BoltHole'):obj.setExpression('LengthFwd','Parameters.WallThickness + 2 mm')
    elif name.endswith('WasherRecess'):obj.setExpression('LengthFwd','Parameters.CounterboreDepth + 1 mm')
    return obj
tools=[]
for label,cy in [('Lower',params['HoleLower']),('Upper',params['HoleUpper'])]:
    tools += [roof_tool(label+'BoltHole',cy,3.5,-1,10),roof_tool(label+'WasherRecess',cy,7.5,4,5),roof_tool(label+'DriverCorridor',cy,8,8,70)]
tool=join('MountingAndAccessTools',tools);body=cut('FinishedBracket',body,tool)
body.Label='Left bracket — finished CAD candidate'

if len(body.Shape.Solids)!=1:
    body.Shape.exportStep(str(OUT/'debug.step'))
    print([(s.Volume,str(s.BoundBox)) for s in body.Shape.Solids],flush=True)
    raise RuntimeError('Disconnected after access cuts')
body.Visibility=True
body.addProperty('App::PropertyString','Status');body.Status='CAD candidate; physical PETG fit, creep and anchor qualification pending'
doc.recompute()

# Native mirrored counterpart and installed links are separate from print source.
mirror=doc.addObject('Part::Mirroring','RightPrint');mirror.Source=body;mirror.Normal=App.Vector(1,0,0);mirror.Base=App.Vector(0,0,0);doc.recompute()
mirror.Placement.Base.x=125
mirror.Label='Right bracket — mirrored, bed oriented';doc.recompute()
assembly=doc.addObject('App::DocumentObjectGroup','InstalledAssembly')
left=doc.addObject('App::Link','InstalledLeft');left.setLink(body)
left.Placement=App.Placement(App.Vector(-177.5,0,0),App.Rotation(App.Vector(1,1,1),120))
right=doc.addObject('Part::Mirroring','InstalledRight');right.Source=left;right.Normal=App.Vector(1,0,0);right.Base=App.Vector(0,0,0)
assembly.addObject(left);assembly.addObject(right);doc.recompute()
hide(left,right);assembly.Visibility=False
sheet.Visibility=False;mirror.Visibility=False
doc.recompute()
doc.saveAs(str(OUT/'Fanless_Curved.FCStd'))

report={'freecad_version':App.Version()[:3],'parameters':params,'solid_count':len(body.Shape.Solids),'valid':body.Shape.isValid(),'volume_mm3':body.Shape.Volume,'surface_area_mm2':body.Shape.Area,'native_features':len(doc.Objects),'fully_constrained_sketches':sum(bool(o.FullyConstrained) for o in doc.Objects if o.TypeId=='Sketcher::SketchObject'),'sketch_count':sum(o.TypeId=='Sketcher::SketchObject' for o in doc.Objects),'checks':{}}
for label,shape in [('left',body.Shape),('right',mirror.Shape)]:
    shape.exportStep(str(OUT/(label+'.step')))
    mesh=MeshPart.meshFromShape(Shape=shape,LinearDeflection=.06,AngularDeflection=.12,Relative=False)
    mesh.write(str(OUT/(label+'.stl')))
    report[label+'_mesh_facets']=mesh.CountFacets

# Exact CAD volume intersections: actual circular tool envelope and laptop travel.
for cy in [18.,132.]:
    shaft=Part.makeCylinder(8,70,App.Vector(8,cy,12),App.Vector(1,0,0))
    report['checks']['tool_'+str(cy)+'_intersection_mm3']=body.Shape.common(shaft).Volume
    hole=Part.makeCylinder(3.5,10,App.Vector(-1,cy,12),App.Vector(1,0,0))
    report['checks']['hole_'+str(cy)+'_intersection_mm3']=body.Shape.common(hole).Volume
for travel in [0,1,5,20,60,120,130]:
    laptop=Part.makeBox(20,230.3,350,App.Vector(21,6+travel,5.3))
    laptop.rotate(App.Vector(20,6,0),App.Vector(0,0,1),-params['Tilt'])
    report['checks']['laptop_travel_'+str(travel)+'_intersection_mm3']=body.Shape.common(laptop).Volume
assert max(report['checks'].values())<1e-5,report['checks']
(OUT/'cad_validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
