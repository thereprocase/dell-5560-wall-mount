"""Export the preserved Revision H prototype as one print-oriented STEP per part.

Run with FreeCAD's bundled Python. Read a completed snapshot, never the GUI save
target. The transformations match prepare_prints.py and the Rev H STL release.
"""
from pathlib import Path
import hashlib
import json
import shutil
import sys

import FreeCAD as App
import Mesh
import Part

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'print_release_step'
OUT.mkdir(exist_ok=True)
source = ROOT / 'freecad/Precision_5560_Native.FCStd'
release = json.loads((ROOT / 'print_release/manifest.json').read_text())
source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
assert source_hash == release['native_sha256'], 'Native file differs from Rev H release'
snapshot = ROOT / 'tmp/Revision_H_STEP_Export_Snapshot.FCStd'
snapshot.parent.mkdir(exist_ok=True)
shutil.copy2(source, snapshot)
sys.path.insert(0, App.getResourceDir() + 'Mod/Assembly')
doc = App.openDocument(str(snapshot))
installed = {o.InstanceKey: o for o in doc.getObject('InstalledAssembly').Group
             if o.TypeId == 'App::Link'}
assert set(installed) == set(release['parts']) and len(installed) == 14
tilted = App.Placement(App.Vector(0, 67, -84), App.Rotation(App.Vector(1, 0, 0), 45)).multiply(
    App.Placement(App.Vector(0, -70, 104), App.Rotation()))
report = {
    'revision': 'H prototype', 'source_native_sha256': source_hash,
    'units': 'mm', 'bed': 'Bambu P1S 256 x 256 mm',
    'source': 'print_release/manifest.json',
    'instructions': 'Import one STEP at a time. Keep orientation; do not auto-orient or scale.',
    'parts': {},
}
for key, link in sorted(installed.items()):
    shape = link.Shape.copy()
    if 'cradle' in key:
        shape.rotate(App.Vector(), App.Vector(0, 1, 0), -90 if 'left' in key else 90)
        shape.rotate(App.Vector(), App.Vector(0, 0, 1), 45)
        orientation = 'outer side down, diagonal on plate (already printed)'
    elif 'outlet_rail' in key:
        shape.rotate(App.Vector(), App.Vector(1, 0, 0), 180)
        orientation = 'lip down'
    elif 'push_pin' in key:
        shape = doc.getObject('PinBody').Shape.copy()
        orientation = 'button down, split tip up'
    else:
        shape.Placement = tilted.inverse().multiply(shape.Placement)
        if 'fan_retainer' in key:
            shape.rotate(App.Vector(), App.Vector(1, 0, 0), -90)
            orientation = 'broad front face down'
        else:
            orientation = 'inclined inlet down' if 'fan_duct' in key else 'grille down'
    bounds = shape.BoundBox
    shape.translate(App.Vector(128 - (bounds.XMin + bounds.XMax) / 2,
                               128 - (bounds.YMin + bounds.YMax) / 2, -bounds.ZMin))
    assert shape.isValid() and len(shape.Solids) == 1, key
    bounds = shape.BoundBox
    assert min(bounds.XMin, bounds.YMin) >= 7.999, key
    assert max(bounds.XMax, bounds.YMax) <= 248.001 and bounds.ZMax <= 256, key
    assert bounds.XMin - 8 >= 18 or bounds.YMin - 8 >= 28, key
    mesh = Mesh.Mesh(str(ROOT / 'print_release' / (key + '.stl')))
    mesh_bounds = mesh.BoundBox
    max_bounds_error = max(abs(getattr(bounds, axis) - getattr(mesh_bounds, axis))
                           for axis in ['XMin', 'XMax', 'YMin', 'YMax', 'ZMin', 'ZMax'])
    assert max_bounds_error < .08, (key, max_bounds_error)
    path = OUT / (key + '.step')
    shape.exportStep(str(path))
    check = Part.read(str(path))
    assert check.isValid() and len(check.Solids) == 1, key
    difference = check.cut(shape).Volume + shape.cut(check).Volume
    assert difference < .01, (key, difference)
    report['parts'][key] = {
        'file': path.name, 'orientation': orientation,
        'dimensions_mm': [bounds.XLength, bounds.YLength, bounds.ZLength],
        'z_min_mm': bounds.ZMin, 'solid_valid_after_step_reimport': True,
        'roundtrip_symmetric_difference_mm3': difference,
        'max_bounds_difference_from_released_stl_mm': max_bounds_error,
        '8mm_brim_and_stock_cutter_clear': True,
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
    }
    print(key, orientation, 'PASS', flush=True)
App.closeDocument(doc.Name)
assert hashlib.sha256(source.read_bytes()).hexdigest() == source_hash
(OUT / 'manifest.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
(OUT / 'README.txt').write_text('''REVISION H PROTOTYPE - PRINT-ORIENTED STEP FILES

14 parts, one of each numbered file. Parts 11-14 are four identical pins.
The arms (01-02) are included for completeness; yours are already printed.
This is the same geometry as the Revision H STL print release, not the
experimental 0.8 mm wall trial or the forthcoming minimalist design.

Open one STEP at a time in OrcaSlicer. Keep the baked orientation, use mm,
and do not auto-orient or scale. Each part sits at Z=0 centered on a 256 mm
P1S plate. Inspect the preview after importing because slicers can arrange
parts automatically. Do not print the whole folder together on one plate.

P1S / ASA starting setup: 0.4 mm nozzle, 0.20 mm layers, 6 walls,
6 top/bottom layers, 100% infill of the intentionally hollow CAD,
8 mm outer brim, supports off. Use the actual spool's ASA temperature and
drying instructions. Review bridges and the first layer before printing.
For both ducts set Bridge direction and Internal bridge direction to 180
degrees, with Relative bridge angle and Align infill direction to model OFF.
See ORCA_BRIDGE_REVIEW.txt for the measured 5.19 mm cross-slot bridge spans
and reviewed previews. This is a toolpath check, not physical print success.

Orientations: arms outer-side-down and diagonal; ducts inlet-down;
trays grille-down; caps broad front face down; rails lip-down; pins button-down.
Fit clearance is nominally 0.30 mm at the revised joints. Pin retention has
intentional interference. The existing fit coupons remain useful.

All 14 STEP files were reimported and checked for one valid solid, source
shape agreement, print-bed/brim clearance and matching Rev H STL bounds.
See manifest.json for per-file checks and hashes. STEP files are editable
exchange solids; the full native feature history remains in the FCStd model.
''', encoding='utf-8')
print('Exported 14 validated Revision H print-oriented STEP files to', OUT, flush=True)
