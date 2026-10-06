"""Generate truthful CFD drawing views from reconstructed iteration 1200.
Run with FreeCAD's bundled Python (VTK + matplotlib).
"""
import os
os.environ.setdefault('WINDIR', 'C:/Windows')
os.environ.setdefault('SystemRoot', 'C:/Windows')
os.environ.setdefault('USERPROFILE', os.path.expanduser('~'))
os.environ['VTK_SMP_MAX_THREADS']='1'
from pathlib import Path
import json, re
import sys
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.tri import Triangulation

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
OUT = ROOT/'output/pdf/assets_release'
OUT.mkdir(parents=True, exist_ok=True)
CASE = BASE/'cases/OpenCFD_v2412/installed_pressure10_v3'
reader = vtk.vtkOpenFOAMReader()
reader.SetFileName(str(CASE/'case.foam'))
reader.CreateCellToPointOn(); reader.UpdateInformation(); reader.SetTimeValue(1200)
reader.EnableAllCellArrays(); reader.Update()
mesh = reader.GetOutput().GetBlock(0)
mesh.GetPointData().SetActiveVectors('U')
surfaces = {}
for name in ['printed','laptop','noctua']:
    r = vtk.vtkSTLReader(); r.SetFileName(str(BASE/'geometry_traced_repaired'/f'{name}.stl')); r.Update()
    surfaces[name] = r.GetOutput()
sr = vtk.vtkXMLPolyDataReader(); sr.SetFileName(str(CASE/'results/iteration_1200/streamlines.vtp')); sr.Update()
calc = vtk.vtkArrayCalculator(); calc.SetInputConnection(sr.GetOutputPort()); calc.AddVectorArrayName('U'); calc.SetFunction('mag(U)'); calc.SetResultArrayName('speed'); calc.Update()
lut = vtk.vtkLookupTable(); lut.SetNumberOfTableValues(256)
for i, rgba in enumerate(plt.get_cmap('turbo')(np.linspace(0,1,256))): lut.SetTableValue(i,*rgba)
lut.SetRange(0,5); lut.Build()

def actor(data, color, opacity=1):
    m=vtk.vtkPolyDataMapper(); m.SetInputData(data); m.ScalarVisibilityOff()
    a=vtk.vtkActor(); a.SetMapper(m); a.GetProperty().SetColor(*color); a.GetProperty().SetOpacity(opacity)
    return a

def view(name, direction, up=(0,0,1), flow=False):
    ren=vtk.vtkRenderer(); ren.SetBackground(1,1,1)
    for key, col in [('printed',(.17,.31,.40)),('laptop',(.66,.73,.77)),('noctua',(.48,.39,.29))]:
        ren.AddActor(actor(surfaces[key], col, (.18 if key=='laptop' else .55) if flow else 1))
        edge=vtk.vtkFeatureEdges(); edge.SetInputData(surfaces[key]); edge.BoundaryEdgesOn(); edge.FeatureEdgesOn(); edge.SetFeatureAngle(35); edge.ManifoldEdgesOff(); edge.NonManifoldEdgesOff(); edge.Update()
        a=actor(edge.GetOutput(),(.13,.21,.27), .28 if flow else .65); a.GetProperty().SetLineWidth(1); ren.AddActor(a)
    if flow:
        m=vtk.vtkPolyDataMapper(); m.SetInputConnection(calc.GetOutputPort()); m.SetScalarModeToUsePointFieldData(); m.SelectColorArray('speed'); m.SetLookupTable(lut); m.SetScalarRange(0,5)
        a=vtk.vtkActor(); a.SetMapper(m); a.GetProperty().SetLineWidth(1.6); ren.AddActor(a)
    cam=ren.GetActiveCamera(); focal=np.array([0,.063,.045]); cam.SetFocalPoint(*focal); cam.SetPosition(*(focal+np.array(direction))); cam.SetViewUp(*up); cam.ParallelProjectionOn()
    cam.SetParallelScale(.275 if flow else .235)
    ren.ResetCameraClippingRange()
    win=vtk.vtkRenderWindow(); win.SetOffScreenRendering(1); win.SetSize(1800,1500); win.AddRenderer(ren); win.SetMultiSamples(8); win.Render()
    shot=vtk.vtkWindowToImageFilter(); shot.SetInput(win); shot.Update()
    w=vtk.vtkPNGWriter(); w.SetFileName(str(OUT/f'{name}.png')); w.SetInputConnection(shot.GetOutputPort()); w.Write(); win.Finalize()
    print(name,flush=True)

if '--sections-only' not in sys.argv:
    view('isometric_flow',(1,1,1),flow=True)
    view('reverse_iso',(-1,-1,.7),flow=True)
    view('front',(0,1,0))
    view('side',(1,0,0))
    view('top',(0,0,1),up=(0,1,0))
    view('iso_solid',(1,1,1))

plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.labelcolor':'#294351','axes.edgecolor':'#9caeb6','xtick.color':'#526974','ytick.color':'#526974','axes.spines.top':False,'axes.spines.right':False,'savefig.facecolor':'white'})

def cut(data, axis, value):
    normal=[0,0,0]; normal[axis]=1; origin=[0,0,0]; origin[axis]=value
    plane=vtk.vtkPlane(); plane.SetNormal(*normal); plane.SetOrigin(*origin)
    c=vtk.vtkCutter(); c.SetInputData(data); c.SetCutFunction(plane); c.Update()
    return c.GetOutput()

def section(name,axis,value,xlim,ylim,field='speed',grid=False):
    print('Starting '+name,flush=True)
    inds=[i for i in range(3) if i!=axis]
    height=max(2.8,min(7.5,6*(ylim[1]-ylim[0])/(xlim[1]-xlim[0])+1.2))
    fig,ax=plt.subplots(figsize=(7.5,height),layout='constrained')
    d=cut(mesh,axis,value)
    t=vtk.vtkTriangleFilter(); t.SetInputData(d); t.Update(); d=t.GetOutput()
    xyz=vtk_to_numpy(d.GetPoints().GetData())*1000
    cells=vtk_to_numpy(d.GetPolys().GetData()).reshape(-1,4)[:,1:]
    tri=Triangulation(xyz[:,inds[0]],xyz[:,inds[1]],cells)
    vals=np.linalg.norm(vtk_to_numpy(d.GetPointData().GetArray('U')),axis=1) if field=='speed' else vtk_to_numpy(d.GetPointData().GetArray('p'))*1.2
    im=ax.tripcolor(tri,vals,shading='gouraud',cmap='turbo' if field=='speed' else 'RdBu_r',vmin=0 if field=='speed' else -12,vmax=5 if field=='speed' else 12,rasterized=True)
    if grid: ax.triplot(tri,lw=.18,color='#173749',alpha=.55,rasterized=True)
    for key,s in surfaces.items():
        boundary=cut(s,axis,value); points=boundary.GetPoints()
        if not points: continue
        pts=vtk_to_numpy(points.GetData())*1000; lines=boundary.GetLines(); lines.InitTraversal(); ids=vtk.vtkIdList(); segments=[]
        while lines.GetNextCell(ids):
            segments.append(pts[[ids.GetId(i) for i in range(ids.GetNumberOfIds())]][:,inds])
        ax.add_collection(LineCollection(segments,colors='#142f3d',linewidths=.8))
    ax.set(xlim=xlim,ylim=ylim,xlabel='XYZ'[inds[0]]+' [mm]',ylabel='XYZ'[inds[1]]+' [mm]',aspect='equal')
    bar=fig.colorbar(im,ax=ax,shrink=.78,pad=.025); bar.set_label('Speed [m/s]' if field=='speed' else 'Gauge pressure [Pa]'); bar.outline.set_visible(False)
    fig.savefig(OUT/f'{name}.png',dpi=260,bbox_inches='tight',pad_inches=.06); plt.close(fig); print(name,flush=True)

section('section_left',0,-.111017192,(0,180),(-145,245))
section('section_right',0,.111263897,(0,180),(-145,245))
section('duct_plane',1,.045,(-185,185),(125,240))
section('pressure_plane',1,.045,(-185,185),(125,240),field='pressure')
section('intake_cross',2,.17111879,(-185,185),(25,80))
section('mesh_duct',0,.111263897,(34,61),(145,205),grid=True)
section('mesh_fan',0,.111263897,(0,160),(-145,15),grid=True)

# Exact source residual histories: first pressure solve per SIMPLE iteration.
raw=(CASE/'log.simpleFoam_windows').read_text()
history={k:[] for k in ['Ux','Uy','Uz','p','k','omega']}; times=[]
for n,block in re.findall(r'^Time = (\d+)\s*\n(.*?)(?=^Time = |\Z)',raw,re.M|re.S):
    row={k:re.search(r'Solving for '+k+r', Initial residual = ([^,]+)',block) for k in history}
    if all(row.values()):
        times.append(int(n))
        for k in history: history[k].append(float(row[k].group(1)))
fig,ax=plt.subplots(figsize=(10,4.5),layout='constrained')
for key,col in zip(history,['#148a99','#2969ad','#805caf','#1b3546','#d3862c','#789b4a']): ax.semilogy(times,history[key],label=key,color=col,lw=1.15)
ax.axhline(1e-5,color='#bf4545',ls='--',lw=1,label='Target 1e-5')
ax.set(xlabel='SIMPLE iteration (warm start from v2 / 300)',ylabel='Initial residual',xlim=(1,1200),ylim=(1e-6,1e-1)); ax.grid(alpha=.15); ax.legend(ncol=7,loc='upper right',fontsize=9)
fig.savefig(OUT/'residuals.png',dpi=240); plt.close(fig)
(OUT/'plot_provenance.json').write_text(json.dumps({'case':str(CASE),'iteration':1200,'cells':mesh.GetNumberOfCells(),'section_units':'mm','speed_range_m_s':[0,5],'pressure_range_Pa':[-12,12],'pressure_conversion':'OpenFOAM kinematic p * rho=1.2 kg/m3','sections':{'A':{'axis':'X','mm':-111.017192},'B':{'axis':'X','mm':111.263897},'C':{'axis':'Y','mm':45},'D':{'axis':'Z','mm':171.11879}},'residual_samples':len(times),'final_initial_residuals':{k:v[-1] for k,v in history.items()}},indent=2))
print('All drawing assets complete',flush=True)
