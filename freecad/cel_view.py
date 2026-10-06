"""Matte technical-illustration preset using stock FreeCAD display properties."""
from pathlib import Path
import json,shutil,time
import FreeCAD as App,FreeCADGui as Gui
from PySide import QtCore,QtWidgets
ROOT=Path(__file__).resolve().parent
D=next(d for d in App.listDocuments().values() if d.FileName and Path(d.FileName).resolve()==(ROOT/'Precision_5560_Native.FCStd').resolve())
App.setActiveDocument(D.Name)
D.save()
stamp=time.strftime('%Y%m%d-%H%M%S')
shutil.copy2(D.FileName,ROOT/('BeforeCel-'+stamp+'.FCStd'))
prefs=App.ParamGet('User parameter:BaseApp/Preferences/View')
prefs.Export(str(ROOT/('display-before-cel-'+stamp+'.FCParam')))
prefs.SetUnsigned('BackgroundColor',0x9EA6ADFF)
prefs.SetBool('Gradient',False); prefs.SetBool('RadialGradient',False); prefs.SetBool('Simple',True)
lights=prefs.GetGroup('LightSources')
for key,value in {'HeadlightIntensity':95,'FillLightIntensity':14,'BacklightIntensity':48,'AmbientLightIntensity':10}.items(): lights.SetInt(key,value)
changed=[]
for o in D.Objects:
    v=o.ViewObject
    if hasattr(v,'DisplayMode') and 'Flat Lines' in v.listDisplayModes(): v.DisplayMode='Flat Lines'
    if hasattr(v,'LineWidth'): v.LineWidth=1.3
    if hasattr(v,'LineColor'): v.LineColor=(.055,.07,.085)
    if hasattr(v,'ShapeMaterial'):
        material=v.ShapeMaterial
        material.SpecularColor=(.06,.07,.08); material.Shininess=8
        v.ShapeMaterial=material
    if hasattr(o,'PartKey') or (o.TypeId=='PartDesign::Body' and 'pin' in o.Label.lower()):
        key=getattr(o,'PartKey',o.Label).lower()
        color=(.10,.55,.59) if any(k in key for k in ['duct','rail']) else ((.94,.63,.19) if 'pin' in key else (.37,.43,.49))
        if hasattr(v,'ShapeColor'): v.ShapeColor=color
        changed.append(o.Name)
Gui.Selection.clearSelection()
view=Gui.activeDocument().mdiViewsOfType('Gui::View3DInventor')[0]
mdi=Gui.getMainWindow().findChild(QtWidgets.QMdiArea)
for window in mdi.subWindowList():
    if window.widget().metaObject().className()=='Gui::View3DInventor':
        mdi.setActiveSubWindow(window); break
Gui.updateGui(); view.redraw()
D.save(); App.saveParameter()
def capture():
    view.saveImage(str(ROOT/'cel_preview.png'),1920,1440,'Current')
    report={'status':'done','file':D.FileName,'styled_sources':changed,'invalid_features':[o.Name for o in D.Objects if 'Invalid' in o.State],'line_width':1.3,'style':'Flat Lines','lighting':lights.GetContents(),'limitations':'Cel-inspired lighting and outlines, no quantized shader or texture geometry.'}
    (ROOT/'cel_status.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    App.Console.PrintMessage('Matte illustration preset saved; geometry unchanged.\n')
QtCore.QTimer.singleShot(1500,capture)
