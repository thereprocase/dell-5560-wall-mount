"""Reproducible OrcaSlicer CLI review; generates files without sending a print."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess
import time
import zipfile


def profiles(root, output, bridge_angle=None):
    index = {}
    for path in root.rglob('*.json'):
        try:
            data = json.loads(path.read_text(encoding='utf-8-sig'))
            index[data.get('name', path.stem)] = data
        except (ValueError, UnicodeError):
            continue

    def flatten(name, seen=()):
        assert name not in seen, name
        data, result = index[name], {}
        if data.get('inherits'): result.update(flatten(data['inherits'], seen + (name,)))
        for parent in data.get('include', []): result.update(flatten(parent, seen + (name,)))
        result.update(data)
        result.pop('inherits', None)
        result.pop('include', None)
        return result

    machine = flatten('Bambu Lab P1S 0.4 nozzle')
    process = flatten('0.20mm Standard @BBL X1C')
    filament = flatten('Bambu ASA @BBL X1C 0.4 nozzle')
    process.update(wall_loops='6', top_shell_layers='6', bottom_shell_layers='6',
                   sparse_infill_density='100%', sparse_infill_pattern='rectilinear',
                   brim_width='8', brim_type='outer_only', enable_support='0',
                   wall_generator='arachne', layer_height='0.2',
                   reduce_crossing_wall='1')
    if bridge_angle is not None:
        process.update(bridge_angle=str(bridge_angle), internal_bridge_angle=str(bridge_angle),
                       relative_bridge_angle='0', align_infill_direction_to_model='0')
    machine['curr_bed_type'] = 'Textured PEI Plate'
    machine['printer_settings_id'] = machine['name']
    process['print_settings_id'] = 'M1 comparison / 0.20 mm / 6 walls / solid CAD'
    filament['filament_settings_id'] = [filament['name']]
    result = {}
    output.mkdir(parents=True, exist_ok=True)
    for kind, data in [('machine', machine), ('process', process), ('filament', filament)]:
        data['from'] = 'system'
        path = output / (kind + '.json')
        path.write_text(json.dumps(data, indent=2) + '\n')
        result[kind] = path
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--orca', required=True, type=Path)
    ap.add_argument('--profiles', required=True, type=Path)
    ap.add_argument('--output', required=True, type=Path)
    ap.add_argument('--bridge-angle', type=float)
    ap.add_argument('models', nargs='+', type=Path)
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    settings = profiles(args.profiles, args.output / 'profiles', args.bridge_angle)
    results = []
    for source in args.models:
        target = args.output / source.stem
        target.mkdir(exist_ok=True)
        commands = [str(args.orca.resolve()), '--datadir', str((args.output / 'orca-user').resolve()),
                    '--load-settings', str(settings['machine'].resolve()) + ';' + str(settings['process'].resolve()),
                    '--load-filaments', str(settings['filament'].resolve()),
                    '--slice', '0', '--orient', '0', '--arrange', '0',
                    '--outputdir', str(target.resolve()), '--export-3mf', source.stem + '.gcode.3mf',
                    str(source.resolve())]
        started = time.time()
        with (target / 'slice.log').open('w') as log:
            proc = subprocess.run(commands, stdout=log, stderr=subprocess.STDOUT)
        result = {'source': source.name, 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                  'exit_code': proc.returncode, 'elapsed_seconds': time.time() - started}
        if (target / 'result.json').exists():
            result['slicer'] = json.loads((target / 'result.json').read_text())
        for archive in target.glob('*.gcode.3mf'):
            with zipfile.ZipFile(archive) as z:
                paths = [s for s in z.namelist() if s.endswith('.gcode')]
                if len(paths) == 1: (target / 'preview.gcode').write_bytes(z.read(paths[0]))
        results.append(result)
        (args.output / 'slice_summary.json').write_text(json.dumps(results, indent=2) + '\n')
        print(source.name, 'exit', proc.returncode, 'seconds', round(result['elapsed_seconds'], 1), flush=True)
        if proc.returncode:
            print((target / 'slice.log').read_text(errors='replace')[-4000:], flush=True)
            raise SystemExit(proc.returncode)


if __name__ == '__main__': main()
