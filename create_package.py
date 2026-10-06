"""Save the reproducible Revision F CAD/print/CFD checkpoint with SHA-256 manifest."""
from pathlib import Path
import hashlib,json,zipfile
OUT=Path(__file__).resolve().parent;NAME='Precision_5560_Wall_Mount_Package.zip'
def main():
 files=[]
 for p in sorted(OUT.rglob('*')):
  if not p.is_file() or any(x in p.parts for x in ['__pycache__','.git','.venv']):continue
  rel=p.relative_to(OUT)
  if p.name in [NAME,'package_manifest.json'] or p.name.endswith('_log.txt') or p.name=='build_log.txt':continue
  if rel.parts[0]=='cfd' or p.suffix in ['.step','.3mf','.stl','.png','.jpg','.pdf','.md','.json','.py','.txt'] or p.name in ['.gitignore','LICENSE']:files.append(p)
 assert len(list((OUT/'parts').glob('*.step')))==14
 assert len(list((OUT/'outlet_gap_variants').glob('*.step')))==4
 assert len(list((OUT/'print_ready').glob('*.3mf')))==23
 g=json.loads((OUT/'geometry_validation.json').read_text());a=json.loads((OUT/'assembly_validation.json').read_text());l=json.loads((OUT/'layer_support_audit.json').read_text())
 assert g['revision']==l['revision']=='F' and g['step_reimport_solids']==14
 assert all(v<.01 for k,v in a.items() if k.endswith('_mm3'))
 assert all(not r['new_islands_above_bed'] and r['maximum_sampled_reach_from_support_mm']<10 for r in l['parts'].values())
 cf=json.loads((OUT/'cfd/results.json').read_text());assert len(cf)==8 and all(r['mass_imbalance_percent']<.001 for r in cf)
 manifest={'revision':'F','checkpoint_date':'2026-09-07','files':[{'path':p.relative_to(OUT).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]}
 m=OUT/'package_manifest.json';m.write_text(json.dumps(manifest,indent=2));files.append(m)
 with zipfile.ZipFile(OUT/NAME,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in files:z.write(p,p.relative_to(OUT))
 with zipfile.ZipFile(OUT/NAME) as z:
  assert z.testzip() is None
  for i in manifest['files']:assert hashlib.sha256(z.read(i['path'])).hexdigest()==i['sha256']
 print(json.dumps({'revision':'F','files':len(files),'bytes':(OUT/NAME).stat().st_size,'archive_and_hashes':'passed'}))
if __name__=='__main__':main()
