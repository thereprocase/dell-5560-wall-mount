from PySide import QtCore,QtWidgets
import FreeCAD as App,FreeCADGui as Gui
r,b,t=App._studio_ribbon
t.setTabText(2,'SOLID');t.setUsesScrollButtons(False);t.setElideMode(QtCore.Qt.ElideNone);t.setMinimumWidth(540);t.setSizePolicy(QtWidgets.QSizePolicy.Minimum,QtWidgets.QSizePolicy.Fixed)
Gui.updateGui()
