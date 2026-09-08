"""Estimate sliced polymer and recheck topology with shell/infill stiffness.

No slicing is implied: all results are estimates under stated assumptions.
"""
import os, json, shutil, subprocess
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as Patch
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from shapely.geometry import box, Polygon, Point
from shapely.ops import unary_union
import trimesh
from run_study import ROOT,grid,deck,H,NX,NY,THICKNESS

OUT=ROOT/'results';OUT.mkdir(exist_ok=True)
WALL=1.2; SKIN=1.0; INFILL=.2; DENSITY=.00127
nodes,elements,fixed=grid()

def shape_from_csv(p):
    d=np.genfromtxt(p,delimiter=',',names=True)
    cells=[box(r['cg_x']-1,r['cg_y']-1,r['cg_x']+1,r['cg_y']+1) for r in d if r['element_state']==1]
    return unary_union(cells)

def metrics(poly):
    core=poly.buffer(-WALL,join_style=2)
    v=poly.area*THICKNESS-(1-INFILL)*core.area*(THICKNESS-2*SKIN)
    return dict(area_mm2=poly.area,perimeter_mm=poly.length,cad_volume_mm3=poly.area*THICKNESS,
                core_area_mm2=core.area,polymer_volume_mm3=v,estimated_pair_mass_g=2*v*DENSITY,
                equivalent_solid_fraction=v/(poly.area*THICKNESS))

def parse_dat(p):
    # Each LOAD displacement table has node id and three vector components.
    disps=[]; stress=[];mode=None;current=[]
    for line in p.read_text().splitlines()+['END']:
        if 'displacements (' in line:
            if current:disps.append(max(current));current=[]
            mode='u';continue
        if 'stresses (' in line:
            if current:disps.append(max(current));current=[]
            mode='s';continue
        if 'internal energy density' in line:mode=None
        t=line.split()
        if mode=='u' and len(t)==4:
            try:current.append(float(np.linalg.norm([float(x) for x in t[1:]])))
            except ValueError:pass
        if mode=='s' and len(t)==8:
            try:
                sx,sy,sz,sxy,sxz,syz=map(float,t[2:]);stress.append(((sx-sy)**2+(sy-sz)**2+(sz-sx)**2+6*(sxy*sxy+sxz*sxz+syz*syz))**.5/2**.5)
            except ValueError:pass
    if current:disps.append(max(current))
    assert len(disps)==2 and stress,(disps,len(stress))
    return {'loadcase_max_displacement_mm':disps,'peak_homogenized_von_mises_MPa':max(stress)}

def main():
    polys={'solid':box(0,0,60,90)}
    for name in ['v40','v25']:
        case=ROOT/'work'/name;p=sorted(case.glob('file*.csv'))[-1]
        polys[name]=shape_from_csv(p)
        shutil.copy2(p,OUT/(name+'_states.csv'))
        shutil.copy2(case/'bracket.inp',OUT/(name+'_initial.inp'))
        shutil.copy2(case/'bracket.log',OUT/(name+'_history.log'))
        shutil.copy2(case/'beso_conf.py',OUT/(name+'_beso_conf.py'))
    # Straight facets replace voxel stairs; small holes add walls with little benefit.
    raw=polys['v25']
    if raw.geom_type!='Polygon':raise RuntimeError('Disconnected topology')
    holes=[r for r in raw.interiors if Polygon(r).area>=45]
    cleaned=Polygon(raw.exterior,holes).simplify(1.5,preserve_topology=True)
    keep=unary_union([box((e-1)%NX*H,(e-1)//NX*H,((e-1)%NX+1)*H,((e-1)//NX+1)*H) for e in fixed])
    polys['faceted25']=cleaned.union(keep)
    results={}
    for name,poly in polys.items():
        assert poly.is_valid and poly.geom_type=='Polygon'
        m=metrics(poly);core=poly.buffer(-WALL,join_style=2)
        active=[];mod={}
        for e,ns in elements.items():
            x=(e-1)%NX*H;y=(e-1)//NX*H
            if poly.covers(Point(x+1,y+1)) or e in fixed:
                active.append(e)
                shellfraction=1-core.intersection(box(x,y,x+H,y+H)).area/(H*H)
                skinfraction=2*SKIN/THICKNESS
                # Deliberately conservative infill stiffness: Erel=rho^2.
                rel=shellfraction+(1-shellfraction)*(skinfraction+(1-skinfraction)*INFILL**2)
                mod[e]=round(1800*rel/10)*10
        # Check face-connected solid elements; corner-touch links do not count.
        from scipy.ndimage import label
        mask=np.zeros((NY,NX),bool)
        for e in active:mask[(e-1)//NX,(e-1)%NX]=1
        assert label(mask)[1]==1, f'{name}: disconnected FE solid'
        m['fea_cells']=len(active)
        inp=OUT/(name+'_fdm_check.inp');deck(inp,active,mod)
        with (OUT/(name+'_ccx.log')).open('w') as f:
            r=subprocess.run([os.environ['CCX'],str(inp.with_suffix(''))],stdout=f,stderr=subprocess.STDOUT)
        if r.returncode:raise RuntimeError(name+' CalculiX failed')
        m.update(parse_dat(inp.with_suffix('.dat')))
        m['mesh_area_difference_percent']=100*(len(active)*H*H/poly.area-1)
        mesh=trimesh.creation.extrude_polygon(poly,height=THICKNESS,engine='earcut')
        assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume>0
        m['stl_watertight']=True;m['stl_volume_mm3']=mesh.volume
        mesh.export(OUT/(name+'_study.stl'))
        results[name]=m
        paths=[]
        for ring in [poly.exterior,*poly.interiors]:
            pts=list(ring.coords);paths.append('M '+' L '.join(f'{x:.3f},{90-y:.3f}' for x,y in pts)+' Z')
        (OUT/(name+'_profile.svg')).write_text('<svg xmlns="http://www.w3.org/2000/svg" width="60mm" height="90mm" viewBox="0 0 60 90"><path fill="#49baad" fill-rule="evenodd" d="'+' '.join(paths)+'"/></svg>')
        print(name,json.dumps(m),flush=True)
    (OUT/'summary.json').write_text(json.dumps(results,indent=2))
    shutil.copy2(ROOT/'work/environment.json',OUT/'environment.json')
    fig,axs=plt.subplots(1,4,figsize=(15,6),facecolor='#101820')
    for ax,(name,p) in zip(axs,polys.items()):
        ax.set_facecolor('#101820');ax.add_patch(Patch(np.asarray(p.exterior.coords),fc='#51cbbd'))
        for r in p.interiors:ax.add_patch(Patch(np.asarray(r.coords),fc='#101820'))
        m=results[name]
        ax.set(xlim=(-3,63),ylim=(-3,100),aspect='equal',title=name,xlabel=f"Pair: {m['estimated_pair_mass_g']:.1f} g estimated\nMax displacement: {max(m['loadcase_max_displacement_mm']):.3f} mm")
        ax.title.set_color('white');ax.xaxis.label.set_color('#d9e2ed');ax.tick_params(colors='#d9e2ed')
    fig.suptitle('Topology versus actual polymer estimate',color='white',fontsize=19)
    fig.text(.5,.02,'PETG | 3 x 0.4 mm walls | 20% infill | assumed 1 mm top / bottom | no fasteners or retention features yet',ha='center',color='#d9e2ed')
    fig.tight_layout(rect=[0,.05,1,.94]);fig.savefig(OUT/'comparison.png',dpi=150,facecolor=fig.get_facecolor());plt.close(fig)
    fig=plt.figure(figsize=(10,7),facecolor='#101820');ax=fig.add_subplot(111,projection='3d');ax.set_facecolor('#101820')
    mesh=trimesh.creation.extrude_polygon(polys['faceted25'],height=10,engine='earcut')
    # Print view: XY profile lies on the bed; Z is build height.
    normals=mesh.face_normals
    colors=[('#64d4c3' if n[2]>.5 else '#287c7c' if n[2]<-.5 else '#3caaa4') for n in normals]
    ax.add_collection3d(Poly3DCollection(mesh.triangles,facecolors=colors,edgecolors='#183b43',linewidths=.12))
    ax.set(xlim=(-5,65),ylim=(-5,95),zlim=(0,15));ax.set_box_aspect((70,100,25));ax.view_init(elev=48,azim=-65);ax.set_axis_off()
    fig.text(.5,.92,'Faceted topology — actual extruded study mesh',ha='center',color='white',fontsize=18)
    fig.text(.5,.07,'Flat side on bed. Openings remain open through every layer.\nMounting hardware, retention and thickness taper remain design work.',ha='center',color='#d9e2ed')
    fig.savefig(OUT/'print_view.png',dpi=170,facecolor=fig.get_facecolor());plt.close(fig)

if __name__=='__main__':main()
