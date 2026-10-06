"""Precision 5560 wall cradle, revision E. All dimensions in mm.
X = laptop width, Y = out from wall, Z = up. Every screw axis is parallel Y.
CadQuery 2.8.0. Run this file to regenerate the ten exact STEP solids and checks.
"""
from pathlib import Path
import json, math
import cadquery as cq
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib

OUT=Path(__file__).resolve().parent
PARTS=OUT/'parts'; PARTS.mkdir(exist_ok=True)
LAPTOP_W=344.4; LAPTOP_H=230.3; LAPTOP_T=20.0
WALL_GAP=40.; FRONT_JAW_FACE=64.; TINE_H=94.
WALL_HOLE_Z=(-36.,174.); JOINT_Z=(-19.,-55.)
FAN_CX=70.; FAN_CY=70.; CAP_SCREW_X=(5.,135.)
OUTLET_GAP=12.; RAMP_START_Z=198.; OUTLET_Z=220.
RAIL_SCREW_X=(150.,174.); RAIL_SCREW_Z=160.

def box(x0,x1,y0,y1,z0,z1):
    return cq.Workplane('XY').box(x1-x0,y1-y0,z1-z0).translate(((x0+x1)/2,(y0+y1)/2,(z0+z1)/2))
def cyl(r,h,base,direction=(0,1,0)):
    return cq.Workplane(obj=cq.Solid.makeCylinder(r,h,cq.Vector(*base),cq.Vector(*direction)))
def yz_prism(x0,x1,pts):
    return cq.Workplane('YZ',origin=(x0,0,0)).polyline(pts).close().extrude(x1-x0)
def fuse(*items):
    r=items[0]
    for s in items[1:]:r=r.union(s)
    return r.clean()
def bbox(s):
    b=Bnd_Box();BRepBndLib.AddOptimal_s(s.wrapped,b,False,False)
    x0,y0,z0,x1,y1,z1=b.Get()
    return dict(xmin=x0,xmax=x1,ymin=y0,ymax=y1,zmin=z0,zmax=z1,
                dimensions_mm=[x1-x0,y1-y0,z1-z0])

def roof_hole(r,h,base,roof='-X',bridge=1.2):
    """Retain the circular clearance and add tangent 45-degree roof faces.
    roof is the print-up direction in assembly coordinates; axis remains Y.
    """
    x,y,z=base;q=r/math.sqrt(2);tip=2*q-bridge/2
    uv=[(q,-q),(tip,-bridge/2),(tip,bridge/2),(q,q)]
    def pt(u,v):
        if roof=='-X':return (x-u,z+v)
        if roof=='+Z':return (x+v,z+u)
        if roof=='-Z':return (x+v,z-u)
        raise ValueError(roof)
    wedge=cq.Workplane('XZ',origin=(0,y+h,0)).polyline([pt(u,v) for u,v in uv]).close().extrude(h)
    return cyl(r,h,base).union(wedge)

def right_cradle():
    # Outboard X=184 face is flat on the bed; print toward decreasing X.
    # Round the YZ outline, never recess the bed-side upper contact or tine.
    back=box(140,184,0,10,-65,184).edges('|X').fillet(4)
    shelf=box(140,184,0,84,-12,0).edges('|X').fillet(2)
    lower=box(140,184,8,38,-1,42).edges('|X').fillet(4)
    front=yz_prism(140,184,[(64,-6),(84,-6),(84,0),(75.1875,94),(67,94),(64,88)])
    front=front.edges('|X').fillet(2)
    # The inboard face tapers inward toward the tip; it closes on supported layers.
    taper=cq.Workplane('XZ',origin=(0,86,0)).polyline([(139,0),(150,94),(150,97),(139,97)]).close().extrude(24)
    front=front.cut(taper)
    guide=box(175,184,36,66,-2,24).edges('|X').fillet(2)
    gusset=yz_prism(176,184,[(10,-51),(84,-12),(10,-12)])
    spine=box(148,184,8,26,-12,164).edges('|X').fillet(4)
    upper=box(150,184,8,38,126,152).edges('|X').fillet(4)
    upper_rib=yz_prism(156,184,[(10,94),(38,126),(10,134)])
    receiver=box(142,184,8,26,-65,-12).edges('|X').fillet(3)
    rail_receiver=box(140,184,8,26,154,166).edges('|X').fillet(3)
    s=fuse(back,shelf,lower,front,guide,gusset,spine,upper,upper_rib,receiver,rail_receiver)
    for z in WALL_HOLE_Z:s=s.cut(roof_hole(3.5,12,(162,-1,z)))
    s=s.cut(roof_hole(9,20,(162,10,-36),bridge=4))
    # Hollow box sections remove neutral-axis material and retain torsional stiffness.
    s=s.cut(yz_prism(151.2,180,[(7,44),(19,44),(22,70),(22,150),(4,150),(4,70)]).edges('|X').fillet(4))
    for a,b in [(11,21),(23,33)]:
        s=s.cut(box(142.4,180,a,b,5,36).edges('|X').fillet(2))
    s=s.cut(box(142.4,180,14,61,-8,-4).edges('|X').fillet(1.5))
    tine_void=yz_prism(142,180,[(68,14),(78.6875,14),(72.125,84),(68,84)]).edges('|X').fillet(1.3)
    inner_skin=cq.Workplane('XZ',origin=(0,86,0)).polyline([(139,0),(142.2,0),(153.2,94),(139,94)]).close().extrude(24)
    tine_void=tine_void.cut(inner_skin)
    s=s.cut(tine_void)
    # Rounded triangular web windows retain the diagonal shear paths.
    for pts in [[(30,-33),(65,-15),(30,-15)]]:
        s=s.cut(yz_prism(175,185,pts).edges('|X').fillet(1.5))
    s=s.cut(box(174,185,43,59,5,18).edges('|X').fillet(3))
    return s.clean()

def right_outlet_rail(gap=OUTLET_GAP):
    # Print lip Z=220 on the bed, toward decreasing Z.
    panel=box(.2,139,0,4,154,220).edges('|Y').fillet(2)
    ramp=yz_prism(.2,160,[(0,198),(4,198),(40-gap,218),(40-gap,220),(0,220)])
    # Flat lip bed face; rounding confined to existing side-panel corners.
    arm=cq.Workplane('XZ',origin=(0,30,0)).polyline([(140,154),(184,154),(184,220),(176,220),(140,184)]).close().extrude(4)
    column=box(176,184,0,30,186,220)
    top_link=box(136,184,0,4,216,220)
    s=fuse(panel,ramp,arm,column,top_link)
    s=s.cut(roof_hole(10,34,(162,-1,174),roof='-Z',bridge=4))
    for x in RAIL_SCREW_X:s=s.cut(roof_hole(2.25,8,(x,24,160),roof='-Z'))
    # Hollow the wedge from its underside, retaining the air skin and ribs.
    top_y=min(23.5,4+(36-gap)*.975-2.8)
    cavity=[(2,200),(top_y-17.5,200),(top_y,217.5),(2,217.5)]
    for x0,x1 in [(.19,34),(36,70),(72,106),(108,142),(144,158)]:
        s=s.cut(yz_prism(x0,x1,cavity))
    s=s.cut(box(.19,135,2,4.1,154,195.5))
    # Through-window closes on a four-mm bridge in the lip-down orientation.
    s=s.cut(yz_prism(175,185,[(4,218),(26,218),(17,209),(17,200),(13,200),(13,209)]))
    return s.clean()

def tongue(cx,y0,y1,clearance=False):
    # Dovetail: 3 mm root / 6 mm crown / 2 mm rise, 36.9 degrees from vertical.
    # Groove has 0.30 mm flank clearance and 0.30 mm roof clearance.
    if clearance:pts=[(cx-1.8,-110.3),(cx+1.8,-110.3),(cx+3.3,-108),(cx+3.3,-107.7),(cx-3.3,-107.7),(cx-3.3,-108)]
    else:pts=[(cx-1.5,-110.1),(cx+1.5,-110.1),(cx+3,-108),(cx-3,-108)]
    return cq.Workplane('XZ',origin=(0,y1,0)).polyline(pts).close().extrude(y1-y0)

def right_duct():
    # Print Z=-110 down: open inlet on bed, no fan-pocket ceiling.
    deck=box(1,140,4,136,-110,-104).edges('|Z').fillet(3)
    outer=(cq.Workplane('XY',origin=(70.5,70,-104)).rect(139,132)
           .workplane(offset=94).center(0,-47).rect(139,38).loft(ruled=True))
    outer=outer.newObject([e for e in outer.edges().vals() if e.BoundingBox().zlen>90]).fillet(1.2)
    inner=(cq.Workplane('XY',origin=(70.5,70,-104.1)).rect(135.8,127.6)
           .workplane(offset=94.2).center(0,-47.1).rect(135.8,33.4).loft(ruled=True))
    shell=outer.cut(inner)
    ear=box(136,174,26,36,-65,-12).edges('|Y').fillet(3)
    ear_ramp=cq.Workplane('XZ',origin=(0,36,0)).polyline([(136,-104),(174,-66),(174,-60),(136,-60)]).close().extrude(10)
    bosses=[box(1,11,122,136,-110,-97).edges('|Z').fillet(2),box(130,140,122,136,-110,-97).edges('|Z').fillet(2)]
    s=fuse(deck,shell,ear,ear_ramp,*bosses)
    s=s.cut(cyl(58,8,(FAN_CX,FAN_CY,-111),(0,0,1)))
    for z in JOINT_Z:s=s.cut(roof_hole(2.25,14,(162,24,z),roof='+Z'))
    s=s.cut(roof_hole(9,14,(162,24,-36),roof='+Z',bridge=4))
    for x in CAP_SCREW_X:
        # Keep heat-set pilots round; this is a short 4 mm horizontal bore.
        s=s.cut(cyl(2.,8,(x,129,-103)))
        s=s.cut(cyl(1.7,9,(x,123,-103)))
        s=s.cut(tongue(x,8.7,137,True))
    s=s.cut(box(11,130,8,132,-107.6,-103.9))
    # Narrow exterior ribs stiffen the thin front skin without narrowing airflow.
    for x in (32,68,104):
        s=s.union(yz_prism(x,x+2,[(128,-96),(128,-94),(46,-12),(44,-12)]))
    return s.clean()

def right_tray():
    # Guard side Z=-146 on bed. The tray stays open above the fan.
    side_l=box(1,5,4,136,-146,-110)
    side_r=box(135,140,4,136,-146,-110)
    stop=box(1,140,4,9,-146,-110)
    ledge_l=box(1,19,4,136,-146,-139)
    ledge_r=box(121,140,4,136,-146,-139)
    guard=[box(8,133,y,y+2.4,-146,-143) for y in range(16,133,12)]
    guard.append(box(69,71.4,4,136,-146,-143))
    beam=cq.Workplane('XZ',origin=(0,136,0)).polyline([(1,-119),(5,-119),(9,-115),(9,-110),(1,-110)]).close().extrude(132)
    other=beam.mirror('YZ').translate((140,0,0))
    lands=[box(x0,x1,y0,y1,-139,-110) for x0,x1 in [(5,9),(131,135)] for y0,y1 in [(9,30),(110,136)]]
    s=fuse(side_l,side_r,stop,ledge_l,ledge_r,beam,other,*lands,*guard,*[tongue(x,9,135.5) for x in CAP_SCREW_X])
    for y in (16,36,56,76,96,116):
        window=[(y,-136),(y+16,-136),(y+16,-124),(y+10,-118),(y+6,-118),(y,-124)]
        for x0,x1 in [(0,9.1),(130.9,141)]:s=s.cut(yz_prism(x0,x1,window))
    for x in (22,44,66,88,110):
        pts=[(x,-136),(x+16,-136),(x+16,-124),(x+10,-118),(x+6,-118),(x,-124)]
        s=s.cut(cq.Workplane('XZ',origin=(0,10,0)).polyline(pts).close().extrude(7))
    for x0,x1 in [(9,19),(121,131)]:s=s.cut(box(x0,x1,36,104,-143,-139))
    return s.clean()

def right_cap():
    # Front face Y=144 on bed; two fine V-flutes replace a broad recessed ceiling.
    cap=box(1,140,136,144,-146,-97).edges('|Y').fillet(4)
    toe=box(14,126,131,137,-138,-112).edges('|Y').fillet(3)
    cap=fuse(cap,toe)
    for z in (-131,-125):
        cap=cap.cut(yz_prism(30,110,[(144.1,z-1.5),(144.1,z+1.5),(142.6,z)]))
    cable=box(117,127,130,145,-115,-106).edges('|Y').fillet(2)
    cap=cap.cut(cable)
    for x in CAP_SCREW_X:cap=cap.cut(cyl(2.25,10,(x,135,-103)))
    # Continuous 2.4 mm outer face with a perimeter rim and two internal ribs.
    for x0,x1 in [(18,45),(47,94),(96,122)]:
        cap=cap.cut(box(x0,x1,130,141.6,-134,-116).edges('|Y').fillet(2))
    for x0,x1 in [(4,45),(47,94),(96,136)]:
        cap=cap.cut(box(x0,x1,130,141.6,-141,-111).edges('|Y').fillet(2))
    cap=cap.cut(box(12,129,130,141.6,-111,-99).edges('|Y').fillet(2))
    return cap.clean()

def fan_reference(cx):
    ring=box(cx-60,cx+60,10,130,-138,-111).edges('|Z').fillet(4)
    ring=ring.cut(cyl(55,29,(cx,70,-139),(0,0,1)))
    hub=cyl(19,8,(cx,70,-127),(0,0,1));spokes=[]
    for angle in (0,90,180,270):
        spokes.append(box(cx-3,cx+3,70,126,-129,-126).rotate((cx,70,0),(cx,70,1),angle))
    return fuse(ring,hub,*spokes)
def laptop_reference():
    return box(-LAPTOP_W/2,LAPTOP_W/2,40,60,2,232.3).edges('|Y').fillet(4)

def fastener_interfaces():
    entries=[]
    for x in (-162,162):
        for z in WALL_HOLE_Z:
            entries.append(dict(kind='wall_anchor',center=[x,10,z],axis=[0,-1,0],
                                shaft_d_mm=7,driver_d_mm=16,head_plane_y=10))
        for z in JOINT_Z:
            entries.append(dict(kind='M4_duct_joint',center=[x,36,z],axis=[0,-1,0],
                                shaft_d_mm=4.5,driver_d_mm=12,head_plane_y=37))
    for x in (-135,-5,5,135):
        entries.append(dict(kind='M3_fan_retainer',center=[x,144,-103],axis=[0,-1,0],
                            shaft_d_mm=3.5,driver_d_mm=12,head_plane_y=144))
    for x in (-174,-150,150,174):
        entries.append(dict(kind='M4_outlet_rail',center=[x,30,160],axis=[0,-1,0],
                            shaft_d_mm=4.5,driver_d_mm=12,head_plane_y=31))
    return entries
