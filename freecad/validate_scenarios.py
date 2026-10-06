from pathlib import Path
import sys,json,time,hashlib
import FreeCAD as A,Part
ROOT=Path(__file__).resolve().parent; sys.path.insert(0,A.getResourceDir()+'Mod/Assembly')
MODEL=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'ValidationSnapshot.FCStd'
d=A.openDocument(str(MODEL)); p=d.getObject('Parameters'); assembly=d.getObject('InstalledAssembly')
links={o.InstanceKey:o for o in assembly.Group if o.TypeId=='App::Link'}
cases={
'layout':{'laptopWidth':346.4,'laptopHeight':231.3,'laptopThickness':20.5,'wallGap':40.5,'tineHeight':95,'wallHoleDiameter':7.2,'wallDriverDiameter':16.2,'lowerWallHoleZ':-35.5,'upperWallHoleZ':174.5},
'fan_module':{'fanFrameWidth':120.5,'fanThicknessNominal':25.5,'fanAngle':46,'fanCenterY':67.5,'fanCenterZ':-83.5,'ductSkinNominal':2.2,'grilleBarWidth':2.6},
'fits':{'keyClearance':.35,'trayHorizontalClearance':.35,'trayRoofClearance':.35,'trayRootClearance':.25,'pinSocketDiameter':4.2,'capPinPassageDiameter':4.6,'pinSplitWidth':1.2}}
if len(sys.argv)>2: cases=json.loads(Path(sys.argv[2]).read_text(encoding='utf-8-sig'))
OUTPUT=ROOT/(sys.argv[3] if len(sys.argv)>3 else 'parameter_scenarios.json')
report={'snapshot_sha256':hashlib.sha256(MODEL.read_bytes()).hexdigest(),'cases':{}}
for name,changes in cases.items():
    print('CASE',name,flush=True); old={alias:p.getContents(p.getCellFromAlias(alias)) for alias in changes}; t=time.time()
    try:
        for alias,value in changes.items(): p.set(p.getCellFromAlias(alias),'='+str(value)+(' deg' if alias=='fanAngle' else ' mm'))
        d.recompute()
        errors=[{'name':o.Name,'status':o.getStatusString()} for o in d.Objects if 'Invalid' in o.State]
        invalid=[key for key,o in links.items() if o.Shape.isNull() or not o.Shape.isValid() or len(o.Shape.Solids)!=1]
        result={'values':changes,'invalid_parts':invalid,'feature_errors':errors,'valid':not invalid and not errors,'seconds':time.time()-t}
        # Check fixed keyed interfaces; other service/physical behavior is not inferred.
        overlaps={}
        for side in ['left','right']:
            cradle=next(o.Shape for key,o in links.items() if side in key and 'cradle' in key)
            for part in ['fan_duct','outlet_rail']:
                shape=next(o.Shape for key,o in links.items() if side in key and part in key)
                c=shape.common(cradle); overlaps[side+' '+part]={'valid':c.isValid(),'volume_mm3':c.Volume}
        result['keyed_joint_overlaps']=overlaps
        result['clearance_pass']=all(v['valid'] and v['volume_mm3']<1e-4 for v in overlaps.values())
        report['cases'][name]=result
        OUTPUT.write_text(json.dumps(report,indent=2))
    finally:
        for alias,value in old.items(): p.set(p.getCellFromAlias(alias),value)
        d.recompute()
    report['cases'][name]['restored_errors']=[o.Name for o in d.Objects if 'Invalid' in o.State]
    OUTPUT.write_text(json.dumps(report,indent=2))
report['restored_solid_validity']={key:o.Shape.isValid() and len(o.Shape.Solids)==1 for key,o in links.items()}
report['regeneration_pass']=all(c['valid'] and not c['restored_errors'] for c in report['cases'].values()) and all(report['restored_solid_validity'].values())
report['clearance_pass']=all(c['clearance_pass'] for c in report['cases'].values())
report['all_pass']=report['regeneration_pass'] and report['clearance_pass']
OUTPUT.write_text(json.dumps(report,indent=2)); print('PASS',report['all_pass'],flush=True)
A.closeDocument(d.Name)
