import FreeCAD as App, FreeCADGui as Gui
D=App.ActiveDocument
Gui.activeDocument().setEdit(D.getObject('Parameters').Name)
Gui.getMainWindow().showNormal()
Gui.getMainWindow().raise_()
Gui.updateGui()
