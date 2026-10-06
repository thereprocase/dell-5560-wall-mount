"""Build a new D4 candidate from the preserved current assembly, then export it."""
from pathlib import Path
import hashlib
import json
import os
import sys

if sys.platform == 'win32':
    sys.path.insert(0, 'C:/Program Files/FreeCAD 1.1/lib')
    dll_directory = os.add_dll_directory('C:/Program Files/FreeCAD 1.1/bin')
import FreeCAD as App
import socket_fix
from preserve_gui import preserve_gui

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
SOURCE = OUT / 'baseline/Precision_5560_RevH_Current.FCStd'
TARGET = OUT / 'Precision_5560_RevH_D4_Current.FCStd'
sys.path.insert(0, str(ROOT / 'minimalist'))
from export import write_shape


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def print_pose(shape):
    transform = App.Placement(App.Vector(0, 67, -84), App.Rotation(App.Vector(1, 0, 0), 45))
    transform = transform.multiply(App.Placement(App.Vector(0, -70, 104), App.Rotation()))
    shape = shape.copy()
    shape.Placement = transform.inverse().multiply(shape.Placement)
    bounds = shape.BoundBox
    shape.translate(App.Vector(128 - (bounds.XMin + bounds.XMax) / 2,
                               128 - (bounds.YMin + bounds.YMax) / 2, -bounds.ZMin))
    return shape


def main():
    expected = json.loads((OUT / 'baseline.json').read_text())['source_sha256']
    assert sha(SOURCE) == expected
    assert not TARGET.exists(), 'Preserve the existing candidate before rebuilding'
    document = App.openDocument(str(SOURCE))
    baseline = {key: obj.Shape.copy() for key, obj in socket_fix.installed(document).items()}
    original_names = [obj.Name for obj in document.Objects]
    result = socket_fix.apply(document, expected)
    report = socket_fix.verify(document, baseline)
    report.update(revision='H-D4', source_sha256=expected,
                  original_object_names_preserved=all(document.getObject(name) for name in original_names),
                  native_cutter_diameter_mm=4.1, native_blind_depth_mm=7.7)
    result.PhysicalStatus = 'Nominal CAD sockets clear; physical pin seating/removal still needs confirmation.'
    document.saveAs(str(TARGET))
    App.closeDocument(document.Name)
    report['gui_preservation'] = preserve_gui(SOURCE, TARGET)
    document = App.openDocument(str(TARGET))
    document.getObject('D4ClearPinSockets').touch()
    document.recompute()
    report['reopened'] = socket_fix.verify(document, baseline)
    report['native_sha256'] = sha(TARGET)
    (OUT / 'build-report.json').write_text(json.dumps(report, indent=2) + '\n')
    print('D4 native checks passed; all four sockets clear and 18 other parts unchanged', flush=True)
    directory = OUT / 'print'
    directory.mkdir(exist_ok=True)
    manifest = {'revision': 'H-D4', 'native_sha256': sha(TARGET), 'parts': {}}
    for key in socket_fix.DUCT_KEYS:
        shape = print_pose(socket_fix.installed(document)[key].Shape)
        manifest['parts'][key] = write_shape(directory, key, shape,
                                            'inlet face down; original D3 pose and profile retained')
        print('Exported ' + key, flush=True)
    (directory / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    App.closeDocument(document.Name)


if __name__ == '__main__':
    main()
