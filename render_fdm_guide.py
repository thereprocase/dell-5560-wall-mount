"""Print orientation sheet and four actual mesh sections for the Rev F checkpoint."""
from pathlib import Path
import numpy as np
import trimesh
from PIL import Image,ImageDraw
import cadquery as cq
from build_mount import OUT,PARTS,box
from prepare_prints import orient
from render_preview import render,font

INK='#172838';MUTED='#526472';TEAL='#168887'

def main():
    page=Image.new('RGB',(1800,1620),'#f8f8f8');d=ImageDraw.Draw(page)
    d.text((60,38),'P1S / ASA — PRINT ORIENTATIONS',font=font(37,True),fill=INK)
    d.text((60,94),'Rev F · Orientation is baked into the 3MF/STL files. Retain the short bridges.',font=font(23),fill=MUTED)
    items=[('02_right_cradle','cradle','BRACKETS · OUTER SIDE DOWN','Side down; hollow spine bridges 18 mm.'),
           ('04_right_fan_duct','fan_duct','DUCTS · WIDE INLET DOWN','Open duct; dovetail roofs bridge only 6.6 mm.'),
           ('10_right_fan_tray','fan_tray','FAN TRAYS · GRILLE DOWN','Open top; dovetails grow on sloped flanks.'),
           ('06_right_fan_retainer','fan_retainer','FRONT CAPS · FACE DOWN','Flat bed face with two shallow V-flutes.'),
           ('08_right_outlet_rail','outlet_rail','OUTLET RAILS · LIP DOWN','Arms and slot skin stay within 45° from vertical.')]
    bed=box(0,256,0,256,-2,0).val()
    for i,(name,family,title,subtitle) in enumerate(items):
        x=40+(i%3)*590;y=165+(i//3)*600
        model=orient(cq.importers.importStep(str(PARTS/f'{name}.step')).val(),family)
        pic,_=render([(bed,(216,225,230)),(model,(32,146,148) if family in ('fan_duct','outlet_rail') else (61,79,97))],(560,440),(1.5,2.5,2.4),pad=22)
        page.paste(pic,(x,y));d=ImageDraw.Draw(page)
        d.text((x+10,y+448),title,font=font(20,True),fill=INK)
        d.text((x+10,y+485),subtitle,font=font(17),fill=MUTED)
    x=1230;y=830
    d.text((x,y),'QUICK SETUP',font=font(25,True),fill=TEAL)
    for k,t in enumerate(['0.4 mm nozzle / 0.20 mm layers','6 walls / 6 top + bottom layers','8 mm outer brim / supports off','Print the fit coupon first','Use your matching ASA preset','Check the Bambu slice preview']):
        d.text((x,y+65+k*48),t,font=font(21),fill=INK)
    d.line((60,1390,1740,1390),fill='#ccd4d8',width=2)
    d.text((60,1432),'Five large part families plus four identical push-pins (button down); orientations are supplied.',font=font(23),fill=INK)
    d.text((60,1478),'Every part + 8 mm brim clears the stock plate boundary and front-left cutter exclusion.',font=font(22),fill=MUTED)
    d.text((60,1520),'Geometric layer audit: no floating starts. Physical ASA printing and extrusion-path validation remain pending.',font=font(20),fill=MUTED)
    page.save(OUT/'FDM_Print_Orientations.png')

    # Section slices in the actual supplied print orientations, four useful heights.
    secpage=Image.new('RGB',(1800,1420),'#f8f8f8');dd=ImageDraw.Draw(secpage)
    dd.text((60,38),'FOUR PRINT-LAYER SECTIONS',font=font(37,True),fill=INK)
    dd.text((60,94),'Actual mesh intersections; print height measured from the build plate.',font=font(23),fill=MUTED)
    choices=[('02_right_cradle',10.1,'BRACKET · 10.1 mm','Side profile remains in the layer plane.'),
             ('04_right_fan_duct',2.1,'DUCT · 2.1 mm','Dovetail channels below their short roof bridges.'),
             ('04_right_fan_duct',30.1,'DUCT · 30.1 mm','Open air channel; sloped wall and ear ramp.'),
             ('08_right_outlet_rail',25.1,'OUTLET RAIL · 25.1 mm','Diagonal support grows from the lip-down bed face.')]
    for i,(name,z,title,sub) in enumerate(choices):
        mesh=trimesh.load(OUT/'print_ready'/f'{name}.stl',force='mesh')
        sec=mesh.section_multiplane([0,0,0],[0,0,1],[z])[0]
        x=60+(i%2)*880;y=185+(i//2)*565
        polygons=sec.polygons_full
        bounds=np.array([p.bounds for p in polygons]);lo=bounds[:,:2].min(0);hi=bounds[:,2:].max(0)
        scale=min(770/(hi[0]-lo[0]),385/(hi[1]-lo[1]));center=(lo+hi)/2
        def pts(coords):
            a=(np.array(coords)-center)*scale
            a[:,0]+=x+390;a[:,1]=y+200-a[:,1]
            return [tuple(p) for p in a]
        for p in polygons:
            dd.polygon(pts(p.exterior.coords),fill=TEAL)
            for h in p.interiors:dd.polygon(pts(h.coords),fill='#f8f8f8')
        dd.text((x,y+430),title,font=font(24,True),fill=INK)
        dd.text((x,y+470),sub,font=font(21),fill=MUTED)
    dd.text((60,1334),'Solid regions shown in teal. These are geometric sections, not simulated or measured extrusion paths.',font=font(22),fill=MUTED)
    secpage.save(OUT/'FDM_Sections.png')

if __name__=='__main__':main()
