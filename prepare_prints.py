"""Bake the intended print orientation into standard 3MF/STL model files.
3MF files contain geometry and units; they do not override Bambu machine settings.
"""
from pathlib import Path
import json, zipfile
import cadquery as cq
import numpy as np
import trimesh
from shapely.geometry import MultiPoint, box as rect
from build_mount import OUT, PARTS, bbox, box, untilt, pin

PRINT=OUT/'print_ready';PRINT.mkdir(exist_ok=True)

def orient(s,family,side='right',center=True):
    if family=='cradle':
        s=s.rotate((0,0,0),(0,1,0),90 if side=='right' else -90)
        s=s.rotate((0,0,0),(0,0,1),45)
    elif family=='outlet_rail':s=s.rotate((0,0,0),(1,0,0),180)
    elif family in ['fan_duct','fan_tray']:s=untilt(s)
    elif family=='fan_retainer':s=untilt(s).rotate((0,0,0),(1,0,0),-90)
    elif family=='push_pin':s=pin().val()
    b=bbox(s)
    x=128-(b['xmin']+b['xmax'])/2 if center else -b['xmin']
    y=128-(b['ymin']+b['ymax'])/2 if center else -b['ymin']
    return s.translate((x,y,-b['zmin']))

def export(s,name,family,side='right'):
    s=orient(s,family,side)
    vs,fs=s.tessellate(.06,.10)
    mesh=trimesh.Trimesh(vertices=[v.toTuple() for v in vs],faces=fs,process=True)
    # OCC can emit zero-area seam triangles; remove them before mesh delivery.
    mesh.merge_vertices(digits_vertex=7)
    mesh.update_faces(mesh.nondegenerate_faces())
    mesh.update_faces(mesh.unique_faces())
    mesh.remove_unreferenced_vertices()
    mesh.metadata['units']='mm';mesh.metadata['name']=name
    assert mesh.is_watertight,(name,'mesh not closed')
    scene=trimesh.Scene();scene.add_geometry(mesh,node_name=name,geom_name=name)
    (PRINT/f'{name}.3mf').write_bytes(trimesh.exchange.threemf.export_3MF(scene))
    mesh.export(PRINT/f'{name}.stl')
    # Conservative footprint includes every projected point and an 8 mm brim.
    footprint=MultiPoint(mesh.vertices[:,:2]).convex_hull.buffer(8)
    assert rect(0,0,256,256).covers(footprint),(name,'brim beyond plate')
    assert footprint.intersection(rect(0,0,18,28)).area<1e-7,(name,'cutter exclusion')
    assert mesh.bounds[1,2]<=256
    with zipfile.ZipFile(PRINT/f'{name}.3mf') as f:assert f.testzip() is None
    # Round-trip mesh confirms standard 3MF retained its orientation and size.
    reread=trimesh.load(PRINT/f'{name}.3mf',force='mesh')
    assert np.allclose(reread.bounds,mesh.bounds,atol=1e-4)
    return {'family':family,'side':side,'print_dimensions_mm':mesh.extents.tolist(),
            'print_bounds_mm':mesh.bounds.tolist(),'8mm_brim_inside_256_plate':True,
            'stock_18x28mm_cutter_exclusion_clear':True,'watertight':True}

def main():
    for p in PRINT.iterdir():
        if p.suffix in ['.stl','.3mf']:p.unlink()
    data={}
    for p in sorted(PARTS.glob('*.step')):
        name=p.stem;family=next(k for k in ['cradle','outlet_rail','fan_retainer','fan_duct','fan_tray','push_pin'] if k in name)
        data[name]=export(cq.importers.importStep(str(p)).val(),name,family,'left' if 'left' in name else 'right')
    for p in sorted((OUT/'outlet_gap_variants').glob('*.step')):
        data[p.stem]=export(cq.importers.importStep(str(p)).val(),p.stem,'outlet_rail','left' if 'left' in p.stem else 'right')
    # Fit coupons reproduce the glued tenon clearance and split-pin fit.
    cradle=cq.importers.importStep(str(PARTS/'02_right_cradle.step')).val()
    duct=cq.importers.importStep(str(PARTS/'04_right_fan_duct.step')).val()
    female=cradle.intersect(box(143,157,9,26.3,-56,-32).val())
    male=duct.intersect(box(145,155,13,31,-56,-32).val())
    for n,s in [('FIT_COUPON_female_key',female),('FIT_COUPON_male_key',male)]:
        assert len(s.Solids())==1 and s.isValid(),n
        data[n]=export(s,n,'cradle')
    data['FIT_COUPON_push_pin']=export(pin().val(),'FIT_COUPON_push_pin','push_pin')
    bore=box(-6,6,-6,6,0,8).cut(__import__('cadquery').Workplane('XY').circle(2.05).extrude(9)).val()
    data['FIT_COUPON_pin_socket']=export(bore,'FIT_COUPON_pin_socket','coupon')
    scene=trimesh.Scene();meshes=[]
    for name,dx in [('FIT_COUPON_female_key',-40),('FIT_COUPON_male_key',0),('FIT_COUPON_push_pin',30),('FIT_COUPON_pin_socket',50)]:
        m=trimesh.load(PRINT/f'{name}.stl',force='mesh');m.apply_translation([dx,0,0]);m.metadata['units']='mm'
        scene.add_geometry(m,node_name=name,geom_name=name);meshes.append(m)
    (PRINT/'00_FIT_COUPONS.3mf').write_bytes(trimesh.exchange.threemf.export_3MF(scene))
    trimesh.util.concatenate(meshes).export(PRINT/'00_FIT_COUPONS.stl')
    (OUT/'print_orientation_validation.json').write_text(json.dumps({'revision':'F','nozzle_mm':.4,'layer_height_mm':.2,'parts':data},indent=2))
    print(json.dumps({n:d['print_dimensions_mm'] for n,d in data.items()},indent=2))

if __name__=='__main__':main()
