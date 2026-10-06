"""Geometric layer audit at 0.20 mm. A support screen, not a printer test.
Checks new islands and measures material beyond a 45-degree support envelope.
Reports bridge/edge regions and samples distance to supported material at 0.25 mm.
Bounding rectangles overstate the span of curved thin regions; use measured reach.
This geometric audit does not generate or validate Bambu Studio extrusion paths.
"""
import json
import numpy as np
import trimesh
from shapely import make_valid, contains_xy, points, distance
from shapely.ops import unary_union
from build_mount import OUT

def polys(g):
    if g.is_empty:return []
    if g.geom_type=='Polygon':return [g]
    return [p for t in getattr(g,'geoms',[]) for p in polys(t)]

def main():
    reports={}
    for name in ['02_right_cradle','04_right_fan_duct','06_right_fan_retainer','08_right_outlet_rail','10_right_fan_tray','right_outlet_rail_gap_8mm','right_outlet_rail_gap_16mm','12_right_push_pin']:
        mesh=trimesh.load(OUT/'print_ready'/f'{name}.stl',force='mesh')
        zs=np.arange(.1,mesh.bounds[1,2],.2)
        sections=mesh.section_multiplane([0,0,0],[0,0,1],zs)
        previous=None;islands=[];events=[];maxarea=0;maxspan=0;maxreach=0
        for z,sec in zip(zs,sections):
            if sec is None:continue
            current=make_valid(unary_union(sec.polygons_full))
            if previous is not None:
                support=previous.buffer(.205)
                for component in polys(current):
                    if component.area>.25 and component.intersection(support).area<.01:
                        islands.append({'z_mm':float(z),'area_mm2':component.area})
                excess=current.difference(support)
                for region in polys(excess):
                    if region.area<.15:continue
                    rectangle=region.minimum_rotated_rectangle
                    corners=np.array(rectangle.exterior.coords)
                    lengths=np.linalg.norm(np.diff(corners,axis=0),axis=1)
                    span=float(min(lengths));maxspan=max(maxspan,span);maxarea=max(maxarea,region.area)
                    # A curved thin ring has a large bounding box but is not a
                    # full-diameter bridge. Measure distance to real support.
                    if span>1.0:
                        x0,y0,x1,y1=region.bounds
                        xx,yy=np.meshgrid(np.arange(x0+.125,x1,.25),np.arange(y0+.125,y1,.25))
                        mask=contains_xy(region,xx,yy)
                        xy=np.column_stack((xx[mask],yy[mask]))
                        rp=region.representative_point()
                        xy=np.vstack((xy,[[rp.x,rp.y]]))
                        reach=float(np.max(distance(points(xy),support)))
                        maxreach=max(maxreach,reach)
                        events.append({'z_mm':round(float(z),2),'bbox_short_span_mm':round(span,3),
                            'maximum_sampled_reach_from_support_mm':round(reach,3),'area_mm2':round(region.area,3),'region_bounds_mm':list(region.bounds)})
            previous=current
        report={'layers':len(zs),'new_islands_above_bed':islands,'max_short_span_beyond_45deg_envelope_mm':maxspan,
                'maximum_sampled_reach_from_support_mm':maxreach,'max_excess_region_area_mm2':maxarea,'regions_with_short_span_over_1mm':events}
        reports[name]=report
        print(name,'islands',len(islands),'maximum unsupported reach',round(maxreach,3),'events',len(events),flush=True)

    (OUT/'layer_support_audit.json').write_text(json.dumps({'revision':'F','layer_height_mm':.2,'method':__doc__,'parts':reports},indent=2))

    for name,r in reports.items():
        assert not r['new_islands_above_bed'],(name,'unattached layer region')
        assert r['maximum_sampled_reach_from_support_mm']<10,(name,'review reach above 10 mm')

if __name__=='__main__':main()
