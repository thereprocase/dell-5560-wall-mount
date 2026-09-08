"""Capture or plot steady-solver convergence against iteration, never fluid time."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re

NUMBER=r'[-+]?(?:\d*\.)?\d+(?:[eE][-+]?\d+)?'


def capture(case,output):
    state=json.loads((case/'run-status.json').read_text());end=state['latest_iteration']
    manifest=json.loads((case/'case_manifest.json').read_text())
    fields={};hashes={}
    for field in ['p','U']:
        raw=(case/'postProcessing/probes/0'/field).read_text()
        rows={}
        for line in raw.splitlines():
            if not line.strip() or line.startswith('#'):continue
            values=[float(v) for v in re.findall(NUMBER,line)]
            if len(values)==1+len(manifest['probes'])*(1 if field=='p' else 3) and values[0]<=end:rows[int(values[0])]=values[1:]
        fields[field]=rows;hashes[field]=hashlib.sha256(raw.encode()).hexdigest()
    iterations=sorted(set(fields['p'])&set(fields['U']));assert iterations
    probes=[]
    for i,probe in enumerate(manifest['probes']):
        probes.append({**probe,'pressure_Pa':[fields['p'][n][i]*1.2 for n in iterations],
                       'speed_m_s':[math.sqrt(sum(v*v for v in fields['U'][n][3*i:3*i+3])) for n in iterations]})
    raw=(case/'log.simpleFoam').read_text(errors='replace');history=[]
    for number,body in re.findall(r'^Time = ('+NUMBER+r')\s*\n(.*?)(?=^Time = |\Z)',raw,re.M|re.S):
        if float(number)>iterations[-1] or 'sumMag(ambient_openings)' not in body:continue
        residuals={field:max(map(float,re.findall(r'Solving for '+field+r', Initial residual = ('+NUMBER+')',body)),default=None) for field in ['p','Ux','Uy','Uz','k','omega']}
        net=float(re.findall(r'sum\(ambient_openings\) of phi = ('+NUMBER+')',body)[-1])
        absolute=float(re.findall(r'sumMag\(ambient_openings\) of phi = ('+NUMBER+')',body)[-1])
        bounds=[{'field':field,'minimum':float(value)} for field,value in re.findall(r'bounding (\w+), min: ('+NUMBER+')',body)]
        history.append({'iteration':int(float(number)),'initial_residuals':residuals,'flux_ratio':abs(net)/absolute,
                        'exchange_L_s':absolute*500,'bounds':bounds})
    report={'captured_utc':datetime.now(timezone.utc).isoformat(),'state':state,'iterations':iterations,
            'probes':probes,'history':history,'source_snapshot_sha256':hashes,
            'interpretation':'SIMPLE convergence history. The horizontal axis is iteration count, not elapsed physical time.'}
    output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'iterations':len(iterations),'last_iteration':iterations[-1],
                      'negative_k_events':sum(b['field']=='k' and b['minimum']<0 for h in history for b in h['bounds']),
                      'positive_k_floor_events':sum(b['field']=='k' and b['minimum']>=0 for h in history for b in h['bounds'])}))


def plot(source):
    os.environ.setdefault('USERPROFILE',str(Path(os.environ['LOCALAPPDATA']).parents[1]))
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    report=json.loads(source.read_text());byname={p['name']:p for p in report['probes']};x=report['iterations']
    plt.rcParams.update({'font.size':11,'figure.facecolor':'#f7f9fa','axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(2,2,figsize=(15,10),dpi=110)
    fig.subplots_adjust(left=.075,right=.965,bottom=.13,top=.85,hspace=.45,wspace=.26)
    ambient=np.array(byname['ambient_reference']['pressure_Pa'])
    for name,label in [('duct_edge_x0.111','Duct edge'),('duct_wake_x0.111','Duct wake'),('front_lip_wallside_x0.111','Lip wall side'),('front_lip_outside_x0.111','Lip outside'),('hinge_exit_x0.111','Hinge exit'),('hinge_wake_x0.111','Hinge wake')]:
        p=byname[name];axes[0,0].plot(x,np.array(p['pressure_Pa'])-ambient,label=label);axes[0,1].plot(x,p['speed_m_s'],label=label)
    axes[0,0].set(title='Pressure relative to ambient probe',ylabel='Pressure difference [Pa]');axes[0,0].legend(ncol=2,fontsize=9)
    axes[0,1].set(title='Local probe speeds',ylabel='Speed [m/s]',ylim=(0,None))
    h=report['history'];xh=[r['iteration'] for r in h]
    for field in ['p','Ux','Uy','Uz','k','omega']:axes[1,0].semilogy(xh,[max(r['initial_residuals'][field] or 0,1e-12) for r in h],label=field)
    axes[1,0].set(title='Initial equation residuals',ylabel='Residual');axes[1,0].legend(ncol=3,fontsize=9)
    axes[1,1].semilogy(xh,[max(r['flux_ratio'],1e-12) for r in h],color='#17686b')
    axes[1,1].axhline(1e-5,ls='--',color='#a5661b',label='Conservation target');axes[1,1].legend(fontsize=9)
    axes[1,1].set(title='Outer-boundary flow imbalance',ylabel='Absolute net flux / absolute flux sum')
    for ax in axes.flat:ax.set_xlabel('SIMPLE iteration (not physical time)');ax.grid(alpha=.15)
    fig.text(.075,.94,'REVISION H  |  STEADY-SOLVER CONVERGENCE',fontsize=23,fontweight='bold',color='#162c36')
    fig.text(.075,.895,f'Through iteration {x[-1]} • Same geometry and fan forcing • Convergence remains under assessment',fontsize=15,color='#17686b')
    fig.text(.075,.055,'These curves show numerical iteration. Oscillations here cannot be assigned a physical shedding frequency.',fontsize=12,color='#536772')
    fig.text(.075,.025,'Provisional mesh; this history alone does not establish a validated steady flow or a Bernoulli mechanism.',fontsize=12,color='#536772')
    fig.savefig(source.with_suffix('.png'));plt.close(fig);print(source.with_suffix('.png'))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--case',type=Path);parser.add_argument('--output',type=Path);parser.add_argument('--plot',type=Path)
    args=parser.parse_args()
    if args.plot:plot(args.plot)
    else:capture(args.case,args.output)
