"""Render actual Rev H CFD surfaces and the sampled lip locations with VTK."""
from pathlib import Path
import argparse
import vtk

BASE=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
renderer=vtk.vtkRenderer();renderer.SetBackground(1,1,1)
renderer.SetViewport(0,.12,1,.86)
window=vtk.vtkRenderWindow();window.SetOffScreenRendering(1)
window.SetSize(1000,1150);window.SetMultiSamples(8);window.AddRenderer(renderer)
window.SetNumberOfLayers(3)
background=vtk.vtkRenderer();background.SetBackground(1,1,1);window.AddRenderer(background)
renderer.SetLayer(1)
overlay=vtk.vtkRenderer();overlay.SetLayer(2);overlay.InteractiveOff();window.AddRenderer(overlay)

def color(value):
    return tuple(int(value[i:i+2],16)/255 for i in (1,3,5))

def actor(poly,hexcolor):
    mapper=vtk.vtkPolyDataMapper();mapper.SetInputData(poly);mapper.ScalarVisibilityOff()
    item=vtk.vtkActor();item.SetMapper(mapper)
    item.GetProperty().SetColor(*color(hexcolor));item.GetProperty().SetAmbient(.3)
    item.GetProperty().SetDiffuse(.7);item.GetProperty().SetSpecular(.12)
    renderer.AddActor(item)
    return item

for name,shade in [('printed','#408b91'),('laptop','#cad2d8'),('noctua','#253e4b')]:
    reader=vtk.vtkSTLReader();reader.SetFileName(str(BASE/'geometry_revh'/(name+'.stl')));reader.Update()
    normals=vtk.vtkPolyDataNormals();normals.SetInputConnection(reader.GetOutputPort())
    normals.SetFeatureAngle(45);normals.ConsistencyOn();normals.Update()
    actor(normals.GetOutput(),shade)
for z0,z1,shade in [(-.008,.035,'#db741d'),(.208,.262,'#9a315d')]:
    plane=vtk.vtkPlaneSource();plane.SetOrigin(.111,.025,z0)
    plane.SetPoint1(.111,.075,z0);plane.SetPoint2(.111,.025,z1);plane.Update()
    item=actor(plane.GetOutput(),shade);item.GetProperty().SetOpacity(.45)
    item.GetProperty().EdgeVisibilityOn();item.GetProperty().SetEdgeColor(*color(shade))
    item.GetProperty().SetLineWidth(3)

def label(text,x,y,size,shade):
    item=vtk.vtkTextActor();item.SetInput(text);item.SetPosition(x,y)
    prop=item.GetTextProperty();prop.SetFontFamilyToArial();prop.SetFontSize(size)
    prop.SetColor(*color(shade));overlay.AddActor2D(item)

label('Where the flow sections are sampled',42,1094,32,'#162c36')
label('Revision H | actual CFD geometry',42,1055,23,'#536772')
label('Laptop',42,1009,21,'#88959e')
label('Printed mount and curved ducts',180,1009,21,'#408b91')
label('Fan housings',655,1009,21,'#253e4b')
label('Orange: front lip / duct outlet',42,91,22,'#db741d')
label('Plum: hinge discharge',530,91,22,'#9a315d')
label('Coloured windows mark the right-side section at X = 111 mm.',42,52,20,'#536772')
label('Geometry locator only; no flow result is shown.',42,23,20,'#536772')
camera=renderer.GetActiveCamera()
camera.SetPosition(.8,.65,.38);camera.SetFocalPoint(0,.065,.036)
camera.SetViewUp(0,0,1);camera.ParallelProjectionOn();camera.SetParallelScale(.255)
renderer.ResetCameraClippingRange();window.Render()
capture=vtk.vtkWindowToImageFilter();capture.SetInput(window);capture.ReadFrontBufferOff();capture.Update()
args.output.parent.mkdir(parents=True,exist_ok=True)
writer=vtk.vtkPNGWriter();writer.SetFileName(str(args.output));writer.SetInputConnection(capture.GetOutputPort());writer.Write()
window.Finalize()
print(args.output)
