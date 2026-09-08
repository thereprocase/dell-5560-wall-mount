"""Render actual voxel geometry, preserving the slot and the printing direction."""
import sys,importlib.util
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import trimesh

def load_study(folder):
    spec=importlib.util.spec_from_file_location('slot_study',Path(folder)/'study.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def mesh_from_ids(m,ids):
    nodes,els,_=m.grid();ids=set(ids);faces=[]
    sides=[(-1,[0,4,7,3]),(1,[1,2,6,5]),(-m.NX,[0,1,5,4]),(m.NX,[3,7,6,2]),(-m.NX*m.NY,[0,3,2,1]),(m.NX*m.NY,[4,5,6,7])]
    for e in ids:
        i=(e-1)%m.NX;j=((e-1)//m.NX)%m.NY;k=(e-1)//(m.NX*m.NY)
        bounds=[i==0,i==m.NX-1,j==0,j==m.NY-1,k==0,k==m.NZ-1]
        for boundary,(delta,q) in zip(bounds,sides):
            if boundary or e+delta not in ids:
                f=[els[e][n] for n in q];faces.extend([[f[0],f[1],f[2]],[f[0],f[2],f[3]]])
    used=sorted(set(n for f in faces for n in f));lookup={n:i for i,n in enumerate(used)}
    mesh=trimesh.Trimesh([nodes[n] for n in used],[[lookup[n] for n in f] for f in faces],process=True)
    return mesh

def read_ids(p):
    rows=np.genfromtxt(p,delimiter=',',names=True);return {int(r['element_number']) for r in rows if int(r['element_state'])==1}

def draw(m,ids,out,title):
    mesh=mesh_from_ids(m,ids);fig=plt.figure(figsize=(12,7),facecolor='white')
    for pos,elev,azim,name in [(121,53,-65,'Print-bed view: slot opens upward in the image'),(122,14,-102,'Low view: see into the actual slot')]:
        ax=fig.add_subplot(pos,projection='3d');norm=mesh.face_normals
        colors=['#5bc3b4' if n[2]>.5 else '#20796f' if abs(n[0])>.5 else '#359d91' for n in norm]
        ax.add_collection3d(Poly3DCollection(mesh.triangles,facecolors=colors,edgecolors='none'))
        ax.set(xlim=(0,m.NX*2),ylim=(0,100),zlim=(0,14));ax.set_box_aspect((m.NX*2,100,20));ax.view_init(elev=elev,azim=azim);ax.set_axis_off();ax.set_title(name,fontsize=11)
    fig.suptitle(title,fontsize=18,y=.97)
    fig.text(.5,.035,'Actual 3D model • bottom seat at 6 mm • slot extends to 96 mm • print build direction through 12 mm width',ha='center',fontsize=11,color='#475569')
    fig.subplots_adjust(left=.02,right=.98,bottom=.08,top=.89,wspace=.05);fig.savefig(out,dpi=165,facecolor='white');plt.close(fig)

if __name__=='__main__':
    folder=Path(sys.argv[1]).resolve();m=load_study(folder)
    p=Path(sys.argv[2]) if len(sys.argv)>2 else None
    ids=read_ids(p) if p else m.grid()[1].keys()
    out=folder/'results'/('live.png' if p else 'initial_3d.png');out.parent.mkdir(exist_ok=True)
    draw(m,ids,out,'Slot-inclusive 3D topology — '+('current retained elements' if p else 'initial design envelope'))
    print(out)
