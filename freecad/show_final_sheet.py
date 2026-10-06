from pathlib import Path
import FreeCAD as App,FreeCADGui as Gui
from PySide import QtWidgets,QtCore
ROOT=Path(__file__).resolve().parent
D=next(d for d in App.listDocuments().values() if Path(d.FileName).resolve()==(ROOT/'Precision_5560_Native.FCStd').resolve())
App.setActiveDocument(D.Name)
P=D.getObject('Parameters')
P.setForeground('A4:F4',(.08,.14,.18))
for cell in P.getNonEmptyCells():
    if P.getAlias(cell): P.setForeground('E'+cell[1:],(.08,.20,.12))
D.save()
mdi=Gui.getMainWindow().findChild(QtWidgets.QMdiArea)
sheets=[w for w in mdi.subWindowList() if w.widget().metaObject().className()=='SpreadsheetGui::SheetView']
assert len(sheets)==1
sheet=sheets[0]; mdi.setActiveSubWindow(sheet); sheet.showMaximized(); Gui.updateGui()
def capture():
    sheet.widget().grab().save(str(ROOT/'parameter_sheet.png'))
QtCore.QTimer.singleShot(1500,capture)
App.Console.PrintMessage('Final native model and organized parameter sheet saved.\n')
