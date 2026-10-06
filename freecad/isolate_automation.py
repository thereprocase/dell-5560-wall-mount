from pathlib import Path
import os,json
import FreeCAD as App
from PySide import QtCore
ROOT=Path(__file__).resolve().parent; pid=os.getpid()
# Change only our timers. No document save, close, or process shutdown.
if pid!=29496:
    def stop_automation():
        if hasattr(App,'_mount_runner'):App._mount_runner.stop()
        if hasattr(App,'_mount_log_timer'):App._mount_log_timer.stop()
    QtCore.QTimer.singleShot(0,stop_automation)
else:
    QtCore.QTimer.singleShot(0,lambda:App._mount_runner.stop())
    QtCore.QTimer.singleShot(4000,lambda:App._mount_runner.start(1000))
(ROOT/('automation-isolation-'+str(pid)+'.json')).write_text(json.dumps({'pid':pid,'owner':pid==29496,'documents':{k:d.FileName for k,d in App.listDocuments().items()},'action':'pause owner briefly' if pid==29496 else 'stop only local automation timers'}),encoding='utf-8')
