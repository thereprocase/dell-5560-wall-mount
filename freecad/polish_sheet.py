from pathlib import Path
import FreeCAD as App,FreeCADGui as Gui
ROOT=Path(__file__).resolve().parent; D=App.ActiveDocument; P=D.getObject('Parameters')
derived={'bareSlot','wallHoleHalfSpacing','contractionStartZ','throatZ','outletZ'}
for c in P.getNonEmptyCells():
    alias=P.getAlias(c)
    if alias:
        is_derived=alias in derived
        P.set('F'+c[1:],'Derived' if is_derived else 'Input')
        P.setBackground(c,(.9,.91,.92) if is_derived else (.79,.9,.98))
        P.setForeground(c,(.16,.19,.22) if is_derived else (.03,.22,.42))
# Keep important columns visible in the user's current window.
for col,width in [('A',200),('B',115),('C',48),('D',390),('E',210),('F',70)]: P.setColumnWidth(col,width)
P.Label='Design parameters — inputs, formulas, tested limits'
D.recompute(); D.save()
Gui.activeDocument().setEdit(P.Name); Gui.updateGui()
Gui.getMainWindow().grab().save(str(ROOT/'parameter_sheet.png'))
