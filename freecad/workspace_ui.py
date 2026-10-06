"""Persistent personal FreeCAD workspace; native commands and dock layout."""
from pathlib import Path
import json,time
import FreeCAD as App,FreeCADGui as Gui
from PySide import QtCore,QtGui,QtWidgets
ROOT=Path(__file__).resolve().parent
QSS="""
/* Personal studio workspace */
QMainWindow, QMenuBar, QToolBar { background: #29323b; color: #e5eaf0; }
QMenuBar::item:selected, QMenu::item:selected { background: #286e78; }
QDockWidget { color: #e5eaf0; font-size: 13px; }
QDockWidget::title { background: #34414d; padding: 6px; }
QTreeView, QListView, QTreeWidget { background: #252e36; alternate-background-color: #2b3640; color: #e5eaf0; font-size: 13px; selection-background-color: #286e78; }
QHeaderView::section { background: #34414d; color: #e5eaf0; padding: 5px; }
QToolBar { spacing: 4px; padding: 3px; border: none; }
QToolButton { border-radius: 4px; padding: 5px; }
QToolButton:hover { background: #43515e; }
QToolButton:checked { background: #286e78; }
QTabBar::tab { padding: 7px 14px; }
QTabBar::tab:selected { border-bottom: 2px solid #52bdc5; }
QStatusBar { background: #29323b; color: #cbd5df; }
"""
def apply():
    mw=Gui.getMainWindow(); app=QtWidgets.QApplication.instance()
    if mw.findChild(QtWidgets.QToolBar,'StudioWorkflow'): return
    stamp=time.strftime('%Y%m%d-%H%M%S')
    App.ParamGet('User parameter:BaseApp').Export(str(ROOT/('workspace-before-'+stamp+'.FCParam')))
    (ROOT/('workspace-layout-before-'+stamp+'.bin')).write_bytes(bytes(mw.saveState()))
    app.setStyleSheet(app.styleSheet().split('/* Personal studio workspace */')[0]+QSS)
    p=App.ParamGet('User parameter:BaseApp/Preferences/View')
    p.SetString('NavigationStyle','Gui::RevitNavigationStyle'); p.SetBool('ZoomAtCursor',True)
    p.SetBool('UseSpinningAnimations',False)
    p.SetUnsigned('BackgroundColor',0x9EA6ADFF); p.SetBool('Gradient',False); p.SetBool('Simple',True)
    App.ParamGet('User parameter:BaseApp/Preferences/General').SetString('AutoloadModule','PartDesignWorkbench')
    Gui.activateWorkbench('PartDesignWorkbench')
    # Dock overlays obscure the canvas and are unfamiliar to Fusion users.
    for action in mw.findChildren(QtGui.QAction):
        if action.objectName()=='Std_DockOverlayAll' and action.isChecked(): action.trigger()
    docks={w.objectName():w for w in mw.findChildren(QtWidgets.QDockWidget)}
    for name,area in [('Model',QtCore.Qt.LeftDockWidgetArea),('Tasks',QtCore.Qt.RightDockWidgetArea)]:
        if name in docks:
            d=docks[name]; d.setFloating(False); mw.addDockWidget(area,d); d.show()
            mw.resizeDocks([d],[320 if name=='Model' else 300],QtCore.Qt.Horizontal)
    for name in ['Python console','Report view','Selection view']:
        if name in docks: docks[name].hide()
    # Retain the complete native Sketcher toolbars when editing a sketch.
    for bar in mw.findChildren(QtWidgets.QToolBar):
        if bar.objectName() in ['Structure','Help','Part Design Helper Features','Part Design Modeling Features','Part Design Dress-Up Features','Part Design Transformation Features']: bar.hide()
        bar.setIconSize(QtCore.QSize(24,24))
    toolbar=QtWidgets.QToolBar('Studio workflow',mw); toolbar.setObjectName('StudioWorkflow')
    toolbar.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon); toolbar.setIconSize(QtCore.QSize(24,24))
    mw.addToolBarBreak(QtCore.Qt.TopToolBarArea); mw.addToolBar(QtCore.Qt.TopToolBarArea,toolbar)
    def native(text,command,icon,tip,workbench=None):
        a=toolbar.addAction(mw.style().standardIcon(QtWidgets.QStyle.SP_FileDialogDetailedView),text); a.setToolTip(tip)
        def run():
            if workbench: Gui.activateWorkbench(workbench)
            Gui.runCommand(command)
        a.triggered.connect(run)
    native('Sketch','Sketcher_NewSketch','Sketcher_NewSketch','Create a sketch on a plane or selected face','SketcherWorkbench')
    native('Body','PartDesign_Body','PartDesign_Body','New Part Design body for a new editable solid','PartDesignWorkbench')
    native('Pad','PartDesign_Pad','PartDesign_Pad','Add material inside a Part Design body','PartDesignWorkbench')
    native('Pocket','PartDesign_Pocket','PartDesign_Pocket','Remove material inside a Part Design body','PartDesignWorkbench')
    toolbar.addSeparator()
    native('Extrude','Part_Extrude','Part_Extrude','Extrude a sketch as a Part feature, as used by most of this mount','PartWorkbench')
    native('Fillet','Part_Fillet','Part_Fillet','Round selected edges of a Part solid','PartWorkbench')
    native('Measure','Std_Measure','Std_Measure','Measure selected geometry')
    toolbar.addSeparator()
    def document():
        target=ROOT/'Precision_5560_Native.FCStd'
        d=next((d for d in App.listDocuments().values() if d.FileName and Path(d.FileName).resolve()==target.resolve()),None)
        if d is None: d=App.openDocument(str(target))
        App.setActiveDocument(d.Name); return d
    params=toolbar.addAction(mw.style().standardIcon(QtWidgets.QStyle.SP_FileDialogContentsView),'Parameters')
    params.setToolTip('Open the named parameter sheet for this mount')
    params.triggered.connect(lambda:Gui.activeDocument().setEdit(document().getObject('Parameters').Name))
    assembly=toolbar.addAction(mw.style().standardIcon(QtWidgets.QStyle.SP_DirIcon),'Assembly')
    assembly.triggered.connect(lambda:Gui.activateWorkbench('AssemblyWorkbench'))
    native('Fit','Std_ViewFitAll','Std_ViewFitAll','Fit model in view (V, F)')
    log=toolbar.addAction(mw.style().standardIcon(QtWidgets.QStyle.SP_MessageBoxInformation),'Log')
    log.setToolTip('Show or hide the actual application error log')
    log.triggered.connect(lambda:docks['Report view'].setVisible(not docks['Report view'].isVisible()))
    guide=toolbar.addAction('Fusion guide')
    guide.triggered.connect(lambda:QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(ROOT/'FUSION_GUIDE.html'))))
    for d in App.listDocuments().values():
        for view in Gui.getDocument(d.Name).mdiViewsOfType('Gui::View3DInventor'):
            view.setNavigationType('Gui::RevitNavigationStyle')
    App._studio_toolbar=toolbar
    App.saveParameter(); Gui.updateGui()
    (ROOT/'workspace_status.json').write_text(json.dumps({'status':'done','navigation':'Revit','background':'#9EA6AD','toolbar':toolbar.objectName(),'docks':{k:v.isVisible() for k,v in docks.items()}},indent=2),encoding='utf-8')
    App.Console.PrintMessage('Studio workspace ready: Revit navigation, workflow toolbar, docked model and tasks.\n')
if __name__=='__main__': apply()
