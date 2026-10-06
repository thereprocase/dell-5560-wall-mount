from pathlib import Path
import json,re
import numpy as np
from cfd_study import ROOT

def vals(text):
 m=re.search(r'value\s+nonuniform\s+List<scalar>\s+\d+\s*\((.*?)\)',text,re.S)
 if m:return np.fromstring(m[1],sep=' ')
 m=re.search(r'value\s+uniform\s+([-+\deE.]+)',text)
 return np.array([float(m[1])]) if m else None

def patch(path,n):
 text=path.read_text();m=re.search(r'\b'+n+r'\s*\{(.*?)\}',text,re.S);v=vals(m[1])
 if v is not None:return v
 # zeroGradient pressure equals the adjacent owner-cell value.
 mesh=path.parent.parent/'constant/polyMesh'
 boundary=(mesh/'boundary').read_text();b=re.search(r'\b'+n+r'\s*\{(.*?)\}',boundary,re.S)[1]
 count=int(re.search(r'nFaces\s+(\d+)',b)[1]);start=int(re.search(r'startFace\s+(\d+)',b)[1])
 ownertext=(mesh/'owner').read_text();owner=np.fromstring(re.search(r'\n\d+\s*\((.*?)\)',ownertext,re.S)[1],sep=' ',dtype=int)
 internal=np.fromstring(re.search(r'internalField\s+nonuniform\s+List<scalar>\s+\d+\s*\((.*?)\)',text,re.S)[1],sep=' ')
 return internal[owner[start:start+count]]

def analyze(c):
 ts=sorted([p for p in c.iterdir() if p.is_dir() and p.name.replace('.','').isdigit() and float(p.name)>0],key=lambda p:float(p.name))
 if not ts:return None
 params=json.loads((c/'case_parameters.json').read_text());rho=params['rho'];t=ts[-1]
 f={n:float(patch(t/'phi',n).sum()) for n in ['fanInlet','slotOutlet','laptopVent']}
 p=patch(t/'p','laptopVent')*rho
 log=(c/'simpleFoam.log').read_text();conv='SIMPLE solution converged' in log
 residuals={n:float(re.findall(r'Solving for '+n+r', Initial residual = ([\deE+.-]+)',log)[-1]) for n in ['Ux','Uy','p','k','omega']}
 pp=float((patch(ts[-2]/'p','laptopVent')*rho).mean()) if len(ts)>1 else float(p.mean())
 return {**params,'last_iteration':float(t.name),'residual_control_met':conv,'last_initial_residuals':residuals,'intake_pressure_mean_Pa':float(p.mean()),'intake_pressure_min_Pa':float(p.min()),'intake_pressure_max_Pa':float(p.max()),'last_saved_pressure_change_percent':100*abs(float(p.mean())-pp)/max(abs(float(p.mean())),.01),'flow_per_1mm_span_m3_s':f,'mass_imbalance_percent':100*abs(sum(f.values()))/abs(f['fanInlet']),'slot_exit_mean_velocity_m_s':f['slotOutlet']/(params['gap_mm']*1e-6)}
if __name__=='__main__':
 out=[]
 for c in sorted(ROOT.iterdir()):
  if c.is_dir() and (c/'case_parameters.json').exists() and c.name!='curved_12_coarse':
   a=analyze(c)
   if a:out.append(a)
 (ROOT/'results.json').write_text(json.dumps(out,indent=2))
 for a in out:print(a['name'],round(a['intake_pressure_mean_Pa'],3),round(a['slot_exit_mean_velocity_m_s'],3),a['residual_control_met'],round(a['mass_imbalance_percent'],5),round(a['last_saved_pressure_change_percent'],3))
