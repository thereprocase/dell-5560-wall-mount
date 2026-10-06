from pathlib import Path
import FreeCAD as App,FreeCADGui as Gui,json
from PySide import QtWidgets,QtCore
ROOT=Path(__file__).resolve().parent

def capture():
    mw=Gui.getMainWindow(); data=[]
    for dock in mw.findChildren(QtWidgets.QDockWidget):
        name=dock.objectName()+' '+dock.windowTitle()
        if any(x in name.lower() for x in ['report','notification','log']):
            entry={'dock':name,'text':[],'rows':[]}
            for cls in [QtWidgets.QTextEdit,QtWidgets.QPlainTextEdit]:
                for w in dock.findChildren(cls): entry['text'].append(w.toPlainText())
            for w in dock.findChildren(QtWidgets.QTreeWidget):
                for i in range(w.topLevelItemCount()):
                    item=w.topLevelItem(i); entry['rows'].append([item.text(c) for c in range(w.columnCount())])
            for w in dock.findChildren(QtWidgets.QTableWidget):
                for r in range(w.rowCount()): entry['rows'].append([w.item(r,c).text() if w.item(r,c) else '' for c in range(w.columnCount())])
            data.append(entry)
    (ROOT/'app_report_log.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    (ROOT/'app_report_log.txt').write_text('\n\n'.join(d['dock']+'\n'+'\n'.join(d['text'])+'\n'+'\n'.join(' | '.join(row) for row in d['rows']) for d in data),encoding='utf-8')
App._mount_capture_log=capture
if hasattr(App,'_mount_log_timer'): App._mount_log_timer.stop()
App._mount_log_timer=QtCore.QTimer(); App._mount_log_timer.timeout.connect(capture); App._mount_log_timer.start(3000)
capture()
P=App.ActiveDocument.getObject('Parameters')
for c in P.getNonEmptyCells():
    if P.getAlias(c):
        contents=P.getContents(c)
        value=getattr(P,P.getAlias(c))
        if isinstance(value,str): P.set(c,'='+str(App.Units.Quantity(value)))
App.ActiveDocument.recompute()
values={P.getAlias(c):{'content':P.getContents(c),'type':type(getattr(P,P.getAlias(c))).__name__,'value':str(getattr(P,P.getAlias(c)))} for c in P.getNonEmptyCells() if P.getAlias(c)}
(ROOT/'parameter_preflight.json').write_text(json.dumps(values,indent=2))
assert all(v['type']=='Quantity' for v in values.values()),{k:v for k,v in values.items() if v['type']!='Quantity'}
