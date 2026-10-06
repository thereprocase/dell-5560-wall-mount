import sys,json,math
from pathlib import Path
import FreeCAD as A,Part
r=Path(__file__).resolve().parent;sys.path.insert(0,A.getResourceDir()+"Mod/Assembly")
d=A.openDocument(str(r/'FinishValidation.FCStd'));g=d.getObject('FlowInnerBlend')
report={'invalid':[o.Name for o in d.Objects if 'Invalid' in o.State],'valid':g.Shape.isValid(),'solids':len(g.Shape.Solids),'small_faces':sum(x.Area<.1 for x in g.Shape.Faces),'gaps':{},'interference':{},'new_curves':[]}
links={o.InstanceKey:o for o in d.getObject('InstalledAssembly').Group if o.TypeId=='App::Link'}
for keys in [['04_right_fan_duct','06_right_fan_retainer','10_right_fan_tray'],['03_left_fan_duct','05_left_fan_retainer','09_left_fan_tray']]:
 for i,j in [(0,1),(0,2),(1,2)]:report['gaps'][keys[i]+' / '+keys[j]]=links[keys[i]].Shape.distToShape(links[keys[j]].Shape)[0]
for k,o in links.items():
 if 'fan_duct' not in k:continue
 for k2,o2 in links.items():
  if k==k2 or 'push_pin' in k2:continue
  if o.Shape.BoundBox.intersect(o2.Shape.BoundBox):
   vol=o.Shape.common(o2.Shape).Volume
   if vol>1e-5:report['interference'][k+' / '+k2]=vol
for face in g.Shape.Faces:
 if type(face.Surface).__name__!='Cylinder' or face.BoundBox.XLength<100 or round(face.Surface.Radius) not in (12,14):continue
 u0,u1,v0,v1=face.ParameterRange;th=[];ang=[]
 for j in range(1,40):
  u=u0+(u1-u0)*j/40;v=(v0+v1)/2;p=face.valueAt(u,v);n=face.normalAt(u,v);th.append(sum(e.Length for e in Part.makeLine(p-n*.001,p-n*6).common(g.Shape).Edges)+.001)
  nz=(n.z-n.y)/math.sqrt(2);ang.append(math.degrees(math.asin(max(0,-nz))))
 report['new_curves'].append({'radius':face.Surface.Radius,'min_sampled_wall_mm':min(th),'max_downward_overhang_from_vertical_deg':max(ang)})
report['pass']=not report['invalid'] and report['valid'] and report['solids']==1 and not report['interference'] and all(abs(x-.3)<1e-5 for x in report['gaps'].values()) and min(c['min_sampled_wall_mm'] for c in report['new_curves'])>1.5 and max(c['max_downward_overhang_from_vertical_deg'] for c in report['new_curves'])<=45
(r/'flow_validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2),flush=True);assert report['pass'];A.closeDocument(d.Name)
