from PySide import QtWidgets
import FreeCADGui as G
for t in G.getMainWindow().findChildren(QtWidgets.QToolBar):
 if t.objectName() not in ['File','Edit','Workbench','View','FusionTabs','FusionCommands']:t.hide()
G.updateGui()
