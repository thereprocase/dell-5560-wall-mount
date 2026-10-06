from pathlib import Path
import json
import FreeCAD as A,FreeCADGui as G
from PySide import QtWidgets
ROOT=Path(__file__).resolve().parent
r=A._fusion_ribbon
r[0].grab().save(str(ROOT/'ribbon_tabs.png'));r[1].grab().save(str(ROOT/'ribbon_commands.png'))
v=G.activeDocument().mdiViewsOfType('Gui::View3DInventor')[0];v.saveImage(str(ROOT/'finished_detail.png'),1600,1200,'Current')
(ROOT/'workspace_layout.json').write_text(json.dumps({'window_size':[G.getMainWindow().width(),G.getMainWindow().height()],'visible_toolbars':[t.objectName() for t in G.getMainWindow().findChildren(QtWidgets.QToolBar) if t.isVisible()],'command_bar_width':r[1].width(),'tabs_width':r[2].width()},indent=2),encoding='utf-8')
