from pathlib import Path
import FreeCAD as App,FreeCADGui as Gui,json
ROOT=Path(__file__).resolve().parent; D=App.ActiveDocument
for o in D.getObject('InstalledAssembly').Group:
    if o.TypeId=='Assembly::JointGroup':
        o.Visibility=False
        for j in o.Group: j.Visibility=False
view=Gui.activeDocument().mdiViewsOfType('Gui::View3DInventor')[0]
rotation=App.Rotation(App.Vector(0,0,1),210).multiply(App.Rotation(App.Vector(1,0,0),65))
view.setCameraOrientation(rotation.Q); view.fitAll(); Gui.updateGui()
view.saveImage(str(ROOT/'assembly_preview.png'),1600,1200,'Current')
D.save()
Gui.activeDocument().setEdit(D.getObject('Parameters').Name)
Gui.updateGui(); Gui.getMainWindow().grab().save(str(ROOT/'parameter_sheet.png'))
(ROOT/'live_reopen_validation.json').write_text(json.dumps({'document':D.Name,'file':D.FileName,'invalid_features':[o.Name for o in D.Objects if 'Invalid' in o.State],'sketches':sum(o.TypeId=='Sketcher::SketchObject' for o in D.Objects)},indent=2))
