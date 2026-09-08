"""Illustrate proposed insertion; orange retainers are NOT optimized geometry."""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle,Polygon
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import trimesh
ROOT=Path(__file__).resolve().parent;out=ROOT/'results'
mesh=trimesh.load(out/'faceted25_study.stl',process=False)
fig=plt.figure(figsize=(14,8),facecolor='white')
ax=fig.add_subplot(121,projection='3d')
def block(x,y,z,dx,dy,dz,color,alpha=1):
    b=trimesh.creation.box([dx,dy,dz]);b.apply_translation([x+dx/2,y+dy/2,z+dz/2])
    ax.add_collection3d(Poly3DCollection(b.triangles,facecolor=color,edgecolor='none',alpha=alpha))
# global X=across laptop; Y=wall distance; Z=up
block(-195,-3,-5,390,3,355,'#e3e7eb',.45)
for x in [-155,145]:
    verts=mesh.vertices[:,[2,0,1]].copy();verts[:,0]+=x
    ax.add_collection3d(Poly3DCollection(verts[mesh.faces],facecolor='#28a498',edgecolor='none'))
    block(x,56,90,10,4,12,'#f59b3a')
block(-172.2,38,90,344.4,18,230.3,'#647991',.32)
for x in [-125,125]:ax.quiver(x,50,365,0,0,-40,color='#c42b3f',arrow_length_ratio=.25,linewidth=2)
ax.set(xlim=(-200,200),ylim=(-10,100),zlim=(-10,380));ax.set_box_aspect((400,110,390));ax.view_init(elev=17,azim=-64);ax.set_axis_off();ax.set_title('Proposed installed arrangement',fontsize=16,pad=10)
ax2=fig.add_subplot(122)
ax2.add_patch(Rectangle((-6,0),6,205,fc='#e3e7eb'))
# reconstruct profile from projection of top triangles
for t in mesh.triangles:
    if np.all(t[:,2]>9.99):ax2.add_patch(Polygon(t[:,:2],fc='#28a498',ec='none'))
ax2.add_patch(Rectangle((38,90),18,100,fc='#dbe4ed',ec='#647991',lw=2))
ax2.text(47,145,'LAPTOP',ha='center',rotation=90,fontsize=13,color='#354b65')
ax2.add_patch(Rectangle((56,90),4,12,fc='#f59b3a'))
ax2.annotate('Lower straight down',xy=(47,193),xytext=(47,220),ha='center',fontsize=12,arrowprops={'arrowstyle':'->','color':'#c42b3f','lw':2},color='#c42b3f')
ax2.annotate('Bottom edge rests here',xy=(46,90),xytext=(76,116),fontsize=12,arrowprops={'arrowstyle':'->','color':'#334155'},color='#334155')
ax2.annotate('Proposed front lip\n(not in study STL)',xy=(59,98),xytext=(76,76),fontsize=12,arrowprops={'arrowstyle':'->','color':'#a55c14'},color='#a55c14')
ax2.annotate('Air gap',xy=(24,145),xytext=(12,171),fontsize=12,arrowprops={'arrowstyle':'->','color':'#64748b'},color='#64748b')
ax2.text(-10,150,'WALL',rotation=90,ha='center',color='#64748b')
ax2.set(xlim=(-16,148),ylim=(-5,235),aspect='equal');ax2.set_axis_off();ax2.set_title('Side section: the laptop stays above the bracket',fontsize=14)
fig.suptitle('How insertion would work — concept illustration',fontsize=21,y=.96)
fig.text(.5,.035,'Teal = optimized support   ·   Blue = laptop   ·   Orange = proposed retention\nFasteners, side stops and anti-tip retention still need design. This is not an assembly-ready mount.',ha='center',fontsize=12,color='#475569')
fig.subplots_adjust(left=.02,right=.98,top=.88,bottom=.12,wspace=.05)
fig.savefig(out/'insertion_concept.png',dpi=180,facecolor='white')
