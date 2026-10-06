"""Replace three fragile edge-linked fillets with native dimensioned rounded sketches."""
from pathlib import Path
import sys,math,json
import FreeCAD as App,Part,Sketcher
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from native_ops import Expr,expr

def sqrt(x): return Expr(math.sqrt(float(x)),'sqrt('+expr(x)+')')
def V(p): return App.Vector(float(p[0]),float(p[1]),0)
def add(a,b): return (a[0]+b[0],a[1]+b[1])
def sub(a,b): return (a[0]-b[0],a[1]-b[1])
def mul(a,t): return (a[0]*t,a[1]*t)
def norm(a): return sqrt(a[0]*a[0]+a[1]*a[1])
def replace(d,names=None):
    made=[]
    selected=names or [o.Name for o in d.Objects if o.TypeId=='Part::Fillet']
    for oldname in selected:
        label=(d.getObject(oldname).Label if d.getObject(oldname) else oldname)+' — rounded sketch'
        old=d.getObject(oldname)
        if old is None: continue
        base=old.Base
        group=next(g for g in old.InList if g.TypeId=='App::DocumentObjectGroup')
        points=[]
        if base.TypeId=='Part::Extrusion':
            sharp=base.Base
            for i,g in enumerate(sharp.Geometry):
                xy=[]
                for axis,value in [('X',g.StartPoint.x),('Y',g.StartPoint.y)]:
                    cs=[j for j,c in enumerate(sharp.Constraints) if c.Type=='Distance'+axis and c.First==i and c.FirstPos==1]
                    xy.append(Expr(value,sharp.Name+'.Constraints['+str(cs[0])+'] / (1 mm)') if cs else value)
                points.append(tuple(xy))
            place=sharp.Placement; place_expressions=[(path,e) for path,e in sharp.ExpressionEngine if path.startswith('Placement')]
            length=base.LengthFwd.Value; length_expr=dict(base.ExpressionEngine).get('LengthFwd')
        else:
            # These sources are axis-aligned native boxes. Bound expressions keep
            # their own parametric dimensions while changing the extrusion plane.
            edge=base.Shape.Edges[old.Edges[0][0]-1]
            direction=edge.Vertexes[-1].Point-edge.Vertexes[0].Point
            axis=max(range(3),key=lambda i:abs(direction[i]))
            def bound(name): return Expr(getattr(base.Shape.BoundBox,name),base.Name+'.Shape.BoundBox.'+name)
            uv=[('Y','Z'),('X','Z'),('X','Y')][axis]
            u0,u1=bound(uv[0]+'Min'),bound(uv[0]+'Max'); v0,v1=bound(uv[1]+'Min'),bound(uv[1]+'Max')
            points=[(u0,v0),(u1,v0),(u1,v1),(u0,v1)]
            rot=[App.Rotation(App.Vector(0,1,0),App.Vector(0,0,1),App.Vector(1,0,0),'ZXY'),App.Rotation(App.Vector(1,0,0),90),App.Rotation()][axis]
            origin=[0.,0.,0.]; origin[axis]=float(bound('XYZ'[axis]+('Max' if axis==1 else 'Min')))
            place=App.Placement(App.Vector(*origin),rot)
            place_expressions=[('Placement.Base.'+'xyz'[axis],base.Name+'.Shape.BoundBox.'+'XYZ'[axis]+('Max' if axis==1 else 'Min'))]
            length=float(bound('XYZ'[axis]+'Length')); length_expr=base.Name+'.Shape.BoundBox.'+'XYZ'[axis]+'Length'
        s=d.addObject('Sketcher::SketchObject','RoundedProfile'); s.Label=label
        s.Placement=place
        for path,e in place_expressions: s.setExpression(path,e)
        s.addProperty('App::PropertyLength','CornerRadius','Design'); s.CornerRadius=old.Edges[0][1]
        radius=Expr(s.CornerRadius.Value,s.Name+'.CornerRadius / (1 mm)')
        tangents=[]
        existing_centers=[e.Curve.Center for e in old.Shape.Edges if isinstance(e.Curve,Part.Circle)]
        for i,p in enumerate(points):
            u=sub(points[(i-1)%len(points)],p); u=mul(u,1/norm(u))
            v=sub(points[(i+1)%len(points)],p); v=mul(v,1/norm(v))
            dot=u[0]*v[0]+u[1]*v[1]
            distance=radius*sqrt((1+dot)/(1-dot))
            a=add(p,mul(u,distance)); b=add(p,mul(v,distance))
            center=add(p,mul(add(u,v),distance/(1+dot)))
            toward=sub(p,center); mid=add(center,mul(toward,radius/norm(toward)))
            world_center=place.multVec(V(center))
            rounded=any((world_center-c).Length<1e-5 for c in existing_centers)
            tangents.append((a,mid,b,center,True) if rounded else (p,p,p,None,False))
        line_ids=[]; arc_ids=[]
        for i,(a,mid,b,center,rounded) in enumerate(tangents):
            prev=tangents[(i-1)%len(tangents)][2]
            line_ids.append(s.addGeometry(Part.LineSegment(V(prev),V(a)),False))
            arc_ids.append(s.addGeometry(Part.Arc(V(a),V(mid),V(b)),False) if rounded else None)
        for i,(a,mid,b,center,rounded) in enumerate(tangents):
            arc=arc_ids[i]; line=line_ids[i]
            if rounded:
                dims=[('X',3,center[0]),('Y',3,center[1])]
                for pos,p in [(1,a),(2,b)]:
                    axis=1 if abs(float(p[0]-center[0]))>abs(float(p[1]-center[1])) else 0
                    dims.append(('Y' if axis else 'X',pos,p[axis]))
                for axis,pos,value in dims:
                    c=s.addConstraint(Sketcher.Constraint('Distance'+axis,arc,pos,float(value)))
                    if isinstance(value,Expr): s.setExpression('Constraints['+str(c)+']',value.text)
                c=s.addConstraint(Sketcher.Constraint('Radius',arc,float(radius)))
                s.setExpression('Constraints['+str(c)+']',s.Name+'.CornerRadius')
                s.addConstraint(Sketcher.Constraint('Coincident',line,2,arc,1))
            else:
                for axis,value in [('X',a[0]),('Y',a[1])]:
                    if abs(float(value))<1e-10:
                        s.addConstraint(Sketcher.Constraint('PointOnObject',line,2,-2 if axis=='X' else -1))
                    else:
                        c=s.addConstraint(Sketcher.Constraint('Distance'+axis,line,2,float(value)))
                        if isinstance(value,Expr): s.setExpression('Constraints['+str(c)+']',value.text)
            prev=(i-1)%len(tangents)
            prev_geometry=arc_ids[prev] if arc_ids[prev] is not None else line_ids[prev]
            s.addConstraint(Sketcher.Constraint('Coincident',line,1,prev_geometry,2))
        d.recompute()
        if not s.FullyConstrained: raise RuntimeError('Rounded sketch is not fully constrained: '+s.Name+' '+s.getStatusString())
        ext=d.addObject('Part::Extrusion','RoundedExtrusion'); ext.Label=label+' — extrude'; ext.Base=s; ext.DirMode='Normal'; ext.LengthFwd=length; ext.Solid=True
        if length_expr: ext.setExpression('LengthFwd',length_expr)
        ext.addProperty('App::PropertyString','SourceLocation','Provenance'); ext.SourceLocation=old.SourceLocation
        d.recompute()
        ab=ext.Shape.cut(old.Shape); ba=old.Shape.cut(ext.Shape)
        circles=lambda shape:[{'center':list(e.Curve.Center),'radius':e.Curve.Radius,'length':e.Length} for e in shape.Edges if isinstance(e.Curve,Part.Circle)]
        (ROOT/'rounded_comparison_detail.json').write_text(json.dumps({'name':oldname,'new_valid':ext.Shape.isValid(),'cut_valid':[ab.isValid(),ba.isValid()],'cut_volume':[ab.Volume,ba.Volume],'new_circles':circles(ext.Shape),'old_circles':circles(old.Shape)},indent=2))
        if not ext.Shape.isValid() or not ab.isValid() or not ba.isValid() or abs(ab.Volume+ba.Volume)>1e-5: raise RuntimeError('Rounded replacement mismatch '+oldname+' '+str(ab.Volume+ba.Volume))
        for parent in list(old.InList):
            for prop in parent.PropertiesList:
                typ=parent.getTypeIdOfProperty(prop)
                if typ=='App::PropertyLink' and getattr(parent,prop)==old: setattr(parent,prop,ext)
                elif typ=='App::PropertyLinkList':
                    value=getattr(parent,prop)
                    if old in value: setattr(parent,prop,[ext if o==old else o for o in value])
        group.addObject(s); group.addObject(ext)
        s.Visibility=False; ext.Visibility=False
        d.removeObject(oldname)
        made.append(ext.Name)
    d.recompute(); return made

if __name__=='__main__':
    sys.path.insert(0,App.getResourceDir()+'Mod/Assembly')
    d=App.openDocument(str(ROOT/'ValidationSnapshot.FCStd'))
    made=replace(d)
    errors=[(o.Name,o.getStatusString()) for o in d.Objects if 'Invalid' in o.State]
    r={'replacements':made,'nominal_errors':errors}
    assert not errors,errors
    d.saveAs(str(ROOT/'RoundedValidation.FCStd'))
    p=d.getObject('Parameters'); p.set(p.getCellFromAlias('laptopThickness'),'=20.5 mm'); d.recompute()
    r['changed_errors']=[(o.Name,o.getStatusString()) for o in d.Objects if 'Invalid' in o.State]
    r['changed_valid']=all(o.Shape.isValid() for o in d.getObject('InstalledAssembly').Group if o.TypeId=='App::Link')
    (ROOT/'rounded_profile_validation.json').write_text(json.dumps(r,indent=2)); print(r,flush=True)
    App.closeDocument(d.Name)
