"""Native sketches and features only. Millimetre expression interface.

Construction geometry is origin-referenced, never attached to generated faces.
Profile vertices are driven by datum ordinate dimensions; only datum axes are fixed.
"""
import adsk.core as c
import adsk.fusion as f
from contextlib import contextmanager
import math
import re

def ex(v):
    return str(v) if isinstance(v, str) else f'{v:.10g} mm'

def add(a,b): return f'({ex(a)})+({ex(b)})'
def sub(a,b): return f'({ex(a)})-({ex(b)})'
def neg(a): return f'-({ex(a)})'
def coll(items):
    o=c.ObjectCollection.create()
    for i in items: o.add(i)
    return o

class Builder:
    def __init__(self,design,component,prefix):
        self.d=design;self.c=component;self.prefix=prefix
        self.sketches=[];self.groups=[]

    def param(self,name,value,comment=''):
        name=self.prefix+'_'+name
        if not self.d.userParameters.itemByName(name):
            p=self.d.userParameters.add(name,c.ValueInput.createByString(ex(value)),'mm',comment)
            p.isFavorite=True
        return name

    def value(self,v):
        return self.d.unitsManager.evaluateExpression(ex(v),'mm')*10

    @contextmanager
    def group(self,name):
        start=self.d.timeline.count
        yield
        end=self.d.timeline.count-1
        if end>=start:
            g=self.d.timeline.timelineGroups.add(start,end)
            g.name=self.prefix+' | '+name
            g.isCollapsed=True
            self.groups.append(g)

    def plane(self,name,kind,offset):
        base={'XY':self.c.xYConstructionPlane,'XZ':self.c.xZConstructionPlane,'YZ':self.c.yZConstructionPlane}[kind]
        axis={'XY':2,'XZ':1,'YZ':0}[kind]
        normal=[base.geometry.normal.x,base.geometry.normal.y,base.geometry.normal.z][axis]
        if ex(offset) in ('0 mm','0'):
            return base
        inp=self.c.constructionPlanes.createInput()
        inp.setByOffset(base,c.ValueInput.createByString(ex(offset) if normal>0 else neg(offset)))
        p=self.c.constructionPlanes.add(inp);p.name=name+' | datum';p.isLightBulbOn=False
        return p

    def sketch(self,name,kind,offset):
        s=self.c.sketches.add(self.plane(name,kind,offset));s.name=name+' | profile'
        self.sketches.append(s)
        return s

    def modelpoint(self,kind,offset,u,v):
        uv=[self.value(u)/10,self.value(v)/10];o=self.value(offset)/10
        xyz={'XY':(uv[0],uv[1],o),'XZ':(uv[0],o,uv[1]),'YZ':(o,uv[0],uv[1])}[kind]
        return c.Point3D.create(*xyz)

    def constrain_points(self,s,points,expressions):
        lines=s.sketchCurves.sketchLines
        ax=lines.addByTwoPoints(c.Point3D.create(-1,0,0),c.Point3D.create(1,0,0))
        ay=lines.addByTwoPoints(c.Point3D.create(0,-1,0),c.Point3D.create(0,1,0))
        for a in (ax,ay):
            a.isConstruction=True
            a.startSketchPoint.isFixed=True
            a.endSketchPoint.isFixed=True
        ori=[f.DimensionOrientations.HorizontalDimensionOrientation,f.DimensionOrientations.VerticalDimensionOrientation]
        for p,expr in zip(points,expressions):
            xyz=[p.geometry.x,p.geometry.y]
            if abs(xyz[0])+abs(xyz[1])<1e-9:
                s.geometricConstraints.addCoincident(p,s.originPoint)
                continue
            for k in range(2):
                if abs(xyz[k])<1e-9:
                    s.geometricConstraints.addCoincident(p,ay if k==0 else ax)
                else:
                    try:
                        dim=s.sketchDimensions.addDistanceDimension(s.originPoint,p,ori[k],
                            c.Point3D.create(p.geometry.x+.2+k*.2,p.geometry.y+.2+k*.2,0))
                    except Exception as error:
                        raise RuntimeError(f'{s.name}: coordinate {k}, point {xyz}, expression {expr[k]}: {error}') from error
                    dim.parameter.expression=expr[k] if xyz[k]>0 else neg(expr[k])

    def polygon(self,name,kind,offset,pts):
        s=self.sketch(name,kind,offset)
        s.isComputeDeferred=True
        # Infer exact local sketch coordinate signs from the origin plane basis.
        q0=s.modelToSketchSpace(self.modelpoint(kind,offset,0,0))
        qu=s.modelToSketchSpace(self.modelpoint(kind,offset,1,0))
        qv=s.modelToSketchSpace(self.modelpoint(kind,offset,0,1))
        def exprs(u,v):
            out=[]
            for a in ('x','y'):
                ku=round((getattr(qu,a)-getattr(q0,a))*10)
                kv=round((getattr(qv,a)-getattr(q0,a))*10)
                out.append(ex(u) if ku==1 else neg(u) if ku==-1 else ex(v) if kv==1 else neg(v))
            return out
        points=[s.sketchPoints.add(s.modelToSketchSpace(self.modelpoint(kind,offset,u,v))) for u,v in pts]
        edges=[s.sketchCurves.sketchLines.addByTwoPoints(p,q) for p,q in zip(points,points[1:]+points[:1])]
        rectangle=(len(pts)==4 and ex(pts[0][0])==ex(pts[3][0]) and ex(pts[1][0])==ex(pts[2][0])
                   and ex(pts[0][1])==ex(pts[1][1]) and ex(pts[2][1])==ex(pts[3][1]))
        if rectangle:
            self.constrain_points(s,points[:1],[exprs(*pts[0])])
            for edge in edges:
                p=edge.startSketchPoint.geometry;q=edge.endSketchPoint.geometry
                if abs(p.y-q.y)<1e-8:s.geometricConstraints.addHorizontal(edge)
                else:s.geometricConstraints.addVertical(edge)
            for edge,delta in zip(edges[:2],(sub(pts[1][0],pts[0][0]),sub(pts[2][1],pts[1][1]))):
                dim=s.sketchDimensions.addDistanceDimension(edge.startSketchPoint,edge.endSketchPoint,
                    f.DimensionOrientations.AlignedDimensionOrientation,edge.endSketchPoint.geometry)
                dim.parameter.expression=delta if self.value(delta)>0 else neg(delta)
        else:
            self.constrain_points(s,points[:1],[exprs(*pts[0])])
            for i,edge in enumerate(edges[:-1]):
                p=points[i];q=points[i+1]
                start=exprs(*pts[i]);end=exprs(*pts[i+1])
                dx=q.geometry.x-p.geometry.x;dy=q.geometry.y-p.geometry.y
                if abs(dx)<1e-9 or abs(dy)<1e-9:
                    if abs(dx)<1e-9:s.geometricConstraints.addVertical(edge);k=1
                    else:s.geometricConstraints.addHorizontal(edge);k=0
                    dim=s.sketchDimensions.addDistanceDimension(p,q,f.DimensionOrientations.AlignedDimensionOrientation,q.geometry)
                    delta=sub(end[k],start[k]);dim.parameter.expression=delta if (dy if k else dx)>0 else neg(delta)
                else:
                    for k,ori in enumerate((f.DimensionOrientations.HorizontalDimensionOrientation,f.DimensionOrientations.VerticalDimensionOrientation)):
                        dim=s.sketchDimensions.addDistanceDimension(p,q,ori,c.Point3D.create(q.geometry.x+.1,q.geometry.y+.1,0))
                        delta=sub(end[k],start[k]);dim.parameter.expression=delta if (dy if k else dx)>0 else neg(delta)
        s.isComputeDeferred=False
        if not s.isFullyConstrained: raise RuntimeError('Underconstrained profile: '+name)
        if s.profiles.count!=1: raise RuntimeError('Unexpected profiles: '+name+': '+str(s.profiles.count))
        return s

    def extrude(self,name,s,depth,kind):
        inp=self.c.features.extrudeFeatures.createInput(s.profiles.item(0),f.FeatureOperations.NewBodyFeatureOperation)
        normal=s.referencePlane.geometry.normal
        desired={'XY':c.Vector3D.create(0,0,1),'XZ':c.Vector3D.create(0,-1,0),'YZ':c.Vector3D.create(1,0,0)}[kind]
        distance=ex(depth) if normal.dotProduct(desired)>0 else neg(depth)
        inp.setDistanceExtent(False,c.ValueInput.createByString(distance))
        feat=self.c.features.extrudeFeatures.add(inp);feat.name=name+' | extrude'
        body=feat.bodies.item(0);body.name=name;s.isVisible=False
        return body

    def prism(self,name,plane,offset,pts,depth,fillet=0):
        s=self.polygon(name,plane,offset,pts)
        body=self.extrude(name,s,depth,plane)
        if fillet:body=self.fillet(name,body,fillet,{'XY':'Z','XZ':'Y','YZ':'X'}[plane])
        return body

    def box(self,name,x0,x1,y0,y1,z0,z1,fillet=0,axis='X'):
        if axis=='X':return self.prism(name,'YZ',x0,[(y0,z0),(y1,z0),(y1,z1),(y0,z1)],sub(x1,x0),fillet)
        if axis=='Y':return self.prism(name,'XZ',y1,[(x0,z0),(x1,z0),(x1,z1),(x0,z1)],sub(y1,y0),fillet)
        return self.prism(name,'XY',z0,[(x0,y0),(x1,y0),(x1,y1),(x0,y1)],sub(z1,z0),fillet)

    def fillet(self,name,body,r,axis):
        omitted=[]
        if isinstance(r,dict):
            omitted=r.get('omit_vertices',[]);r=r['radius']
        vector={'X':c.Vector3D.create(1,0,0),'Y':c.Vector3D.create(0,1,0),'Z':c.Vector3D.create(0,0,1)}[axis]
        edges=[e for e in body.edges if isinstance(e.geometry,c.Line3D) and e.geometry.startPoint.vectorTo(e.geometry.endPoint).isParallelTo(vector)]
        def retained(e):
            p=e.geometry.startPoint
            uv={'X':(p.y*10,p.z*10),'Y':(p.x*10,p.z*10),'Z':(p.x*10,p.y*10)}[axis]
            return not any(abs(uv[0]-self.value(a))<1e-5 and abs(uv[1]-self.value(b))<1e-5 for a,b in omitted)
        edges=[e for e in edges if retained(e)]
        if not edges: raise RuntimeError('No axial edges: '+name)
        inp=self.c.features.filletFeatures.createInput()
        inp.edgeSetInputs.addConstantRadiusEdgeSet(coll(edges),c.ValueInput.createByString(ex(r)),False)
        feat=self.c.features.filletFeatures.add(inp);feat.name=name+' | section radii'
        return feat.bodies.item(0)

    def boolean(self,name,target,tools,op):
        if not tools:return target
        inp=self.c.features.combineFeatures.createInput(target,coll(tools));inp.operation=op;inp.isKeepToolBodies=False
        feat=self.c.features.combineFeatures.add(inp);feat.name=name
        return feat.bodies.item(0)

    def join(self,name,*bodies):return self.boolean(name,bodies[0],bodies[1:],f.FeatureOperations.JoinFeatureOperation)
    def cut(self,name,body,*tools):return self.boolean(name,body,tools,f.FeatureOperations.CutFeatureOperation)
    def intersect(self,name,body,*tools):return self.boolean(name,body,tools,f.FeatureOperations.IntersectFeatureOperation)

    def cylinder(self,name,r,h,base,axis='Y'):
        x,y,z=base
        kind,offset,uv=('XZ',add(y,h),(x,z)) if axis=='Y' else ('XY',z,(x,y))
        s=self.sketch(name,kind,offset)
        pt=s.modelToSketchSpace(self.modelpoint(kind,offset,*uv))
        circle=s.sketchCurves.sketchCircles.addByCenterRadius(pt,self.value(r)/10)
        q0=s.modelToSketchSpace(self.modelpoint(kind,offset,0,0));qu=s.modelToSketchSpace(self.modelpoint(kind,offset,1,0));qv=s.modelToSketchSpace(self.modelpoint(kind,offset,0,1))
        es=[]
        for a in ('x','y'):
            ku=round((getattr(qu,a)-getattr(q0,a))*10);kv=round((getattr(qv,a)-getattr(q0,a))*10)
            es.append(ex(uv[0]) if ku==1 else neg(uv[0]) if ku==-1 else ex(uv[1]) if kv==1 else neg(uv[1]))
        self.constrain_points(s,[circle.centerSketchPoint],[es])
        dim=s.sketchDimensions.addDiameterDimension(circle,c.Point3D.create(pt.x+1,pt.y+1,0));dim.parameter.expression=f'2*({ex(r)})'
        if not s.isFullyConstrained:raise RuntimeError('Underconstrained circle '+name)
        return self.extrude(name,s,h,kind)

    def roof_hole(self,name,r,h,base,roof='-X',bridge=1.2):
        x,y,z=base;q=f'({ex(r)})/sqrt(2)';tip=sub(f'2*({q})',f'({ex(bridge)})/2')
        uv=[(q,neg(q)),(tip,f'-({ex(bridge)})/2'),(tip,f'({ex(bridge)})/2'),(q,q)]
        pts=[]
        for u,v in uv:
            pts.append((sub(x,u),add(z,v)) if roof=='-X' else (add(x,v),add(z,u)) if roof=='+Z' else (add(x,v),sub(z,u)))
        return self.join(name+' | printable bore',self.cylinder(name+' bore',r,h,base),self.prism(name+' roof','XZ',add(y,h),pts,h))

    def keys(self,name,kind,clearance=0):
        spec=[(146,154,-59,-19),(167,175,-59,-19)] if kind=='duct' else [(143,152,156,164),(168,177,156,164)]
        result=[]
        for i,(a,b,z0,z1) in enumerate(spec):
            a=add('wallBoltX',a-162);b=add('wallBoltX',b-162)
            datum='lowerWallBoltZ' if kind=='duct' else 'upperWallBoltZ'
            nominal=-36 if kind=='duct' else 174
            z0=add(datum,z0-nominal);z1=add(datum,z1-nominal)
            n=name+f' {i+1}'
            if clearance:
                y0=sub(14,clearance);y1=add(26.6,clearance)
                pts=[(sub(a,clearance),y0),(add(b,clearance),y0),(add(b,clearance),y1),(sub(sub(a,clearance),sub(y1,y0)),y1)]
                top=add(add(z1,clearance),12.6 if kind=='rail' else 0)
                result.append(self.prism(n,'XY',sub(z0,clearance),pts,sub(top,sub(z0,clearance))))
            elif kind=='rail':result.append(self.prism(n,'YZ',a,[(14,z0),(26.6,z0),(26.6,add(z1,12.6)),(14,z1)],sub(b,a)))
            else:result.append(self.box(n,a,b,14,26.6,z0,z1))
        return result

    def tongue(self,name,cx,y0,y1,clearance=False):
        if clearance:
            pts=[(sub(cx,1.8),-110.3),(add(cx,1.8),-110.3),(add(cx,3.3),-108),(add(cx,3.3),-107.7),(sub(cx,3.3),-107.7),(sub(cx,3.3),-108)]
        else:pts=[(sub(cx,1.5),-110.1),(add(cx,1.5),-110.1),(add(cx,3),-108),(sub(cx,3),-108)]
        return self.prism(name,'XZ',y1,pts,sub(y1,y0))

    def pattern(self,name,body,axis,quantity,spacing):
        before={b.entityToken for b in self.c.bRepBodies}
        direction={'X':self.c.xConstructionAxis,'Y':self.c.yConstructionAxis,'Z':self.c.zConstructionAxis}[axis]
        inp=self.c.features.rectangularPatternFeatures.createInput(coll([body]),direction,
            c.ValueInput.createByString(str(quantity)),c.ValueInput.createByString(ex(spacing)),f.PatternDistanceType.SpacingPatternDistanceType)
        feat=self.c.features.rectangularPatternFeatures.add(inp);feat.name=name
        return [body]+[b for b in self.c.bRepBodies if b.entityToken not in before]

    def translate(self,name,body,x,y,z):
        inp=self.c.features.moveFeatures.createInput2(coll([body]))
        inp.defineAsTranslateXYZ(*[c.ValueInput.createByString(ex(v)) for v in (x,y,z)],True)
        feat=self.c.features.moveFeatures.add(inp);feat.name=name
        return feat.bodies.item(0)

    def rotate_x(self,name,body,angle):
        occurrence=self.d.rootComponent.occurrencesByComponent(self.c).item(0)
        axis=self.c.xConstructionAxis.createForAssemblyContext(occurrence)
        inp=self.c.features.moveFeatures.createInput2(coll([body]))
        inp.defineAsRotate(axis,c.ValueInput.createByString(angle))
        feat=self.c.features.moveFeatures.add(inp);feat.name=name
        return feat.bodies.item(0)

    def tilt(self,name,body):
        body=self.translate(name+' | fan pivot',body,0,-70,104)
        body=self.rotate_x(name+' | inclination',body,'fanAngle')
        return self.translate(name+' | installed datum',body,0,'fanCenterY','fanCenterZ')

    def section(self,name,L,R,inner=False):
        # Section plane follows a constrained station line in the YZ datum sketch.
        datum=self.sketch(name+' station','YZ',0)
        p=[datum.sketchPoints.add(datum.modelToSketchSpace(self.modelpoint('YZ',0,*v))) for v in (L,R)]
        line=datum.sketchCurves.sketchLines.addByTwoPoints(*p);line.isConstruction=True
        # YZ built-in sketch coordinates are derived explicitly.
        q0=datum.modelToSketchSpace(self.modelpoint('YZ',0,0,0))
        qu=datum.modelToSketchSpace(self.modelpoint('YZ',0,1,0));qv=datum.modelToSketchSpace(self.modelpoint('YZ',0,0,1))
        expressions=[]
        for u,v in (L,R):
            es=[]
            for a in ('x','y'):
                ku=round((getattr(qu,a)-getattr(q0,a))*10);kv=round((getattr(qv,a)-getattr(q0,a))*10)
                es.append(ex(u) if ku==1 else neg(u) if ku==-1 else ex(v) if kv==1 else neg(v))
            expressions.append(es)
        self.constrain_points(datum,p,expressions)
        inp=self.c.constructionPlanes.createInput();inp.setByAngle(line,c.ValueInput.createByString('90 deg'),self.c.yZConstructionPlane)
        plane=self.c.constructionPlanes.add(inp);plane.name=name+' | station plane';plane.isLightBulbOn=False;datum.isVisible=False
        s=self.c.sketches.add(plane);s.name=name+' | section';self.sketches.append(s)
        dy=R[0]-L[0];dz=R[1]-L[1];n=math.hypot(dy,dz)
        a=[add(L[0],f'ductSkin*{dy/n:.12g}'),add(L[1],f'ductSkin*{dz/n:.12g}')] if inner else L
        z=[sub(R[0],f'ductSkin*{dy/n:.12g}'),sub(R[1],f'ductSkin*{dz/n:.12g}')] if inner else R
        x0='1 mm+ductSkin' if inner else 1;x1='140 mm-ductSkin' if inner else 140
        world=[(x0,*a),(x1,*a),(x1,*z),(x0,*z)]
        origin=s.modelToSketchSpace(c.Point3D.create(0,0,0))
        bases=[s.modelToSketchSpace(c.Point3D.create(*v)) for v in ((1,0,0),(0,1,0),(0,0,1))]
        ps=[];es=[]
        for xyz in world:
            ps.append(s.sketchPoints.add(s.modelToSketchSpace(c.Point3D.create(*[self.value(v)/10 for v in xyz]))))
            es.append([' + '.join([ex(getattr(origin,axis)*10)]+[f'({ex(v)})*{getattr(b,axis)-getattr(origin,axis):.12g}' for v,b in zip(xyz,bases)]) for axis in ('x','y')])
        edges=[s.sketchCurves.sketchLines.addByTwoPoints(p,q) for p,q in zip(ps,ps[1:]+ps[:1])]
        self.constrain_points(s,ps[:1],es[:1])
        for edge in edges:
            if abs(edge.startSketchPoint.geometry.y-edge.endSketchPoint.geometry.y)<1e-7:
                s.geometricConstraints.addHorizontal(edge)
            else:s.geometricConstraints.addVertical(edge)
        for i,edge in enumerate(edges[:2]):
            p=edge.startSketchPoint.geometry;q=edge.endSketchPoint.geometry
            k=0 if abs(q.x-p.x)>abs(q.y-p.y) else 1
            delta=sub(es[i+1][k],es[i][k])
            dim=s.sketchDimensions.addDistanceDimension(edge.startSketchPoint,edge.endSketchPoint,
                f.DimensionOrientations.AlignedDimensionOrientation,q)
            dim.parameter.expression=delta if self.value(delta)>0 else neg(delta)
        if not s.isFullyConstrained:raise RuntimeError('Underconstrained section '+name)
        return s

    def loft(self,name,a,b):
        inp=self.c.features.loftFeatures.createInput(f.FeatureOperations.NewBodyFeatureOperation)
        inp.loftSections.add(a.profiles.item(0));inp.loftSections.add(b.profiles.item(0))
        inp.isSolid=True
        feat=self.c.features.loftFeatures.add(inp);feat.name=name
        a.isVisible=False;b.isVisible=False
        return feat.bodies.item(0)
