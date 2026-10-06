"""Summarize real transient logs and probes, without treating startup as validation."""
from pathlib import Path
import os
os.environ.setdefault('USERPROFILE',str(Path(os.environ['LOCALAPPDATA']).parents[1]))
import argparse
import json
import re
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--case',type=Path,default=BASE/'runs/revh_transient_04')
args=parser.parse_args();case=args.case.resolve()
out=ROOT/'docs/simulation/revh-transient';out.mkdir(parents=True,exist_ok=True)
manifest=json.loads((case/'case_manifest.json').read_text())
logs=sorted(case.glob('log.pimpleFoam*'),key=lambda p:int(re.search(r'attempt(\d+)',p.name)[1]) if 'attempt' in p.name else 1)
log_path=logs[-1]
log=log_path.read_text(errors='replace')
completed=[]
for t,block in re.findall(r'^Time = ([\d.eE+-]+)\s*\n(.*?)(?=^Time = |\Z)',log,re.M|re.S):
    timing=re.search(r'ExecutionTime = ([\d.eE+-]+) s\s+ClockTime = ([\d.eE+-]+) s',block)
    if timing:completed.append({'time_s':float(t),'cpu_s':float(timing.group(1)),'wall_s':float(timing.group(2))})
co=[float(v) for v in re.findall(r'Courant Number mean: [\d.eE+-]+ max: ([\d.eE+-]+)',log)]
after_start=log.split('Starting time loop',1)[-1]
advancing_co=[float(v) for v in re.findall(r'Courant Number mean: [\d.eE+-]+ max: ([\d.eE+-]+)',after_start)]
dt=[float(v) for v in re.findall(r'^deltaT = ([\d.eE+-]+)',log,re.M)]
report={'scope':'Commissioning evidence only; no mature-flow, shedding or Bernoulli validation claim.',
        'solver_log':log_path.name,
        'completed_steps':len(completed),'latest_completed_time_s':completed[-1]['time_s'] if completed else None,
        'max_logged_Courant':max(co) if co else None,'fatal_error':'FOAM FATAL' in log,
        'max_Courant_after_starting_loop':max(advancing_co) if advancing_co else None,
        'Courant_note':'The raw maximum includes the mapped initial field before time-step adjustment. OpenFOAM logs Courant before adjusting the next step.',
        'time_step_range_s':[min(dt),max(dt)] if dt else None,
        'turbulence_bounding_events':re.findall(r'^bounding (?:k|omega),.*$',log,re.M),
        'probe_location_warning':bool(re.search(r'Did not find location|not find cell for location',log,re.I)),
        'linear_and_outer_convergence':'Retain and inspect the complete log; a successful linear solve does not establish temporal convergence.',
        'pressure_unit':'Pa (kinematic p multiplied by assumed density 1.2 kg/m3)'}
if len(completed)>5:
    a,b=completed[2],completed[-1]
    report['observed_wall_seconds_per_simulated_second']=(b['wall_s']-a['wall_s'])/(b['time_s']-a['time_s'])

def rows(path,columns):
    data=[]
    for line in path.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith('#'):continue
        row=np.fromstring(line.replace('(',' ').replace(')',' '),sep=' ')
        if row.size==columns:data.append(row)
    return np.array(data)

flux={}
for name in ['ambient_flux','ambient_abs_flux']:
    series=[]
    for p in (case/'postProcessing'/name).glob('*/surfaceFieldValue.dat'):series.extend(rows(p,2))
    if series:flux[name]=np.array(series)
if len(flux)==2:
    signed={t:v for t,v in flux['ambient_flux']}
    balance=[{'time_s':float(t),'net_m3_s':float(signed[t]),'sum_absolute_m3_s':float(v),
              'net_relative_to_one_way_throughflow':float(2*abs(signed[t])/v) if v>1e-20 else None}
             for t,v in flux['ambient_abs_flux'] if t in signed]
    report['ambient_mass_balance']=balance
    report['mass_balance_definition']='abs(net flux) divided by half the sum of absolute boundary fluxes; assumes a closed incompressible balance with the ambient patch providing all external flow.'
yplus=[]
for path in (case/'postProcessing/yPlus').glob('*/yPlus.dat'):
    for line in path.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith('#'):continue
        values=line.split()
        if len(values)==5:yplus.append({'time_s':float(values[0]),'patch':values[1],'min':float(values[2]),'max':float(values[3]),'mean':float(values[4])})
report['startup_yPlus']=yplus
report['yPlus_caution']='Startup y+ depends on the mapped initial flow and transient adjustment; it does not establish settled wall resolution.'

n=len(manifest['probes'])
folders=sorted((case/'postProcessing/probes').glob('*'),key=lambda p:float(p.name)) if (case/'postProcessing/probes').exists() else []
pressure=[];velocity=[]
for folder in folders:
    if (folder/'p').exists():pressure.extend(rows(folder/'p',n+1))
    if (folder/'U').exists():velocity.extend(rows(folder/'U',3*n+1))
if pressure:
    p=np.array(pressure);p=p[np.argsort(p[:,0])]
    good=np.isfinite(p[:,1:]).all(axis=0)&(np.abs(p[:,1:])<1e20).all(axis=0)
    report['probe_rows']=len(p)
    report['invalid_probe_indices']=np.flatnonzero(~good).tolist()
    static=1.2*p[:,1:]
    ref=static[:,-1]
    report['sampled_pressure']=[{'name':probe['name'],'valid':bool(good[i]),
        'mean_gauge_Pa':float(static[:,i].mean()) if good[i] else None,
        'mean_relative_to_ambient_probe_Pa':float((static[:,i]-ref).mean()) if good[i] and good[-1] else None,
        'min_gauge_Pa':float(static[:,i].min()) if good[i] else None,
        'max_gauge_Pa':float(static[:,i].max()) if good[i] else None} for i,probe in enumerate(manifest['probes'])]
    if len(p)>1:
        fig,axs=plt.subplots(2,1,figsize=(11,7),layout='constrained',sharex=True)
        for i,probe in enumerate(manifest['probes']):
            if not good[i] or probe['point_m'][0]!=.111:continue
            ax=axs[1] if probe['name'].startswith('hinge') else axs[0]
            ax.plot(p[:,0]*1000,static[:,i],marker='o',markersize=4,label=probe['name'].split('_x')[0])
        for ax in axs:
            ax.axhline(0,color='#7b8b90',lw=.8);ax.set_ylabel('Gauge static pressure [Pa]');ax.grid(alpha=.2);ax.legend(fontsize=8)
        axs[0].set_title('Revision H | commissioning pressure history at X=111 mm\nStartup record; sustained shedding and settled suction are not established')
        axs[1].set_xlabel('Physical simulation time [ms]')
        fig.savefig(out/'pilot-pressure-history.png',dpi=170);plt.close(fig)
    if velocity:
        u=np.array(velocity)
        if u.shape[0]==p.shape[0] and np.allclose(u[:,0],p[:,0]):
            speed2=np.sum(u[:,1:].reshape(-1,n,3)**2,axis=2)
            total=static+.6*speed2
            report['sampled_total_pressure']=[{'name':probe['name'],'mean_gauge_total_Pa':float(total[:,i].mean()) if good[i] and np.isfinite(total[:,i]).all() else None}
                for i,probe in enumerate(manifest['probes'])]
            report['total_pressure_caution']='p + 0.5 rho U squared at sample points; point pairs are not established to share a streamline. Do not attribute causality from this alone.'
(out/'pilot-review.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if not k.startswith('sampled_')},indent=2))
