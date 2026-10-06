"""Render actual OpenFOAM cell fields and report the screening limits."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as MPath
from scipy.interpolate import griddata
import vtk
from vtk.util.numpy_support import vtk_to_numpy
from cfd_study import ROOT,OUT

def main():
 results=json.loads((ROOT/'results.json').read_text());r={a['name']:a for a in results}
 c=ROOT/'curved_12_fine';vtu=next((c/'VTK').glob('*/internal.vtu'))
 reader=vtk.vtkXMLUnstructuredGridReader();reader.SetFileName(str(vtu));reader.Update();mesh=reader.GetOutput()
 centers=vtk.vtkCellCenters();centers.SetInputData(mesh);centers.Update();xy=vtk_to_numpy(centers.GetOutput().GetPoints().GetData())[:,:2]*1000
 U=vtk_to_numpy(mesh.GetCellData().GetArray('U'));pressure=vtk_to_numpy(mesh.GetCellData().GetArray('p'))*1.2
 gx=np.arange(0,121,.6);gy=np.arange(-140,241,.6);X,Y=np.meshgrid(gx,gy)
 levels=np.array(r['curved_12_fine']['levels_mm']);poly=np.concatenate([levels[:,0],levels[::-1,1]])
 mask=MPath(poly).contains_points(np.c_[X.ravel(),Y.ravel()]).reshape(X.shape)
 ux=griddata(xy,U[:,0],(X,Y),method='linear');uy=griddata(xy,U[:,1],(X,Y),method='linear');p=griddata(xy,pressure,(X,Y),method='linear')
 speed=np.hypot(ux,uy)
 for a in [ux,uy,p,speed]:a[~mask]=np.nan
 plt.rcParams.update({'font.size':12,'axes.spines.top':False,'axes.spines.right':False,'font.family':'DejaVu Sans'})
 fig=plt.figure(figsize=(17,12),facecolor='#f8f8f8');gs=fig.add_gridspec(1,3,width_ratios=[1,1,1.45],left=.05,right=.98,bottom=.15,top=.85,wspace=.35)
 for i,(field,title,cmap,vmax) in enumerate([(p,'Static pressure / Pa','viridis',20),(speed,'Air speed / m/s','magma',7)]):
  ax=fig.add_subplot(gs[0,i]);ax.set_facecolor('#f8f8f8')
  im=ax.pcolormesh(X,Y,field,cmap=cmap,vmin=0,vmax=vmax,shading='auto',rasterized=True)
  ax.plot(*np.vstack([poly,poly[0]]).T,color='#3d515c',lw=.8)
  ax.fill_betweenx([2,232.3],40,60,color='#ccd2d8',zorder=0)
  ax.plot([40,40],[156,192],color='#dc621c',lw=4)
  if i==1:ax.streamplot(gx,gy,np.ma.masked_invalid(ux),np.ma.masked_invalid(uy),color='white',density=.85,linewidth=.6,arrowsize=.7)
  ax.set(xlim=(0,119),ylim=(-139,244),xlabel='Distance from wall / mm',ylabel='Height above shelf / mm',title=title,aspect='equal')
  fig.colorbar(im,ax=ax,orientation='horizontal',pad=.09,fraction=.035)
 ax=fig.add_subplot(gs[0,2]);ax.axis('off')
 ax.text(0,1,'SLOT COMPARISON',fontsize=18,fontweight='bold',color='#172838',transform=ax.transAxes)
 lines=['20 Pa inlet total pressure','0.4 m/s prescribed intake demand','','Gap      Intake pressure      Exit speed']
 for n,g in [('curved_8',8),('curved_12',12),('curved_16',16)]:
  a=r[n];lines.append(f'{g:2d} mm       {a["intake_pressure_mean_Pa"]:4.1f} Pa              {a["slot_exit_mean_velocity_m_s"]:.1f} m/s')
 for j,t in enumerate(lines):ax.text(0,.94-.047*j,t,fontsize=13,color='#172838',transform=ax.transAxes)
 notes=['12 mm remains the starting choice.','8 mm raises upstream pressure but','reduces bypass flow. 16 mm passes','more flow with lower intake pressure.','','The gentler lower turn changes mean','intake pressure by only about 0.1 Pa.','','2D, steady RANS / k-omega SST','Sealed representative fan-band section','2 mm estimated rear-foot projection','','Not a resolved laptop, rotating fan,','heated plume or side-leakage simulation.','Actual fan curves and measurements','are needed for performance predictions.']
 for j,t in enumerate(notes):ax.text(0,.53-.029*j,t,fontsize=12,color='#526472',transform=ax.transAxes)
 fig.text(.05,.95,'PLENUM CFD / REVISION F',fontsize=25,fontweight='bold',color='#172838')
 fig.text(.05,.90,'Actual OpenFOAM fields. 12 mm slot shown at the finest mesh; comparisons use the common coarse mesh.',fontsize=13,color='#526472')
 fig.text(.05,.085,'Mesh refinement changes mean intake pressure by 0.3% and exit speed by 2.9% (coarse to fine).',fontsize=13,color='#526472')
 fig.text(.05,.05,'Flow imbalance <0.001%. Four cases miss the strict residual target; reported pressure monitors stabilize within 0.01%.',fontsize=12,color='#526472')
 fig.savefig(OUT/'CFD_Plenum_Study.png',dpi=130);plt.close(fig)
 rows='\n'.join(f'| {a["name"]} | {a["intake_pressure_mean_Pa"]:.2f} | {a["intake_pressure_min_Pa"]:.2f} | {a["slot_exit_mean_velocity_m_s"]:.2f} | {a["mass_imbalance_percent"]:.5f} | {"yes" if a["residual_control_met"] else "no"} |' for a in results)
 fine=r['curved_12_fine'];coarse=r['curved_12'];medium=r['curved_12_medium']
 report=f'''# Plenum and outlet CFD — Revision F

**Keep a 12 mm nominal slot as the starting configuration.** The 8 mm slot
retains more intake pressure, while 16 mm passes more bypass flow. At fixed
inlet total pressure, narrowing the slot does not automatically create the
fastest outlet jet. These are comparative model results, not predictions for
the user's uncharacterized fans or laptop.

The gentler lower turn improves mean intake pressure by only
{coarse['intake_pressure_mean_Pa']-r['straight_12']['intake_pressure_mean_Pa']:.2f} Pa
on the common mesh. That small difference does not justify calling it an
optimized shape. Retain its printable transition and use the larger slot-width
tradeoff to guide the first prototype. The contraction starts at Z=198 mm,
after the estimated intake band, reaches its throat at Z=226 mm, and guides
the outlet upward to Z=232 mm. All three variants keep the skin within 45° for
lip-down printing.

## Model and boundary conditions

OpenFOAM v1912 (Ubuntu package 1912.200626-2build3), simpleFoam, incompressible
steady RANS, k-omega SST. Density1.2 kg/m³; kinematic viscosity1.5e-5 m²/s.
Two-dimensional block mesh with a1 mm empty span. No-slip smooth walls,
20 Pa inlet total pressure (10 Pa sensitivity), zero-gauge static pressure at
the slot exit, prescribed0.4 m/s suction through the intake band (0.8 m/s
sensitivity). Inlet k=0.015 m²/s² and omega=50 s⁻¹. Wall functions use the
solver's standard SST setup. This is not a transition-resolving calculation.

The inlet line slopes45° and has wallward/upward normal. The mesh idealizes
the center section of a fan band with sealed cheeks; it omits the grille,
fan hub/swirl, structural ribs, three-dimensional spreading and leakage at
noncontact joints. The CAD skins sit around a similar ruled flow path;
2 mm wall thickness and small transitions are simplified in the CFD geometry.
The CFD intake patch is Z=156–192 mm, a simplified band within the image-derived
layout. The rear foot projects2 mm at Z≈218–222 mm; its true height is unmeasured.

Laptop intake flow is a prescribed demand, not a pressure-coupled internal
resistance or laptop-blower model. The supplied fan pressure is an assumption,
not a measured operating point or an adopted fan curve. Do not multiply a
representative slice across the entire laptop to claim total CFM.

## Results

Pressure is gauge pressure relative to the slot outlet. Mean and minimum
values sample the intake patch; velocity is area-mean at the slot exit.

| Case | Mean intake Pa | Minimum intake Pa | Exit m/s | Flow imbalance % | Strict residual target met |
|---|---:|---:|---:|---:|---|
{rows}

## Numerical checks

All eight block meshes pass checkMesh; positive volumes and acceptable
nonorthogonality/skewness. Pressure-velocity coupling uses SIMPLE with one
nonorthogonal correction and under-relaxation. Momentum uses bounded
linear-upwind convection; turbulence uses upwind convection.

The nominal cell-size sequence is2.0,1.3,0.85 mm. Coarse-to-fine mean intake
pressure changes by{100*abs(fine['intake_pressure_mean_Pa']/coarse['intake_pressure_mean_Pa']-1):.2f}%;
exit velocity changes by{100*abs(fine['slot_exit_mean_velocity_m_s']/coarse['slot_exit_mean_velocity_m_s']-1):.2f}%.
Medium-to-fine pressure changes by{100*abs(fine['intake_pressure_mean_Pa']/medium['intake_pressure_mean_Pa']-1):.2f}%.
Mass imbalance remains below0.001%. Four cases do not satisfy the strict
1e-6 residual stop before1600 iterations. Their final monitored mean pressures
change by less than0.01% between saved states. Treat them as stabilized
screening results, with unresolved residual/flow unsteadiness, not fully
converged high-accuracy solutions. Raw logs preserve this limitation.

## What this does not establish

No conjugate heat transfer, laptop temperature, exhaust entrainment distance,
room recirculation, noise, buoyancy or fan-off cooling prediction. Side leakage
can lower real plenum pressure. The unheated domain ends at the hinge height;
it does not model how far the hot plume travels. No topology or generative
optimization solve is represented by this study.

A useful next calibration is the exact120 mm fan model and RPM/PWM setting,
plus intake static pressure and laptop temperature at a repeatable workload.
Those allow a fan-curve/internal-resistance model and a meaningful3D study.

## Reproduce and inspect

Run run_cfd_sweep.py with OpenFOAM available, then analyze_cfd.py and render_cfd.py.
Each cfd/ case contains its mesh dictionaries, initial conditions, parameters,
checkMesh and solver logs, and the final field state. VTK output for the
comparison cases opens in ParaView. The included foam_environment.md explains
the runtime setup and the -noFunctionObjects option used to avoid an old
function-object hashing incompatibility; postprocessing reads written fields.

Sources: [OpenFOAM SST model](https://doc.openfoam.com/2306/tools/processing/models/turbulence/ras/linear-evm/rtm/kOmegaSST/),
[OpenFOAM boundary conditions](https://www.openfoam.com/documentation/user-guide/a-reference/a.4-standard-boundary-conditions),
[Dell service manual](https://dl.dell.com/content/manual44781765-precision-5560-service-manual.pdf?language=en-us).
'''
 # Add spaces between common numeric units in authored text.
 for a,b in [('Density1.2','Density 1.2'),('viscosity1.5','viscosity 1.5'),('a1 mm','a 1 mm'),('prescribed0.4','prescribed 0.4'),('slopes45','slopes 45'),('projects2','projects 2'),('is2.0,1.3,0.85','is 2.0, 1.3, 0.85'),('by{','by {'),('below0.001','below 0.001'),('before1600','before 1600'),('than0.01','than 0.01'),('exact120','exact 120'),('meaningful3D','meaningful 3D')]:report=report.replace(a,b)
 (OUT/'CFD_Design_Report.md').write_text(report)
if __name__=='__main__':main()
