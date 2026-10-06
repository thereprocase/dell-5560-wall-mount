"""Read the completed OpenFOAM case, integrate sampled openings, render streamlines."""
from pathlib import Path
import json,math
import vtk
from vtk.util.numpy_support import vtk_to_numpy
import numpy as np
base=Path(__file__).resolve().parent
case=base/'cases/OpenCFD_v2412/installed_pressure10_v3'
out=case/'results';out.mkdir(exist_ok=True)
reader=vtk.vtkOpenFOAMReader();reader.SetFileName(str(case/'case.foam'));reader.CreateCellToPointOn();reader.UpdateInformation()
times=reader.GetTimeValues();last=times.GetValue(times.GetNumberOfValues()-1);reader.SetTimeValue(last)
out=out/f'iteration_{int(last)}';out.mkdir(exist_ok=True)
reader.EnableAllCellArrays();reader.Update()
mesh=reader.GetOutput().GetBlock(0)
assert isinstance(mesh,vtk.vtkUnstructuredGrid),mesh.GetClassName()
if mesh.GetPointData().GetArray('U') is None:
 conv=vtk.vtkCellDataToPointData();conv.SetInputData(mesh);conv.Update();mesh=conv.GetOutput()
mesh.GetPointData().SetActiveVectors('U')
meta=json.loads((base/'geometry_traced_repaired/geometry_manifest.json').read_text())
report={'iteration':last,'cells':mesh.GetNumberOfCells(),'scope':'Uncalibrated constant-force four-fan airflow; 10 Pa nominal pressure assumptions; no thermal solution','sampled_flows':{}}
def probe(points):
 pts=vtk.vtkPoints()
 for p in points:pts.InsertNextPoint(*p)
 cloud=vtk.vtkPolyData();cloud.SetPoints(pts)
 sample=vtk.vtkProbeFilter();sample.SetSourceData(mesh);sample.SetInputData(cloud);sample.Update()
 data=sample.GetOutput();return vtk_to_numpy(data.GetPointData().GetArray('U')),vtk_to_numpy(data.GetPointData().GetArray('vtkValidPointMask'))
for name,z in meta['zones'].items():
 if 'fan' not in name:continue
 c=np.array(z['centroid_mm'])*.001;n=np.array(z['actuator_direction']);r=.025 if name.startswith('dell') else .055
 a=np.array([1.,0,0]);b=np.cross(n,a);points=[]
 for i in range(24):
  rr=r*math.sqrt((i+.5)/24)
  for j in range(64):points.append(c+rr*(math.cos(2*math.pi*j/64)*a+math.sin(2*math.pi*j/64)*b))
 u,valid=probe(points);q=float(np.mean(u@n)*math.pi*r*r)
 report['sampled_flows'][name]={'net_m3_s':q,'net_CFM':q*60/.028316846592,'valid_sample_fraction':float(valid.mean()),'method':'Equal-area disk quadrature of interpolated velocity; inspect valid fraction before interpretation'}
for i,w in enumerate(meta['trace']['data']['effective_intake_windows']):
 x0,x1=np.array(w['x_mm'])*.001;z0,z1=np.array(w['z_mm'])*.001
 pts=[(x0+(a+.5)*(x1-x0)/48,.0405,z0+(b+.5)*(z1-z0)/32) for a in range(48) for b in range(32)]
 u,valid=probe(pts);q=float(np.mean(u[:,1])*(x1-x0)*(z1-z0))
 report['sampled_flows']['intake_'+('left' if i==0 else 'right')]={'net_m3_s':q,'net_CFM':q*60/.028316846592,'valid_sample_fraction':float(valid.mean()),'method':'Rectangle quadrature at y=40.5mm, positive into laptop'}
(out/'flow_samples.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2),flush=True)
renderer=vtk.vtkRenderer();renderer.SetBackground(.96,.97,.98)
for name,color,opacity in [('printed',(.35,.40,.46),.38),('laptop',(.5,.55,.60),.14),('noctua',(.30,.22,.16),.45)]:
 stl=vtk.vtkSTLReader();stl.SetFileName(str(base/'geometry_traced_repaired'/(name+'.stl')));stl.Update()
 mapper=vtk.vtkPolyDataMapper();mapper.SetInputConnection(stl.GetOutputPort())
 actor=vtk.vtkActor();actor.SetMapper(mapper);actor.GetProperty().SetColor(*color);actor.GetProperty().SetOpacity(opacity);renderer.AddActor(actor)
seed=vtk.vtkPoints()
for name,z in meta['zones'].items():
 if 'fan' not in name:continue
 c=np.array(z['centroid_mm'])*.001;n=np.array(z['actuator_direction']);a=np.array([1.,0,0]);b=np.cross(n,a);r=.018 if name.startswith('dell') else .045
 for j in range(24):
  p=c+r*(math.cos(2*math.pi*j/24)*a+math.sin(2*math.pi*j/24)*b)
  seed.InsertNextPoint(*p)
cloud=vtk.vtkPolyData();cloud.SetPoints(seed)
stream=vtk.vtkStreamTracer();stream.SetInputData(mesh);stream.SetSourceData(cloud);stream.SetInputArrayToProcess(0,0,0,vtk.vtkDataObject.FIELD_ASSOCIATION_POINTS,'U');stream.SetIntegratorTypeToRungeKutta45();stream.SetIntegrationDirectionToBoth();stream.SetMaximumPropagation(1.2);stream.SetInitialIntegrationStep(.2);stream.SetMinimumIntegrationStep(.02);stream.SetMaximumIntegrationStep(.5);stream.SetMaximumNumberOfSteps(3000);stream.Update()
writer=vtk.vtkXMLPolyDataWriter();writer.SetFileName(str(out/'streamlines.vtp'));writer.SetInputConnection(stream.GetOutputPort());writer.Write()
calc=vtk.vtkArrayCalculator();calc.SetInputConnection(stream.GetOutputPort());calc.AddVectorArrayName('U');calc.SetFunction('mag(U)');calc.SetResultArrayName('speed');calc.Update()
lut=vtk.vtkLookupTable();lut.SetHueRange(.67,0);lut.SetTableRange(0,6);lut.Build()
mapper=vtk.vtkPolyDataMapper();mapper.SetInputConnection(calc.GetOutputPort());mapper.SetScalarModeToUsePointFieldData();mapper.SelectColorArray('speed');mapper.SetLookupTable(lut);mapper.SetScalarRange(0,6)
actor=vtk.vtkActor();actor.SetMapper(mapper);actor.GetProperty().SetLineWidth(2);renderer.AddActor(actor)
bar=vtk.vtkScalarBarActor();bar.SetLookupTable(lut);bar.SetTitle('Speed (m/s)');bar.SetNumberOfLabels(5);bar.GetTitleTextProperty().SetColor(.1,.1,.1);bar.GetLabelTextProperty().SetColor(.1,.1,.1);bar.SetWidth(.10);bar.SetHeight(.5);bar.SetPosition(.87,.2);renderer.AddActor2D(bar)
text=vtk.vtkTextActor();text.SetInput('Precision 5560 | traced profile + twin internal ducts\nEXPLORATORY: idealized 10 Pa fan sources; no thermal prediction');text.SetPosition(35,30);text.GetTextProperty().SetFontSize(22);text.GetTextProperty().SetColor(.1,.13,.17);renderer.AddActor2D(text)
camera=renderer.GetActiveCamera();camera.SetPosition(.65,.8,.45);camera.SetFocalPoint(0,.065,.045);camera.SetViewUp(0,0,1);renderer.ResetCamera();camera.Zoom(1.45)
window=vtk.vtkRenderWindow();window.SetOffScreenRendering(1);window.SetSize(1600,1200);window.AddRenderer(renderer);window.Render()
shot=vtk.vtkWindowToImageFilter();shot.SetInput(window);shot.Update();png=vtk.vtkPNGWriter();png.SetFileName(str(out/'airflow_streamlines.png'));png.SetInputConnection(shot.GetOutputPort());png.Write()
window.Finalize()
