"""Render actual cut-cell outlines; run with FreeCAD's VTK/matplotlib Python."""
import os
os.environ.setdefault('WINDIR','C:/Windows')
os.environ.setdefault('SystemRoot','C:/Windows')
os.environ.setdefault('USERPROFILE',str(__import__('pathlib').Path(os.environ['LOCALAPPDATA']).parents[1]))
os.environ['VTK_SMP_MAX_THREADS']='1'
from pathlib import Path
import argparse
import json
import re
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection, LineCollection

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--case',type=Path,default=BASE/'runs/revh_transient_04')
parser.add_argument('--output',type=Path,default=ROOT/'docs/simulation/revh-transient')
args=parser.parse_args()
case=args.case.resolve()
out=args.output.resolve()
out.mkdir(parents=True,exist_ok=True)
reader=vtk.vtkOpenFOAMReader()
reader.SetFileName(str(case/'case.foam'));reader.CreateCellToPointOff()
reader.UpdateInformation();reader.DisableAllCellArrays();reader.SetTimeValue(0);reader.Update()
mesh=reader.GetOutput().GetBlock(0)
assert isinstance(mesh,vtk.vtkUnstructuredGrid)
print('Read',mesh.GetNumberOfCells(),'cells',flush=True)
def read_set(name):
    path=case/'constant/polyMesh/sets'/name
    if not path.exists():
        check=(case/'log.checkMesh.expanded').read_text()
        assert name=='underdeterminedCells' and 'Cell determinant' in check and 'Cells with small determinant' not in check
        return np.empty(0,dtype=np.int64)
    text=path.read_text()
    match=re.search(r'\n\s*(\d+)\s*\(\s*([\d\s]*)\)',text)
    assert match, 'Unrecognized cell-set list: '+name
    ids=np.fromstring(match[2],dtype=np.int64,sep=' ')
    assert len(ids)==int(match[1])
    return ids

bad_ids=read_set('underdeterminedCells')
bad=[]
for cell_id in bad_ids:
    cell=mesh.GetCell(int(cell_id))
    points=vtk_to_numpy(cell.GetPoints().GetData())
    bad.append([int(cell_id),*points.mean(axis=0),*np.ptp(points,axis=0)])
bad=np.array(bad).reshape(-1,7)
np.savetxt(out/'underdetermined-cell-locations.csv',bad,delimiter=',',header='cell_id,x_m,y_m,z_m,span_x_m,span_y_m,span_z_m',comments='',fmt=['%d']+['%.10g']*6)
diagnostic={'count':len(bad),'center_bounds_m':[bad[:,1:4].min(axis=0).tolist(),bad[:,1:4].max(axis=0).tolist()] if len(bad) else None,
            'span_quantiles_m':np.quantile(bad[:,4:],[0,.01,.5,.99,1],axis=0).tolist() if len(bad) else None,
            'near_wall_plane_y_lt_2mm':int(np.sum(bad[:,2]<.002)),
            'front_lip_z_minus10_to30mm':int(np.sum((bad[:,3]>-.010)&(bad[:,3]<.030))),
            'hinge_z_210_to260mm':int(np.sum((bad[:,3]>.210)&(bad[:,3]<.260)))}
(out/'mesh-defect-locations.json').write_text(json.dumps(diagnostic,indent=2)+'\n')
print(json.dumps(diagnostic),flush=True)
surfaces={}
for name in ['printed','laptop','noctua']:
    r=vtk.vtkSTLReader();r.SetFileName(str(BASE/'geometry_revh'/(name+'.stl')));r.Update();surfaces[name]=r.GetOutput()
locators={}
for name,surface in surfaces.items():
    locator=vtk.vtkStaticCellLocator();locator.SetDataSet(surface);locator.BuildLocator();locators[name]=locator
distances=[];closest=[]
for point in bad[:,1:4]:
    candidates=[]
    for name,locator in locators.items():
        closest_point=[0.,0.,0.];cell_id=vtk.mutable(0);sub_id=vtk.mutable(0);dist2=vtk.mutable(0.)
        locator.FindClosestPoint(point,closest_point,cell_id,sub_id,dist2)
        candidates.append((float(dist2),name))
    d2,name=min(candidates);distances.append(np.sqrt(d2));closest.append(name)
diagnostic['nearest_CAD_patch_counts']={name:closest.count(name) for name in surfaces}
diagnostic['nearest_CAD_distance_quantiles_mm']=(1000*np.quantile(distances,[0,.01,.5,.99,1])).tolist() if distances else None
diagnostic['distance_note']='Centroid approximated by mean of cell vertices; distance to the original tessellated CAD surface, not the snapped mesh wall.'
(out/'mesh-defect-locations.json').write_text(json.dumps(diagnostic,indent=2)+'\n')

def cut(data):
    plane=vtk.vtkPlane();plane.SetNormal(1,0,0);plane.SetOrigin(.111,0,0)
    c=vtk.vtkCutter();c.SetInputData(data);c.SetCutFunction(plane);c.GenerateTrianglesOff();c.Update();return c.GetOutput()

fig,axs=plt.subplots(1,3,figsize=(15,6),layout='constrained')
overview,overview_ax=plt.subplots(figsize=(8,9),layout='constrained')
views=[('Duct outlet / front lip',(30,66),(-6,28)),('Front lip detail',(43,61),(-2,14)),('Hinge lip / discharge',(32,63),(213,253)),
       ('Complete duct section / Revision H bends',(-2,155),(-150,28))]
checks=[]
d=cut(mesh)
pts=vtk_to_numpy(d.GetPoints().GetData())[:,1:]*1000
all_polys=[];ids=vtk.vtkIdList();cells=d.GetPolys();cells.InitTraversal()
while cells.GetNextCell(ids):all_polys.append(pts[[ids.GetId(i) for i in range(ids.GetNumberOfIds())]])
all_bounds=np.array([[*p.min(axis=0),*p.max(axis=0)] for p in all_polys])
for ax,(title,ys,zs) in zip([*axs,overview_ax],views):
    selected=(all_bounds[:,0]<=ys[1])&(all_bounds[:,2]>=ys[0])&(all_bounds[:,1]<=zs[1])&(all_bounds[:,3]>=zs[0])
    polys=[p for p,keep in zip(all_polys,selected) if keep]
    ax.add_collection(PolyCollection(polys,facecolors='#eaf4f3',edgecolors='#366a70',linewidths=.22))
    for name,s in surfaces.items():
        b=cut(s)
        if b.GetNumberOfPoints()==0:continue
        bpts=vtk_to_numpy(b.GetPoints().GetData())[:,1:]*1000
        lines=b.GetLines();lines.InitTraversal();segments=[]
        while lines.GetNextCell(ids):segments.append(bpts[[ids.GetId(i) for i in range(ids.GetNumberOfIds())]])
        ax.add_collection(LineCollection(segments,colors='#101d28',linewidths=1))
    ax.set(xlim=ys,ylim=zs,xlabel='Outward from wall Y [mm]',ylabel='Height Z [mm]',title=title,aspect='equal')
    checks.append({'title':title,'plane_x_mm':111,'y_bounds_mm':ys,'z_bounds_mm':zs,'cut_polygons':len(polys)})
    print(title,len(polys),flush=True)
fig.suptitle('Revision H | actual mesh sections | '+case.name+'\nCell targets and wall-layer prescription are recorded in the case manifest; inspect achieved coverage.',fontsize=13)
fig.savefig(out/'mesh-sections.png',dpi=180);plt.close(fig)
overview.savefig(out/'mesh-duct-overview.png',dpi=200);plt.close(overview)
raw=(case/'log.checkMesh.standard').read_text(errors='replace')
expanded=(case/'log.checkMesh.expanded').read_text(errors='replace')
snappy=(case/'log.snappyHexMesh').read_text(errors='replace')
report={'case':case.name,'cells':mesh.GetNumberOfCells(),'standard_mesh_ok':'Mesh OK.' in raw,
        'expanded_mesh_ok':'Mesh OK.' in expanded,'refinement_cell_limit_hit':'reached limit' in snappy,
        'sections':checks,'rendering':'Cut-cell polygon outlines at X=111 mm. VTK may omit non-contourable cells; gaps are not filled.',
        'quality_summary':[l.strip() for l in expanded.splitlines() if re.search(r'\*\*\*|Failed|regions|non-orthogonality|skewness|determinant|concave|warped|Mesh OK',l,re.I)]}
(out/'mesh-review.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2),flush=True)
