from pathlib import Path
import json,shutil
import FreeCAD as App,FreeCADGui as Gui,Part
ROOT=Path(__file__).resolve().parent
D=next(d for d in App.listDocuments().values() if d.FileName and Path(d.FileName).resolve()==(ROOT/'Precision_5560_Native.FCStd').resolve());App.setActiveDocument(D.Name)
right=next(o for o in D.Objects if o.TypeId!='App::Link' and getattr(o,'PartKey','')=='08_right_outlet_rail')
if D.getObject('RailTipRound'):raise RuntimeError('Tip round already exists')
D.openTransaction('Round teal tip; preserve printed arms')
try:
    base=right.Links[0]
    edges=[i for i,e in enumerate(base.Shape.Edges,1) if abs(e.BoundBox.YMin)<1e-6 and abs(e.BoundBox.YMax)<1e-6 and abs(e.BoundBox.ZMin-184.3)<1e-6 and abs(e.BoundBox.ZMax-184.3)<1e-6 and e.BoundBox.XMin>179.9]
    assert len(edges)==1
    tip=D.addObject('Part::Fillet','RailTipRound');tip.Label='Teal shoulder tip - R2';tip.Base=base;tip.Edges=[(edges[0],2.,2.)]
    D.getObject('RailRefinement').addObject(tip);right.Links=[tip]
    # Explicit reference values; this chamfer is edited through its native feature.
    P=D.getObject('Parameters');P.setAlias('B67','');P.set('F67','Reference');P.setBackground('B67',(.9,.91,.92));P.setForeground('B67',(.16,.19,.22))
    P.set('D67','0.6 mm native chamfer; edit feature Edges to change')
    P.set('A70','Teal shoulder tip radius');P.set('B70','2 mm');P.set('D70','Edit RailTipRound native fillet');P.set('F70','Reference')
    D.recompute()
    assert tip.Shape.isValid() and len(tip.Shape.Solids)==1
    assert not [o.Name for o in D.Objects if 'Invalid' in o.State]
    for key,info in json.loads((ROOT/'frozen_print_arms/manifest.json').read_text())['parts'].items():
        a=D.getObject(info['source']).Shape;b=Part.read(str(ROOT/'frozen_print_arms'/info['file']))
        ab=a.cut(b);ba=b.cut(a);assert ab.isValid() and ba.isValid() and abs(ab.Volume)+abs(ba.Volume)<1e-6
    tip.Visibility=False;base.Visibility=False
    D.commitTransaction();D.save();shutil.copy2(D.FileName,ROOT/'RailValidation.FCStd')
    Gui.updateGui();v=Gui.activeDocument().mdiViewsOfType('Gui::View3DInventor')[0]
    v.saveImage(str(ROOT/'rail_refinement_preview.png'),1920,1440,'Current')
    App.Console.PrintMessage('Teal R2 tip saved. Printed arms unchanged. GUI modeling pass finished.\n')
except Exception:D.abortTransaction();raise
