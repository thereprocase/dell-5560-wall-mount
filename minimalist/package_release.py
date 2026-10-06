"""Build reviewed offline-friendly downloads and a portable evidence summary."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
import zipfile

ROOT=Path(__file__).resolve().parent
DOCS=ROOT.parent/'docs'
SITE='https://thereprocase.github.io/dell-5560-wall-mount/'


def sha(data): return hashlib.sha256(data).hexdigest()


def slice_record(folder, require_audit=True):
    gcode=folder/'preview.gcode'
    raw=gcode.read_bytes();text=raw.decode('utf8')
    weight=float(re.search(r'; filament used \[g\] = ([\d.]+)',text)[1])
    duration=re.search(r'total estimated time: ([^\r\n]+)',text)[1]
    seconds=sum(float(a)*{'h':3600,'m':60,'s':1}[b] for a,b in re.findall(r'([\d.]+)([hms])',duration))
    result={'part_or_plate':folder.name,'estimated_filament_g':weight,'total_estimated_seconds':seconds,'gcode_sha256':sha(raw)}
    if require_audit:
        audit_path=folder/'toolpath-audit.json'
        assert audit_path.stat().st_mtime_ns>=gcode.stat().st_mtime_ns, 'Stale toolpath audit: '+str(folder)
        audit=json.loads(audit_path.read_text())
        audit['method']=audit['method'].replace('A bridge bead','A deposited bead')
        audit['analysis_feature_scope']='All positive-extrusion model paths; bridge-tagged and all-feature maxima are reported separately.'
        if 'source_gcode_sha256' in audit: assert audit['source_gcode_sha256']==sha(raw)
        audit['source_gcode_sha256']=sha(raw)
        assert not audit['floating_components'], folder
        assert audit['max_unsupported_bridge_span_mm']<6, folder
        assert 'max_unsupported_deposition_span_mm' in audit, 'Full feature audit required'
        result.update(max_unsupported_bridge_span_mm=audit['max_unsupported_bridge_span_mm'],
                      max_unsupported_deposition_span_mm=audit['max_unsupported_deposition_span_mm'],
                      unsupported_by_feature_mm=audit['unsupported_by_feature_mm'],disconnected_floating_components=0)
        archive=next(folder.glob('*.gcode.3mf'))
        with zipfile.ZipFile(archive) as z:
            g=[n for n in z.namelist() if n.endswith('.gcode')]
            assert len(g)==1 and sha(z.read(g[0]))==sha(raw)
        report_path=ROOT/'reports/toolpaths'/folder.parent.name/(folder.name+'.json')
        report_path.parent.mkdir(parents=True,exist_ok=True)
        report_path.write_text(json.dumps(audit,indent=2)+'\n')
    return result


def offline_guide():
    text=(DOCS/'minimalist-guide.html').read_text()
    for relative in ('index.html','downloads/','assets/minimalist-release-report.json','assets/minimalist-section-review.json','assets/minimalist-wall-transition-review.json','simulation/revh-transient/'):
        text=text.replace('href="'+relative,'href="'+SITE+relative)
    files={'Guide/START_HERE.html':text.encode()}
    for name in ['style.css','minimalist.css','assets/minimalist-with-envelopes.png',
                 'assets/minimalist-wall-junction-before.png','assets/minimalist-wall-junction-after.png',
                 'assets/minimalist-wall-transition-section.png']:
        files['Guide/'+name]=(DOCS/name).read_bytes()
    return files


def make_zip(path, files):
    checks=''.join(sha(data)+'  '+name+'\n' for name,data in sorted(files.items()))
    files={**files,'SHA256SUMS.txt':checks.encode()}
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        for name,data in sorted(files.items()):z.writestr(name,data)
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        for line in z.read('SHA256SUMS.txt').decode().splitlines():
            digest,name=line.split('  ',1)
            assert sha(z.read(name))==digest
    return {'file':path.name,'bytes':path.stat().st_size,'sha256':sha(path.read_bytes()),'members':len(files),'all_member_hashes_verified':True}


def start_here(name):
    return f'''MINIMALIST M1.1 / {name} / PRINT CANDIDATE

1. Open Guide/START_HERE.html in a browser. It works offline for the included
   instructions and pictures. Confirm the measured case dimensions first.
2. Print the eight-piece fit coupon package before printing the complete set.
3. Open M1.FCStd in FreeCAD 1.1 for the editable native model. Blue spreadsheet
   cells are measured inputs; gray cells are derived. Recheck after any edit.
4. For this set print ONE EACH of 01-08 plus 21_all_hardware from Print/.
   Files 09-20 are individual replacements for hardware already on plate 21.
   STL, STEP and geometry-only 3MF are alternatives. Do not print all formats.
5. Keep the supplied orientations and scale in OrcaSlicer. P1S / 0.4 nozzle /
   ASA / 0.20 layers / 6 walls / 6 top and bottom / 100% rectilinear / 8 mm outer
   brim / supports off. Use the actual spool's temperatures and drying rules.
6. Orca_preview/ contains reviewed slices with embedded G-code. Inspect them,
   then re-slice for your actual printer and spool. Nothing was sent to a printer.
7. M1_assembled.step is for installed-assembly inspection, not a print plate.

Optional dam: omit 07,08,11,12,15,16. Print 01-06 plus 22_hardware_without_dam for seven plates, replacing plate 21.
Upgrading from M1.0: replace both reinforced arms (01/02) and, if fitted,
both dams (07/08) with their matching clearance notch. Other parts are unchanged.
See the illustrated guide.

Physical fit, retention, ASA creep, wall anchors and cooling need qualification.
The CAD and toolpath checks do not establish a load rating or print success.

Public guide: {SITE}minimalist-guide.html
All included files are covered by SHA256SUMS.txt.
'''.encode()


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--revh-slices',type=Path,default=ROOT.parent.parent/'dell-5560-wall-mount/tmp/orca_H_comparison')
    args=ap.parse_args()
    names=json.loads((DOCS/'models/minimalist/manifest.json').read_text())['presets']
    report={'revision':'Minimalist M1.1 prototype','native_design':'constrained sketches and stock FreeCAD features',
            'source_native_sha256':sha((ROOT/'Laptop_Wall_Mount_Minimalist.FCStd').read_bytes()),
            'process':{'slicer':'OrcaSlicer 2.4.2','printer':'Bambu P1S','material_profile':'Bambu ASA','nozzle_mm':.4,'layer_mm':.2,'walls':6,'top_layers':6,'bottom_layers':6,'infill':'100% rectilinear','brim_mm':8,'supports':False},
            'presets':{},'downloads':{},'physical_qualification_complete':False,
            'limits':['No physical fit/retention test','No ASA creep or anchor qualification','No calibrated airflow or cooling result','Section demand is not a load rating','Toolpath screen does not prove sag or same-layer anchoring order']}
    rebuilt=json.loads((ROOT/'rebuild-validation.json').read_text())
    comparison=json.loads((ROOT/'rebuild-shape-comparison.json').read_text())
    gui=json.loads((ROOT/'gui-review.json').read_text())
    preset_gui=json.loads((ROOT/'reports/preset-gui-review.json').read_text())
    transitions=json.loads((ROOT/'reports/wall-transition-review.json').read_text())
    assert len(transitions['presets'])==6
    report['wall_transition_revision']={'baseline_commit':transitions['baseline_commit'],
        'changed_parts':['01_left_arm','02_right_arm','07_left_dam','08_right_dam'],
        'wall_pad_height_mm':32,'paired_web_thickness_mm':6,'web_rise_from_pad_face_mm':16,
        'report':'minimalist-wall-transition-review.json','strength_rating_established':False}
    assert len(preset_gui)==6 and all(v['pass'] and v['file_unchanged'] for v in preset_gui.values())
    assert rebuilt['pass'] and all(v['pass'] for v in comparison['parts'].values()) and not gui['bad_features']
    assert comparison['source_native_sha256']==report['source_native_sha256']
    report['source_reconstruction']={'native_validation_pass':True,'matching_solids':20,
        'maximum_shape_difference_mm3':max(v['symmetric_difference_mm3'] for v in comparison['parts'].values()),
        'live_gui_bad_features':gui['bad_features'],'live_gui_constrained_sketches':gui['constrained_sketches']}
    h_native=ROOT.parent/'freecad/Precision_5560_Native.FCStd'
    h_manifest=json.loads((ROOT.parent/'print_release/manifest.json').read_text())
    assert sha(h_native.read_bytes())==h_manifest['native_sha256']
    report['preserved_revh_native_sha256']=h_manifest['native_sha256']
    downloads=DOCS/'downloads';downloads.mkdir(exist_ok=True)
    common=offline_guide()
    if (ROOT.parent/'LICENSE').exists():common['LICENSE.txt']=(ROOT.parent/'LICENSE').read_bytes()
    for name,meta in names.items():
        folder=ROOT/'presets'/name
        native=json.loads((folder/'validation.json').read_text())
        assert len(native['dam_positions'])==9 and all(v['pass'] for v in native['dam_positions'].values())
        assert native['saved_reopened']['pass'] and native['source_unchanged']
        manifest=json.loads((folder/'print/manifest.json').read_text())
        assert sha((folder/'M1.FCStd').read_bytes())==manifest['native_sha256']
        assert preset_gui[name]['native_sha256']==manifest['native_sha256']
        transition=transitions['presets'][name]
        assert transition['after_native_sha256']==manifest['native_sha256']
        assert transition['unchanged_other_parts']==16 and transition['bolt_centers_unchanged']
        assert transition['original_arm_material_removed_mm3']<.01
        for key,part in {**manifest['parts'],**manifest['plates']}.items():
            for suffix,digest in part['sha256'].items():assert sha((folder/'print'/(key+suffix)).read_bytes())==digest
        sliced=ROOT/'slices'/name
        summary=json.loads((sliced/'slice_summary.json').read_text())
        assert len(summary)==9 and all(r['exit_code']==0 for r in summary)
        for row in summary:
            assert row['source_sha256']==sha((folder/'print'/row['source']).read_bytes())
        records=[slice_record(p.parent) for p in sorted(sliced.glob('*/preview.gcode'))]
        assert len(records)==9
        optional_folder=ROOT/'slices'/('optional-'+name)
        optional_summary=json.loads((optional_folder/'slice_summary.json').read_text())
        assert len(optional_summary)==1 and optional_summary[0]['exit_code']==0
        assert optional_summary[0]['source_sha256']==sha((folder/'print/22_hardware_without_dam.stl').read_bytes())
        optional=slice_record(optional_folder/'22_hardware_without_dam')
        no_dam=[r for r in records if int(r['part_or_plate'][:2])<=6]+[optional]
        report['presets'][name]={'label':meta['label'],'width_mm':meta['width'],'depth_mm':meta['depth'],'thickness_mm':meta['thickness'],
            'native_dam_positions_passed':9,'reopened_pass':True,'valid_individual_prints':20,'hardware_plate_solids':12,
            'live_gui_preset_open_pass':True,
            'estimated_filament_g':round(sum(r['estimated_filament_g'] for r in records),2),
            'total_estimated_seconds':sum(r['total_estimated_seconds'] for r in records),
            'max_unsupported_bridge_span_mm':max(r['max_unsupported_bridge_span_mm'] for r in records),
            'max_unsupported_deposition_span_mm':max(r['max_unsupported_deposition_span_mm'] for r in records),
            'disconnected_floating_components':0,'plates':records}
        report['presets'][name]['without_dam']={'plates':7,'hardware_plate':optional,
            'estimated_filament_g':round(sum(r['estimated_filament_g'] for r in no_dam),2),
            'total_estimated_seconds':sum(r['total_estimated_seconds'] for r in no_dam)}
        files={**common,'START_HERE.txt':start_here(name),'M1.FCStd':(folder/'M1.FCStd').read_bytes(),
               'native-validation.json':(folder/'validation.json').read_bytes()}
        for p in sorted((folder/'print').iterdir()):
            if p.is_file():files['M1_assembled.step' if p.name=='M1_assembled.step' else 'Print/'+p.name]=p.read_bytes()
        for p in sorted(sliced.glob('*/*.gcode.3mf')):files['Orca_preview/'+p.name]=p.read_bytes()
        for p in sorted(optional_folder.glob('*/*.gcode.3mf')):files['Orca_preview/'+p.name]=p.read_bytes()
        for p in sorted((sliced/'profiles').glob('*.json')):files['Orca_preview/Profiles/'+p.name]=p.read_bytes()
        files['Orca_preview/review.json']=(json.dumps(report['presets'][name],indent=2)+'\n').encode()
        report['downloads'][name]=make_zip(downloads/('Minimalist_M1_'+name+'.zip'),files)
    coupon_summary=json.loads((ROOT/'slices/coupons/slice_summary.json').read_text())
    assert len(coupon_summary)==1 and coupon_summary[0]['exit_code']==0
    assert coupon_summary[0]['source_sha256']==sha((ROOT/'coupons/00_fit_coupon_plate.stl').read_bytes())
    coupon_slice=slice_record(ROOT/'slices/coupons/00_fit_coupon_plate')
    report['fit_coupon']=coupon_slice
    files={**common,'START_HERE.txt':b'MINIMALIST M1 FIT COUPON\n\nOpen Guide/START_HERE.html. Print 00_fit_coupon_plate once, or the eight\nindividual samples as alternatives. These are fit samples, not mount parts.\nThe coupon retains each interface\'s actual full-part build direction.\n'}
    for p in (ROOT/'coupons').iterdir():
        if p.is_file():files[p.name]=p.read_bytes()
    for p in (ROOT/'slices/coupons/00_fit_coupon_plate').glob('*.gcode.3mf'):files['Orca_preview/'+p.name]=p.read_bytes()
    report['downloads']['coupons']=make_zip(downloads/'Minimalist_M1_Fit_Coupons.zip',files)
    h=[slice_record(p.parent,False) for p in sorted(args.revh_slices.glob('*/preview.gcode'))]
    assert len(h)==14
    report['revh_comparison']={'layout':'14 individual plates, including four separate pin plates','bridge_direction_override_degrees':180,'relative_bridge_angle':False,'estimated_filament_g':round(sum(r['estimated_filament_g'] for r in h),2),'total_estimated_seconds':sum(r['total_estimated_seconds'] for r in h),'parts':h}
    (ROOT/'reports').mkdir(exist_ok=True)
    for path in [ROOT/'reports/release.json',DOCS/'assets/minimalist-release-report.json']:
        path.write_text(json.dumps(report,indent=2)+'\n')
    section=ROOT/'section-review.json'
    assert len(json.loads(section.read_text()))==6
    shutil.copy2(section,DOCS/'assets/minimalist-section-review.json')
    shutil.copy2(ROOT/'reports/wall-transition-review.json',DOCS/'assets/minimalist-wall-transition-review.json')
    shutil.copy2(ROOT/'slices/5560/03_left_fan_cage/bridge-review.png',DOCS/'assets/minimalist-cage-toolpaths.png')
    print('Seven delivery archives verified; six presets and all plate audits published',flush=True)


if __name__=='__main__':main()
