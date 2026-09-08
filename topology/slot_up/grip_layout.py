"""Dimensioned side view of the actual tilted slot and laptop envelope."""
from pathlib import Path
import math,json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as Patch
from shapely.geometry import Polygon
from shapely.ops import unary_union
from render_model import load_study

ROOT=Path(__file__).resolve().parent
m=load_study(ROOT/'tilted_grip')
nodes,els,_=m.grid()
shape=unary_union([Polygon([nodes[n][:2] for n in ns[:4]]) for ns in els.values()])
def p(x,s):return m.transform(x,6+s,0)[:2]
rear0=p(21,0);rear1=p(21,m.LAPTOP_HEIGHT-80);rear2=p(21,m.LAPTOP_HEIGHT)
fig,ax=plt.subplots(figsize=(9,11));fig.patch.set_facecolor('white')
ax.axvspan(-6,0,color='#cbd5e1')
for poly in [shape] if shape.geom_type=='Polygon' else shape.geoms:
    ax.add_patch(Patch(list(poly.exterior.coords),color='#43aa98',alpha=.8))
ax.add_patch(Patch([p(21,0),p(41,0),p(41,m.LAPTOP_HEIGHT),p(21,m.LAPTOP_HEIGHT)],facecolor='#dfe6ef',edgecolor='#334155',linewidth=2))
ax.add_patch(Patch([(0,rear1[1]),rear1,rear2,(0,rear2[1])],facecolor='#f8cd69',alpha=.55))
def dim(x,y,label,offset=0):
    ax.annotate('',xy=(x,y),xytext=(0,y),arrowprops={'arrowstyle':'<->','color':'#334155','lw':1.4})
    ax.text(x/2,y+offset,label,ha='center',va='bottom',fontsize=11)
dim(rear1[0],rear1[1],'32 mm minimum',3)
dim(rear2[0],rear2[1],f'{rear2[0]:.1f} mm',3)
dim(rear0[0],rear0[1]-11,f'{rear0[0]:.1f} mm',-10)
ax.text(67,198,'Upper 80 mm:\nreserved grasp region',fontsize=12,va='center')
ax.annotate('',xy=(24,198),xytext=(65,198),arrowprops={'arrowstyle':'->','color':'#475569'})
ax.text(70,105,'Slot and seat lean\ntogether by '+f'{math.degrees(m.ANGLE):.2f}°',fontsize=12)
ax.annotate('',xy=(32,84),xytext=(70,102),arrowprops={'arrowstyle':'->','color':'#475569'})
ax.text(70,49,'Green: initial bracket envelope\nGrey: 20 mm laptop envelope\n22 mm slot: 1 mm nominal\nclearance on each face',fontsize=10,color='#475569')
a=p(46,110);b=p(46,143)
ax.annotate('',xy=b,xytext=a,arrowprops={'arrowstyle':'->','color':'#18786a','lw':3})
ax.text(67,135,'Lift along the slot',fontsize=11,color='#18786a')
ax.text(-8,125,'WALL',rotation=90,ha='center',color='#64748b')
ax.set_aspect('equal');ax.set_xlim(-15,157);ax.set_ylim(-25,265);ax.axis('off')
ax.set_title('Finger clearance where you grip\nBottom closer to the wall; top gently leans out',fontsize=17,pad=15)
fig.text(.5,.025,'Dimensioned geometry • 230.3 mm laptop height • clearance target informed by NASA handle guidance; physical fit unverified',ha='center',fontsize=8)
out=ROOT/'tilted_grip/results';out.mkdir(exist_ok=True)
fig.savefig(out/'grip_layout.png',dpi=150,bbox_inches='tight');plt.close(fig)
(out/'grip_dimensions.json').write_text(json.dumps({'tilt_deg':math.degrees(m.ANGLE),'laptop_height_mm':m.LAPTOP_HEIGHT,'grip_length_mm':80,'rear_clearance_bottom_mm':rear0[0],'rear_clearance_grip_start_mm':rear1[0],'rear_clearance_top_mm':rear2[0],'slot_width_normal_mm':22,'laptop_thickness_mm':20,'status':'geometric clearances; physical grip unverified'},indent=2)+'\n')
assert abs(rear1[0]-32)<1e-8
assert rear2[0]>rear1[0]
print(out/'grip_layout.png')
