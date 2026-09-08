"""Record hashes and verify the delivered Orca project carries the requested setup."""
from pathlib import Path
import json,zipfile,hashlib,re
ROOT=Path(__file__).resolve().parent
with zipfile.ZipFile(ROOT/'orca/curved_review.3mf') as z:
    j=json.loads(z.read('Metadata/project_settings.config'))
    expected={'wall_loops':'3','line_width':'0.4','outer_wall_line_width':'0.4','inner_wall_line_width':'0.4','sparse_infill_density':'20%','sparse_infill_pattern':'gyroid','top_shell_layers':'5','bottom_shell_layers':'5','top_shell_thickness':'1','bottom_shell_thickness':'1','layer_height':'0.2','initial_layer_print_height':'0.2','ensure_vertical_shell_thickness':'ensure_all','enable_support':'0'}
    for k,v in expected.items():assert j[k]==v,(k,j[k],v)
    gcode=z.read('Metadata/plate_1.gcode')
    assert gcode==(ROOT/'orca/plate_1.gcode').read_bytes()
    mass=float(re.search(rb'; filament used \[g\] = ([\d.]+)',gcode).group(1))
files=[p for p in ROOT.rglob('*') if p.is_file() and p.suffix in {'.FCStd','.step','.stl','.3mf','.py','.json','.csv','.jpg','.md','.txt'} and not any(k in p.parts for k in ['work','__pycache__']) and p.name not in ['debug.step','package_manifest.json']]
report={'status':'Fit/print prototype; structural qualification unresolved','orca_embedded_settings_verified':expected,'orca_embedded_gcode_matches_audited_gcode':True,'pair_mass_g':mass,'files':[{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(files)]}
(ROOT/'package_manifest.json').write_text(json.dumps(report,indent=2)+'\n');print('Verified project settings, embedded G-code and',len(files),'file hashes; pair mass',mass)
