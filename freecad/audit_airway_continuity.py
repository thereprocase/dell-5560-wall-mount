from pathlib import Path
import json
import FreeCAD as A, FreeCADGui as G, Part
ROOT=Path(__file__).resolve().parent
D=next(d for d in A.listDocuments().values() if d.FileName and Path(d.FileName).resolve()==(ROOT/'Precision_5560_Native.FCStd').resolve())
A.setActiveDocument(D.Name)
links={o.InstanceKey:o for o in D.getObject('InstalledAssembly').Group if o.TypeId=='App::Link'}
core=D.getObject('Loft001').Shape
shell=D.getObject('Cut016').Shape
final=D.getObject('Compound027').Shape
base=D.getObject('MatchedOutline001').Base.Shape
patches=[D.getObject('LoftSkinPatch').Shape,D.getObject('LoftSkinPatch001').Shape]
report={'patch_intrusion_into_original_airway_mm3':[p.common(core).Volume for p in patches], 'unexpected_material_inside_original_airway_mm3':final.cut(base).common(core).Volume,'unexpected_wall_loss_mm3':D.getObject('OriginalWallSkin').Shape.cut(final).Volume,'core_valid':core.isValid(),'core_solids':len(core.Solids),'duct_valid':final.isValid(),'arms_difference_mm3':{},'fit_gaps_mm':{}}
for key,info in json.loads((ROOT/'frozen_print_arms/manifest.json').read_text())['parts'].items():
 arm=D.getObject(info['source']).Shape;ref=Part.read(str(ROOT/'frozen_print_arms'/info['file']));report['arms_difference_mm3'][key]=arm.cut(ref).Volume+ref.cut(arm).Volume
for keys in [['04_right_fan_duct','06_right_fan_retainer','10_right_fan_tray'],['03_left_fan_duct','05_left_fan_retainer','09_left_fan_tray']]:
 for i,j in [(0,1),(0,2),(1,2)]:report['fit_gaps_mm'][keys[i]+' / '+keys[j]]=links[keys[i]].Shape.distToShape(links[keys[j]].Shape)[0]
if D.getObject('FlowInnerBlend'):
 flow=json.loads((ROOT/'flow_refinement.json').read_text())
 report['intentional_flow_material_in_airway_mm3']=flow['added_to_original_airway_mm3']
 report['intentional_wall_relief_mm3']=flow['removed_from_original_wall_mm3']
 report['unexpected_material_inside_original_airway_mm3']-=flow['added_to_original_airway_mm3']
 report['unexpected_wall_loss_mm3']-=flow['removed_from_original_wall_mm3']
report['pass']=all(x<1e-6 for x in report['patch_intrusion_into_original_airway_mm3']) and abs(report['unexpected_material_inside_original_airway_mm3'])<1e-6 and abs(report['unexpected_wall_loss_mm3'])<1e-6 and all(x<1e-6 for x in report['arms_difference_mm3'].values()) and all(abs(x-.3)<1e-5 for x in report['fit_gaps_mm'].values()) and core.isValid() and final.isValid()
report['scope']='Geometric continuity and obstruction audit. Does not establish pressure loss, thermal performance, turbulence or physical print quality.'
(ROOT/'airway_continuity_audit.json').write_text(json.dumps(report,indent=2))
assert report['pass'],report
G.Selection.clearSelection();G.Selection.addSelection(links['04_right_fan_duct']);v=G.activeDocument().activeView();v.viewAxonometric();v.fitAll();G.updateGui()
A.Console.PrintMessage('Airway audit PASS: no unexpected airway intrusion or wall loss; intentional flow blends accounted for; arms frozen; six gaps 0.30 mm.\n')
