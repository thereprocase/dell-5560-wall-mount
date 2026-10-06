"""Reapply the original editable socket cutters after the finished duct union."""
import math
import FreeCAD as App
import Part

DUCT_KEYS = ('03_left_fan_duct', '04_right_fan_duct')
PIN_KEYS = ('11_left_push_pin', '12_right_push_pin', '13_left_push_pin', '14_right_push_pin')
TOOL_NAMES = ('Extrusion038', 'Extrusion040')


def installed(document):
    return {
        getattr(obj, 'InstanceKey', None) or obj.OptionalInstanceKey: obj
        for obj in document.Objects
        if obj.TypeId == 'App::Link'
        and (hasattr(obj, 'InstanceKey') or hasattr(obj, 'OptionalInstanceKey'))
    }


def apply(document, source_sha256):
    existing = document.getObject('D4ClearPinSockets')
    if existing:
        assert existing.Base == document.getObject('D3EndWallRootR1')
        assert existing.Tool.Links == [document.getObject(name) for name in TOOL_NAMES]
        return existing

    base = document.getObject('D3EndWallRootR1')
    right = document.getObject('D3RightDuct')
    assert base and right and right.Links == [base]
    cutters = [document.getObject(name) for name in TOOL_NAMES]
    assert all(obj and obj.TypeId == 'Part::Extrusion' for obj in cutters)
    assert all(any('pinSocketDiameter' in expression for _, expression in obj.Base.ExpressionEngine)
               for obj in cutters)

    group = document.addObject('App::DocumentObjectGroup', 'DuctSocketCorrectionD4')
    group.Label = 'D4 / clear fan-cover sockets after the duct union'
    tool = document.addObject('Part::Compound', 'D4OriginalSocketCutters')
    tool.Label = 'Original pin bores / shared diameter, positions and blind bottoms'
    tool.Links = cutters
    group.addObject(tool)
    result = document.addObject('Part::Cut', 'D4ClearPinSockets')
    result.Label = 'D4 / finished duct with clear blind pin sockets'
    result.Base = base
    result.Tool = tool
    result.Refine = True
    group.addObject(result)
    right.Links = [result]

    # Preserve source names and installed links so section helpers and the
    # current parameter bindings continue to refer to the same objects.
    for name in ('CurrentDuctSection', 'T3ReinforcedWallCoupon'):
        obj = document.getObject(name)
        if obj and obj.Base == base:
            obj.Base = result
    for key, name in zip(DUCT_KEYS, ('D3LeftDuct', 'D3RightDuct')):
        document.getObject(name).Label = key.replace('_', ' ') + ' / D4 clear sockets'
        installed(document)[key].Label = key.replace('_', ' ') + ' / D4 clear sockets'

    result.addProperty('App::PropertyString', 'Correction', 'Provenance')
    result.Correction = 'Repeat the original socket cuts after the final duct union; preserve blind bottoms.'
    result.addProperty('App::PropertyString', 'SourceSHA256', 'Provenance')
    result.SourceSHA256 = source_sha256
    result.addProperty('App::PropertyString', 'PhysicalStatus', 'Provenance')
    result.PhysicalStatus = 'CAD and toolpaths require validation; physical pin fit/removal remains untested.'
    for obj in [tool, result] + cutters:
        obj.Visibility = False
    if document.getObject('RevHParameters'):
        document.getObject('RevHParameters').set('A1', 'REV H CURRENT / D4 + T3 + R2')
    document.Label = 'Rev H current / D4 sockets + T3 trays + R2 retainers'
    document.recompute()
    return result


def socket_checks(document):
    result = document.getObject('D4ClearPinSockets')
    assert result and result.Shape.isValid() and len(result.Shape.Solids) == 1
    rows = []
    for name in TOOL_NAMES:
        tool = document.getObject(name)
        blocked = result.Shape.common(tool.Shape).Volume
        assert blocked < 1e-6, (name, blocked)
        rows.append({'native_cutter': name, 'remaining_material_mm3': blocked})
    return rows


def verify(document, baseline=None):
    errors = [(obj.Name, list(obj.State)) for obj in document.Objects
              if 'Invalid' in obj.State or 'Error' in obj.State]
    assert not errors, errors
    objects = installed(document)
    assert len(objects) == 20
    result = {'socket_checks': socket_checks(document), 'parts': {}, 'pins': {}}
    for key, obj in objects.items():
        shape = obj.Shape
        assert shape.isValid() and len(shape.Solids) == 1, key
        row = {'valid_single_solid': True}
        if baseline is not None:
            added = shape.cut(baseline[key]).Volume
            removed = baseline[key].cut(shape).Volume
            if key in DUCT_KEYS:
                assert added < 1e-6 and 40 < removed < 45, (key, added, removed)
            else:
                assert added + removed < 1e-6, (key, added, removed)
            row.update(added_mm3=added, removed_mm3=removed)
        result['parts'][key] = row

    local = document.getObject('D4ClearPinSockets')
    removed = local.Base.Shape.cut(local.Shape)
    outside = removed.cut(local.Tool.Shape).Volume
    assert outside < 1e-6, outside
    result['removed_outside_original_bores_mm3'] = outside
    # This explicitly excludes the shaft and head from the retention allowance.
    crown = document.getObject('PinCrown').Shape.cut(document.getObject('PinShaft').Shape)
    assert crown.Volume > 0 and crown.BoundBox.ZMin >= 11.999
    outward = App.Vector(0, 1 / math.sqrt(2), 1 / math.sqrt(2))
    for key in PIN_KEYS:
        pin = objects[key]
        duct = objects[DUCT_KEYS[0] if 'left' in key else DUCT_KEYS[1]].Shape
        mask = crown.copy()
        mask.Placement = pin.LinkPlacement.multiply(mask.Placement)
        samples = []
        for distance in (0, .2, .5, 1, 2, 3, 5, 8, 12):
            shape = pin.Shape.copy()
            allowance = mask.copy()
            shape.translate(outward * distance)
            allowance.translate(outward * distance)
            contact = shape.common(duct)
            unintended = contact.cut(allowance).Volume
            assert unintended < 1e-6, (key, distance, unintended)
            if distance == 0 and abs(float(document.getObject('Parameters').get('pinSocketDiameter').Value) - 4.1) < 1e-6:
                assert .005 < contact.Volume < .2, (key, 'seated crown contact', contact.Volume)
            samples.append({'outward_mm': distance, 'crown_overlap_mm3': contact.Volume,
                            'overlap_outside_crown_mm3': unintended})
        result['pins'][key] = samples
    result['passed'] = True
    return result
