"""Section properties from CAD tessellation, including unsymmetric bending."""
import cadquery as cq
import trimesh,numpy as np
from shapely.geometry.polygon import orient
from build_mount import OUT,box

def properties(polygons):
    A=Qx=Qy=Ixx=Iyy=Ixy=0.;coords=[]
    for p in polygons:
        p=orient(p,sign=1)
        for ring in [p.exterior,*p.interiors]:
            v=np.array(ring.coords);a=v[:-1];b=v[1:];cross=a[:,0]*b[:,1]-b[:,0]*a[:,1]
            A+=cross.sum()/2;Qx+=((a[:,0]+b[:,0])*cross).sum()/6;Qy+=((a[:,1]+b[:,1])*cross).sum()/6
            Ixx+=((a[:,1]**2+a[:,1]*b[:,1]+b[:,1]**2)*cross).sum()/12
            Iyy+=((a[:,0]**2+a[:,0]*b[:,0]+b[:,0]**2)*cross).sum()/12
            Ixy+=((2*a[:,0]*a[:,1]+a[:,0]*b[:,1]+b[:,0]*a[:,1]+2*b[:,0]*b[:,1])*cross).sum()/24
            coords.extend(a)
    cx,cy=Qx/A,Qy/A
    Ixx-=A*cy**2;Iyy-=A*cx**2;Ixy-=A*cx*cy
    v=np.array(coords)-[cx,cy];det=Ixx*Iyy-Ixy**2
    unit_stress=(Iyy*v[:,1]-Ixy*v[:,0])/det
    return {'area_mm2':float(A),'effective_section_modulus_mm3':float(1/max(abs(unit_stress))),
            'effective_inertia_mm4':float(det/Iyy),'Ixy_mm4':float(Ixy)}

def profiles():
    s=cq.importers.importStep(str(OUT/'parts/02_right_cradle.step')).val()
    result={}
    specs=[('tine',box(139,185,64,85,.001,94).val(),np.arange(.2,90,.5),False),
           ('rear',box(139,185,-.1,26,41,154).val(),np.arange(42,153,.5),False),
           ('shelf',box(139,185,10,64,-12,0).val(),np.arange(10.2,63.9,.5),True)]
    for name,clip,heights,rotate in specs:
        c=s.intersect(clip)
        if rotate:c=c.rotate((0,0,0),(1,0,0),90)
        vs,fs=c.tessellate(.025,.1);mesh=trimesh.Trimesh(vertices=[v.toTuple() for v in vs],faces=fs,process=True)
        sections=mesh.section_multiplane([0,0,0],[0,0,1],heights)
        result[name]=[{'station_mm':float(z),**properties(sec.polygons_full)} for z,sec in zip(heights,sections)]
    return result

if __name__=='__main__':
    import json
    d=profiles();(OUT/'section_properties.json').write_text(json.dumps(d,indent=2))
    for n,v in d.items():print(n,'minimum modulus',min(p['effective_section_modulus_mm3'] for p in v))
