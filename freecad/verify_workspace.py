from pathlib import Path
import json
import FreeCAD as A,FreeCADGui as G
from PySide import QtCore,QtWidgets
ROOT=Path(__file__).resolve().parent
old=G.activeWorkbench().name()
for wb in ['SurfaceWorkbench','MeshWorkbench','PartDesignWorkbench','SketcherWorkbench','AssemblyWorkbench','PartWorkbench']:G.activateWorkbench(wb)
import fusion_ribbon as F
entries=F.CREATE+F.MODIFY+F.ASSEMBLE+F.CONSTRUCT+F.INSPECT+F.INSERT+F.SELECT+F.SKETCH_CREATE+F.SKETCH_MODIFY+F.CONSTRAINTS
missing=[e for e in entries if not e[1].startswith('@') and e[1] not in G.listCommands()]
# Render the selected tab again after verifying commands from installed workbenches.
ribbon=A._fusion_ribbon;tabs=ribbon[2];tabs.setCurrentIndex(5);tabs.setCurrentIndex(0)
status={'missing_commands':missing,'surface_filling':'Surface_Filling' in G.listCommands(),'mesh_from_part':'Mesh_FromPartShape' in G.listCommands(),'tabs':[tabs.tabText(i) for i in range(tabs.count())],'tab_scroll_buttons':tabs.usesScrollButtons()}
(ROOT/'workspace_validation.json').write_text(json.dumps(status,indent=2),encoding='utf-8')
def capture():
 mw=G.getMainWindow();mw.screen().grabWindow(int(mw.winId())).save(str(ROOT/'workspace_preview.png'))
QtCore.QTimer.singleShot(1200,capture)
