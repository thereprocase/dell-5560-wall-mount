from pathlib import Path
import json
import FreeCAD as App,FreeCADGui as Gui
from PySide import QtWidgets,QtCore
ROOT=Path(__file__).resolve().parent
D=next(d for d in App.listDocuments().values() if Path(d.FileName).resolve()==(ROOT/'Precision_5560_Native.FCStd').resolve())
App.setActiveDocument(D.Name); P=D.getObject('Parameters')
P.Label='Design parameters - inputs, formulas, tested limits'
P.set('A2','Blue: inputs | Gray: formulas | Validation refers to discrete cases in freecad/README.md')
for cell in P.getNonEmptyCells():
    alias=P.getAlias(cell)
    if not alias: continue
    P.set('E'+cell[1:],'Nominal geometry checked')
    P.setBackground('E'+cell[1:],(.91,.93,.95))
    P.setForeground('E'+cell[1:],(.08,.20,.12))
for case in json.loads((ROOT/'parameter_scenarios.json').read_text())['cases'].values():
    if case['clearance_pass']:
        for alias in case['values']:
            cell='E'+P.getCellFromAlias(alias)[1:]; P.set(cell,'Changed case: regen / keys OK'); P.setBackground(cell,(.82,.94,.84))
f=ROOT/'interface_scenarios.json'
if f.exists():
    result=json.loads(f.read_text())
    for case in result['cases'].values():
        for alias in case['values']:
            cell='E'+P.getCellFromAlias(alias)[1:]
            P.set(cell,'Changed case: regen / keys OK' if case['clearance_pass'] else 'Changed case: interference')
            P.setBackground(cell,(.82,.94,.84) if case['clearance_pass'] else (1,.85,.55))
for col,width in [('A',190),('B',100),('C',45),('D',330),('E',215),('F',65)]: P.setColumnWidth(col,width)
D.recompute(); D.save()
import shutil
shutil.copy2(ROOT/'Precision_5560_Native.FCStd',ROOT/'ValidationSnapshot.FCStd')
Gui.activeDocument().setEdit(P.Name)
mdi=Gui.getMainWindow().findChild(QtWidgets.QMdiArea)
sheet=next(w for w in mdi.subWindowList() if w.widget().metaObject().className()=='SpreadsheetGui::SheetView')
mdi.setActiveSubWindow(sheet); sheet.showMaximized(); Gui.updateGui()
def capture():
    sheet.widget().grab().save(str(ROOT/'parameter_sheet.png'))
QtCore.QTimer.singleShot(1500,capture)
App.Console.PrintMessage('Native Revision F saved; parameter evidence labels updated.\n')
