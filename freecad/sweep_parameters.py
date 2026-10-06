from pathlib import Path
import sys,json,time
import FreeCAD as App,Part
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(Path(App.getResourceDir())/'Mod'/'Assembly'))
D=App.openDocument(str(ROOT/'ValidationSnapshot.FCStd'))
P=D.getObject('Parameters'); a=D.getObject('InstalledAssembly')
links={o.InstanceKey:o for o in a.Group if o.TypeId=='App::Link'}
cases={'outletGap':[8,16],'laptopWidth':[342.4,346.4],'laptopHeight':[229.3,231.3],
       'laptopThickness':[19.5,20.5],'wallGap':[39.5,40.5],'tineHeight':[93,95],
       'wallHoleDiameter':[6.8,7.2],'wallDriverDiameter':[15.8,16.2],
       'wallHoleHalfSpacing':[161.5,162.5],'lowerWallHoleZ':[-36.5,-35.5],'upperWallHoleZ':[173.5,174.5],
       'fanFrameWidth':[119.5,120.5],'fanThicknessNominal':[24.5,25.5],'fanAngle':[44,46],
       'fanCenterY':[66.5,67.5],'fanCenterZ':[-84.5,-83.5],'ductSkinNominal':[1.8,2.2],
       'keyClearance':[.25,.35],'trayHorizontalClearance':[.25,.35],'trayRoofClearance':[.25,.35],
       'trayRootClearance':[.15,.25],'pinSocketDiameter':[4,4.2],'pinSplitWidth':[.8,1.2],
       'capPinPassageDiameter':[4.4,4.6],'grilleBarWidth':[2.2,2.6]}
results=json.loads((ROOT/'parametric_validation.json').read_text()) if (ROOT/'parametric_validation.json').exists() else {}
for name,values in cases.items():
    if name in results and [x['value'] for x in results[name]]==values: continue
    print('CHECK',name,flush=True)
    cell=P.getCellFromAlias(name); old=P.getContents(cell); results[name]=[]
    try:
        for value in values:
            P.set(cell,'='+str(value)+(' deg' if name=='fanAngle' else ' mm')); D.recompute()
            issues=[]
            for key,o in links.items():
                if o.Shape.isNull() or not o.Shape.isValid() or len(o.Shape.Solids)!=1: issues.append(key)
            errors=[o.Name for o in D.Objects if 'Invalid' in o.State]
            row={'value':value,'valid':not issues and not errors,'invalid_parts':issues,'feature_errors':errors}
            if name=='outletGap':
                row['variant_comparison']={}
                for side in ['left','right']:
                    key=next(k for k in links if side in k and 'outlet_rail' in k)
                    shape=links[key].Shape; ref=Part.read(str(ROOT.parent/'outlet_gap_variants'/(side+'_outlet_rail_gap_'+str(value)+'mm.step')))
                    ab=shape.cut(ref); ba=ref.cut(shape)
                    row['variant_comparison'][side]={'delta_mm3':ab.Volume+ba.Volume,'boolean_valid':ab.isValid() and ba.isValid()}
            results[name].append(row)
            (ROOT/'parametric_validation.json').write_text(json.dumps(results,indent=2))
            (ROOT/'build_progress.json').write_text(json.dumps({'phase':'parameter checks','parameter':name,'value':value,'valid':row['valid']},indent=2))

    finally:
        P.set(cell,old); D.recompute()
    r=cell[1:]; P.set('E'+r,('PASS ' if all(c['valid'] for c in results[name]) else 'LIMIT: failed test ')+', '.join(str(v) for v in values))
    P.setBackground('E'+r,(.83,.94,.85) if all(c['valid'] for c in results[name]) else (1,.88,.67))
D.recompute(); D.save()
(ROOT/'build_progress.json').write_text(json.dumps({'phase':'parameter checks complete','failed_parameters':[n for n,cases in results.items() if any(not c['valid'] for c in cases)]},indent=2))

App.closeDocument(D.Name)
