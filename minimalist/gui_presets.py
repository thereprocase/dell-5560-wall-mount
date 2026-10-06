"""Open all delivered presets in the live FreeCAD GUI without saving them."""
from pathlib import Path
import hashlib
import json
import FreeCAD as App
import FreeCADGui as Gui

ROOT = Path(__file__).resolve().parent
previous = App.ActiveDocument
results = {}
for path in sorted((ROOT / 'presets').glob('*/M1.FCStd')):
    initial = hashlib.sha256(path.read_bytes()).hexdigest()
    assert not any(Path(d.FileName) == path for d in App.listDocuments().values() if d.FileName)
    doc = App.openDocument(str(path))
    doc.recompute()
    links = [o for o in doc.getObject('M1Assembly').Group if o.TypeId == 'App::Link']
    visible = [o.Name for o in doc.Objects if o.TypeId != 'App::Part' and hasattr(o, 'Shape')
               and not o.Shape.isNull() and o.ViewObject.Visibility
               and not any(p.TypeId == 'App::Origin' and not p.ViewObject.Visibility for p in o.InList)]
    errors = [o.Name for o in doc.Objects if 'Invalid' in o.State or 'Error' in o.State]
    colors = {o.InstanceKey: list(o.LinkedObject.ViewObject.ShapeColor) for o in links}
    Gui.activeDocument().activeView().fitAll()
    if path.parent.name == '17-inch-example':
        Gui.activeDocument().activeView().saveImage(str(ROOT / 'browser/preset-17-native.png'), 1200, 900, 'White')
    result = {'visible_shape_objects': len(visible), 'installed_visible_parts': sum(o.ViewObject.Visibility for o in links),
              'bad_features': errors, 'distinct_part_colors': len({tuple(c) for c in colors.values()}),
              'native_sha256': initial}
    result['pass'] = not errors and len(links) == 20 and set(visible) == {o.Name for o in links} and result['distinct_part_colors'] >= 3
    App.closeDocument(doc.Name)
    result['file_unchanged'] = hashlib.sha256(path.read_bytes()).hexdigest() == initial
    results[path.parent.name] = result
    (ROOT / 'reports/preset-gui-review.json').write_text(json.dumps(results, indent=2) + '\n')
    assert result['pass'] and result['file_unchanged'], path.parent.name
if previous:
    App.setActiveDocument(previous.Name)
    Gui.activeDocument().activeView().fitAll()
App.Console.PrintMessage('All six M1 presets opened with 20 visible installed parts and restored colors; no errors.\n')
