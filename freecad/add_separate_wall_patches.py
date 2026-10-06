from pathlib import Path
import json,shutil
import FreeCAD as A,FreeCADGui as G,Part,Sketcher
from PySide import QtCore
ROOT=Path(__file__).resolve().parent
D=next(d for d in A.listDocuments().values() if d.FileName and Path(d.FileName).resolve()==(ROOT/'Precision_5560_Native.FCStd').resolve())
assert not D.getObject('DuctBlendPatches')
D.save();shutil.copy2(D.FileName,ROOT/'BeforeSeparateWallPatches.FCStd');D.openTransaction('Separate loft-derived duct wall patches')
try:
 source=D.getObject('Compound027');before=source.Shape.copy();group=D.addObject('App::DocumentObjectGroup','DuctBlendPatches');group.Label='Duct wall patches - native loft surfaces'
 p=A.Placement(A.Vector(0,67,-84),A.Rotation(A.Vector(1,0,0),45)).multiply(A.Placement(A.Vector(0,-70,104),A.Rotation()))
 reference=D.addObject('Part::Common','OriginalWallSkin');reference.Base=D.getObject('Cut016');reference.Tool=D.getObject('MatchedOutline001').Base;reference.Refine=True;group.addObject(reference)
 patches=[]
 for x0,x1 in [(.5,5.5),(135.5,140.5)]:
  sk=D.addObject('Sketcher::SketchObject','WallPatchBoundary');sk.Label='Wall patch boundary - inlet corner';group.addObject(sk);sk.Placement=p.multiply(A.Placement(A.Vector(0,132,0),A.Rotation(A.Vector(1,0,0),90)))
  pts=[(x0,-105),(x1,-105),(x1,-90),(x0,-90)]
  for i,pt in enumerate(pts):
   j=sk.addGeometry(Part.LineSegment(A.Vector(*pt,0),A.Vector(*pts[(i+1)%4],0)),False);sk.addConstraint(Sketcher.Constraint('Block',j))
  extent=D.addObject('Part::Extrusion','PatchExtent');extent.Base=sk;extent.DirMode='Normal';extent.LengthFwd=16;extent.Solid=True;group.addObject(extent)
  patch=D.addObject('Part::Common','LoftSkinPatch');patch.Label='Continuous patch from original wall loft';patch.Base=reference;patch.Tool=extent;patch.Refine=True;group.addObject(patch);patches.append(patch)
 # Make the closure explicitly additive and independently editable.
 for name in ['MatchedOutline001','BlendedDuctCorners']:
  cut=D.getObject(name);guard=cut.Tool;assert guard.Name.startswith('ReliefOutsideWall');cut.Tool=guard.Base
 fuse=D.addObject('Part::MultiFuse','DuctWithWallPatches');fuse.Shapes=[source.Links[0]]+patches;fuse.Refine=True;group.addObject(fuse);source.Links=[fuse]
 D.recompute();assert not [o.Name for o in D.Objects if 'Invalid' in o.State]
 assert source.Shape.isValid() and len(source.Shape.Solids)==1
 missing=reference.Shape.cut(source.Shape);assert missing.Volume<1e-6,missing.Volume
 # Match the already-validated wall-preserving solid, now using separate patches.
 delta=source.Shape.cut(before).Volume+before.cut(source.Shape).Volume;assert delta<1e-4,delta
 links={o.InstanceKey:o for o in D.getObject('InstalledAssembly').Group if o.TypeId=='App::Link'};gaps={}
 for keys in [['04_right_fan_duct','06_right_fan_retainer','10_right_fan_tray'],['03_left_fan_duct','05_left_fan_retainer','09_left_fan_tray']]:
  for i,j in [(0,1),(0,2),(1,2)]:
   gap=links[keys[i]].Shape.distToShape(links[keys[j]].Shape)[0];assert abs(gap-.3)<1e-5;gaps[keys[i]+' / '+keys[j]]=gap
 for key,info in json.loads((ROOT/'frozen_print_arms/manifest.json').read_text())['parts'].items():
  arm=D.getObject(info['source']).Shape;ref=Part.read(str(ROOT/'frozen_print_arms'/info['file']));assert arm.cut(ref).Volume+ref.cut(arm).Volume<1e-6
 for o in group.Group:o.Visibility=False
 D.commitTransaction();D.save();shutil.copy2(D.FileName,ROOT/'FinishValidation.FCStd')
 (ROOT/'duct_blend_patches.json').write_text(json.dumps({'status':'done','construction':'Separate additive patches derived from the original native wall loft','wall_loss_mm3':missing.Volume,'difference_from_wall_preserving_solid_mm3':delta,'gaps_mm':gaps,'arms_difference_mm3':0,'patches_per_duct':2,'new_sketches':2},indent=2))
 # Inspect from the outboard side, with enough context to see the cap.
 v=G.activeDocument().mdiViewsOfType('Gui::View3DInventor')[0];q=A.Rotation(A.Vector(0,1,0),A.Vector(0,0,1),A.Vector(1,0,0),'ZXY');center=p.multVec(A.Vector(140,124,-98));node=v.getCameraNode();position=center+q.multVec(A.Vector(0,0,150));node.orientation.setValue(*q.Q);node.position.setValue(position.x,position.y,position.z);node.focalDistance.setValue(150);node.nearDistance.setValue(.1);node.farDistance.setValue(3000);G.updateGui()
 QtCore.QTimer.singleShot(1200,lambda:v.saveImage(str(ROOT/'duct_blended_patch.png'),1400,1000,'Current'))
 A.Console.PrintMessage('Separate loft-derived wall patches saved; wall continuity and all 0.30 mm fan fits verified.\n')
except Exception:D.abortTransaction();D.recompute();raise
