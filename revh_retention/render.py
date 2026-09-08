"""Capture review images from the installed native solids in FreeCAD's GUI."""
from pathlib import Path
import hashlib
import FreeCAD as App
import FreeCADGui as Gui
import Part
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'revh_retention/Precision_5560_RevH_Removable_Retainers.FCStd'
OUT=ROOT/'docs/assets'

def run():
    sha=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    doc=next((d for d in App.listDocuments().values() if Path(d.FileName)==SOURCE),None)
    if doc is None:doc=App.openDocument(str(SOURCE))
    parts={o.InstanceKey:o.Shape.copy() for name in ['BaselineAssembly','RetentionAssembly']
           for o in doc.getObject(name).Group if o.TypeId=='App::Link'}
    def capture(name,selected,direction=(1,1,.7),crop=None,explode=False):
        show=App.newDocument('RetainerReview')
        for key in selected:
            shape=parts[key].copy()
            if crop is not None:shape=shape.common(crop)
            if shape.isNull() or shape.Volume<1e-6:continue
            if explode and 'side_retainer' in key:shape.translate(App.Vector(35,0,0))
            if explode and 'retainer_keeper' in key:shape.translate(App.Vector(0,0,-16))
            obj=show.addObject('Part::Feature','Display'+key.replace('_',''));obj.Shape=shape
            obj.ViewObject.ShapeColor=(.97,.56,.16) if 'side_retainer' in key else (.35,.80,.35) if 'retainer_keeper' in key else (.32,.39,.43) if 'cradle' in key else (.13,.53,.54)
            obj.ViewObject.LineColor=(.10,.17,.19);obj.ViewObject.DisplayMode='Flat Lines'
        show.recompute();view=Gui.activeDocument().activeView();view.setCameraType('Orthographic')
        back=App.Vector(*direction);back.normalize();right=App.Vector(0,0,1).cross(back);right.normalize();up=back.cross(right)
        view.getCameraNode().orientation.setValue(*App.Rotation(right,up,back,'ZXY').Q)
        view.fitAll();camera=view.getCameraNode();camera.height.setValue(camera.height.getValue()*(1.3 if crop is None else 1.08));Gui.updateGui();view.saveImage(str(OUT/name),1600,1100,'White')
        App.closeDocument(show.Name)
    capture('revh-retainers-installed.png',list(parts))
    right=[k for k in parts if 'right' in k]
    capture('revh-retainers-removed.png',right,explode=True)
    capture('revh-retainers-lower.png',right,(-1,1,.7),Part.makeBox(31,60,85,App.Vector(164,10,-58)))
    capture('revh-retainers-upper.png',right,(1,1,.7),Part.makeBox(31,39,48,App.Vector(164,12,145)))
    App.setActiveDocument(doc.Name)
    Gui.activeDocument().activeView().viewAxonometric();Gui.activeDocument().activeView().fitAll();Gui.updateGui()
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==sha
    App.Console.PrintMessage('H-R1 native review images saved; source file unchanged.\n')

if __name__=='__main__':run()
