from pathlib import Path
import FreeCAD as App,FreeCADGui as Gui
from PySide import QtCore
ROOT=Path(__file__).resolve().parent
p=App.ParamGet('User parameter:BaseApp/Preferences/View')
p.SetUnsigned('BackgroundColor',0x9EA6ADFF)
p.SetBool('Gradient',False); p.SetBool('RadialGradient',False); p.SetBool('Simple',True)
App.saveParameter()
D=next(d for d in App.listDocuments().values() if d.FileName and Path(d.FileName).resolve()==(ROOT/'Precision_5560_Native.FCStd').resolve())
App.setActiveDocument(D.Name)
v=Gui.activeDocument().mdiViewsOfType('Gui::View3DInventor')[0]
v.redraw(); Gui.updateGui()
QtCore.QTimer.singleShot(1000,lambda:v.saveImage(str(ROOT/'cel_preview.png'),1920,1440,'Current'))
App.Console.PrintMessage('Solid slate background applied; illustration styling retained.\n')
