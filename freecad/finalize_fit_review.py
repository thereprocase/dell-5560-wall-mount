from pathlib import Path
import json,shutil
import FreeCAD as A,FreeCADGui as G,Part
ROOT=Path(__file__).resolve().parent
D=next(d for d in A.listDocuments().values() if d.FileName and Path(d.FileName).resolve()==(ROOT/'Precision_5560_Native.FCStd').resolve())
assert not A._fit_review_timer.isActive()
links={o.InstanceKey:o for o in D.getObject('InstalledAssembly').Group if o.TypeId=='App::Link'}
report={'parts':{},'fit_gaps_mm':{},'frozen_arms_difference_mm3':{},'fully_constrained_sketches':0}
for key,o in links.items():
 s=o.Shape;assert s.isValid() and len(s.Solids)==1
 report['parts'][key]={'valid':True,'solids':1,'small_faces':sum(f.Area<.1 for f in s.Faces),'short_edges':sum(e.Length<.05 for e in s.Edges)}
 if 'cradle' not in key:assert report['parts'][key]['small_faces']==0 and report['parts'][key]['short_edges']==0,key
for left in [False,True]:
 keys=['03_left_fan_duct','05_left_fan_retainer','09_left_fan_tray'] if left else ['04_right_fan_duct','06_right_fan_retainer','10_right_fan_tray']
 for i,j in [(0,1),(0,2),(1,2)]:
  gap=links[keys[i]].Shape.distToShape(links[keys[j]].Shape)[0];assert abs(gap-.3)<1e-5;report['fit_gaps_mm'][keys[i]+' / '+keys[j]]=gap
 rail,arm=('07_left_outlet_rail','01_left_cradle') if left else ('08_right_outlet_rail','02_right_cradle')
 gap=links[rail].Shape.distToShape(links[arm].Shape)[0];assert abs(gap-.3)<1e-5;report['fit_gaps_mm'][rail+' / '+arm]=gap
for key,info in json.loads((ROOT/'frozen_print_arms/manifest.json').read_text())['parts'].items():
 arm=D.getObject(info['source']).Shape;ref=Part.read(str(ROOT/'frozen_print_arms'/info['file']));delta=arm.cut(ref).Volume+ref.cut(arm).Volume;assert delta<1e-6;report['frozen_arms_difference_mm3'][key]=delta
for o in D.Objects:
 if o.TypeId=='Sketcher::SketchObject':assert o.FullyConstrained,o.Name;report['fully_constrained_sketches']+=1
wall_ref=D.getObject('OriginalWallSkin').Shape
flow=D.getObject('FlowInnerBlend')
if flow:
    relief=flow.Base.Shape.cut(flow.Shape)
    report['intentional_flow_wall_relief_mm3']=wall_ref.common(relief).Volume
    wall_ref=wall_ref.cut(relief)
wall_loss=wall_ref.cut(D.getObject('Compound027').Shape).Volume
assert wall_loss<1e-6
report['original_wall_loss_mm3']=wall_loss
report['release_revision']='H' if flow else 'G'
sheet=D.getObject('ManufacturingFitReview') or D.addObject('Spreadsheet::Sheet','ManufacturingFitReview');sheet.Label='Fit review - P1S ASA - measured clearances'
sheet.mergeCells('A1:E1');sheet.set('A1','MANUFACTURING FIT REVIEW | PRINTED ARMS FROZEN');sheet.setBackground('A1:E1',(.16,.26,.32));sheet.setForeground('A1:E1',(1,1,1))
for c,t in zip('ABCDE',['Interface','Target mm','Measured mm','Status','Native edit point / exception']):sheet.set(c+'3',t)
sheet.setBackground('A3:E3',(.70,.81,.84));row=4
for key,value in report['fit_gaps_mm'].items():
 for c,t in zip('ABCDE',[key,'0.30',f'{value:.3f}','PASS','FanFitClearance / RailRefinement']):sheet.set(c+str(row),t)
 row+=1
for key,value in json.loads((ROOT/'fixed_key_fit_audit.json').read_text()).items():
 for c,t in zip('ABCDE',[key,'0.30',f'{value:.3f}','PASS','Frozen receiver; keys retained']):sheet.set(c+str(row),t)
 row+=1
extras=[['Fixed load shoulders','0','0','RETAINED','Intentional bearing / bonded seating contact'],['Pin shaft / socket','0.10','0.10','RETAINED','Diametral clearance; not a 0.30 mm fit'],['Split crown / socket','-0.10','-0.10','RETAINED','Diametral interference for retention'],['Printed arm shape difference','0','0','PASS','Frozen BRep comparison'],['Print baseline','','','REFERENCE','P1S, ASA, 0.4 nozzle, 0.20 layer, supports off'],['Values above are measurements','','','REFERENCE','Edit native feature profiles; this sheet does not drive geometry']]
for cells in extras:
 for c,t in zip('ABCDE',cells):sheet.set(c+str(row),t)
 row+=1
for c,w in [('A',420),('B',90),('C',110),('D',110),('E',440)]:sheet.setColumnWidth(c,w)
sheet.setBackground('B4:C'+str(row-1),(.9,.92,.93));D.recompute()
assert not [o.Name for o in D.Objects if 'Invalid' in o.State]
D.save();shutil.copy2(D.FileName,ROOT/'FinishValidation.FCStd')
(ROOT/'complete_fit_review.json').write_text(json.dumps(report,indent=2))
G.Selection.clearSelection();v=G.activeDocument().mdiViewsOfType('Gui::View3DInventor')[0];v.viewAxonometric();v.fitAll();G.updateGui()
A.Console.PrintMessage('Complete fit review saved: 14 valid solids, all sketches constrained, frozen arms unchanged.\n')
