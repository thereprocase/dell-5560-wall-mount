from pathlib import Path
import FreeCAD as App,FreeCADGui as Gui
ROOT=Path(__file__).resolve().parent
D=next(d for d in App.listDocuments().values() if d.FileName and Path(d.FileName).resolve()==(ROOT/'Precision_5560_Native.FCStd').resolve())
App.setActiveDocument(D.Name)
v=Gui.activeDocument().mdiViewsOfType('Gui::View3DInventor')[0]
v.getCameraOrientation()
v.getCameraNode().heightAngle=.35
v.fitAll(); Gui.updateGui(); v.saveImage(str(ROOT/'studio_preview.png'),1920,1440,'Current'); D.save()
