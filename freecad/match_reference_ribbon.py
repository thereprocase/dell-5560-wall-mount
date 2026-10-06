from pathlib import Path
import importlib,json
import FreeCAD as A,FreeCADGui as G
from PySide import QtCore
ROOT=Path(__file__).resolve().parent
import fusion_ribbon
importlib.reload(fusion_ribbon);fusion_ribbon.apply();A.saveParameter()
def capture():
 r=A._fusion_ribbon
 r[0].grab().save(str(ROOT/'fusion_reference_ribbon.png'))
 r[1].grab().save(str(ROOT/'ribbon_commands.png'))
 r[2].grab().save(str(ROOT/'ribbon_tabs.png'))
 (ROOT/'ribbon_density_check.json').write_text(json.dumps({'tabs':[r[2].tabText(i) for i in range(r[2].count())],'button_count':len(r[1].findChildren(__import__('PySide').QtWidgets.QToolButton)),'size':[r[0].width(),r[0].height()]},indent=2),encoding='utf-8')
QtCore.QTimer.singleShot(1000,capture)
