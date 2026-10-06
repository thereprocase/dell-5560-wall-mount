"""Offline cross-kernel STEP comparison using installed FreeCAD Python.

Run with C:/Program Files/FreeCAD 1.1/bin/python.exe.
Does not open a GUI or modify a FreeCAD document.
"""
import json
import hashlib
from pathlib import Path
import FreeCAD as App
import Part

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'onshape'/'exploration_20'
native_path=OUT/'33-native-pin-download.step'
source_path=ROOT/'parts'/'12_right_push_pin.step'
native=Part.read(str(native_path))
source=Part.read(str(source_path))
source.translate(App.Vector(0,-67,84))
source.rotate(App.Vector(0,0,0),App.Vector(1,0,0),-45)
source.translate(App.Vector(-5,-76,-1))
source.rotate(App.Vector(0,0,0),App.Vector(1,0,0),-90)

def bounds(shape):
    b=shape.BoundBox
    return [b.XMin,b.YMin,b.ZMin,b.XMax,b.YMax,b.ZMax]

result=dict(native_valid=native.isValid(),source_valid=source.isValid(),
    native_solids=len(native.Solids),source_solids=len(source.Solids),
    native_volume_mm3=native.Volume,source_volume_mm3=source.Volume,
    native_bounds_mm=bounds(native),source_bounds_mm=bounds(source),
    native_minus_source_mm3=native.cut(source).Volume,
    source_minus_native_mm3=source.cut(native).Volume,
    common_volume_mm3=native.common(source).Volume,
    freecad_version=App.Version(),occt_version=Part.OCC_VERSION,
    input_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [native_path,source_path]})
result['symmetric_difference_mm3']=result['native_minus_source_mm3']+result['source_minus_native_mm3']
result['passes_1e-4_mm3_difference']=abs(result['symmetric_difference_mm3'])<1e-4
result['volume_delta_mm3']=result['native_volume_mm3']-result['source_volume_mm3']
result['volume_and_boolean_agree']=abs(result['volume_delta_mm3'])<1e-4

def mesh_volume(shape, tolerance):
    vertices, triangles=shape.tessellate(tolerance)
    return abs(sum(vertices[a].dot(vertices[b].cross(vertices[c])) for a,b,c in triangles)/6)

result['tessellated_volume_checks']=[dict(deflection_mm=t,
    native_mm3=mesh_volume(native,t),source_mm3=mesh_volume(source,t)) for t in [.005,.001,.0001]]
result['assessment']='Both Boolean differences empty and fine tessellated volumes agree closely. Raw OCCT volume integration disagrees; an integration discrepancy is suspected, not proven. Exact conversion is not unconditionally accepted.'
(OUT/'pin_geometry_comparison.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
assert result['native_valid'] and result['source_valid']
assert result['native_solids']==result['source_solids']==1
# Boolean emptiness alone is not a sufficient acceptance gate when independent volumes disagree.
