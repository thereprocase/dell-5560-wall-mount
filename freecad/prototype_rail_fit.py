from pathlib import Path
import json,sys
import FreeCAD as A,Part
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,A.getResourceDir()+'Mod/Assembly')
d=A.openDocument(str(ROOT/'BeforeRailFit.FCStd'))
cradle=Part.read(str(ROOT/'frozen_print_arms/02_right_cradle.brep'))
rail=next(o.Shape for o in d.Objects if o.TypeId!='App::Link' and getattr(o,'PartKey','')=='08_right_outlet_rail')
plane=Part.makePlane(500,500,A.Vector(182,-150,-150),A.Vector(1,0,0))
# A large explicit YZ face guarantees section bounds independent of plane orientation.
plane=Part.Face(Part.makePolygon([A.Vector(182,y,z) for y,z in [(-100,-100),(200,-100),(200,300),(-100,300),(-100,-100)]]))
section=cradle.section(plane)
wires=[Part.Wire(edges) for edges in Part.sortEdges(section.Edges)]
outer=max(wires,key=lambda w:Part.Face(w).Area)
face=Part.Face(outer); enlarged=face.makeOffset2D(.30,join=0,fill=False)
print('OFFSET',enlarged.ShapeType,len(enlarged.Wires),enlarged.isValid(),flush=True)
wire=enlarged.OuterWire if enlarged.ShapeType=='Face' else enlarged.Wires[0]
wire.exportBrep(str(ROOT/'arm_clearance_profile.brep'))
pocket=Part.Face(wire).extrude(A.Vector(3,0,0)).fuse(Part.Face(wire).extrude(A.Vector(-43,0,0)))
side=Part.makeBox(4,26.3,44,A.Vector(180,0,154))
back=Part.makeBox(44,2,48,A.Vector(140,0,184))
# Remove the full insertion envelope at the top shoulder; matching a rear-facing undercut would trap the rail.
pocket=pocket.fuse(Part.makeBox(46,8.3,31,A.Vector(139,-2,153.3)))
patch=side.cut(pocket)
driver=Part.makeCylinder(10,60,A.Vector(162,-1,174),A.Vector(0,1,0))
patch=patch.cut(driver)
roof=Part.makeBox(183.8,28,2,A.Vector(.2,0,230))
# Outboard end cover extends over the side window, outside the central exhaust span.
end=Part.makeBox(44,11,2,A.Vector(140,28,230))
result=rail.fuse(patch).fuse(roof).fuse(end).removeSplitter()
result.exportBrep(str(ROOT/'rail_fit_candidate.brep'))
report={'valid':result.isValid(),'solids':len(result.Solids),'added_volume':result.Volume-rail.Volume,'arm_overlap':result.common(cradle).Volume,'service':{}}
for y in [0,.3,1,3,10,30,60]:
 q=result.copy();q.translate(A.Vector(0,y,0));c=q.common(cradle);report['service'][str(y)]={'volume':c.Volume,'bbox':str(c.BoundBox)}
print(json.dumps(report),flush=True)
(ROOT/'rail_fit_prototype.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
A.closeDocument(d.Name)
