"""Tabbed native workspaces and contextual command strip."""
from pathlib import Path
import json
import FreeCAD as App,FreeCADGui as Gui
from PySide import QtCore,QtGui,QtWidgets
ROOT=Path(__file__).resolve().parent
def apply():
    mw=Gui.getMainWindow()
    if mw.findChild(QtWidgets.QToolBar,'StudioTabs'): return
    old=mw.findChild(QtWidgets.QToolBar,'StudioWorkflow')
    if old: old.hide()
    ribbon=QtWidgets.QToolBar('Workspace tabs',mw); ribbon.setObjectName('StudioTabs')
    tabs=QtWidgets.QTabBar(); tabs.setExpanding(False); tabs.setDrawBase(False); tabs.setUsesScrollButtons(False); tabs.setElideMode(QtCore.Qt.ElideNone)
    for label in ['DESIGN','SKETCH','SOLID','ASSEMBLY','INSPECT']: tabs.addTab(label)
    tabs.setMinimumWidth(540); tabs.setSizePolicy(QtWidgets.QSizePolicy.Minimum,QtWidgets.QSizePolicy.Fixed)
    ribbon.addWidget(tabs); mw.addToolBarBreak(); mw.addToolBar(ribbon)
    bar=QtWidgets.QToolBar('Workspace commands',mw); bar.setObjectName('StudioRibbonCommands')
    bar.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon); bar.setIconSize(QtCore.QSize(24,24))
    mw.addToolBarBreak(); mw.addToolBar(bar)
    sets=[('PartDesignWorkbench',[('New body','PartDesign_Body'),('Sketch','PartDesign_NewSketch'),('Pad / add','PartDesign_Pad'),('Pocket / cut','PartDesign_Pocket'),('Revolve','PartDesign_Revolution'),('Fillet','PartDesign_Fillet'),('Chamfer','PartDesign_Chamfer')]),('SketcherWorkbench',[('New sketch','Sketcher_NewSketch'),('Line','Sketcher_CreateLine'),('Rectangle','Sketcher_CreateRectangle'),('Circle','Sketcher_CreateCircle'),('Dimension','Sketcher_Dimension'),('Trim','Sketcher_Trimming'),('Finish sketch','Sketcher_LeaveSketch')]),('PartWorkbench',[('Extrude','Part_Extrude'),('Revolve','Part_Revolve'),('Loft','Part_Loft'),('Union','Part_Fuse'),('Cut','Part_Cut'),('Fillet','Part_Fillet'),('Chamfer','Part_Chamfer')]),('AssemblyWorkbench',[]),('PartWorkbench',[('Measure','Std_Measure'),('Fit','Std_ViewFitAll'),('Isometric','Std_ViewAxonometric'),('Front','Std_ViewFront')])]
    def params():
        D=App.ActiveDocument
        if D and D.getObject('Parameters'): Gui.activeDocument().setEdit('Parameters')
    def switch(index):
        wb,commands=sets[index]; Gui.activateWorkbench(wb); bar.clear()
        for text,cmd in commands:
            if cmd not in Gui.listCommands(): continue
            original=next((a for a in mw.findChildren(QtGui.QAction) if a.objectName()==cmd),None)
            icon=original.icon() if original else mw.style().standardIcon(QtWidgets.QStyle.SP_FileDialogDetailedView)
            action=bar.addAction(icon,text); action.setToolTip(original.toolTip() if original else cmd)
            action.triggered.connect(lambda checked=False,c=cmd:Gui.runCommand(c))
        bar.addSeparator()
        a=bar.addAction(mw.style().standardIcon(QtWidgets.QStyle.SP_FileDialogContentsView),'Parameters'); a.triggered.connect(params)
        a=bar.addAction(mw.style().standardIcon(QtWidgets.QStyle.SP_MessageBoxInformation),'Fusion guide'); a.triggered.connect(lambda:QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(ROOT/'FUSION_GUIDE.html'))))
        for t in mw.findChildren(QtWidgets.QToolBar):
            if t.objectName().startswith('Part Design '): t.hide()
        # Keep Assembly's native joint toolbar and Sketcher's full constraints available.
    tabs.currentChanged.connect(switch); switch(0)
    App._studio_ribbon=(ribbon,bar,tabs)
    (ROOT/'ribbon_status.json').write_text(json.dumps({'status':'done','user_data':App.getUserAppDataDir(),'tabs':[tabs.tabText(i) for i in range(tabs.count())]}),encoding='utf-8')
    Gui.updateGui()
if __name__=='__main__': apply()
