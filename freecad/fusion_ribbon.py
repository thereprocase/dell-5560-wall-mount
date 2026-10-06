"""Fusion-inspired command grouping with native FreeCAD operations."""
from pathlib import Path
import json
import FreeCAD as A,FreeCADGui as G
from PySide import QtCore,QtGui,QtWidgets
ROOT=Path(__file__).resolve().parent
# (label, command, workbench). Labels explain material-operation differences.
CREATE=[('Create sketch','Sketcher_NewSketch','SketcherWorkbench'),('Extrude (separate solid)','Part_Extrude','PartWorkbench'),('Extrude join (Pad)','PartDesign_Pad','PartDesignWorkbench'),('Extrude cut (Pocket)','PartDesign_Pocket','PartDesignWorkbench'),('Revolve','Part_Revolve','PartWorkbench'),('Sweep','Part_Sweep','PartWorkbench'),('Loft','Part_Loft','PartWorkbench'),('Hole','PartDesign_Hole','PartDesignWorkbench'),('New body','PartDesign_Body','PartDesignWorkbench'),('New component (Part)','Std_Part',None),('Box','Part_Box','PartWorkbench'),('Cylinder','Part_Cylinder','PartWorkbench'),('Rectangular pattern','PartDesign_LinearPattern','PartDesignWorkbench'),('Circular pattern','PartDesign_PolarPattern','PartDesignWorkbench'),('Mirror','Part_Mirror','PartWorkbench')]
MODIFY=[('Fillet','Part_Fillet','PartWorkbench'),('Chamfer','Part_Chamfer','PartWorkbench'),('Combine: join','Part_Fuse','PartWorkbench'),('Combine: cut','Part_Cut','PartWorkbench'),('Combine: intersect','Part_Common','PartWorkbench'),('Shell / thickness','Part_Thickness','PartWorkbench'),('Draft','PartDesign_Draft','PartDesignWorkbench'),('Scale','Part_Scale','PartWorkbench'),('Move / rotate','Std_TransformManip',None),('Align','Std_Alignment',None),('Split body','Part_CompSplitFeatures','PartWorkbench'),('Offset surface','Part_Offset','PartWorkbench'),('Appearance','Std_SetAppearance',None),('Change parameters','@parameters',None)]
ASSEMBLE=[('Joint: fixed','Assembly_CreateJointFixed','AssemblyWorkbench'),('Joint: revolute','Assembly_CreateJointRevolute','AssemblyWorkbench'),('Joint: slider','Assembly_CreateJointSlider','AssemblyWorkbench'),('Joint: cylindrical','Assembly_CreateJointCylindrical','AssemblyWorkbench'),('Joint: ball','Assembly_CreateJointBall','AssemblyWorkbench'),('Ground / unground','Assembly_ToggleGrounded','AssemblyWorkbench'),('New assembly','Assembly_CreateAssembly','AssemblyWorkbench'),('Insert component','Assembly_Insert','AssemblyWorkbench'),('Solve assembly','Assembly_SolveAssembly','AssemblyWorkbench')]
CONSTRUCT=[('Datum plane','Part_DatumPlane','PartWorkbench'),('Datum axis','Part_DatumLine','PartWorkbench'),('Datum point','Part_DatumPoint','PartWorkbench')]
INSPECT=[('Measure','Std_Measure',None),('Section analysis','Part_SectionCut','PartWorkbench'),('Clip plane','Std_ToggleClipPlane',None),('Check geometry','Part_CheckGeometry','PartWorkbench')]
INSERT=[('Insert file','Std_Import',None),('Insert linked component','Assembly_InsertLink','AssemblyWorkbench')]
SELECT=[('Select all','Std_SelectAll',None),('Box selection','Std_BoxSelection',None),('Clarify selection','Std_ClarifySelection',None),('Faces only','Part_FaceSelection','PartWorkbench'),('Edges only','Part_EdgeSelection','PartWorkbench'),('Vertices only','Part_VertexSelection','PartWorkbench'),('Clear selection filter','Part_RemoveSelectionGate','PartWorkbench')]
SKETCH_CREATE=[('Line','Sketcher_CreateLine','SketcherWorkbench'),('Rectangle','Sketcher_CreateRectangle','SketcherWorkbench'),('Circle','Sketcher_CreateCircle','SketcherWorkbench'),('Arc','Sketcher_CreateArc','SketcherWorkbench'),('Slot','Sketcher_CreateSlot','SketcherWorkbench'),('Spline','Sketcher_CreateBSpline','SketcherWorkbench'),('Project','Sketcher_Projection','SketcherWorkbench')]
SKETCH_MODIFY=[('Trim','Sketcher_Trimming','SketcherWorkbench'),('Extend','Sketcher_Extend','SketcherWorkbench'),('Offset','Sketcher_Offset','SketcherWorkbench'),('Fillet','Sketcher_CreateFillet','SketcherWorkbench'),('Construction','Sketcher_ToggleConstruction','SketcherWorkbench')]
CONSTRAINTS=[('Dimension','Sketcher_Dimension','SketcherWorkbench'),('Coincident','Sketcher_ConstrainCoincident','SketcherWorkbench'),('Horizontal / vertical','Sketcher_ConstrainHorVer','SketcherWorkbench'),('Parallel','Sketcher_ConstrainParallel','SketcherWorkbench'),('Perpendicular','Sketcher_ConstrainPerpendicular','SketcherWorkbench'),('Tangent','Sketcher_ConstrainTangent','SketcherWorkbench'),('Equal','Sketcher_ConstrainEqual','SketcherWorkbench'),('Symmetry','Sketcher_ConstrainSymmetric','SketcherWorkbench')]
def apply():
 mw=G.getMainWindow()
 if hasattr(A,'_fusion_ribbon'):A._fusion_ribbon[4].stop()
 for name in ['StudioWorkflow','StudioTabs','StudioRibbonCommands','FusionTabs','FusionCommands']:
  old=mw.findChild(QtWidgets.QToolBar,name)
  if old:mw.removeToolBar(old);old.deleteLater()
 top=QtWidgets.QToolBar('Design ribbon',mw);top.setObjectName('FusionTabs');top.setMovable(False)
 container=QtWidgets.QWidget();container.setObjectName('FusionRibbonSurface')
 outer=QtWidgets.QHBoxLayout(container);outer.setContentsMargins(8,3,8,4);outer.setSpacing(12)
 space=QtWidgets.QComboBox();space.addItems(['DESIGN','DRAWING','MANUFACTURE','SIMULATION']);space.setFixedSize(116,64);outer.addWidget(space,0,QtCore.Qt.AlignVCenter)
 right=QtWidgets.QVBoxLayout();right.setContentsMargins(0,0,0,0);right.setSpacing(0)
 tabs=QtWidgets.QTabBar();tabs.setExpanding(False);tabs.setUsesScrollButtons(False);tabs.setElideMode(QtCore.Qt.ElideNone);tabs.setMinimumWidth(780)
 for name in ['SOLID','SURFACE','MESH','SHEET METAL','PLASTIC','MANAGE','UTILITIES','SKETCH']:tabs.addTab(name)
 for index,reason in [(3,'Sheet Metal add-on is not installed.'),(4,'Fusion Plastic tools have no installed native equivalent.'),(5,'Fusion Manage services have no native equivalent here.')]:
  tabs.setTabEnabled(index,False);tabs.setTabToolTip(index,reason)
 tabs.setTabVisible(7,False)
 right.addWidget(tabs,0,QtCore.Qt.AlignLeft)
 bar=QtWidgets.QToolBar('Design commands');bar.setObjectName('FusionCommands');bar.setMovable(False)
 right.addWidget(bar);outer.addLayout(right,1);top.addWidget(container);mw.addToolBarBreak();mw.addToolBar(top)
 container.setStyleSheet("""
 QWidget#FusionRibbonSurface, QToolBar#FusionCommands { background:#3b4554; color:#eff3f7; border:0; padding:0; spacing:0; }
 QTabBar::tab { background:transparent; color:#eff3f7; border:0; padding:5px 14px 3px; font-size:11px; min-height:17px; }
 QTabBar::tab:selected { border-bottom:2px solid #dfe9f3; font-weight:600; }
 QTabBar::tab:disabled { color:#84909e; }
 QComboBox { background:#3b4554; color:#ffffff; border:1px solid #7e8c9e; border-radius:3px; padding-left:15px; font-size:12px; }
 QToolButton { background:transparent; border:0; border-radius:2px; padding:2px; color:#ffffff; }
 QToolButton:hover { background:#526378; }
 QToolBar::separator { background:#667282; width:1px; margin:5px 8px 5px 8px; }
 """)
 mappings=[]
 def invoke(cmd,wb):
  if cmd=='@parameters':
   d=A.ActiveDocument
   if d and d.getObject('Parameters'):G.activeDocument().setEdit('Parameters')
   return
  if cmd=='@guide':QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(ROOT/'FUSION_GUIDE.html')));return
  if cmd=='@log':
   d=mw.findChild(QtWidgets.QDockWidget,'Report view');d.setVisible(not d.isVisible());return
  if wb:G.activateWorkbench(wb)
  if space.currentIndex()==0:
   for t in mw.findChildren(QtWidgets.QToolBar):
    if t.objectName() not in ['File','Edit','FusionTabs','FusionCommands']:t.hide()
  if cmd in G.listCommands():G.runCommand(cmd)
 def action(item,parent):
  text,cmd,wb=item
  a=QtGui.QAction(text,parent)
  original=next((a for a in mw.findChildren(QtGui.QAction) if a.objectName()==cmd),None)
  icon=original.icon() if original else QtGui.QIcon()
  if icon.isNull():
   try:
    info=G.Command.get(cmd).getInfo();pic=info.get('pixmap','') or info.get('Pixmap','')
    if pic:icon=G.getIcon(pic)
   except Exception:pass
  if icon.isNull():icon=mw.style().standardIcon(QtWidgets.QStyle.SP_FileDialogDetailedView)
  a.setIcon(icon);a.setToolTip(text+' — '+cmd+((' ['+wb.replace('Workbench','')+']') if wb else ''))
  a.triggered.connect(lambda checked=False:invoke(cmd,wb));mappings.append({'label':text,'command':cmd,'workbench':wb})
  return a
 def group(title,items,pins):
  widget=QtWidgets.QWidget();layout=QtWidgets.QVBoxLayout(widget);layout.setContentsMargins(2,0,2,0);layout.setSpacing(0)
  row=QtWidgets.QHBoxLayout();row.setSpacing(1)
  for item in pins:
   b=QtWidgets.QToolButton();a=action(item,b);b.setDefaultAction(a);b.setToolButtonStyle(QtCore.Qt.ToolButtonIconOnly);b.setIconSize(QtCore.QSize(34,34));b.setFixedSize(41,43);row.addWidget(b)
  layout.addLayout(row)
  menu=QtWidgets.QMenu(widget)
  for item in items:menu.addAction(action(item,menu))
  button=QtWidgets.QToolButton();button.setText(title);button.setMenu(menu);button.setPopupMode(QtWidgets.QToolButton.InstantPopup);button.setMinimumWidth(button.fontMetrics().horizontalAdvance(title)+28);button.setFixedHeight(20);button.setStyleSheet('font-size:11px;padding:0 16px 0 4px;');layout.addWidget(button,0,QtCore.Qt.AlignHCenter)
  bar.addWidget(widget);bar.addSeparator()
 def render(index):
  bar.clear();mappings.clear()
  if index==0:
   configure=[('Change parameters','@parameters',None),('New spreadsheet','Spreadsheet_CreateSheet','SpreadsheetWorkbench'),('Document information','Std_DlgProjectInformation',None)]
   groups=[('CREATE',CREATE,[CREATE[0],CREATE[1],CREATE[4],CREATE[7],CREATE[12],CREATE[8]]),('MODIFY',MODIFY,[MODIFY[11],MODIFY[0],MODIFY[1],MODIFY[5],MODIFY[2],MODIFY[8],MODIFY[10]]),('ASSEMBLE',ASSEMBLE,[ASSEMBLE[0],('New component','Std_Part',None),ASSEMBLE[5]]),('CONFIGURE',configure,configure),('CONSTRUCT',CONSTRUCT,[CONSTRUCT[0]]),('INSPECT',INSPECT,INSPECT[:2]),('INSERT',INSERT,[INSERT[0]]),('SELECT',SELECT,[SELECT[1]])]
  elif index==7:
   groups=[('CREATE',SKETCH_CREATE,SKETCH_CREATE[:3]),('MODIFY',SKETCH_MODIFY,SKETCH_MODIFY[:2]),('CONSTRAINTS',CONSTRAINTS,[CONSTRAINTS[0],CONSTRAINTS[5]]),('INSPECT',INSPECT,[INSPECT[0]]),('FINISH',[('Finish sketch','Sketcher_LeaveSketch','SketcherWorkbench')],[('Finish sketch','Sketcher_LeaveSketch','SketcherWorkbench')])]
  elif index==1:
   surface=[('Surface filling','Surface_Filling','SurfaceWorkbench'),('Ruled surface','Part_RuledSurface','PartWorkbench'),('Loft','Part_Loft','PartWorkbench'),('Sweep','Part_Sweep','PartWorkbench')]
   groups=[('CREATE',surface,surface[:2]),('MODIFY',MODIFY,[MODIFY[5],MODIFY[11]]),('CONSTRUCT',CONSTRUCT,[CONSTRUCT[0]]),('INSPECT',INSPECT,[INSPECT[0]]),('INSERT',INSERT,[INSERT[0]])]
  elif index==2:
   mesh=[('Mesh from shape','Mesh_FromPartShape','MeshWorkbench'),('Import mesh','Std_Import',None),('Export mesh','Std_Export',None)]
   groups=[('CREATE',mesh,mesh[:1]),('INSERT',mesh[1:],mesh[1:]),('INSPECT',INSPECT,[INSPECT[0]])]
  else:
   tools=[('Parameters','@parameters',None),('Report log','@log',None),('Fusion guide','@guide',None),('Preferences','Std_DlgPreferences',None),('Add-on manager','Std_AddonMgr',None)]
   groups=[('TOOLS',tools,tools[:3]),('SETTINGS',tools[3:],tools[3:]),('EXPORT',[('Export','Std_Export',None)],[('Export','Std_Export',None)])]
  for title,items,pins in groups:group(title,items,pins)
  # Replaced native rows remain available through menus; prevent duplication.
  for t in mw.findChildren(QtWidgets.QToolBar):
   if t.objectName() not in ['File','Edit','FusionTabs','FusionCommands']:t.hide()
  (ROOT/'fusion_ribbon_mapping.json').write_text(json.dumps(mappings,indent=2),encoding='utf-8');G.updateGui()
 def choose(index):
  wb={0:'PartWorkbench',1:'SurfaceWorkbench',2:'MeshWorkbench',7:'SketcherWorkbench'}.get(index)
  if wb:G.activateWorkbench(wb)
  render(index)
 tabs.currentChanged.connect(choose)
 space.currentIndexChanged.connect(lambda i:G.activateWorkbench(['PartWorkbench','TechDrawWorkbench','CAMWorkbench','FemWorkbench'][i]))
 # Observe edit state so sketch commands become visible when a sketch opens.
 timer=QtCore.QTimer();timer.setInterval(600)
 def context():
  d=G.activeDocument()
  obj=d.getInEdit() if d else None
  editing=bool(obj and obj.TypeId=='Sketcher::SketchObject')
  tabs.setTabVisible(7,editing)
  if editing and tabs.currentIndex()!=7:tabs.setCurrentIndex(7)
  elif not editing and tabs.currentIndex()==7:tabs.setCurrentIndex(0)
 timer.timeout.connect(context);timer.start()
 A._fusion_ribbon=(top,bar,tabs,space,timer);choose(0)
 for t in mw.findChildren(QtWidgets.QToolBar):
  if t.objectName() in ['File','Edit']:t.setIconSize(QtCore.QSize(20,20))
 G.updateGui();A.Console.PrintMessage('Fusion-style grouped ribbon ready. Native commands are listed in tooltips.\n')
if __name__=='__main__':apply()
