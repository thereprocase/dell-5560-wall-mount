from pathlib import Path
import FreeCAD as App,FreeCADGui as Gui,json
ROOT=Path(__file__).resolve().parent
D=next(d for d in App.listDocuments().values() if Path(d.FileName).resolve()==(ROOT/'Precision_5560_Native.FCStd').resolve())
App.setActiveDocument(D.Name)
a=D.getObject('InstalledAssembly')
r={'documents':{k:v.FileName for k,v in App.listDocuments().items()},'joints':[],'invalid':[o.Name for o in D.Objects if 'Invalid' in o.State]}
for group in a.Group:
    if group.TypeId=='Assembly::JointGroup':
        for j in group.Group:
            if hasattr(j,'Reference1'):
                r['joints'].append({'name':j.Name,'r1':str(j.Reference1),'r2':str(j.Reference2),'state':j.State,'status':j.getStatusString()})
(ROOT/'joint_reopen_diagnostics.json').write_text(json.dumps(r,indent=2))
Gui.activeDocument().setEdit(D.getObject('Parameters').Name); Gui.updateGui()
