"""Integrate velocity across lines in actual sampled planes, per unit span.

This is a local section diagnostic. It is not a full-width flow rate or a
conservative flow split for the three-dimensional device.
"""
from render_revh_progress import read_plane,sha
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import numpy as np


def integrate(points,tri,U,start,end,normal):
    a=np.asarray(start,float);b=np.asarray(end,float);n=np.asarray(normal,float);n/=np.linalg.norm(n)
    tangent=b-a;length=np.linalg.norm(tangent);tangent/=length
    signed=(points-a)@n
    candidates=tri[(signed[tri].min(axis=1)<0)&(signed[tri].max(axis=1)>0)]
    outflow=inflow=covered=0.
    for cell in candidates:
        crossing=[]
        for i,j in [(cell[0],cell[1]),(cell[1],cell[2]),(cell[2],cell[0])]:
            if signed[i]*signed[j]>=0:continue
            fraction=signed[i]/(signed[i]-signed[j])
            p=points[i]+fraction*(points[j]-points[i]);u=U[i]+fraction*(U[j]-U[i])
            crossing.append((float((p-a)@tangent),float(u[1:]@n)))
        if len(crossing)!=2:continue
        (s0,v0),(s1,v1)=sorted(crossing)
        low=max(s0,0);high=min(s1,length)
        if high<=low:continue
        w0=v0+(v1-v0)*(low-s0)/(s1-s0);w1=v0+(v1-v0)*(high-s0)/(s1-s0)
        span=(high-low)/1000;covered+=span
        if w0*w1>=0:
            value=(w0+w1)*.5*span
            if value>=0:outflow+=value
            else:inflow-=value
        else:
            fraction=abs(w0)/(abs(w0)+abs(w1))
            for value in [w0*.5*span*fraction,w1*.5*span*(1-fraction)]:
                if value>=0:outflow+=value
                else:inflow-=value
    return {'start_YZ_mm':start,'end_YZ_mm':end,'positive_normal_YZ':n.tolist(),
            'sampled_fluid_line_length_mm':covered*1000,'positive_flux_m2_s':outflow,
            'negative_flux_m2_s':inflow,'net_flux_m2_s':outflow-inflow}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--snapshot',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();results={};hashes={}
    for side in ['left','right']:
        source=args.snapshot/(side+'_section.vtp');pts,tri,data=read_plane(source)
        a=[40.,0.];b=[48.129883,4.663238];d=np.array(b)-a
        results[side]={'front_opening':integrate(pts,tri,data['U'],a,b,[d[1],-d[0]]),
                       'upward_channel_at_Z20':integrate(pts,tri,data['U'],[.01,20.001],[45.,20.001],[0.,1.])}
        hashes[side]=sha(source)
    report={'created_utc':datetime.now(timezone.utc).isoformat(),'snapshot':args.snapshot.name,
            'scope':__doc__,'sections_x_m':[-.111,.111],'source_sha256':hashes,'results':results,
            'method':'Piecewise-linear sampled velocities integrated over intersected triangles. Front line joins the printed divider tip to the laptop nose shoulder in the CAD section.'}
    args.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__=='__main__':main()
