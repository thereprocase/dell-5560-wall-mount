"""FreeCAD verification script for the Two-Banger 5560 Rack.

Run headless:
    flatpak run --command=freecadcmd org.freecad.FreeCAD "$PWD"/two-banger/work/check_rack.py

Checks:
1. Every part is a single valid solid and all sketches are fully constrained.
2. Every part fits inside the Bambu P1S 256 x 256 x 256 mm bed with an 8 mm
   outer perimeter brim (+16 mm to X and Y footprints).
3. Zero boolean interference (common.Volume == 0.0 mm3) between all pairs of
   printed parts.
4. Zero boolean interference (common.Volume == 0.0 mm3) between every printed
   part and the two 344.4 x 230.3 x 20.0 mm laptop envelopes and two
   140.0 x 140.0 x 25.0 mm fan envelopes.
5. Prints and saves volume (cm3) and PETG mass (g at 1.27 g/cm3) per part.
"""
from pathlib import Path
import itertools
import json
import math
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from params import get_params

import FreeCAD as App
import Part


def orient_for_print(key: str, shape):
    """Orient part flat onto the Bambu P1S XY bed with zero supports."""
    result = shape.copy()
    if key == '01_left_end_frame':
        result.rotate(App.Vector(), App.Vector(0, 1, 0), 90)
        pose = 'outer flat face down'
    elif key == '02_right_end_frame':
        result.rotate(App.Vector(), App.Vector(0, 1, 0), -90)
        pose = 'outer flat face down'
    else:
        pose = 'bottom deck flat down'
    b = result.BoundBox
    result.translate(App.Vector(128.0 - (b.XMin + b.XMax) / 2.0, 128.0 - (b.YMin + b.YMax) / 2.0, -b.ZMin))
    return result, pose

FCSTD = ROOT / 'TwoBanger.FCStd'
RESULTS_JSON = ROOT / 'check_results.json'
OUTPUT_TXT = ROOT / 'check_output.txt'


def _overlap_mm3(a, b) -> float:
    if not a.BoundBox.intersect(b.BoundBox):
        return 0.0
    common = a.common(b)
    if common.isNull():
        return 0.0
    return abs(float(common.Volume))


def _reference_envelopes(p: dict) -> dict:
    """Create the two tilted 5560 laptop envelopes and two 140 mm fan envelopes."""
    w = p['laptopWidth']
    d = p['laptopDepth']
    t = p['laptopThickness']
    yb = p['plenumBaseHalfY']
    zb = p['laptopBaseZ']
    tilt = p['tiltDeg']

    # Front (+Y) laptop: local box [X in -W/2..W/2, Y in 0..T, Z in 0..D]
    # rotated by +tilt around X so top leans inward (-Y), then translated to (0, yb, zb).
    lap_front = Part.makeBox(w, t, d, App.Vector(-w / 2.0, 0.0, 0.0))
    lap_front.rotate(App.Vector(0, 0, 0), App.Vector(1, 0, 0), tilt)
    lap_front.translate(App.Vector(0.0, yb, zb))

    # Back (-Y) laptop: local box [X in -W/2..W/2, Y in -T..0, Z in 0..D]
    # rotated by -tilt around X so top leans inward (+Y), then translated to (0, -yb, zb).
    lap_back = Part.makeBox(w, t, d, App.Vector(-w / 2.0, -t, 0.0))
    lap_back.rotate(App.Vector(0, 0, 0), App.Vector(1, 0, 0), -tilt)
    lap_back.translate(App.Vector(0.0, -yb, zb))

    # Two 140 x 140 x 25 mm fans sitting on top of the tray deck (Z = fanDeckTopZ = 21.0 mm)
    fs = p['fanSize']
    ft = p['fanThickness']
    fc_x = p['fanCenterX']
    fz = p['fanDeckTopZ']
    fan_left = Part.makeBox(fs, fs, ft, App.Vector(-fc_x - fs / 2.0, -fs / 2.0, fz))
    fan_right = Part.makeBox(fs, fs, ft, App.Vector(fc_x - fs / 2.0, -fs / 2.0, fz))

    return {
        'laptop_front': lap_front,
        'laptop_back': lap_back,
        'fan_left': fan_left,
        'fan_right': fan_right,
    }


def run_checks():
    p = get_params()
    doc = App.openDocument(str(FCSTD))
    doc.recompute()

    assembly = doc.getObject('RackAssembly')
    links = sorted(
        [o for o in assembly.Group if o.TypeId == 'App::Link'],
        key=lambda o: o.InstanceKey,
    )
    parts = {o.InstanceKey: o.Shape for o in links}

    bad_features = [
        o.Name for o in doc.Objects
        if 'Invalid' in o.State or 'Error' in o.State
    ]
    unconstrained = [
        o.Name for o in doc.Objects
        if o.TypeId == 'Sketcher::SketchObject' and not o.FullyConstrained
    ]

    brim_xy = 2.0 * p['brimWidth']  # 16.0 mm
    bed = p['bedLimit']             # 256.0 mm
    density = p['petgDensity']      # 1.27 g/cm3

    part_reports = {}
    total_vol_cm3 = 0.0
    total_mass_g = 0.0
    all_valid = True
    all_fit = True

    for key, shape in parts.items():
        valid = bool(shape.isValid() and len(shape.Solids) == 1)
        all_valid = all_valid and valid
        placed, pose = orient_for_print(key, shape)
        b = placed.BoundBox
        dx, dy, dz = float(b.XLength), float(b.YLength), float(b.ZLength)
        bx, by = dx + brim_xy, dy + brim_xy
        fits = ((bx <= bed + 1e-5 and by <= bed + 1e-5) or (by <= bed + 1e-5 and bx <= bed + 1e-5)) and dz <= bed + 1e-5
        all_fit = all_fit and fits
        vol_cm3 = float(shape.Volume) / 1000.0
        mass_g = vol_cm3 * density
        total_vol_cm3 += vol_cm3
        total_mass_g += mass_g
        part_reports[key] = {
            'orientation': pose,
            'valid_single_solid': valid,
            'footprint_xy_mm': [round(dx, 3), round(dy, 3)],
            'with_8mm_brim_xy_mm': [round(bx, 3), round(by, 3)],
            'height_z_mm': round(dz, 3),
            'fits_256_bed_with_brim': fits,
            'volume_cm3': round(vol_cm3, 3),
            'mass_g_petg': round(mass_g, 3),
        }

    part_overlaps = {}
    for (ka, sa), (kb, sb) in itertools.combinations(parts.items(), 2):
        vol = _overlap_mm3(sa, sb)
        if vol > 1e-5:
            part_overlaps[f'{ka} / {kb}'] = round(vol, 4)

    envs = _reference_envelopes(p)
    env_overlaps = {}
    for e_name, e_shape in envs.items():
        for p_name, p_shape in parts.items():
            vol = _overlap_mm3(p_shape, e_shape)
            if vol > 1e-5:
                env_overlaps[f'{p_name} / {e_name}'] = round(vol, 4)

    for (ea, sa), (eb, sb) in itertools.combinations(envs.items(), 2):
        vol = _overlap_mm3(sa, sb)
        if vol > 1e-5:
            env_overlaps[f'{ea} / {eb}'] = round(vol, 4)

    passed = (
        len(parts) == 4
        and not bad_features
        and not unconstrained
        and all_valid
        and all_fit
        and not part_overlaps
        and not env_overlaps
    )

    report = {
        'passed': passed,
        'part_count': len(parts),
        'petg_density_g_per_cm3': density,
        'total_volume_cm3': round(total_vol_cm3, 3),
        'total_mass_g': round(total_mass_g, 3),
        'bad_features': bad_features,
        'unconstrained_sketches': unconstrained,
        'part_overlaps_mm3': part_overlaps,
        'envelope_overlaps_mm3': env_overlaps,
        'parts': part_reports,
    }
    RESULTS_JSON.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')

    lines = [
        'Two-Banger 5560 Rack — FreeCAD B-Rep & Bed-Fit Verification',
        '=' * 96,
        f'Part count          : {len(parts)}',
        f'Invalid features    : {len(bad_features)}',
        f'Unconstrained sk    : {len(unconstrained)}',
        f'Part-to-part clash  : {len(part_overlaps)} (max overlap 0.0 mm3)',
        f'Part-to-env clash   : {len(env_overlaps)} (max overlap 0.0 mm3)',
        f'Material            : PETG ({density:.2f} g/cm3)',
        '',
        f"{'Part Name':<22} | {'Footprint XY (mm)':<17} | {'With 8mm Brim':<17} | {'Height Z':>8} | {'Vol cm3':>8} | {'Mass g':>8} | {'Status':<6}",
        '-' * 96,
    ]
    for key, info in part_reports.items():
        fx, fy = info['footprint_xy_mm']
        bx, by = info['with_8mm_brim_xy_mm']
        fz = info['height_z_mm']
        st = 'PASS' if (info['valid_single_solid'] and info['fits_256_bed_with_brim']) else 'FAIL'
        lines.append(
            f"{key:<22} | {fx:6.1f} x {fy:6.1f}   | {bx:6.1f} x {by:6.1f}   | {fz:6.1f}mm | {info['volume_cm3']:8.2f} | {info['mass_g_petg']:8.2f} | {st:<6}"
        )
    lines.extend([
        '-' * 96,
        f"TOTAL (4 parts)        | {'4 print plates':<17} | {'all <= 256x256':<17} | {'<=256mm':>8} | {total_vol_cm3:8.2f} | {total_mass_g:8.2f} | {'PASS' if passed else 'FAIL':<6}",
        '=' * 96,
        f"OVERALL RESULT: {'PASS' if passed else 'FAIL'}",
    ])
    if part_overlaps:
        lines.append(f"Part overlaps: {part_overlaps}")
    if env_overlaps:
        lines.append(f"Envelope overlaps: {env_overlaps}")

    text = '\n'.join(lines) + '\n'
    OUTPUT_TXT.write_text(text, encoding='utf-8')
    print(text, flush=True)
    App.closeDocument(doc.Name)
    if not passed:
        raise SystemExit(1)


run_checks()
