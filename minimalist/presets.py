"""Recompute six measured examples through every allowed dam index, then export."""
from pathlib import Path
import argparse
import json
import shutil
import time

import FreeCAD as App

from build import TARGET, values
from validate import audit
from export import export, sha
from preserve_gui import restore

ROOT = Path(__file__).resolve().parent
PRESETS = {
    '5560': {'label': 'Precision 5560 reference', 'width': 344.4, 'depth': 230.3, 'thickness': 20},
    '13-inch-example': {'label': '13-inch class example', 'width': 304, 'depth': 210, 'thickness': 16},
    '14-inch-example': {'label': '14-inch class example', 'width': 320, 'depth': 220, 'thickness': 18},
    '15-6-inch-example': {'label': '15.6-inch class example', 'width': 360, 'depth': 245, 'thickness': 24},
    '16-inch-example': {'label': '16-inch class example', 'width': 360, 'depth': 250, 'thickness': 24},
    '17-inch-example': {'label': '17-inch class example', 'width': 400, 'depth': 275, 'thickness': 28},
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('names', nargs='*', default=list(PRESETS))
    ap.add_argument('--no-export', action='store_true')
    ap.add_argument('--export-existing', action='store_true')
    args = ap.parse_args()
    initial = sha(TARGET)
    for name in args.names:
        preset = PRESETS[name]
        output = ROOT / 'presets' / name
        output.mkdir(parents=True, exist_ok=True)
        native = output / 'M1.FCStd'
        if args.export_existing:
            doc = App.openDocument(str(native))
            result = json.loads((output / 'validation.json').read_text())
            result['saved_reopened'] = audit(doc)
            assert result['saved_reopened']['pass']
            result['export'] = export(doc, output / 'print')
            result['source_unchanged'] = sha(TARGET) == initial
            App.closeDocument(doc.Name)
            (output / 'validation.json').write_text(json.dumps(result, indent=2)+'\n')
            continue
        shutil.copy2(TARGET, native)
        doc = App.openDocument(str(native))
        sheet = doc.getObject('M1Parameters')
        for alias, field in [('laptopWidth', 'width'), ('laptopDepth', 'depth'), ('laptopThickness', 'thickness')]:
            sheet.set(sheet.getCellFromAlias(alias), str(preset[field])+' mm')
        result = {'preset': preset, 'dam_positions': {}, 'source_sha256': initial}
        for index in range(9):
            sheet.set(sheet.getCellFromAlias('damIndex'), str(index))
            doc.recompute()
            check = audit(doc, service=index in (0, 8))
            result['dam_positions'][str(index)] = check
            (output / 'validation.json').write_text(json.dumps(result, indent=2)+'\n')
            print(name, 'index', index, 'PASS' if check['pass'] else 'FAIL', 'volume', round(check['total_printed_volume_mm3']), flush=True)
            if not check['pass']:
                print(json.dumps({k:v for k,v in check.items() if k != 'parts'}, indent=2), flush=True)
                raise SystemExit(1)
        doc.Label = 'Minimalist M1 / '+preset['label']
        doc.recompute()
        doc.save()
        App.closeDocument(doc.Name)
        result['gui_preservation'] = restore(TARGET, native)
        doc = App.openDocument(str(native))
        result['saved_reopened'] = audit(doc)
        assert result['saved_reopened']['pass']
        if not args.no_export: result['export'] = export(doc, output / 'print')
        App.closeDocument(doc.Name)
        result['source_unchanged'] = sha(TARGET) == initial
        assert result['source_unchanged']
        (output / 'validation.json').write_text(json.dumps(result, indent=2)+'\n')


if __name__ == '__main__': main()
