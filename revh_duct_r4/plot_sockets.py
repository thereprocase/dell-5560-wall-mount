"""Plot actual old/new G-code centerlines at one formerly blocked socket."""
from pathlib import Path
import sys,tempfile,zipfile
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
O=Path(__file__).resolve().parent
sys.path.insert(0,str(O/'tools'))
from support_audit import read_paths
fig,axes=plt.subplots(1,2,figsize=(10,6),sharex=True,sharey=True)
key='04_right_fan_duct'
for ax,root,title in zip(axes,[O/'baseline',O],['Before D4: shell crosses the socket','D4: the same passage is clear']):
 with tempfile.TemporaryDirectory() as folder:
  path=Path(folder)/'preview.gcode'
  with zipfile.ZipFile(root/'slices'/key/(key+'.gcode.3mf')) as z:path.write_bytes(z.read(next(n for n in z.namelist() if n.endswith('.gcode'))))
  layers,_=read_paths(path)
 for points,width,feature in layers[6.8]:
  x=[p[0]-44.75 for p in points];depth=[193.85-(p[1]+2) for p in points]
  if min(x)>5 or max(x)<-5 or min(depth)>10 or max(depth)<-2:continue
  ax.plot(x,depth,color='#245e84' if not feature.startswith('Support') else '#b43535',lw=1.1)
 ax.add_patch(Rectangle((-2.05,0),4.1,7.7,fill=False,ls='--',lw=1.5,color='#008a83'))
 ax.set_title(title,fontsize=12,pad=12);ax.set_xlim(-5,5);ax.set_ylim(10,-2);ax.set_aspect('equal');ax.grid(alpha=.15)
 ax.set_xlabel('Across socket center (mm)')
axes[0].set_ylabel('Depth from socket face (mm)')
fig.suptitle('Actual Orca toolpath centerlines · Z = 6.8 mm',fontsize=15,y=.98)
fig.text(.5,.015,'Dashed: nominal blind bore. Coordinates include the configured +2 mm Y extruder offset.',ha='center',fontsize=10)
fig.tight_layout(rect=(0,.045,1,.95))
fig.savefig(O/'images/socket-before-after.png',dpi=170)
