"""Exercise upstream edits and prove that the final socket cuts stay active."""
from pathlib import Path
import json
import os
import sys
if sys.platform == 'win32':
    sys.path.insert(0, 'C:/Program Files/FreeCAD 1.1/lib')
    dll_directory = os.add_dll_directory('C:/Program Files/FreeCAD 1.1/bin')
import FreeCAD as App
import socket_fix

OUT = Path(__file__).resolve().parent
document = App.openDocument(str(OUT / 'Precision_5560_RevH_D4_Current.FCStd'))
baseline = {key: obj.Shape.copy() for key, obj in socket_fix.installed(document).items()}
report = {'trials': [], 'wall_mount_pattern_mm': {}}
parameters = document.getObject('Parameters')
for alias in ('wallHoleHalfSpacing', 'lowerWallHoleZ', 'upperWallHoleZ', 'wallHoleDiameter'):
    report['wall_mount_pattern_mm'][alias] = float(parameters.get(alias).Value)
assert report['wall_mount_pattern_mm'] == {
    'wallHoleHalfSpacing': 162.0, 'lowerWallHoleZ': -36.0,
    'upperWallHoleZ': 174.0, 'wallHoleDiameter': 7.0}
for sheet_name, alias, value in [('Parameters', 'pinSocketDiameter', 4.2),
                                ('RevHParameters', 'ductSideRoot', 3.5)]:
    sheet = document.getObject(sheet_name)
    cell = sheet.getCellFromAlias(alias)
    original = sheet.getContents(cell)
    try:
        print('Checking edit: ' + alias, flush=True)
        sheet.set(cell, str(value) + ' mm')
        document.recompute()
        check = socket_fix.verify(document)
        print('Socket and pin checks passed: ' + alias, flush=True)
        comparisons = {}
        for key, obj in socket_fix.installed(document).items():
            old, new = baseline[key], obj.Shape
            if key not in socket_fix.DUCT_KEYS or alias == 'pinSocketDiameter':
                delta = old.cut(new).Volume + new.cut(old).Volume
                if key in socket_fix.DUCT_KEYS:
                    assert 1 < delta < 30, (key, delta)
                elif alias == 'pinSocketDiameter' and key in socket_fix.PIN_KEYS:
                    assert 1 < delta < 15, (key, delta)
                else:
                    assert delta < .001, (key, delta)
                comparisons[key] = {'geometry_difference_mm3': delta,
                                    'method': 'both directional cuts',
                                    'before_mm3': old.Volume, 'trial_mm3': new.Volume}
                continue
            common = old.common(new).Volume
            # Nearly coincident fillets can make OCC's reverse Cut report the
            # entire solid. Use the intersection-volume identity for this
            # parameter-change metric; retain the diagnostic separately.
            assert common <= min(old.Volume, new.Volume) + .1, (key, common)
            delta = max(0, old.Volume + new.Volume - 2 * common)
            assert common > min(old.Volume, new.Volume) - .5, (key, common)
            assert .001 < delta < 300, (key, delta)
            comparisons[key] = {'geometry_difference_mm3': delta,
                                'common_mm3': common, 'before_mm3': old.Volume,
                                'trial_mm3': new.Volume}
        difference = sum(row['geometry_difference_mm3'] for row in comparisons.values())
        assert difference > .001
        report['trials'].append({'sheet': sheet_name, 'parameter': alias, 'trial_mm': value,
                                 'geometry_changed_mm3': difference, 'socket_checks': check['socket_checks'],
                                 'all_pins_checked': len(check['pins']), 'passed': check['passed'],
                                 'part_comparisons': comparisons})
    finally:
        sheet.set(cell, original)
        document.recompute()
    for key, obj in socket_fix.installed(document).items():
        difference = obj.Shape.cut(baseline[key]).Volume + baseline[key].cut(obj.Shape).Volume
        assert difference < .001, (alias, key, difference)
    print('Parameter edit and restore passed: ' + alias, flush=True)
report['all_defaults_restored'] = True
report['comparison_note'] = ('Root-radius duct delta uses V(A)+V(B)-2V(common); other comparisons use both Cuts. Raw reverse Cut on the '
                            'nearly coincident root fillets returned an inconsistent whole-solid '
                            'volume in both D3 and D4; see boolean-probe.json and '
                            'parameter-placement-probe.json. Final default restoration uses both Cuts.')
report['shared_socket_parameter'] = 'pinSocketDiameter sizes the four matching pins as well as the two ducts.'
report['passed'] = True
(OUT / 'parameter-validation.json').write_text(json.dumps(report, indent=2) + '\n')
App.closeDocument(document.Name)
