"""Slice D4 with the exact checked D3 machine, material and process values."""
from pathlib import Path
import hashlib
import json
import shutil
import sys
import argparse

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'minimalist'))
import slice_models


def profiles(unused_root, output, unused_angle=None):
    output.mkdir(parents=True, exist_ok=True)
    result, provenance = {}, {}
    for kind in ('machine', 'process', 'filament'):
        source = OUT / 'baseline/profiles' / (kind + '.json')
        target = output / source.name
        shutil.copy2(source, target)
        assert target.read_bytes() == source.read_bytes()
        result[kind] = target
        provenance[kind] = {'source': str(source.relative_to(ROOT)),
                            'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                            'byte_identical': True}
    (OUT / 'preset-provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    return result


slice_models.profiles = profiles
parser = argparse.ArgumentParser()
parser.add_argument('--orca', required=True, help='OrcaSlicer executable or extracted AppRun')
parser.add_argument('--orca-profiles', required=True, help='OrcaSlicer resources/profiles directory')
args = parser.parse_args()
sys.argv = ['slice_models.py', '--orca', args.orca,
            '--profiles', args.orca_profiles, '--output', str(OUT / 'slices')]
sys.argv += [str(OUT / 'prepared' / (key + '.3mf'))
             for key in ('03_left_fan_duct', '04_right_fan_duct')]
slice_models.main()
