"""Compare actual print-layer sections at the arm/wall-pad transition.

The layer plane is normal to installed X in the released side-down arm pose.
Area and second moments quantify the geometry change, not a strength rating.
"""
from pathlib import Path
import argparse
import hashlib
import json
import shutil

import FreeCAD as App
import Part
from validate import shapes, overlap

ROOT = Path(__file__).resolve().parent


def number(doc, alias):
    raw = getattr(doc.getObject('M1Parameters'), alias)
    return raw.Value if hasattr(raw, 'Value') else App.Units.Quantity(str(raw)).Value


def section(arm, origin_x, print_height, z):
    thickness = .02
    x = origin_x - print_height
    slab = arm.common(Part.makeBox(thickness, 100, 36,
                                  App.Vector(x - thickness / 2, -1, z - 18)))
    assert slab.isValid() and slab.Volume > 0
    center = App.Vector(*[sum(getattr(s.CenterOfMass, axis) * s.Volume for s in slab.Solids) / slab.Volume
                          for axis in ('x', 'y', 'z')])
    area = slab.Volume / thickness
    iy = sum(s.MatrixOfInertia.A22 + s.Volume * ((s.CenterOfMass.x - center.x) ** 2
             + (s.CenterOfMass.z - center.z) ** 2) for s in slab.Solids) / thickness
    iz = sum(s.MatrixOfInertia.A33 + s.Volume * ((s.CenterOfMass.x - center.x) ** 2
             + (s.CenterOfMass.y - center.y) ** 2) for s in slab.Solids) / thickness
    loops = [[[v.y, v.z - z] for v in w.discretize(Deflection=.04)]
             for w in slab.slice(App.Vector(1, 0, 0), x)]
    return {'print_height_mm': print_height, 'area_mm2': area,
            'I_about_installed_Y_mm4': iy, 'I_about_installed_Z_mm4': iz,
            'polar_second_moment_mm4': iy + iz, 'profile_y_z_from_bolt_mm': loops}


def compare(before, after):
    old, new = shapes(before), shapes(after)
    x = number(after, 'armOriginX')
    thick = number(after, 'armThickness')
    h = number(after, 'armHeight')
    arm_old, arm_new = old['02_right_arm'], new['02_right_arm']
    differences = {key: old[key].cut(new[key]).Volume + new[key].cut(old[key]).Volume for key in old}
    assert all(differences[k] < .01 for k in differences if not k.endswith(('_arm', '_dam')))
    assert arm_old.cut(arm_new).Volume < .01, 'Reinforcement removed original arm material'
    old_bores = before.getObject('M1WallBoreCircles').Geometry
    new_bores = after.getObject('M1WallBoreCircles').Geometry
    assert len(old_bores) == len(new_bores)
    assert all((a.Center - b.Center).Length < 1e-9 and abs(a.Radius - b.Radius) < 1e-9
               for a, b in zip(old_bores, new_bores))
    junctions = {}
    for name, z in [('lower', 18), ('upper', h - 16)]:
        rows = []
        for height in (thick + .02, 14, 16, 18, 21, 24, 27, 29):
            a, b = section(arm_old, x, height, z), section(arm_new, x, height, z)
            rows.append({'before': a, 'after': b, 'area_ratio': b['area_mm2'] / a['area_mm2'],
                         'polar_second_moment_ratio': b['polar_second_moment_mm4'] / a['polar_second_moment_mm4']})
        # Representative 11 mm access cylinder, beginning 0.3 mm off the pad.
        # This is a modeled clearance envelope, not a confirmed anchor/socket.
        driver = Part.makeCylinder(5.5, 80, App.Vector(x - 18, number(after, 'wallPadDepth') + .3, z), App.Vector(0, 1, 0))
        interference = overlap(arm_new, driver)
        assert interference < 1e-4
        junctions[name] = {'sections': rows, 'driver_envelope_diameter_mm': 11,
                           'driver_envelope_interference_mm3': interference,
                           'driver_envelope_gap_mm': arm_new.distToShape(driver)[0]}
    return {'junctions': junctions, 'bolt_centers_unchanged': True,
            'original_arm_material_removed_mm3': arm_old.cut(arm_new).Volume,
            'changed_parts_mm3': {k: v for k, v in differences.items() if v > .01},
            'added_arm_volume_mm3_each': arm_new.Volume - arm_old.Volume,
            'added_arm_solid_mass_g_pair_at_1_05': 2 * (arm_new.Volume - arm_old.Volume) * .00105,
            'assembly_solid_mass_change_g_at_1_05': sum(new[k].Volume - old[k].Volume for k in old) * .00105,
            'unchanged_other_parts': 16, 'strength_rating_established': False}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--nominal-only', action='store_true')
    ap.add_argument('--baseline-dir', type=Path, default=ROOT / 'snapshots/before-gussets')
    ap.add_argument('--output', type=Path, default=ROOT / 'reports/wall-transition-review.json')
    args = ap.parse_args()
    report = {'revision': 'Minimalist M1.1', 'baseline_commit': '64fc1aa',
              'layer_section_method': '0.02 mm slab normal to installed X, matching the released arm build axis; evaluated just above the original 12 mm arm thickness and through the pads.',
              'limits': 'Geometric section comparison only. Ratios are not tested strength multipliers. No ASA interlayer allowable, notch concentration, creep, anchor capacity, uneven loading or physical load qualification is established.',
              'presets': {}}
    cases = [('5560', ROOT / 'Laptop_Wall_Mount_Minimalist.FCStd', ROOT / 'snapshots/M1_64fc1aa_before_gussets.FCStd')] if args.nominal_only else [
        (p.parent.name, p, args.baseline_dir / p.parent.name / 'M1.FCStd') for p in sorted((ROOT / 'presets').glob('*/M1.FCStd'))]
    for name, new_path, old_path in cases:
        current = ROOT / 'scratch/TransitionCurrent.FCStd'
        shutil.copy2(new_path, current)
        before, after = App.openDocument(str(old_path)), App.openDocument(str(current))
        data = compare(before, after)
        data['before_native_sha256'] = hashlib.sha256(old_path.read_bytes()).hexdigest()
        data['after_native_sha256'] = hashlib.sha256(new_path.read_bytes()).hexdigest()
        report['presets'][name] = data
        App.closeDocument(after.Name)
        App.closeDocument(before.Name)
        args.output.parent.mkdir(exist_ok=True, parents=True)
        args.output.write_text(json.dumps(report, indent=2) + '\n')
        joint = data['junctions']['lower']['sections'][0]
        print(name, 'layer area', round(joint['before']['area_mm2'], 2), 'to', round(joint['after']['area_mm2'], 2),
              'arm pair added solid mass', round(data['added_arm_solid_mass_g_pair_at_1_05'], 2), flush=True)


if __name__ == '__main__': main()
