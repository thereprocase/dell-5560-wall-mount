"""Retain saved FreeCAD view data when a headless save emits geometry only."""
from pathlib import Path
import copy,hashlib,zipfile,xml.etree.ElementTree as ET

def preserve_gui(source,target):
 source,target=Path(source),Path(target)
 with zipfile.ZipFile(source) as old,zipfile.ZipFile(target) as new:
  geometry={n:new.read(n) for n in new.namelist()}
  assert 'GuiDocument.xml' not in geometry,'Do not overwrite existing GUI edits'
  root=ET.fromstring(old.read('GuiDocument.xml'));providers=root.find('ViewProviderData')
  by_name={p.get('name'):p for p in providers}
  for name,template in [('DuctSocketCorrectionD4','DuctRootR3'),('D4OriginalSocketCutters','D3RightDuct'),('D4ClearPinSockets','D3EndWallRootR1')]:
   assert name not in by_name
   node=copy.deepcopy(by_name[template]);node.set('name',name)
   prop=node.find("Properties/Property[@name='Visibility']/Bool")
   if prop is not None:prop.set('value','false')
   providers.append(node)
  providers.set('Count',str(len(providers)))
  gui={'GuiDocument.xml':ET.tostring(root,encoding='utf-8',xml_declaration=True)}
  for node in root.iter():
   name=node.get('file')
   if name:
    assert name in old.namelist(),name
    gui[name]=old.read(name)
  assert not set(gui)&set(geometry),'GUI resource names must not replace geometry'
  temp=target.with_suffix('.gui-staging.FCStd')
  assert not temp.exists()
  with zipfile.ZipFile(temp,'w',compression=zipfile.ZIP_DEFLATED) as out:
   for name,data in {**geometry,**gui}.items():out.writestr(name,data)
 with zipfile.ZipFile(temp) as check:
  assert check.testzip() is None
  assert all(check.read(name)==data for name,data in geometry.items())
 temp.replace(target)
 return {'geometry_archive_members_unchanged':len(geometry),'gui_archive_members_restored':len(gui),
         'old_view_providers_retained':len(by_name),'new_hidden_view_providers':3,
         'document_xml_sha256':hashlib.sha256(geometry['Document.xml']).hexdigest(),
         'native_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'passed':True}
