"""Orthographic preview rasterized directly from the exported STEP B-reps.
No generated imagery. Z-buffer rendering uses only numpy and Pillow.
"""
from pathlib import Path
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import cadquery as cq
from build_mount import OUT, PARTS, box, cyl, laptop_reference, fan_reference, fastener_interfaces

FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
def font(n,bold=False):
    return ImageFont.truetype(BOLD if bold else FONT,n)

def render(objects,size,camvec,target=None,pad=25):
    cam=np.array(camvec,dtype=float);cam/=np.linalg.norm(cam)
    right=np.cross(cam,[0,0,1.]);right/=np.linalg.norm(right)
    up=np.cross(right,cam)
    basis=np.array([right,up,cam]).T
    meshes=[]
    for shape,color in objects:
        vs,fs=shape.tessellate(.35,.2)
        vertices=np.array([v.toTuple() for v in vs])
        triangles=vertices[np.array(fs)]
        meshes.append((triangles,np.array(color,dtype=float)))
    allpts=np.concatenate([t.reshape(-1,3) for t,c in meshes])@basis
    lo=allpts[:,:2].min(0);hi=allpts[:,:2].max(0)
    scale=min((size[0]-2*pad)/(hi[0]-lo[0]),(size[1]-2*pad)/(hi[1]-lo[1]))
    center=(lo+hi)/2
    def project(points):
        pts=np.array(points)@basis
        pts[...,:2]=(pts[...,:2]-center)*scale
        pts[...,0]+=size[0]/2
        pts[...,1]=size[1]/2-pts[...,1]
        return pts
    pix=np.full((size[1],size[0],3),248,dtype=np.uint8)
    dep=np.full((size[1],size[0]),-np.inf,dtype=np.float32)
    normbuf=np.zeros((size[1],size[0],3),dtype=np.float32)
    light=np.array([-.3,.5,1]);light/=np.linalg.norm(light)
    for triangles,color in meshes:
        for tri in triangles:
            normal=np.cross(tri[1]-tri[0],tri[2]-tri[0])
            nl=np.linalg.norm(normal)
            if nl<1e-8:continue
            normal/=nl
            if np.dot(normal,cam)<0:normal=-normal
            p=project(tri)
            x0=max(0,int(np.floor(p[:,0].min())));x1=min(size[0]-1,int(np.ceil(p[:,0].max())))
            y0=max(0,int(np.floor(p[:,1].min())));y1=min(size[1]-1,int(np.ceil(p[:,1].max())))
            if x0>x1 or y0>y1:continue
            a,b,c=p
            det=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
            if abs(det)<1e-8:continue
            yy,xx=np.mgrid[y0:y1+1,x0:x1+1]
            xx=xx+.5;yy=yy+.5
            w0=((b[1]-c[1])*(xx-c[0])+(c[0]-b[0])*(yy-c[1]))/det
            w1=((c[1]-a[1])*(xx-c[0])+(a[0]-c[0])*(yy-c[1]))/det
            w2=1-w0-w1
            z=w0*a[2]+w1*b[2]+w2*c[2]
            old=dep[y0:y1+1,x0:x1+1]
            mask=(w0>=-1e-7)&(w1>=-1e-7)&(w2>=-1e-7)&(z>old)
            old[mask]=z[mask]
            shade=.58+.38*max(0,np.dot(normal,light))+.10*max(0,np.dot(normal,cam))
            rgb=np.clip(color*shade,0,255).astype(np.uint8)
            pix[y0:y1+1,x0:x1+1][mask]=rgb
            normbuf[y0:y1+1,x0:x1+1][mask]=normal
    # Crisp boundaries at real surface discontinuities, without triangle lines.
    edge=np.zeros(dep.shape,dtype=bool)
    for axis in (0,1):
        d2=np.roll(dep,1,axis);n2=np.roll(normbuf,1,axis)
        finite=np.isfinite(dep)&np.isfinite(d2)
        jump=np.zeros(dep.shape,dtype=bool)
        jump[finite]=(np.abs(dep[finite]-d2[finite])>1.3)|((normbuf[finite]*n2[finite]).sum(-1)<.78)
        edge|=jump
    pix[edge]=(pix[edge]*.68).astype(np.uint8)
    return Image.fromarray(pix),project

def arrow(draw,start,end,color,width=5):
    a=np.array(start,dtype=float);b=np.array(end,dtype=float)
    d=b-a;d/=np.linalg.norm(d);p=np.array([-d[1],d[0]])
    draw.line([tuple(a),tuple(b)],fill=color,width=width)
    draw.polygon([tuple(b),tuple(b-15*d+6*p),tuple(b-15*d-6*p)],fill=color)

def main():
    shapes=[(p.stem,cq.importers.importStep(str(p)).val()) for p in sorted(PARTS.glob('*.step'))]
    holder=[(s,(32,146,148) if any(k in n for k in ['duct','rail']) else (61,79,97)) for n,s in shapes]
    laptop=laptop_reference().val();fans=[(fan_reference(x).val(),(48,51,57)) for x in [-70,70]]
    hardware=[(cyl(7,3,(x,10,z)).val(),(164,174,180)) for x in [-162,162] for z in [-36,174]]
    page=Image.new('RGB',(1800,1450),'#f8f8f8');d=ImageDraw.Draw(page)
    d.text((60,35),'PRECISION 5560 / REV F',font=font(45,True),fill='#172838')
    d.text((60,99),'Shrouded plenum · 45° fan modules · Four wall bolts',font=font(28),fill='#526472')
    pic,pr=render(holder+fans+hardware+[(laptop,(190,198,207))],(1000,980),(1.3,2.8,1.1),pad=45);page.paste(pic,(20,170))
    pic2,_=render(holder+hardware,(740,960),(-1.8,2.9,1.3),pad=35);page.paste(pic2,(1030,180));d=ImageDraw.Draw(page)
    d.text((70,1150),'INSTALLED / LIFT UP TO REMOVE',font=font(25,True),fill='#172838')
    d.text((1060,1150),'CHEEKS CONTAIN THE REAR FLOW',font=font(23,True),fill='#172838')
    d.text((70,1200),'Keyed CA joints carry the fixed assembly; split push-pins retain removable fan caps.',font=font(25),fill='#526472')
    d.text((70,1245),'Cradles print on their outer sides. Ducts print fan-inlet down. Only the wall bolts need tools.',font=font(24),fill='#526472')
    d.text((70,1300),'94 mm tines | 40 mm rear gap | 12 mm nominal slot | 8 / 16 mm alternate rails',font=font(26,True),fill='#168887')
    d.text((70,1370),'Exact CAD rendering. Laptop/fan envelopes simplified. CFD is a 2D design screen; physical validation remains pending.',font=font(21),fill='#526472')
    page.save(OUT/'Precision_5560_Wall_Mount_Preview.png')
    # Actual exploded assembly, offset parts along their removal/assembly directions.
    exp=[]
    for n,s in shapes:
        if 'cradle' in n:shift=(0,0,0)
        elif 'outlet_rail' in n:shift=(0,50,25)
        elif 'fan_duct' in n:shift=(0,40,0)
        elif 'fan_tray' in n:shift=(0,72,-32)
        elif 'fan_retainer' in n:shift=(0,108,-14)
        else:shift=(0,123,-20)
        exp.append((s.translate(shift),(32,146,148) if 'duct' in n or 'rail' in n else (61,79,97)))
    im,_=render(exp,(1650,1200),(1.5,3,1.4),pad=60)
    p=Image.new('RGB',(1800,1420),'#f8f8f8');p.paste(im,(75,130));dd=ImageDraw.Draw(p)
    dd.text((60,35),'TOOL-FREE / CA ASSEMBLY',font=font(41,True),fill='#172838')
    dd.text((60,96),'Dry-fit the printed keys. Glue fixed joints. Keep the fan caps and split pins removable.',font=font(25),fill='#526472')
    dd.text((60,1350),'Exploded illustration; assembly guide gives the order. Four printed pins replace all fan-cap screws.',font=font(23),fill='#526472')
    p.save(OUT/'Tool_Free_Assembly.png')

if __name__=='__main__':main()
