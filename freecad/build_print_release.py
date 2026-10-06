from pathlib import Path
import json,hashlib,shutil,zipfile,xml.etree.ElementTree as E
import FreeCAD as A,Mesh
ROOT=Path(__file__).resolve().parent;OUT=ROOT.parent/'print_release';OUT.mkdir(exist_ok=True)
manifest={'revision':'H','native_model':'freecad/Precision_5560_Native.FCStd','native_sha256':hashlib.sha256((ROOT/'Precision_5560_Native.FCStd').read_bytes()).hexdigest(),'machine':'Bambu P1S','material':'ASA','nozzle_mm':.4,'layer_mm':.2,'parts':{}}
keys=json.loads((ROOT/'assembly_native_validation.json').read_text())['parts']
ns='http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
for key in keys:
 revised=any(t in key for t in ['fan_duct','fan_tray','outlet_rail']);src=(ROOT/'print_refinements_oriented' if revised else ROOT.parent/'print_ready')/(key+'.stl')
 dst=OUT/src.name;shutil.copy2(src,dst);mesh=Mesh.Mesh(str(dst));assert mesh.isSolid(),key
 if revised:
  vertices,faces=mesh.Topology;model=E.Element('model',{'unit':'millimeter','xml:lang':'en-US','xmlns':ns});resources=E.SubElement(model,'resources');obj=E.SubElement(resources,'object',{'id':'1','type':'model','name':key});m=E.SubElement(obj,'mesh');vs=E.SubElement(m,'vertices');ts=E.SubElement(m,'triangles')
  for v in vertices:E.SubElement(vs,'vertex',dict(zip(['x','y','z'],[format(x,'.9g') for x in v])))
  for f in faces:E.SubElement(ts,'triangle',dict(zip(['v1','v2','v3'],[str(i) for i in f])))
  E.SubElement(E.SubElement(model,'build'),'item',{'objectid':'1'})
  with zipfile.ZipFile(OUT/(key+'.3mf'),'w',zipfile.ZIP_DEFLATED) as z:
   z.writestr('3D/3dmodel.model',E.tostring(model,encoding='utf-8',xml_declaration=True));z.writestr('[Content_Types].xml','<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>');z.writestr('_rels/.rels','<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
 else:shutil.copy2(ROOT.parent/'print_ready'/(key+'.3mf'),OUT/(key+'.3mf'))
 with zipfile.ZipFile(OUT/(key+'.3mf')) as z:assert z.testzip() is None
 b=mesh.BoundBox;assert b.XMin>=7.99 and b.YMin>=7.99 and b.XMax<=248.01 and b.YMax<=248.01 and b.ZMax<=256
 assert b.XMin-8>=18 or b.YMin-8>=28
 files={suffix:hashlib.sha256((OUT/(key+suffix)).read_bytes()).hexdigest() for suffix in ['.stl','.3mf']}
 manifest['parts'][key]={'revised':revised,'printed_arm_frozen':'cradle' in key,'closed_mesh':True,'dimensions_mm':[b.XLength,b.YLength,b.ZLength],'sha256':files}
assert len(manifest['parts'])==14
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
(OUT/'README.md').write_text("""# Revision H - preserved ducted prototype print set

Print one each of 01-14. STL and 3MF are alternatives for the same part; do not
print both formats. Standard 3MF models contain millimeter geometry and baked
orientation, not slicer settings or G-code.

This is the preserved Rev H prototype print set. Original root print_ready/ and Fusion/Onshape
ports remain Revision F baseline/history. Six parts are revised: ducts, trays,
and outlet rails. Both cradle/arm files are byte-identical to the already-printed
Revision F files. Caps and four pins are also unchanged.

P1S / ASA: 0.4 mm nozzle, 0.20 mm layers, 6 walls, 6 top/bottom layers, 100% fill
of the explicitly hollow CAD, 8 mm outer brim, supports off. Cradles outer-side
down with the supplied diagonal rotation; ducts inlet down; trays grille down;
caps front down; rails lip down; pins button down. Keep the baked orientations.

Fan-interface and rail-to-arm clearances measure 0.30 mm. Pin retention keeps
its intentional interference; fixed load shoulders retain seating contact.
Separate native loft-skin patches close the unintended duct-wall notches.
Revision H adds three R12 tangent airway blends per duct with two R14 exterior
support blends. Inlet and outlet profiles remain fixed. Sampled new bend walls
are at least 1.60 mm; sampled new curved overhangs stay below 40 degrees in the
inlet-down orientation. Cooling performance is not yet physically validated.

Final checks: valid native solids, constrained sketches, unchanged printed arms,
wall continuity, assembly/service clearances, closed meshes, and bed/brim/cutter
fit. Both duct toolpaths were checked with Bridge direction and Internal bridge
direction 180 degrees; Relative bridge angle and Align infill direction to
model off. See ../print_release_step/ORCA_BRIDGE_REVIEW.txt. Physical fit, ASA
bridge quality and retention remain to be checked. Use the root P1S_ASA_Print_Guide.md for material and assembly guidance.
Original fit coupons remain under print_ready/; full-length tray fit needs its
own check because the revised flank clearance is normal to the dovetail slope.

See manifest.json for hashes tying this print set to the native FCStd document.
""",encoding='utf-8')
with zipfile.ZipFile(ROOT.parent/'Precision_5560_RevH_Print_Set.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(OUT.iterdir()):
  if p.is_file():z.write(p,'Revision_H/'+p.name)
print('Revision H: 14 closed oriented parts, 28 model files, frozen arm bytes retained',flush=True)
