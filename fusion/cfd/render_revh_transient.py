"""Render actual sampled p and 3D vorticity with fixed scales and physical times."""
import os
os.environ['VTK_SMP_MAX_THREADS']='1'
from pathlib import Path
os.environ.setdefault('USERPROFILE',str(Path(os.environ['LOCALAPPDATA']).parents[1]))
import argparse
import io
import json
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image
from matplotlib.collections import LineCollection

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--case',type=Path,default=BASE/'runs/revh_transient_04')
parser.add_argument('--output',type=Path,default=ROOT/'docs/simulation/revh-transient')
parser.add_argument('--max-frames',type=int,default=80)
args=parser.parse_args();case=args.case.resolve();out=args.output.resolve()
meta=json.loads((case/'case_manifest.json').read_text())
smoke=meta.get('scope')=='runtime_smoke_only'
if smoke:assert case in out.parents, 'Smoke images must stay inside the smoke case'
out.mkdir(parents=True,exist_ok=True)
cad_lines=[]
if not smoke:
    plane=vtk.vtkPlane();plane.SetOrigin(.111,0,0);plane.SetNormal(1,0,0)
    for patch in ['printed','laptop','noctua']:
        reader=vtk.vtkSTLReader();reader.SetFileName(str(BASE/'geometry_revh'/(patch+'.stl')));reader.Update()
        cutter=vtk.vtkCutter();cutter.SetInputConnection(reader.GetOutputPort());cutter.SetCutFunction(plane);cutter.Update()
        cut=cutter.GetOutput()
        if not cut.GetNumberOfPoints():continue
        points=vtk_to_numpy(cut.GetPoints().GetData())[:,1:]*1000
        ids=vtk.vtkIdList();lines=cut.GetLines();lines.InitTraversal()
        while lines.GetNextCell(ids):cad_lines.append(points[[ids.GetId(i) for i in range(ids.GetNumberOfIds())]])
folders=sorted([p for p in (case/'postProcessing/edge_sections').iterdir() if p.is_dir()],key=lambda p:float(p.name))
folders=[p for p in folders if all((p/(n+'.vtp')).exists() for n in ['right_front','right_hinge'])]
assert folders,'No complete right-side section frames'
available_count=len(folders)
selected=np.unique(np.linspace(0,len(folders)-1,min(args.max_frames,len(folders))).round().astype(int))
folders=[folders[i] for i in selected]

def data(path):
    reader=vtk.vtkXMLPolyDataReader();reader.SetFileName(str(path));reader.Update()
    poly=reader.GetOutput()
    if poly.GetPointData().GetArray('p') is None:
        conv=vtk.vtkCellDataToPointData();conv.SetInputData(poly);conv.Update();poly=conv.GetOutput()
    tri=vtk.vtkTriangleFilter();tri.SetInputData(poly);tri.Update();poly=tri.GetOutput()
    xyz=vtk_to_numpy(poly.GetPoints().GetData())
    ids=vtk_to_numpy(poly.GetPolys().GetData()).reshape(-1,4)[:,1:]
    p=vtk_to_numpy(poly.GetPointData().GetArray('p'))*1.2
    omega=vtk_to_numpy(poly.GetPointData().GetArray('vorticity'))[:,0]
    valid=np.isfinite(p)&np.isfinite(omega)
    ids=ids[valid[ids].all(axis=1)]
    assert len(ids)>0
    return xyz[:,1:]*1000,ids,p,omega

samples=[];pressure_samples=[];ranges={'pressure_Pa':[],'vorticity_x_per_s':[]}
for folder in folders:
    for name in ['right_front','right_hinge']:
        pts,ids,p,w=data(folder/(name+'.vtp'))
        samples.extend(np.abs(w[::max(1,len(w)//5000)]))
        pressure_samples.extend(np.abs(p[::max(1,len(p)//5000)]))
        ranges['pressure_Pa'].extend([float(p.min()),float(p.max())])
        ranges['vorticity_x_per_s'].extend([float(w.min()),float(w.max())])
vlim=max(100,float(np.ceil(np.percentile(samples,99)/100)*100))
plim=max(12,float(np.ceil(np.percentile(pressure_samples,99)/10)*10))
frames=[];times=[]
for folder in folders:
    t=float(folder.name);times.append(t)
    fig,axs=plt.subplots(2,2,figsize=(12,10),layout='constrained')
    for row,name in enumerate(['right_front','right_hinge']):
        pts,ids,p,w=data(folder/(name+'.vtp'))
        for col,values,limit,label in [(0,p,plim,'Gauge static pressure [Pa]'),(1,w,vlim,'Spanwise vorticity X [1/s]')]:
            ax=axs[row,col]
            ax.set_facecolor('#dce3e7')
            im=ax.tripcolor(pts[:,0],pts[:,1],ids,values,shading='gouraud',cmap='RdBu_r',vmin=-limit,vmax=limit,rasterized=True)
            ax.set(xlim=(25,75),ylim=(-8,35) if row==0 else (208,262),aspect='equal',xlabel='Y from wall [mm]',ylabel='Height Z [mm]',title='Front lip / duct outlet' if row==0 else 'Hinge lip / discharge')
            if cad_lines:ax.add_collection(LineCollection(cad_lines,colors='#172d36',linewidths=.6))
            fig.colorbar(im,ax=ax,shrink=.8,label=label)
    fig.suptitle(('RUNTIME SMOKE ONLY' if smoke else 'Revision H | transient commissioning')+f' | t = {t*1000:.4f} ms\nRight-side sections at X=111 mm. Startup; sustained shedding is not established.\nGrey: solid or no sampled data. Black: CAD surface. Unsampled cells are not filled.',fontsize=12)
    buf=io.BytesIO();fig.savefig(buf,format='png',dpi=120);buf.seek(0)
    frames.append(Image.open(buf).convert('RGB'))
    if folder==folders[-1]:fig.savefig(out/'pilot-sections.png',dpi=170)
    plt.close(fig)
    print('Rendered',t,flush=True)
slowdown=max(1000,.02/min(np.diff(times))) if len(times)>1 else None
durations=[max(20,int(round((times[i+1]-t)*slowdown*1000))) for i,t in enumerate(times[:-1])]+[2000]
# Deliberately play once: repeatedly wrapping a startup record can suggest a
# periodicity that has not been demonstrated in the physical simulation.
if len(frames)>1:
    frames[0].save(out/'pilot-sections.gif',save_all=True,append_images=frames[1:],duration=durations,optimize=False)
report={'scope':'runtime_smoke_only' if smoke else 'transient_commissioning_only',
        'physical_times_s':times,'source_case':case.name,'sections':['right_front','right_hinge'],
        'available_frame_count':available_count,'displayed_frame_count':len(folders),
        'pressure_scale_Pa':[-plim,plim],'vorticity_x_scale_per_s':[-vlim,vlim],
        'scale_selection':'99th percentile of absolute sampled values across displayed frames, rounded upward; minimum half-ranges 12 Pa and 100 per s. Same scale on every displayed frame.',
        'sampled_ranges':{k:[min(v),max(v)] for k,v in ranges.items()},
        'vorticity':'Sampled from the solver-side 3D vorticity field, X component; not inferred from 2D streamlines.',
        'sampling_gaps':'Bounded cutting-plane output can omit coarse cells that cross its clipping box. Grey denotes solid or unsampled regions; CAD outlines distinguish the intended geometry. Gaps are not filled.',
        'playback_slowdown':slowdown,
        'animation':'Single playback with recorded timestamp spacing rounded to GIF timing; final frame held for 2 s.' if len(frames)>1 else 'One recorded section time; still image only, no animation.',
        'caution':'A startup animation is not evidence of sustained periodic shedding or a Bernoulli cause for pressure depression. Colour scales are fixed across all displayed frames; values outside them are clipped.'}
(out/'animation-provenance.json').write_text(json.dumps(report,indent=2)+'\n')
print('Wrote',out,flush=True)
