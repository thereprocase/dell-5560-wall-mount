"""Integrate saved 3-D sampled velocity across explicitly bounded opening cuts.

These are central-span plane integrals, not a closed device control volume or
a calibrated fan flow measurement. Input triangles contain only meshed fluid.
"""
from render_revh_progress import sha
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy,numpy_to_vtk
import matplotlib.pyplot as plt


def clip(poly,origin,normal):
    plane=vtk.vtkPlane();plane.SetOrigin(origin);plane.SetNormal(normal)
    cut=vtk.vtkClipPolyData();cut.SetInputData(poly);cut.SetClipFunction(plane);cut.SetValue(0);cut.Update()
    result=vtk.vtkPolyData();result.DeepCopy(cut.GetOutput());return result


def triangles(poly):
    tri=vtk.vtkTriangleFilter();tri.SetInputData(poly);tri.Update();return tri.GetOutput()


def integral(poly,normal):
    poly=triangles(poly)
    if not poly.GetNumberOfCells():return 0.,0.
    pts=vtk_to_numpy(poly.GetPoints().GetData());ids=vtk_to_numpy(poly.GetPolys().GetData()).reshape(-1,4)[:,1:]
    area=np.linalg.norm(np.cross(pts[ids[:,1]]-pts[ids[:,0]],pts[ids[:,2]]-pts[ids[:,0]]),axis=1)*.5
    velocity=vtk_to_numpy(poly.GetPointData().GetArray('U'))@normal
    return float(np.sum(area)),float(np.sum(area*velocity[ids].mean(axis=1)))


def directions(poly,normal):
    velocity=vtk_to_numpy(poly.GetPointData().GetArray('U'))@normal
    scalar=numpy_to_vtk(velocity,deep=True);scalar.SetName('normalVelocity')
    poly.GetPointData().SetScalars(scalar)
    result={}
    for inside,name in [(False,'positive'),(True,'negative')]:
        cut=vtk.vtkClipPolyData();cut.SetInputData(poly);cut.SetValue(0);cut.SetInsideOut(inside);cut.Update()
        area,flow=integral(cut.GetOutput(),normal);result[name+'_area_m2']=area;result[name+'_flow_L_s']=abs(flow)*1000
    area,net=integral(poly,normal)
    result.update(fluid_area_m2=area,net_flow_L_s=net*1000,normal_velocity_range_m_s=[float(velocity.min()),float(velocity.max())])
    assert abs(result['positive_flow_L_s']-result['negative_flow_L_s']-result['net_flow_L_s'])<1e-6
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--samples',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);args=p.parse_args();args.output.mkdir(exist_ok=False)
    a=np.array([0.,.040,0.]);b=np.array([0.,.048129883,.004663238]);tangent=b-a;tangent/=np.linalg.norm(tangent)
    normal=np.array([0.,tangent[2],-tangent[1]])
    results={};polys={};hashes={};definitions={}
    for name in ['front_mouth','upward_channel']:
        source=args.samples/(name+'.vtp');reader=vtk.vtkXMLPolyDataReader();reader.SetFileName(str(source));reader.Update()
        poly=reader.GetOutput()
        if not poly.GetPointData().GetArray('U'):
            to_points=vtk.vtkCellDataToPointData();to_points.SetInputData(poly);to_points.Update();poly=to_points.GetOutput()
        poly=clip(poly,[-.140,0,0],[1,0,0]);poly=clip(poly,[.140,0,0],[-1,0,0])
        if name=='front_mouth':
            poly=clip(poly,a,tangent);poly=clip(poly,b,-tangent);direction=normal
            definition={'span_x_m':[-.140,.140],'gap_endpoints_m':[a.tolist(),b.tolist()],
                        'positive_normal':normal.tolist(),'positive_meaning':'Outward through the front opening'}
        else:
            poly=clip(poly,[0,.00001,0],[0,1,0]);poly=clip(poly,[0,.045,0],[0,-1,0]);direction=np.array([0.,0.,1.])
            definition={'span_x_m':[-.140,.140],'range_y_m':[.00001,.045],'height_z_m':.020001,
                        'positive_normal':direction.tolist(),'positive_meaning':'Upward in the laptop-side passage'}
        poly=triangles(poly);assert poly.GetNumberOfCells()>0
        assert np.isfinite(vtk_to_numpy(poly.GetPointData().GetArray('U'))).all()
        results[name]=directions(poly,direction);definitions[name]=definition;polys[name]=poly;hashes[name]=sha(source)
        writer=vtk.vtkXMLPolyDataWriter();writer.SetFileName(str(args.output/(name+'-clipped.vtp')));writer.SetInputData(poly);assert writer.Write()==1
    report={'created_utc':datetime.now(timezone.utc).isoformat(),'steady_iteration':400,'converged':False,
        'scope':__doc__,'definitions':definitions,'source_sha256':hashes,'results':results,
        'upward_to_net_front_flow_ratio':results['upward_channel']['net_flow_L_s']/results['front_mouth']['net_flow_L_s'],
        'method':'Clip sampled fluid triangles to stated bounds. Integrate linearly interpolated normal velocity over triangle area; split at zero normal velocity for inward and outward components.'}
    (args.output/'opening-flow.json').write_text(json.dumps(report,indent=2)+'\n')
    plt.rcParams.update({'font.size':12,'figure.facecolor':'#f7f9fa'})
    fig,axes=plt.subplots(2,1,figsize=(14,9),dpi=120);fig.subplots_adjust(top=.81,bottom=.16,left=.09,right=.90,hspace=.58)
    for ax,name,title in zip(axes,['front_mouth','upward_channel'],['Front opening: positive velocity points outward','Laptop-side passage at Z = 20.001 mm: positive velocity points upward']):
        poly=polys[name];pts=vtk_to_numpy(poly.GetPoints().GetData());ids=vtk_to_numpy(poly.GetPolys().GetData()).reshape(-1,4)[:,1:]
        values=vtk_to_numpy(poly.GetPointData().GetArray('normalVelocity'))
        ordinate=(pts-a)@tangent*1000 if name=='front_mouth' else pts[:,1]*1000
        im=ax.tripcolor(pts[:,0]*1000,ordinate,ids,values,cmap='RdBu_r',vmin=-4,vmax=4,shading='gouraud')
        ax.set(title=title,xlabel='Across laptop: X [mm]',ylabel='Distance across opening [mm]' if name=='front_mouth' else 'Y from wall [mm]',xlim=(-140,140))
        fig.colorbar(im,ax=ax,label='Normal velocity [m/s]',pad=.02)
    fig.text(.09,.93,'REVISION H  |  FLOW ACROSS THE CENTRAL 280 mm',fontsize=22,fontweight='bold',color='#162c36')
    fig.text(.09,.878,'Steady iteration 400, unconverged. These maps show flow across the cuts; gap axes are expanded.',fontsize=13,color='#17686b')
    front=results['front_mouth'];up=results['upward_channel']
    fig.text(.09,.08,f'Front: {front["positive_flow_L_s"]:.2f} L/s outward, {front["negative_flow_L_s"]:.2f} L/s inward; net {front["net_flow_L_s"]:.2f} L/s outward. Upward passage: {up["net_flow_L_s"]:.2f} L/s net.',fontsize=13,color='#162c36')
    fig.text(.09,.035,'Defined open cuts, not a closed device flow balance. Provisional geometry, mesh and fan forcing; no thermal prediction.',fontsize=12,color='#536772')
    fig.savefig(args.output/'opening-flow.png');plt.close(fig);print(json.dumps(report,indent=2))


if __name__=='__main__':main()
