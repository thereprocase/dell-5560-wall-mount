"""Workspace-only file queue; Fusion API calls execute on its UI thread."""
import adsk.core
import adsk.fusion
import json
import sys
import threading
import time
import traceback
from pathlib import Path

ROOT = Path('F:/Code/dell-5560-wall-mount/fusion')
QUEUE = ROOT / 'queue'
EVENT = 'Dell5560NativeBridge20260907'
handlers = []
stop_event = threading.Event()
app = None

class Execute(adsk.core.CustomEventHandler):
    def notify(self, args):
        for path in sorted(QUEUE.glob('*.request.json')):
            active = path.with_suffix('.running')
            path.rename(active)
            result = {'request': path.name}
            try:
                req = json.loads(active.read_text(encoding='utf-8-sig'))
                script = (ROOT / req['script']).resolve()
                if not script.is_relative_to(ROOT.resolve()):
                    raise ValueError('Script must be inside fusion workspace')
                # Reload builder modules between commands, retaining the bridge itself.
                for key in list(sys.modules):
                    if key == 'native' or key.startswith('native.'):
                        del sys.modules[key]
                if str(ROOT) not in sys.path:
                    sys.path.insert(0, str(ROOT))
                ns = {'__name__': '__fusion_command__', '__file__': str(script),
                      'app': app, 'request': req, 'result': result}
                exec(compile(script.read_text(encoding='utf-8'), str(script), 'exec'), ns)
                result['status'] = 'success'
            except Exception:
                result.update(status='error', traceback=traceback.format_exc())
            (QUEUE / path.name.replace('.request.', '.result.')).write_text(
                json.dumps(result, indent=2), encoding='utf-8')
            active.rename(active.with_suffix('.done'))

def run(context):
    global app
    app = adsk.core.Application.get()
    QUEUE.mkdir(parents=True, exist_ok=True)
    stop_event.clear()
    handler = Execute()
    handlers.append(handler)
    app.registerCustomEvent(EVENT).add(handler)
    (QUEUE / 'bridge.json').write_text(json.dumps({'version': app.version, 'ready': True}))
    def worker():
        while not stop_event.wait(1):
            if list(QUEUE.glob('*.request.json')):
                app.fireCustomEvent(EVENT)
    threading.Thread(target=worker, daemon=True).start()

def stop(context):
    stop_event.set()
    if app:
        app.unregisterCustomEvent(EVENT)
    handlers.clear()
