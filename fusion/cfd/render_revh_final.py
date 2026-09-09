"""Render final saved fields, complete probe records and time-weighted summaries."""
from render_revh_progress import read_plane,cad_sections,choose,arrows,sha
from measure_revh_section_flow import integrate
import argparse,csv,ctypes,gzip,json,os
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

def weighted(times,values,start):
    """Exact integral of piecewise-linear samples, with an interpolated boundary."""
    x=np.asarray(times);y=np.asarray(values);keep=x>start
    x=np.r_[start,x[keep]];y=np.r_[np.interp(start,times,values),y[keep]]
    span=np.diff(x);duration=x[-1]-x[0]
    mean=np.sum(span*(y[:-1]+y[1:])/2)/duration
    second=np.sum(span*(y[:-1]**2+y[:-1]*y[1:]+y[1:]**2)/3)/duration
    return {'mean':float(mean),'rms_fluctuation':float(np.sqrt(max(0,second-mean*mean))),
            'minimum':float(y.min()),'maximum':float(y.max())}

def field_images(out,data,phase,end):
    pts,tri,fields=read_plane(out/'right_section.vtp');lines=cad_sections();ranges={}
    for filename,label,values,cmap,low,high in [
        ('speed-arrows','Speed [m/s]',np.linalg.norm(fields['U'],axis=1),'viridis',0,6),
        ('pressure-arrows','Static pressure [Pa, solver reference]',fields['p']*1.2,'RdBu_r',-12,12),
        ('vorticity-arrows','Vorticity X [1/s]',fields['vorticity'][:,0],'RdBu_r',-2000,2000)]:
        fig=plt.figure(figsize=(18,10),dpi=110)
        grid=fig.add_gridspec(1,3,width_ratios=[.70,1,1],left=.055,right=.91,top=.81,bottom=.16,wspace=.32)
        for i,(title,bounds,spacing,scale) in enumerate([
            ('Complete air path',(-4,155,-155,257),8,.5),('Front lip / duct outlet',(25,75,-8,35),3,1),('Hinge discharge',(25,75,208,262),3,1)]):
            ax=fig.add_subplot(grid[0,i]);selected=choose(pts,tri,bounds)
            im=ax.tripcolor(pts[:,0],pts[:,1],selected,values,cmap=cmap,vmin=low,vmax=high,shading='gouraud',rasterized=True)
            ax.add_collection(LineCollection(lines,colors='#102c38',linewidths=1))
            q=arrows(ax,pts,fields['U'],bounds,spacing=spacing,scale=scale)
            ax.set(xlim=bounds[:2],ylim=bounds[2:],aspect='equal',xlabel='Y from wall [mm]',ylabel='Height Z [mm]',title=title,facecolor='#cdd5db')
            ax.quiverkey(q,.7,1.085,5,'5 m/s',labelpos='E',coordinates='axes',fontproperties={'size':11})
            local=values[np.unique(selected)];ranges[filename+'/'+title]=[float(local.min()),float(local.max())]
        cax=fig.add_axes([.935,.24,.016,.46]);fig.colorbar(im,cax=cax,label=label,extend='both')
        fig.text(.055,.94,f'REVISION H  |  {phase.upper()}  |  FINAL SAVED FIELD',fontsize=22,fontweight='bold',color='#162c36')
        fig.text(.055,.888,f'{label}  |  t = {end*1000:.5f} ms  |  X = +111 mm',fontsize=17,color='#17686b')
        fig.text(.055,.075,'Arrows: sampled in-plane velocity. Black: CAD. Grey: solid or unsampled. Color limits match between runs.',fontsize=13,color='#536772')
        fig.text(.055,.035,'Existing isothermal exploratory run. This transient snapshot is not a temperature or validated steady-state prediction.',fontsize=12,color='#536772')
        fig.savefig(out/(filename+'.png'));plt.close(fig)
    return ranges

def history_image(out,data):
    times=np.array(data['probe_times_s']);probes={p['name']:p for p in data['probes']};ambient=np.array(probes['ambient_reference']['pressure_Pa'])
    fig,axs=plt.subplots(2,2,figsize=(16,10),dpi=120);fig.subplots_adjust(left=.075,right=.97,bottom=.10,top=.86,wspace=.25,hspace=.46)
    selected=[('duct_edge','Duct edge'),('duct_wake','Duct wake'),('front_lip_wallside','Lip / wall side'),('front_lip_outside','Lip / outside'),('hinge_exit','Hinge exit'),('hinge_wake','Hinge wake')]
    colors=['#0057b8','#9c3273','#008066','#bc6800','#5733a6','#64717c']
    for (name,label),color in zip(selected,colors):
        p=probes[name+'_x0.111'];axs[0,0].plot(times*1000,np.array(p['pressure_Pa'])-ambient,label=label,lw=1.4,color=color)
        axs[0,1].plot(times*1000,p['speed_m_s'],lw=1.4,color=color)
    axs[0,0].set(title='Right-section probes / pressure relative to ambient',ylabel='Pressure difference [Pa]')
    axs[0,1].set(title='Right-section probes / local speed',ylabel='Speed [m/s]')
    axs[0,0].legend(ncol=3,fontsize=10,loc='upper center',bbox_to_anchor=(1.05,1.30))
    history=data['history'];ht=np.array([r['time_s'] for r in history])*1000
    co=np.array([r['max_Courant_reported'] if r['max_Courant_reported'] is not None else np.nan for r in history])
    axs[1,0].plot(ht,co,color='#0057b8',lw=1.5);axs[1,0].set(title='Recorded maximum Courant number',ylabel='Courant number',ylim=(0,max(.55,float(np.nanmax(co))*1.15)))
    ratio=[abs(r['ambient_net_flux_m3_s'])/r['ambient_absolute_flux_m3_s'] if r['ambient_absolute_flux_m3_s'] else np.nan for r in history]
    axs[1,1].plot(ht,ratio,color='#008066',lw=1.5);axs[1,1].set(title='Outer-boundary net / absolute volume flux',ylabel='Absolute net / total absolute flux',yscale='symlog');axs[1,1].set_yscale('symlog',linthresh=1e-9)
    for ax in axs.flat:
        ax.set_xlabel('Time since '+('startup' if data['phase']=='startup' else 'flowing-field initialization')+' [ms]');ax.grid(alpha=.18)
        ax.axvspan((times[-1]-.01)*1000,times[-1]*1000,color='#baf24a',alpha=.16)
        if data['visual_timestep_change_s']:
            ax.axvline(data['visual_timestep_change_s']*1000,color='#b87900',ls='--',lw=1.1)
    title='STARTUP' if data['phase']=='startup' else 'FROM FLOWING INITIALIZATION'
    fig.suptitle(f'REVISION H  |  {title}  |  FULL SAVED DIAGNOSTIC HISTORY',fontsize=20,fontweight='bold',x=.075,ha='left',y=.97)
    fig.text(.075,.025,'Green band: final 10 ms used for time-weighted probe statistics. '+('Dashed line: switch to fixed 80.93 µs visual steps.' if data['phase']=='startup' else 'This time axis belongs to the separate flowing-field transient.'),fontsize=12,color='#536772')
    fig.savefig(out/'history.png');plt.close(fig)

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    if os.name=='nt':
        handle=ctypes.windll.kernel32.GetCurrentProcess();ctypes.windll.kernel32.SetPriorityClass(handle,0x40);ctypes.windll.kernel32.SetProcessAffinityMask(handle,3<<12)
    plt.rcParams.update({'font.size':12,'axes.titlesize':15,'figure.facecolor':'#f7f9fa'})
    # Independent analytic checks of the exact time-weighted integration.
    check=weighted([0,1,3],[2,4,8],1);assert abs(check['mean']-6)<1e-12 and abs(check['rms_fluctuation']-np.sqrt(4/3))<1e-12
    summary={'created_utc':datetime.now(timezone.utc).isoformat(),'method':'Existing sampled fields only. Probe means and RMS use exact piecewise-linear time integrals over the final 10 ms; boundary values are interpolated. RMS is fluctuation about that mean.','phases':{}}
    for phase in ['startup','flowing']:
        out=args.output/phase
        with gzip.open(out/'diagnostics.json.gz','rt',encoding='utf-8') as f:data=json.load(f)
        end=data['through_time_s'];times=data['probe_times_s'];start=times[-1]-.01
        ranges=field_images(out,data,'STARTUP' if phase=='startup' else 'FLOWING INITIALIZATION',end);history_image(out,data)
        probes={p['name']:p for p in data['probes']};ambient=np.array(probes['ambient_reference']['pressure_Pa']);stats=[]
        for name,probe in probes.items():
            pressure=weighted(times,np.array(probe['pressure_Pa'])-ambient,start);speed=weighted(times,probe['speed_m_s'],start)
            stats.append({'probe':name,**{'pressure_relative_ambient_Pa_'+k:v for k,v in pressure.items()},**{'speed_m_s_'+k:v for k,v in speed.items()}})
        with (out/'probe-summary.csv').open('w',encoding='utf-8',newline='') as f:
            w=csv.DictWriter(f,fieldnames=stats[0].keys());w.writeheader();w.writerows(stats)
        flux={}
        for side in ['left','right']:
            pts,tri,fields=read_plane(out/(side+'_section.vtp'));a=[40.,0.];b=[48.129883,4.663238];d=np.array(b)-a
            flux[side]={'front_opening':integrate(pts,tri,fields['U'],a,b,[d[1],-d[0]]),
                        'upward_channel':integrate(pts,tri,fields['U'],[.01,20.001],[45.,20.001],[0.,1.])}
        result={'through_time_s':end,'probe_time_range_s':[times[0],times[-1]],'probe_samples':len(times),'solver_rows':len(data['history']),
                'window_s':[start,times[-1]],'probe_statistics':stats,'final_section_flux':flux,'field_plot_ranges':ranges,
                'section_flux_scope':'Local line integrals at X = +/-111 mm, in m2/s (volume flux per unit span). Not full-width L/s or a closed 3D flow balance.',
                'files_sha256':{p.name:sha(p) for p in out.iterdir() if p.is_file() and p.name!='summary.json'}}
        summary['phases'][phase]=result
        (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({'phase':phase,'through_ms':end*1000,'lip_probe_means_Pa':[s['pressure_relative_ambient_Pa_mean'] for s in stats if 'front_lip_wallside' in s['probe']],'final_section_flux':flux}),flush=True)
    (args.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
