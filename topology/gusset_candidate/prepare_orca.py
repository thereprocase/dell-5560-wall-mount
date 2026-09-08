"""Flatten shipped Orca P1S/PETG profiles and apply the user's print settings."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'orca';OUT.mkdir(exist_ok=True)
resources=Path(sys.argv[1]);profiles={}
for p in (resources/'profiles/BBL').rglob('*.json'):
    try:
        j=json.loads(p.read_text())
        if 'name' in j:profiles[j['name']]=j
    except (ValueError,UnicodeDecodeError):pass
def resolve(name,seen=()):
    assert name not in seen
    j=profiles[name];base=resolve(j['inherits'],seen+(name,)) if j.get('inherits') else {}
    return {**base,**j}
machine=resolve('Bambu Lab P1S 0.4 nozzle')
process=resolve('0.20mm Standard @BBL P1P')
filament=resolve('Generic PETG @BBL P1P')
process.update({'name':'Cloud curved PETG 0.20','layer_height':'0.2','initial_layer_print_height':'0.2','wall_loops':'3','line_width':'0.4','outer_wall_line_width':'0.4','inner_wall_line_width':'0.4','top_surface_line_width':'0.4','sparse_infill_line_width':'0.4','internal_solid_infill_line_width':'0.4','initial_layer_line_width':'0.4','sparse_infill_density':'20%','sparse_infill_pattern':'gyroid','top_shell_layers':'5','bottom_shell_layers':'5','top_shell_thickness':'1','bottom_shell_thickness':'1','ensure_vertical_shell_thickness':'ensure_all','wall_generator':'classic','enable_support':'0','brim_type':'no_brim','compatible_printers':[]})
filament.update({'filament_density':['1.27'],'filament_max_volumetric_speed':['8'],'compatible_printers':[]})
for name,j in [('machine',machine),('process',process),('filament',filament)]:
    j.pop('inherits',None);j['from']='User';j['instantiation']='true'
    (OUT/(name+'.json')).write_text(json.dumps(j,indent=2)+'\n')
print(OUT)

# CLI compatibility uses the base machine identity even for flattened profiles.
config = {}
for kind in ['machine','process','filament']:
    config[kind] = json.loads((OUT/(kind+'.json')).read_text())
config['machine'].update(name='Cloud P1S PETG', inherits='Bambu Lab P1S 0.4 nozzle', printer_settings_id='Cloud P1S PETG')
for kind in ['process','filament']:
    config[kind]['compatible_printers']=['Bambu Lab P1S 0.4 nozzle']
    config[kind]['compatible_printers_condition']=''
config['filament']['compatible_prints_condition']=''
config['process']['curr_bed_type']='Textured PEI Plate'
for kind,j in config.items():
    (OUT/(kind+'.json')).write_text(json.dumps(j,indent=2)+'\n')
