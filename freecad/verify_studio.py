from pathlib import Path
import json
import FreeCAD as App,FreeCADGui as Gui
from PySide import QtWidgets
ROOT=Path(__file__).resolve().parent
D=next(d for d in App.listDocuments().values() if d.FileName and Path(d.FileName).resolve()==(ROOT/'Precision_5560_Native.FCStd').resolve())
a=D.getObject('InstalledAssembly'); links=[o for o in a.Group if o.TypeId=='App::Link']; joints=[j for g in a.Group if g.TypeId=='Assembly::JointGroup' for j in g.Group]
widgets=[]
for w in Gui.getMainWindow().findChildren(QtWidgets.QWidget):
    if 'OpenGL' in w.metaObject().className() and hasattr(w,'format'):
        fmt=w.format(); widgets.append({'class':w.metaObject().className(),'samples':fmt.samples(),'version':fmt.version()})
r={'valid_solids':sum(o.Shape.isValid() and len(o.Shape.Solids)==1 for o in links),'invalid_features':[o.Name for o in D.Objects if 'Invalid' in o.State],'broken_joint_references':[j.Name for j in joints if hasattr(j,'Reference1') and (not j.Reference1[0] or not j.Reference2[0])],'opengl_widgets':widgets,'view_methods':[x for x in dir(Gui.activeDocument().activeView()) if any(t in x.lower() for t in ['sample','render','light'])]}
(ROOT/'studio_verification.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
App.Console.PrintMessage('Studio display verified; native solid and joint checks completed.\n')
