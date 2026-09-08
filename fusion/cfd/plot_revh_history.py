"""Plot measured hourly histories; no inferred shedding-frequency fit."""
import os
os.environ['OMP_NUM_THREADS']='1'
import argparse
import json
from pathlib import Path
os.environ.setdefault('USERPROFILE',str(Path(os.environ['LOCALAPPDATA']).parents[1]))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();report=json.loads((args.output/'diagnostics.json').read_text())
    t=np.array(report['probe_times_s'])*1000
    byname={p['name']:p for p in report['probes']}
    ambient=np.array(byname['ambient_reference']['pressure_Pa'])
    selected=[('duct_edge_x0.111','Duct edge'),('duct_wake_x0.111','Duct wake'),
              ('front_lip_wallside_x0.111','Lip wall side'),('front_lip_outside_x0.111','Lip outside'),
              ('hinge_exit_x0.111','Hinge exit'),('hinge_wake_x0.111','Hinge wake')]
    plt.rcParams.update({'font.size':12,'axes.titlesize':15,'figure.facecolor':'#f7f9fa','axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(2,2,figsize=(15,10),dpi=110)
    fig.subplots_adjust(top=.85,bottom=.13,left=.075,right=.96,hspace=.45,wspace=.25)
    for name,label in selected:
        probe=byname[name]
        axes[0,0].plot(t,np.array(probe['pressure_Pa'])-ambient,label=label)
        axes[0,1].plot(t,probe['speed_m_s'],label=label)
    axes[0,0].axhline(0,color='#8d9aa2',lw=.8)
    axes[0,0].set(title='Pressure relative to ambient probe',ylabel='Pressure difference [Pa]')
    axes[0,1].set(title='Local speed at the same six probes',ylabel='Speed [m/s]',ylim=(0,None))
    axes[0,0].legend(ncol=2,fontsize=10,loc='best')
    h=report['history'];th=np.array([r['time_s'] for r in h])*1000
    net=np.array([r['ambient_net_flux_m3_s'] for r in h]);absolute=np.array([r['ambient_absolute_flux_m3_s'] for r in h])
    axes[1,0].plot(th,(absolute-net)*500,label='Inflow',lw=2)
    axes[1,0].plot(th,(absolute+net)*500,label='Outflow',ls='--')
    axes[1,0].set(title='Exchange across the outer domain boundary',ylabel='Volume flow [L/s]',ylim=(0,None))
    axes[1,0].legend(fontsize=10)
    axes[1,1].plot(th,[r['max_Courant_after_step'] for r in h],color='#17686b')
    axes[1,1].axhline(.5,color='#a5661b',ls='--',label='Adaptive limit 0.5')
    axes[1,1].set(title='Maximum Courant number',ylabel='Courant number',ylim=(0,.55))
    axes[1,1].legend(fontsize=10)
    for ax in axes.flat:ax.set_xlabel('Physical time [ms]');ax.grid(alpha=.16)
    label=f'HOUR {report["hour_checkpoint"]}' if report['hour_checkpoint'] else 'CURRENT CHECKPOINT'
    fig.text(.075,.945,f'REVISION H  |  {label} MEASURED HISTORIES',fontsize=23,fontweight='bold',color='#162c36')
    fig.text(.075,.903,f'Through {report["through_time_s"]*1000:.4f} ms • {len(h)} completed continuation steps • {report["new_bounding_events"]} new turbulence-bounding events',fontsize=15,color='#17686b')
    fig.text(.075,.055,'Startup on a provisional mesh. Curves show recorded solver outputs; periodic shedding and settled suction are not established.',fontsize=12,color='#536772')
    fig.text(.075,.025,'Right-side probes at X = +111 mm. Outer-boundary exchange is not a calibrated fan flow-rate measurement.',fontsize=12,color='#536772')
    fig.savefig(args.output/'history.png');plt.close(fig)
    print(args.output/'history.png')


if __name__=='__main__':main()
