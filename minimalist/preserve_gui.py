"""Restore saved display data after a headless parameter-only FreeCAD save.

Only applies when both documents have exactly the same named objects. Core
geometry and parameters are left byte-for-byte intact; no thumbnail is copied.
"""
from pathlib import Path
import hashlib
import xml.etree.ElementTree as ET
import zipfile


def restore(source, target, force=False):
    source, target = Path(source), Path(target)
    with zipfile.ZipFile(source) as src, zipfile.ZipFile(target) as dst:
        if 'GuiDocument.xml' in dst.namelist() and not force:
            return {'restored': False, 'gui_present': True}
        gui = src.read('GuiDocument.xml')
        providers = {e.get('name') for e in ET.fromstring(gui).iter('ViewProvider')}
        core = dst.read('Document.xml')
        names = {e.get('name') for e in ET.fromstring(core).find('ObjectData')}
        assert providers == names, 'GUI template must match every native object'
        streams = {v for e in ET.fromstring(gui).iter()
                   for k, v in e.attrib.items() if k.lower() == 'file' and v}
        streams.add('GuiDocument.xml')
        # FreeCAD consumes GUI payloads in archive order: XML first, then its
        # binary arrays in the writer's order. Appending XML last loses colors.
        files = {name: src.read(name) for name in src.namelist() if name in streams}
        original = {name: hashlib.sha256(dst.read(name)).hexdigest() for name in dst.namelist()}
        for name, data in files.items():
            assert name not in original or original[name] == hashlib.sha256(data).hexdigest(), name
        core_files = [(name, dst.read(name)) for name in dst.namelist() if name not in files]
    temporary = target.with_suffix('.gui-tmp')
    with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED) as dst:
        for name, data in core_files:
            dst.writestr(name, data)
        for name, data in files.items():
            dst.writestr(name, data)
    temporary.replace(target)
    with zipfile.ZipFile(target) as dst:
        assert dst.testzip() is None
        assert all(hashlib.sha256(dst.read(n)).hexdigest() == h for n, h in original.items())
    return {'restored': True, 'gui_present': True, 'matching_view_providers': len(providers),
            'core_and_existing_streams_unchanged': True,
            'core_sha256': hashlib.sha256(core).hexdigest()}
