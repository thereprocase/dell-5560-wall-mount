"""Render exported CAD meshes, with explicit bolt/tool geometry. No image generation."""
from pathlib import Path
import math
import vtk
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'results'
def mesh_actor(path,color=(.13,.15,.18)):
    r=vtk.vtkSTLReader();r.SetFileName(str(path));r.Update()
    n=vtk.vtkPolyDataNormals();n.SetInputConnection(r.GetOutputPort());n.SetFeatureAngle(38);n.SplittingOn();n.ConsistencyOn()
    mapper=vtk.vtkPolyDataMapper();mapper.SetInputConnection(n.GetOutputPort())
    a=vtk.vtkActor();a.SetMapper(mapper);a.GetProperty().SetColor(*color);a.GetProperty().SetInterpolationToPhong();a.GetProperty().SetAmbient(.25);a.GetProperty().SetDiffuse(.7);a.GetProperty().SetSpecular(.3);a.GetProperty().SetSpecularPower(45)
    return a
def cylinder(x0,x1,cy,cz,r,color,opacity=1):
    s=vtk.vtkCylinderSource();s.SetRadius(r);s.SetHeight(x1-x0);s.SetResolution(72)
    m=vtk.vtkPolyDataMapper();m.SetInputConnection(s.GetOutputPort());a=vtk.vtkActor();a.SetMapper(m);a.RotateZ(-90);a.SetPosition((x0+x1)/2,cy,cz);a.GetProperty().SetColor(*color);a.GetProperty().SetOpacity(opacity);return a
def render(name,camera,tools=False,laptop=False):
    ren=vtk.vtkRenderer();ren.SetBackground(.94,.945,.955)
    rw=vtk.vtkRenderWindow();rw.SetSize(1500,1500);rw.SetOffScreenRendering(1);rw.AddRenderer(ren);rw.SetMultiSamples(8)
    actor=mesh_actor(OUT/'left.stl');ren.AddActor(actor)
    for cy in [18,132]:
        if not tools:
            ren.AddActor(cylinder(-14,5,cy,12,3,(.45,.47,.5)))
            ren.AddActor(cylinder(4,5,cy,12,7.3,(.62,.64,.67)))
            ren.AddActor(cylinder(5,7,cy,12,5.7,(.28,.3,.33)))
        else:
            ren.AddActor(cylinder(8,95,cy,12,8,(.2,.6,.85),.20))
            ren.AddActor(cylinder(4,102,cy,12,3,(.16,.4,.6),.7))
    if laptop:
        cube=vtk.vtkCubeSource();cube.SetXLength(20);cube.SetYLength(230.3);cube.SetZLength(344.4);cube.SetCenter(31,121.15,177.5)
        t=vtk.vtkTransform();t.Translate(20,6,0);t.RotateZ(-4.19808196);t.Translate(-20,-6,0)
        f=vtk.vtkTransformPolyDataFilter();f.SetInputConnection(cube.GetOutputPort());f.SetTransform(t)
        mapper=vtk.vtkPolyDataMapper();mapper.SetInputConnection(f.GetOutputPort());a=vtk.vtkActor();a.SetMapper(mapper);a.GetProperty().SetColor(.67,.7,.74);a.GetProperty().SetSpecular(.4);ren.AddActor(a)
        other=mesh_actor(OUT/'left.stl');tr=vtk.vtkTransform();tr.Translate(0,0,355);tr.Scale(1,1,-1);other.SetUserTransform(tr);ren.AddActor(other)
    cam=ren.GetActiveCamera();cam.SetPosition(*camera);cam.SetFocalPoint(28,112 if laptop else 74,25 if laptop else 10);cam.SetViewUp(0,1,0);cam.ParallelProjectionOn();cam.SetParallelScale(142 if laptop else 91)
    for pos,intensity in [((150,250,220),.8),((-100,130,100),.6),((50,-100,-150),.4)]:
        light=vtk.vtkLight();light.SetPosition(*pos);light.SetFocalPoint(25,70,8);light.SetIntensity(intensity);ren.AddLight(light)
    ren.ResetCameraClippingRange();rw.Render()
    grab=vtk.vtkWindowToImageFilter();grab.SetInput(rw);grab.SetScale(1);grab.Update();w=vtk.vtkPNGWriter();w.SetFileName(str(OUT/(name+'.png')));w.SetInputConnection(grab.GetOutputPort());w.Write();rw.Finalize()
    im=Image.open(OUT/(name+'.png')).convert('RGB');d=ImageDraw.Draw(im)
    font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    title={'curved_bracket':'Curved CAD candidate — actual geometry','screw_access':'Laptop removed — both screw approaches are clear','installed':'Installed candidate — simplified laptop envelope'}[name]
    d.text((52,35),title,font=ImageFont.truetype(font,34),fill='#253343')
    sub='Ø7 mm bolt holes • Ø15 mm washer seats • Ø16 mm tool corridors' if not laptop else '4.2° outward lean • upper grasp region remains exposed'
    d.text((52,90),sub,font=ImageFont.truetype(font,23),fill='#556476')
    d.text((52,1440),'Native FreeCAD model • prototype candidate • hardware shown as dimensional envelopes',font=ImageFont.truetype(font,18),fill='#556476')
    im.save(OUT/(name+'.jpg'),quality=93);print(OUT/(name+'.jpg'))
render('curved_bracket',(160,155,220))
render('screw_access',(200,135,160),tools=True)
render('installed',(200,185,-500),laptop=True)
