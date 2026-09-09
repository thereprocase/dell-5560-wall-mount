"""Replace only duct geometry in the checked D3 Orca project templates."""
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
NS = '{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}'
ET.register_namespace('', NS[1:-1])
ET.register_namespace('p', 'http://schemas.microsoft.com/3dmanufacturing/production/2015/06')
(OUT / 'prepared').mkdir(exist_ok=True)
for key in ('03_left_fan_duct', '04_right_fan_duct'):
    with zipfile.ZipFile(OUT / 'print' / (key + '.3mf')) as archive:
        mesh = ET.fromstring(archive.read('3D/3dmodel.model')).find('.//' + NS + 'mesh')
    template = OUT / 'baseline/prepared' / (key + '.3mf')
    with zipfile.ZipFile(template) as old, zipfile.ZipFile(
            OUT / 'prepared' / (key + '.3mf'), 'w', zipfile.ZIP_DEFLATED) as new:
        top = ET.fromstring(old.read('3D/3dmodel.model'))
        component = next(c for c in top.iter(NS + 'component') if c.get('objectid') == '1')
        assert component.get('transform') == '1 0 0 0 1 0 0 0 1 0 0 0'
        path = next(v.lstrip('/') for k, v in component.attrib.items() if k.endswith('}path'))
        model = ET.fromstring(old.read(path))
        part = next(obj for obj in model.find(NS + 'resources') if obj.get('id') == '1')
        part.remove(part.find(NS + 'mesh'))
        part.append(mesh)
        settings = ET.fromstring(old.read('Metadata/model_settings.config'))
        for item in settings.iter('metadata'):
            if item.get('key') == 'name' and 'fan_duct' in item.get('value', ''):
                item.set('value', key + ' / D4 clear pin sockets')
        replacement = {
            path: ET.tostring(model, encoding='utf-8', xml_declaration=True),
            'Metadata/model_settings.config': ET.tostring(settings, encoding='utf-8', xml_declaration=True),
        }
        for name in old.namelist():
            if not name.endswith(('.gcode', '.gcode.md5')):
                new.writestr(name, replacement.get(name, old.read(name)))
    print('Prepared ' + key, flush=True)
