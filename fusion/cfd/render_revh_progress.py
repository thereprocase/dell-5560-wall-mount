"""Render immutable hourly MP4s from actual full-plane Rev H samples.

Run with FreeCAD's Python (VTK, Matplotlib, NumPy, Pillow). Uses fixed scales,
CAD context, actual in-plane velocity arrows and physical timestamps. It never
interpolates between CFD times. Repeated encoded frames are timing holds only.
"""
import os
os.environ['VTK_SMP_MAX_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
os.environ.setdefault('WINDIR','C:/Windows')
os.environ.setdefault('SystemRoot','C:/Windows')
from pathlib import Path
os.environ.setdefault('USERPROFILE',str(Path(os.environ['LOCALAPPDATA']).parents[1]))
import argparse
from datetime import datetime,timezone
import hashlib
import json
import subprocess
import time
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from PIL import Image

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def read_plane(path):
    r=vtk.vtkXMLPolyDataReader();r.SetFileName(str(path));r.Update()
    poly=r.GetOutput()
    if not poly.GetPointData().GetArray('p'):
        c=vtk.vtkCellDataToPointData();c.SetInputData(poly);c.Update();poly=c.GetOutput()
    tri=vtk.vtkTriangleFilter();tri.SetInputData(poly);tri.Update();poly=tri.GetOutput()
    points=vtk_to_numpy(poly.GetPoints().GetData()).copy()[:,1:]*1000
    ids=vtk_to_numpy(poly.GetPolys().GetData()).reshape(-1,4)[:,1:].copy()
    fields={name:vtk_to_numpy(poly.GetPointData().GetArray(name)).copy() for name in ['p','U','vorticity','Q']}
    assert all(np.isfinite(a).all() for a in fields.values()), 'Nonfinite sampled field'
    return points,ids,fields


def cad_sections():
    result=[]
    for name in ['printed','laptop','noctua']:
        r=vtk.vtkSTLReader();r.SetFileName(str(BASE/'geometry_revh'/(name+'.stl')));r.Update()
        plane=vtk.vtkPlane();plane.SetNormal(1,0,0);plane.SetOrigin(.111,0,0)
        cut=vtk.vtkCutter();cut.SetInputConnection(r.GetOutputPort());cut.SetCutFunction(plane);cut.Update()
        poly=cut.GetOutput()
        if not poly.GetNumberOfPoints():continue
        points=vtk_to_numpy(poly.GetPoints().GetData())[:,1:]*1000
        ids=vtk.vtkIdList();lines=poly.GetLines();lines.InitTraversal()
        while lines.GetNextCell(ids):result.append(points[[ids.GetId(i) for i in range(ids.GetNumberOfIds())]].copy())
    return result


def choose(pts,tri,bounds):
    lo=np.min(pts[tri],axis=1);hi=np.max(pts[tri],axis=1)
    x0,x1,y0,y1=bounds
    return tri[(lo[:,0]<=x1)&(hi[:,0]>=x0)&(lo[:,1]<=y1)&(hi[:,1]>=y0)]


def arrows(ax,pts,U,bounds,spacing=3.0,scale=1.0):
    x0,x1,y0,y1=bounds
    indices=np.flatnonzero((pts[:,0]>x0)&(pts[:,0]<x1)&(pts[:,1]>y0)&(pts[:,1]<y1))
    bins=np.floor(pts[indices]/spacing).astype(np.int32)
    _,selected=np.unique(bins,axis=0,return_index=True)
    indices=indices[selected]
    indices=indices[np.linalg.norm(U[indices,1:],axis=1)>.01]
    return ax.quiver(pts[indices,0],pts[indices,1],U[indices,1],U[indices,2],
                     color='#172d36',angles='xy',scale_units='xy',scale=scale,
                     width=.0028,headwidth=3.8,headlength=4.5,pivot='middle')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--case',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--hour',type=int,required=True)
    p.add_argument('--ffmpeg',default='F:/Code/gpu-offload/bin/ffmpeg.exe')
    p.add_argument('--max-frames',type=int,default=0,help='For local preview only; production default retains every sample')
    args=p.parse_args();case=args.case.resolve();out=args.output.resolve()
    out.mkdir(parents=True,exist_ok=False)
    state=json.loads((case/'run-status.json').read_text())
    manifest=json.loads((case/'case_manifest.json').read_text())
    warm=manifest.get('initialization_kind')=='steady_solver'
    phase='TRANSIENT FROM FLOWING FIELD' if warm else 'EXPLORATORY FLOW STARTUP'
    clock_label='Time after flowing-field initialization' if warm else 'Physical time'
    assert not manifest.get('runtime_fixture',False), 'Do not publish the synthetic fixture as Rev H'
    folders=sorted([p for p in (case/'postProcessing/edge_sections').iterdir()
                    if p.is_dir() and not p.name.startswith('.') and (p/'right_section.vtp').is_file()
                    and float(p.name)<=state['latest_physical_time_s']+1e-13],key=lambda p:float(p.name))
    available=len(folders)
    if args.max_frames and len(folders)>args.max_frames:
        folders=[folders[i] for i in np.unique(np.linspace(0,len(folders)-1,args.max_frames).round().astype(int))]
    assert len(folders)>=2,'Need at least two genuine samples'
    times=[float(p.name) for p in folders]
    fps=30;slowdown=max(1000,1/(fps*min(np.diff(times))))
    starts=[round((t-times[0])*slowdown*fps) for t in times]
    counts=[b-a for a,b in zip(starts,starts[1:])]+[15]
    assert min(counts)>0
    locator=ROOT/'docs/simulation/revh-transient/section-locator.png'
    context=Image.open(locator).convert('RGB')
    lines=cad_sections()
    style={'pressure_front_Pa':12 if warm else 6,'pressure_hinge_Pa':12,'vorticity_per_s':2000,'speed_m_s':6 if warm else 5,
           'size_px':[1800,1100],'style_version':3,'phase':phase}
    signature=hashlib.sha256((json.dumps(style,sort_keys=True)+sha(Path(__file__))+sha(locator)).encode()).hexdigest()[:16]
    cache=case/'render-cache'/signature;cache.mkdir(parents=True,exist_ok=True)
    images=[];ranges=[];hashes={};started=time.monotonic()
    for index,folder in enumerate(folders):
        source=folder/'right_section.vtp';source_hash=sha(source);hashes[str(float(folder.name))]=source_hash
        frame=cache/(folder.name+'-'+source_hash[:10]+'.png')
        if not frame.exists():
            pts,tri,data=read_plane(source)
            pressure=data['p']*1.2;speed=np.linalg.norm(data['U'],axis=1);vort=data['vorticity'][:,0]
            plt.rcParams.update({'font.size':11,'axes.titlesize':14,'axes.labelsize':11,'figure.facecolor':'#f7f9fa'})
            fig=plt.figure(figsize=(18,11),dpi=100)
            grid=fig.add_gridspec(2,3,width_ratios=[.77,1,1],left=.035,right=.965,bottom=.14,top=.835,hspace=.34,wspace=.28)
            context_ax=fig.add_subplot(grid[0,0]);context_ax.imshow(context);context_ax.axis('off')
            overall=fig.add_subplot(grid[1,0]);whole=(-4,155,-155,257)
            t=choose(pts,tri,whole)
            im=overall.tripcolor(pts[:,0],pts[:,1],t,speed,cmap='viridis',vmin=0,vmax=style['speed_m_s'],shading='gouraud',rasterized=True)
            overall.add_collection(LineCollection(lines,colors='#172d36',linewidths=.5))
            overall.set(xlim=whole[:2],ylim=whole[2:],aspect='equal',title='Complete air path',xlabel='Y from wall [mm]',ylabel='Height Z [mm]',facecolor='#cdd5db')
            fig.colorbar(im,ax=overall,fraction=.06,pad=.045,label='Speed [m/s]')
            for row,(name,bounds,plim) in enumerate([
                ('Front lip / duct outlet',(25,75,-8,35),style['pressure_front_Pa']),
                ('Hinge lip / discharge',(25,75,208,262),style['pressure_hinge_Pa'])]):
                t=choose(pts,tri,bounds)
                inside=np.unique(t)
                ranges.append({'time_s':float(folder.name),'region':name,
                               'pressure_Pa':[float(pressure[inside].min()),float(pressure[inside].max())],
                               'speed_m_s':[float(speed[inside].min()),float(speed[inside].max())],
                               'vorticity_x_per_s':[float(vort[inside].min()),float(vort[inside].max())]})
                for col,values,limit,title in [(1,pressure,plim,'Static pressure [Pa]'),(2,vort,style['vorticity_per_s'],'Vorticity X [1/s]')]:
                    ax=fig.add_subplot(grid[row,col])
                    im=ax.tripcolor(pts[:,0],pts[:,1],t,values,cmap='RdBu_r',vmin=-limit,vmax=limit,shading='gouraud',rasterized=True)
                    ax.add_collection(LineCollection(lines,colors='#172d36',linewidths=.85))
                    q=arrows(ax,pts,data['U'],bounds)
                    ax.set(xlim=bounds[:2],ylim=bounds[2:],aspect='equal',title=name+'\n'+title,
                           xlabel='Y from wall [mm]',ylabel='Height Z [mm]',facecolor='#cdd5db')
                    fig.colorbar(im,ax=ax,fraction=.05,pad=.035,shrink=.85)
                    if row==0 and col==2:ax.quiverkey(q,.70,1.23,5,'5 m/s',labelpos='E',coordinates='axes',fontproperties={'size':11})
            fig.text(.035,.95,'REVISION H  |  '+phase,fontsize=23,fontweight='bold',color='#162c36')
            fig.text(.035,.91,f'{clock_label}: {float(folder.name)*1000:.4f} ms    |    X = +111 mm',fontsize=18,color='#17686b')
            fig.text(.035,.052,'Arrows show in-plane velocity. Grey is solid or unsampled. Black lines are CAD surfaces. Colour scales stay fixed.',fontsize=13,color='#536772')
            caveat=('Initial steady-solver field is not converged. Initial adjustment remains. Mesh and time-step independence are unproven.' if warm else
                    'Known mesh limitations. These recorded frames do not by themselves establish periodic shedding or validated lip suction.')
            fig.text(.035,.025,caveat,fontsize=12,color='#536772')
            fig.savefig(frame,dpi=100);plt.close(fig)
        images.append(frame)
        if index%20==0:print('Prepared',index+1,'/',len(folders),'frames',flush=True)
    video=out/'flow.mp4';width,height=style['size_px']
    command=[args.ffmpeg,'-hide_banner','-loglevel','error','-f','rawvideo','-pixel_format','rgb24',
             '-video_size',f'{width}x{height}','-framerate',str(fps),'-i','pipe:0','-an',
             '-c:v','libx264','-threads','2','-preset','veryfast','-crf','19','-pix_fmt','yuv420p',
             '-g','30','-movflags','+faststart',str(video)]
    with (out/'encoding.log').open('w') as log:
        encoder=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=log)
        try:
            for path,count in zip(images,counts):
                with Image.open(path) as img:pixels=img.convert('RGB').tobytes()
                for _ in range(count):encoder.stdin.write(pixels)
        finally:encoder.stdin.close()
        if encoder.wait():raise RuntimeError('Video encoder failed; see encoding.log')
    for name,path in [('poster.png',images[-1]),('first-frame.png',images[0])]:
        with Image.open(path) as img:img.save(out/name)
    report={'created_utc':datetime.now(timezone.utc).isoformat(),'hour_checkpoint':args.hour,
            'scope':('Exploratory transient from a flowing steady-solver iterate; initial adjustment remains; not validated shedding or suction.' if warm else
                     'Exploratory startup on a provisional mesh; not validated shedding or suction.'),
            'initialization_kind':manifest.get('initialization_kind','native_transient_startup'),
            'transient_initialization':manifest.get('transient_initialization'),
            'case':state['case'],'compute_elapsed_seconds_at_snapshot':state['elapsed_seconds'],
            'solver_state_at_snapshot':state['state'],'completed_steps_at_snapshot':state['completed_steps'],
            'source_sample_count_available':available,'source_frames':len(folders),'physical_times_s':times,
            'first_time_s':times[0],'last_time_s':times[-1],'physical_duration_s':times[-1]-times[0],
            'encoded_frames':sum(counts),'fps':fps,'video_duration_s':sum(counts)/fps,'playback_slowdown':slowdown,
            'timing':'Recorded intervals uniformly slowed, rounded to 30 fps; half-second final hold. No interpolation between CFD states.',
            'source_frame_start_s':[v/fps for v in starts],'source_frame_duration_s':[v/fps for v in counts],
            'fixed_scales':style,'sampled_ranges_for_newly_rendered_frames':ranges,
            'source_sha256':hashes,'video_sha256':sha(video),'poster_sha256':sha(out/'poster.png'),
            'render_wall_seconds':time.monotonic()-started,'max_logged_Courant':state.get('max_logged_Courant'),
            'bounding_events':state.get('bounding_events'),'density_kg_m3':1.2,
            'source_mesh':'revh_sequence_05 (3193565 cells); 4 low-determinant cells, poor wall-layer coverage',
            'preview_subsampled':bool(args.max_frames)}
    (out/'progress.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['source_frames','last_time_s','video_duration_s','render_wall_seconds']},indent=2),flush=True)


if __name__=='__main__':main()
