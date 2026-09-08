"""Render actual steady-solver fields with velocity arrows and iteration labels."""
from render_revh_progress import read_plane,cad_sections,choose,arrows,sha
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--section',type=Path,required=True)
    parser.add_argument('--iteration',type=int,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    pts,tri,data=read_plane(args.section);lines=cad_sections()
    fields=[('speed-arrows','Speed [m/s]',np.linalg.norm(data['U'],axis=1),'viridis',0,6),
            ('pressure-arrows','Static pressure [Pa]',data['p']*1.2,'RdBu_r',-10,10),
            ('vorticity-arrows','Vorticity X [1/s]',data['vorticity'][:,0],'RdBu_r',-2000,2000)]
    ranges={};hashes={}
    plt.rcParams.update({'font.size':13,'axes.titlesize':17,'figure.facecolor':'#f7f9fa'})
    for filename,label,values,cmap,low,high in fields:
        fig=plt.figure(figsize=(18,10),dpi=110)
        grid=fig.add_gridspec(1,3,width_ratios=[.70,1,1],left=.055,right=.91,top=.82,bottom=.16,wspace=.32)
        for index,(title,bounds,spacing,scale) in enumerate([
            ('Complete air path',(-4,155,-155,257),8,.5),
            ('Front lip / duct outlet',(25,75,-8,35),3,1),
            ('Hinge lip / discharge',(25,75,208,262),3,1)]):
            ax=fig.add_subplot(grid[0,index]);selected=choose(pts,tri,bounds)
            im=ax.tripcolor(pts[:,0],pts[:,1],selected,values,cmap=cmap,vmin=low,vmax=high,shading='gouraud',rasterized=True)
            ax.add_collection(LineCollection(lines,colors='#102c38',linewidths=1))
            q=arrows(ax,pts,data['U'],bounds,spacing=spacing,scale=scale)
            ax.set(xlim=bounds[:2],ylim=bounds[2:],aspect='equal',xlabel='Y from wall [mm]',ylabel='Height Z [mm]',title=title,facecolor='#cdd5db')
            ax.quiverkey(q,.70,1.085,5,'5 m/s',labelpos='E',coordinates='axes',fontproperties={'size':11})
            local=values[np.unique(selected)];ranges[filename+'/'+title]=[float(local.min()),float(local.max())]
        color_ax=fig.add_axes([.935,.24,.016,.46]);fig.colorbar(im,cax=color_ax,label=label)
        fig.text(.055,.94,f'REVISION H  |  STEADY SOLVER ITERATION {args.iteration}',fontsize=24,fontweight='bold',color='#162c36')
        fig.text(.055,.893,label+' with velocity arrows  |  X = +111 mm  |  Not converged',fontsize=17,color='#17686b')
        fig.text(.055,.075,'Arrows are sampled in-plane velocity vectors. Black lines are CAD surfaces. Grey areas are solid or unsampled.',fontsize=13,color='#536772')
        fig.text(.055,.035,'This is a numerical steady-solver iterate, not elapsed physical time. It does not establish settled suction or periodic shedding.',fontsize=12,color='#536772')
        output=args.output/(filename+'.png');fig.savefig(output);plt.close(fig);hashes[output.name]=sha(output)
    report={'created_utc':datetime.now(timezone.utc).isoformat(),'solver':'simpleFoam','iteration':args.iteration,
            'converged':False,'scope':'Current numerical steady-solver iterate on a provisional mesh; not a validated steady solution.',
            'section_x_m':.111,'density_kg_m3':1.2,'source_section_sha256':sha(args.section),
            'image_sha256':hashes,'sampled_ranges':ranges,
            'arrows':'Actual sampled in-plane U components. Reference arrows show 5 m/s; overview and close-up scales are marked independently.'}
    (args.output/'images.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'iteration':args.iteration,'output':str(args.output),'files':list(hashes)}))


if __name__=='__main__':main()
