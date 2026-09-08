"""Package checked C1 replacement prints, the corner coupon and offline guide."""
from pathlib import Path
import hashlib
import json
import re
import shutil
import zipfile
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'revh_cables';DOCS=ROOT/'docs'
SITE='https://thereprocase.github.io/dell-5560-wall-mount/'
NAME='Precision_5560_RevH_Cable_Management_C1.zip'


def sha(data):return hashlib.sha256(data).hexdigest()
def read(path):return json.loads(path.read_text())
def duration(seconds):
    seconds=int(seconds);return f'{seconds//3600} h {seconds%3600//60} m {seconds%60} s'


def main():
    native=OUT/'Precision_5560_RevH_Cable_Management_C1.FCStd'
    validation=read(OUT/'validation.json');manifest=read(OUT/'print/manifest.json')
    gui=read(OUT/'gui-review.json');renders=read(OUT/'render-review.json')
    service=read(OUT/'service-animation-review.json')
    source_sha=sha(native.read_bytes())
    assert source_sha==validation['native_sha256']==manifest['native_sha256']==gui['native_sha256']==renders['native_sha256']
    assert gui['pass'] and gui['visible_parts']==18 and gui['report_view_checked_since_reopen']
    assert service['pass'] and service['native_sha256']==source_sha
    assert len(validation['unchanged_parts'])==14 and len(validation['replaced_parts'])==4
    assert all(row['difference_mm3']<.001 for row in validation['unchanged_parts'].values())
    assert validation['baseline_native_sha256']==sha((ROOT/'revh_retention/Precision_5560_RevH_Removable_Retainers.FCStd').read_bytes())
    for name,digest in renders['images'].items():assert sha((DOCS/'assets'/name).read_bytes())==digest,name
    report={'revision':'H-C1 prototype','native_sha256':source_sha,'replaced_part_ids':sorted(validation['replaced_parts']),
        'unchanged_installed_parts':14,'requires_H_R1_retainers':False,'new_fully_constrained_sketches':gui['new_fully_constrained_sketches'],
        'cad_ASA_g':round(manifest['total_cad_ASA_g'],2),'added_cad_ASA_g':round(manifest['added_cad_ASA_g'],2),
        'slicer':'OrcaSlicer 2.4.2','process':'P1S / ASA / 0.4 mm / 0.20 mm / 6 walls / 6 top and bottom / 100% rectilinear / Arachne / 8 mm outer brim / supports off',
        'reviewed_cable_diameter_mm':4,'minimum_cable_clearance_mm':.5,'tie_lugs_per_tray':2,'checked_tie_tail_cross_section_mm':[1.5,3.6],
        'plates':{},'qualification':'Native and toolpath geometry checks only; physical fit, abrasion, tie-lug strength and warm ASA behavior untested.'}
    files={'Precision_5560_RevH_Cable_Management_C1.FCStd':native.read_bytes(),
        'LICENSE.txt':(ROOT/'LICENSE').read_text().encode(),
        'Engineering-README.md':(OUT/'README.md').read_text().replace('(../docs/revh-cables.html)','(Guide/START_HERE.html)').replace('(print/)','(Print/)').replace('(validation.json)','(Evidence/native-validation.json)').encode(),
        'Evidence/native-validation.json':(OUT/'validation.json').read_bytes(),
        'Evidence/gui-review.json':(OUT/'gui-review.json').read_bytes(),
        'Evidence/render-review.json':(OUT/'render-review.json').read_bytes(),
        'Evidence/service-animation-review.json':(OUT/'service-animation-review.json').read_bytes()}
    for group in ['full','coupon']:
        summary=read(OUT/'slices'/group/'slice_summary.json')
        assert len(summary)==(3 if group=='full' else 1)
        for row in summary:
            name=Path(row['source']).stem;folder=OUT/'slices'/group/name
            assert row['exit_code']==0 and row['source_sha256']==sha((OUT/'print'/row['source']).read_bytes())
            raw=(folder/'preview.gcode').read_bytes();text=raw.decode()
            audit=read(OUT/'reports'/(name+'-toolpath.json'))
            assert audit['source_gcode_sha256']==sha(raw) and not audit['floating_components']
            assert audit['max_unsupported_deposition_span_mm']<10,(name,'Inspect unexpectedly long unsupported run')
            mass=float(re.search(r'; filament used \[g\] = ([\d.]+)',text)[1])
            label=re.search(r'total estimated time: ([^\r\n]+)',text)[1]
            seconds=sum(float(n)*{'h':3600,'m':60,'s':1}[u] for n,u in re.findall(r'([\d.]+)([hms])',label))
            process=read(OUT/'slices'/group/'profiles/process.json')
            if group=='coupon':
                assert float(process['bridge_angle'])==180 and float(process['internal_bridge_angle'])==180
                assert process['relative_bridge_angle']=='0' and process['align_infill_direction_to_model']=='0'
            else:
                assert float(process.get('bridge_angle',0))==0 and float(process.get('internal_bridge_angle',0))==0
            report['plates'][name]={'estimated_filament_g':mass,'total_estimated_seconds':seconds,
                'source_3mf_sha256':row['source_sha256'],'gcode_sha256':sha(raw),'disconnected_floating_components':0,
                'max_unsupported_bridge_span_mm':audit['max_unsupported_bridge_span_mm'],
                'max_unsupported_deposition_span_mm':audit['max_unsupported_deposition_span_mm'],
                'bridge_directions':'both 180 degrees; relative and align-to-model off' if group=='coupon' else 'automatic'}
            archives=list(folder.glob('*.gcode.3mf'));assert len(archives)==1
            archive=archives[0]
            with zipfile.ZipFile(archive) as z:
                paths=[p for p in z.namelist() if p.endswith('.gcode')]
                assert len(paths)==1 and sha(z.read(paths[0]))==sha(raw)
            files['Orca_Review/'+archive.name]=archive.read_bytes()
            files['Evidence/'+name+'-toolpath.json']=(OUT/'reports'/(name+'-toolpath.json')).read_bytes()
    full=[v for k,v in report['plates'].items() if k!='00_cable_fit_coupon']
    report['replacement_set']={'parts':4,'plates':3,'estimated_filament_g':round(sum(v['estimated_filament_g'] for v in full),2),
                               'total_estimated_seconds':sum(v['total_estimated_seconds'] for v in full)}
    totals=report['replacement_set'];coupon=report['plates']['00_cable_fit_coupon']
    maximum=max(v['max_unsupported_deposition_span_mm'] for v in report['plates'].values())
    estimate=(f'The four replacements are estimated at <strong>{totals["estimated_filament_g"]:.2f} g and {duration(totals["total_estimated_seconds"])}</strong> across three plates. '
        f'The corner coupon is {coupon["estimated_filament_g"]:.2f} g and {duration(coupon["total_estimated_seconds"])}. '
        f'These are Orca estimates under the reviewed process, not measured print results. All four layouts have zero disconnected floating components in the deposited-path screen; '
        f'the longest unsupported deposition span is {maximum:.2f} mm. That geometric screen does not prove adhesion or ASA bridge quality.')
    guide=(DOCS/'revh-cables.html').read_text()
    guide,count=re.subn(r'<p id="cable-estimates">.*?</p>','<p id="cable-estimates">'+estimate+'</p>',guide,flags=re.S);assert count==1
    (DOCS/'revh-cables.html').write_text(guide)
    offline=re.sub(r'<section id="model">.*?</section>',
        '<section id="model"><figure><img src="assets/revh-cables-installed.png" alt="Native Rev H-C1 assembly"></figure><p><a href="'+SITE+'revh-cables.html#model">Open the interactive model online ↗</a></p></section>',guide,flags=re.S)
    offline=re.sub(r'<script.*?</script>','',offline,flags=re.S)
    offline=offline.replace('href="downloads/'+NAME+'" download','href="'+SITE+'revh-cables.html"')
    offline=offline.replace('Download covers, trays, fit coupon and native model ↓','Open the online guide ↗')
    for prefix in ['index.html','revh-retainers.html','assets/revh-cables-validation.json','assets/revh-cables-release.json','simulation/revh-transient/']:
        offline=offline.replace('href="'+prefix,'href="'+SITE+prefix)
    files['Guide/START_HERE.html']=offline.encode()
    for name in ['style.css','minimalist.css','cables.css']:files['Guide/'+name]=(DOCS/name).read_bytes()
    for p in (DOCS/'assets').glob('revh-cables-*.png'):files['Guide/assets/'+p.name]=p.read_bytes()
    for p in (OUT/'print').iterdir():
        if p.is_file():files['Print/'+p.name]=p.read_bytes()
    report_bytes=(json.dumps(report,indent=2)+'\n').encode();files['Evidence/release-report.json']=report_bytes
    files['START-HERE.txt']=('''REV H-C1 CABLE ROUTING — PROTOTYPE

Open Guide/START_HERE.html for illustrated printing, fitting and service.
Print Print/00_cable_fit_coupon.3mf first. It contains four test pieces.
Then print Print/20_both_cable_covers.3mf and trays 09/10: four replacement
parts across three plates. Covers 05/06 are alternatives already on plate 20.
STL, STEP and geometry-only 3MF are alternative formats of the same parts.

Use OrcaSlicer, ASA and the supplied orientation at 100% scale. The coupon
duct corner prints front mating face down; other pieces retain their full-part
print directions. The reviewed coupon uses both bridge directions at 180 degrees,
with Relative bridge angle and Align infill direction to model OFF. Full-size
cover/tray review slices use automatic bridge direction. Re-slice for your spool.

Lay the wire into the cover's open mating-edge groove, then fit the cover.
The tray closes the passage; the connector remains outside. Both tie anchors
are on the tray, so the cover can come off without removing those ties.
Disconnect the fan and release any off-tray cable attachment before sliding
the tray out. Check actual fit and avoid compressing the cable's insulation.

Replace Rev H covers 05/06 and trays 09/10 only. The arms, ducts, rails,
pins and optional H-R1 retainers are unchanged. This is not an M1 upgrade.
The native model includes eighteen installed parts with optional H-R1 retainers;
the Print folder supplies only the four C1 replacements and the coupon.

Physical fit, cable abrasion, tie-lug strength and warm ASA behavior are untested.
Orca_Review contains settings and G-code for inspecting the reviewed paths,
not universal printer-ready jobs. No print has been sent to a printer.

Original Rev H parts and instructions:
'''+SITE+'''#ducted
''').encode()
    files['SHA256SUMS.txt']=''.join(sha(data)+'  '+name+'\n' for name,data in sorted(files.items())).encode()
    target=DOCS/'downloads'/NAME
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
        for name,data in sorted(files.items()):z.writestr(name,data)
    with zipfile.ZipFile(target) as z:
        for line in z.read('SHA256SUMS.txt').decode().splitlines():
            digest,name=line.split('  ',1);assert sha(z.read(name))==digest,name
    report['download']={'file':NAME,'bytes':target.stat().st_size,'sha256':sha(target.read_bytes()),'members':len(files),'all_member_hashes_verified':True}
    (OUT/'release-report.json').write_text(json.dumps(report,indent=2)+'\n')
    (DOCS/'assets/revh-cables-release.json').write_text(json.dumps(report,indent=2)+'\n')
    shutil.copy2(OUT/'validation.json',DOCS/'assets/revh-cables-validation.json')
    print(json.dumps({'replacement_set':totals,'coupon':coupon,'max_unsupported_mm':maximum,'download':report['download']},indent=2))


if __name__=='__main__':main()
