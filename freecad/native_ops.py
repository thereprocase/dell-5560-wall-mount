"""Native FreeCAD feature adapter for the small Revision F construction vocabulary.

Creates persistent Sketcher + Part features, never assigns an opaque BRep Shape.
Source scripts are inputs; this adapter is only needed to construct, not edit, FCStd.
"""
import math, inspect, linecache, json, time
from pathlib import Path
import FreeCAD as App, Part, Sketcher
D=None
GROUP=None
FAMILY=''
ROOT=Path(__file__).resolve().parent
COUNT=0

class Expr(float):
    def __new__(cls,value,text):
        o=super().__new__(cls,value); o.text=text; return o
    def op(self,other,sign,fn): return Expr(fn(float(self),float(other)), '('+self.text+sign+expr(other)+')')
    def __add__(self,o): return self.op(o,'+',lambda a,b:a+b)
    __radd__=__add__
    def __sub__(self,o): return self.op(o,'-',lambda a,b:a-b)
    def __rsub__(self,o): return Expr(float(o)-float(self),'('+expr(o)+'-'+self.text+')')
    def __mul__(self,o): return self.op(o,'*',lambda a,b:a*b)
    __rmul__=__mul__
    def __truediv__(self,o): return self.op(o,'/',lambda a,b:a/b)
    def __rtruediv__(self,o): return Expr(float(o)/float(self),'('+expr(o)+'/'+self.text+')')
    def __neg__(self): return Expr(-float(self),'(-'+self.text+')')
def expr(x): return x.text if isinstance(x,Expr) else repr(float(x))
def bind(o,prop,x):
    if isinstance(x,Expr): o.setExpression(prop,x.text)
def vec(x): return App.Vector(*[float(a) for a in x])
def new(t,label):
    global COUNT
    o=D.addObject(t,t.split('::')[-1]); o.Label=FAMILY+' — '+label
    if GROUP: GROUP.addObject(o)
    for f in inspect.stack()[1:]:
        if f.filename.endswith(('base_geometry.py','build_mount.py')):
            o.addProperty('App::PropertyString','SourceLocation','Provenance')
            o.SourceLocation=Path(f.filename).name+':'+str(f.lineno)
            break
    COUNT+=1
    return o
def update(o,hide=()):
    D.recompute()
    if hasattr(o,'Shape') and (o.Shape.isNull() or not o.Shape.isValid()):
        raise RuntimeError('Invalid native feature '+o.Name+' '+o.Label+' '+str(o.State))
    for h in hide: h.Visibility=False
    if App.GuiUp:
        import FreeCADGui as Gui
        if COUNT % 8 == 0:
            Gui.activeDocument().mdiViewsOfType('Gui::View3DInventor')[0].fitAll(); Gui.updateGui()
    if COUNT % 20 == 0:
        (ROOT/'build_progress.json').write_text(json.dumps({'family':FAMILY,'features':COUNT,'last':o.Label,'time':time.time()},indent=2))
    return Shape(o)
def placement(s,origin,rot):
    s.Placement=App.Placement(vec(origin),rot)
    for i,a in enumerate('xyz'): bind(s,'Placement.Base.'+a,origin[i])
def polygon(points,origin=(0,0,0),rot=None,label='profile'):
    s=new('Sketcher::SketchObject',label)
    placement(s,origin,rot or App.Rotation())
    n=len(points)
    s.addGeometry([Part.LineSegment(App.Vector(float(points[i][0]),float(points[i][1]),0),App.Vector(float(points[(i+1)%n][0]),float(points[(i+1)%n][1]),0)) for i in range(n)],False)
    for i in range(n): s.addConstraint(Sketcher.Constraint('Coincident',i,2,(i+1)%n,1))
    for i,(x,y) in enumerate(points):
        for axis,v in [('X',x),('Y',y)]:
            if abs(v)<1e-10:
                s.addConstraint(Sketcher.Constraint('PointOnObject',i,1,-2 if axis=='X' else -1))
            else:
                c=s.addConstraint(Sketcher.Constraint('Distance'+axis,i,1,float(v)))
                bind(s,'Constraints['+str(c)+']',v)
    D.recompute()
    if not s.FullyConstrained: raise RuntimeError('Underconstrained '+s.Name)
    return s

def circle(radius,origin,rot):
    s=new('Sketcher::SketchObject','circular profile'); placement(s,origin,rot)
    s.addGeometry(Part.Circle(App.Vector(),App.Vector(0,0,1),float(radius)),False)
    s.addConstraint(Sketcher.Constraint('Coincident',0,3,-1,1))
    c=s.addConstraint(Sketcher.Constraint('Radius',0,float(radius)))
    bind(s,'Constraints['+str(c)+']',radius)
    D.recompute(); return s

def extrude(sk,length):
    o=new('Part::Extrusion','extrude'); o.Base=sk
    o.DirMode='Normal'; o.LengthFwd=float(length); bind(o,'LengthFwd',length)
    o.Solid=True
    return update(o,[sk])

class Shape:
    def __init__(self,obj): self.obj=obj
    def val(self): return self
    def clean(self): return self
    def named(self,name): self.obj.Label=FAMILY+' — '+name; return self
    def union(self,other):
        o=new('Part::Fuse','join'); o.Base=self.obj; o.Tool=unwrap(other).obj; o.Refine=True
        return update(o,[self.obj,unwrap(other).obj])
    def cut(self,other):
        o=new('Part::Cut','remove'); o.Base=self.obj; o.Tool=unwrap(other).obj; o.Refine=True
        return update(o,[self.obj,unwrap(other).obj])
    def edges(self,selector): return Edges(self,selector)
    def translate(self,offset):
        o=new('Part::Compound','position'); o.Links=[self.obj]
        o.Placement=App.Placement(vec(offset),App.Rotation())
        for i,a in enumerate('xyz'): bind(o,'Placement.Base.'+a,offset[i])
        return update(o,[self.obj])
    def rotate(self,base,end,angle):
        o=new('Part::Compound','orient'); o.Links=[self.obj]
        rot=App.Rotation(vec(end)-vec(base),float(angle))
        p=App.Placement(vec(base)-rot.multVec(vec(base)),rot)
        o.Placement=p
        bind(o,'Placement.Rotation.Angle',angle)
        return update(o,[self.obj])
    def mirror(self,plane):
        o=new('Part::Mirroring','mirror '+plane); o.Source=self.obj; o.Normal={'YZ':App.Vector(1,0,0),'XZ':App.Vector(0,1,0),'XY':App.Vector(0,0,1)}[plane]
        return update(o)

def unwrap(x): return x.shape if isinstance(x,Workplane) else x
class Edges:
    def __init__(self,shape,selector): self.shape=shape; self.selector=selector
    def indices(self):
        edges=self.shape.obj.Shape.Edges; axis='XYZ'.index(self.selector[-1]); ids=[]
        if self.selector.startswith('|'):
            for i,e in enumerate(edges,1):
                if isinstance(e.Curve,Part.Line):
                    v=e.Vertexes[-1].Point-e.Vertexes[0].Point
                    if abs(abs(v[axis])-v.Length)<1e-7: ids.append(i)
        elif self.selector.startswith('>'):
            highest=max(e.CenterOfMass[axis] for e in edges)
            ids=[i for i,e in enumerate(edges,1) if abs(e.CenterOfMass[axis]-highest)<1e-7]
        else: raise NotImplementedError(self.selector)
        if not ids: raise RuntimeError('No edges '+self.selector)
        return ids
    def fillet(self,r): return self.finish('Part::Fillet',r)
    def chamfer(self,r): return self.finish('Part::Chamfer',r)
    def finish(self,t,r):
        o=new(t,t.split('::')[-1].lower()); o.Base=self.shape.obj
        o.Edges=[(i,float(r),float(r)) for i in self.indices()]
        return update(o,[self.shape.obj])

class Workplane:
    def __init__(self,plane='XY',origin=(0,0,0),obj=None):
        self.origin=origin
        self.rot={'XY':App.Rotation(),'YZ':App.Rotation(App.Vector(0,1,0),App.Vector(0,0,1),App.Vector(1,0,0),'ZXY'),'XZ':App.Rotation(App.Vector(1,0,0),90)}[plane]
        self.shape=unwrap(obj) if obj is not None else None
    def __getattr__(self,name): return getattr(self.shape,name)
    def polyline(self,pts): self.pts=pts; return self
    def close(self): return self
    def circle(self,r): self.radius=r; return self
    def extrude(self,length):
        s=circle(self.radius,self.origin,self.rot) if hasattr(self,'radius') else polygon(self.pts,self.origin,self.rot)
        return extrude(s,length)
    def box(self,w,h,d):
        s=polygon([(-w/2,-h/2),(w/2,-h/2),(w/2,h/2),(-w/2,h/2)],(0,0,-d/2))
        return extrude(s,d)
class Wire:
    @staticmethod
    def makePolygon(points,close=True):
        origin=points[0]; u=points[1]-origin; u.normalize(); v=points[-1]-origin; v.normalize(); n=u.cross(v); n.normalize()
        rot=App.Rotation(u,v,n,'ZXY'); inv=rot.inverted()
        pts=[inv.multVec(p-origin) for p in points]
        return polygon([(p.x,p.y) for p in pts],(origin.x,origin.y,origin.z),rot,'loft section')
class Solid:
    @staticmethod
    def makeLoft(wires,ruled=False):
        o=new('Part::Loft','ruled loft'); o.Sections=wires; o.Solid=True; o.Ruled=ruled; o.Linearize=True
        return update(o,wires)
    @staticmethod
    def makeCylinder(r,h,base,direction):
        s=circle(r,(base.x,base.y,base.z),App.Rotation(App.Vector(0,0,1),direction))
        return extrude(s,h)
Vector=App.Vector

def tag(value,name):
    if isinstance(value,(Shape,Workplane)) and unwrap(value) is not None: unwrap(value).named(name.replace('_',' '))
    return value
