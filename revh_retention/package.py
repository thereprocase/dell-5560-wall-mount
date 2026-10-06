"""Package the reviewed four-part add-on, native model and offline guide."""
from pathlib import Path
import hashlib
import html
import json
import re
import shutil
import sys
import zipfile
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'revh_retention';DOCS=ROOT/'docs'
SITE='https://thereprocase.github.io/dell-5560-wall-mount/'

def sha(data):return hashlib.sha256(data).hexdigest()
def read(path):return json.loads(path.read_text())
def duration(seconds):
    seconds=int(seconds);return f'{seconds//3600} h {(seconds%3600)//60} m {seconds%60} s'

def main():
    native=OUT/'Precision_5560_RevH_Removable_Retainers.FCStd'
    validation=read(OUT/'validation.json');manifest=read(OUT/'print/manifest.json');gui=read(OUT/'gui-review.json')
    native_sha=sha(native.read_bytes())
    assert native_sha==validation['native_sha256']==manifest['native_sha256']==gui['native_sha256']
    assert gui['pass'] and gui['visible_parts']==18
    summary=read(OUT/'slices/slice_summary.json')
    assert len(summary)==2 and all(row['exit_code']==0 for row in summary)
    report={'revision':'H-R1 prototype','native_sha256':native_sha,'unchanged_original_parts':14,'added_parts':4,
            'new_fully_constrained_sketches':validation['new_fully_constrained_sketches'],
            'cad_ASA_g':round(manifest['total_cad_ASA_g'],2),'slicer':'OrcaSlicer 2.4.2',
            'process':'P1S 0.4 mm / 0.20 mm / ASA / 6 walls / 6 top and bottom / 100% rectilinear / Arachne / 8 mm outer brim / supports off',
            'plates':{},'qualification':'CAD, export and geometric toolpath screening only. Physical fit, retention, stiffness, layer adhesion and creep untested.'}
    files={'Precision_5560_RevH_Removable_Retainers.FCStd':native.read_bytes(),
           'Engineering-README.md':(OUT/'README.md').read_text().replace('(../docs/revh-retainers.html)','(Guide/START_HERE.html)').replace('(print/)','(Print/)').replace('(validation.json)','(Evidence/native-validation.json)').encode(),
           'Evidence/native-validation.json':(OUT/'validation.json').read_bytes(),
           'Evidence/gui-review.json':(OUT/'gui-review.json').read_bytes()}
    for row in summary:
        name=Path(row['source']).stem;folder=OUT/'slices'/name
        assert row['source_sha256']==sha((OUT/'print'/row['source']).read_bytes())
        raw=(folder/'preview.gcode').read_bytes();text=raw.decode('utf8')
        audit=read(folder/'toolpath-audit.json')
        assert audit['source_gcode_sha256']==sha(raw)
        assert not audit['floating_components']
        assert audit['max_unsupported_deposition_span_mm']<6
        mass=float(re.search(r'; filament used \[g\] = ([\d.]+)',text)[1])
        estimate=re.search(r'total estimated time: ([^\r\n]+)',text)[1]
        seconds=sum(float(a)*{'h':3600,'m':60,'s':1}[b] for a,b in re.findall(r'([\d.]+)([hms])',estimate))
        record={'estimated_filament_g':mass,'total_estimated_seconds':seconds,'source_3mf_sha256':row['source_sha256'],
                'gcode_sha256':sha(raw),'disconnected_floating_components':0,
                'max_unsupported_bridge_span_mm':audit['max_unsupported_bridge_span_mm'],
                'max_unsupported_deposition_span_mm':audit['max_unsupported_deposition_span_mm']}
        report['plates'][name]=record
        archive=next(folder.glob('*.gcode.3mf'))
        with zipfile.ZipFile(archive) as z:
            paths=[p for p in z.namelist() if p.endswith('.gcode')]
            assert len(paths)==1 and sha(z.read(paths[0]))==sha(raw)
        files['Orca_Review/'+archive.name]=archive.read_bytes()
        files['Evidence/'+name+'-toolpath.json']=(folder/'toolpath-audit.json').read_bytes()
        for suffix in ['.json','.png']:
            shutil.copy2(folder/('toolpath-audit'+suffix),OUT/'reports'/(name+'-toolpath'+suffix))
    full=report['plates']['00_four_retainer_parts'];coupon=report['plates']['01_right_arm_fit_test']
    estimate=(f'The four-part plate is estimated at <strong>{full["estimated_filament_g"]:.2f} g and {duration(full["total_estimated_seconds"])}</strong> in Orca. '
              f'The right-arm coupon plate is {coupon["estimated_filament_g"]:.2f} g and {duration(coupon["total_estimated_seconds"])}. '
              f'The four parts total {report["cad_ASA_g"]:.2f} g by native solid volume at 1.05 g/cm³; that is a separate calculation. '
              f'Both Orca plates have zero disconnected floating components in the deposited-path screen. '
              f'The maximum unsupported deposition span is {max(r["max_unsupported_deposition_span_mm"] for r in report["plates"].values()):.2f} mm. '
              'This screens geometric support and does not prove ASA bridge quality.')
    guide=(DOCS/'revh-retainers.html').read_text()
    guide=re.sub(r'<p id="retainer-estimate">.*?</p>','<p id="retainer-estimate">'+estimate+'</p>',guide,flags=re.S)
    (DOCS/'revh-retainers.html').write_text(guide)
    offline=re.sub(r'<section id="model".*?</section>',
        '<section id="model"><figure><img src="assets/revh-retainers-installed.png" alt="Native Rev H-R1 assembly"></figure><p><a href="'+SITE+'revh-retainers.html#model">Open the interactive model online ↗</a></p></section>',guide,flags=re.S)
    offline=re.sub(r'<script.*?</script>','',offline,flags=re.S)
    offline=offline.replace('href="downloads/Precision_5560_RevH_Removable_Retainers_R1.zip" download','href="'+SITE+'revh-retainers.html"')
    offline=offline.replace('Download native model, four parts and fit coupon ↓','Open the online guide ↗')
    for prefix in ['index.html','assets/revh-retainers-validation.json','assets/revh-retainers-release.json','simulation/revh-transient/']:
        offline=offline.replace('href="'+prefix,'href="'+SITE+prefix)
    files['Guide/START_HERE.html']=offline.encode()
    for name in ['style.css','minimalist.css']:
        files['Guide/'+name]=(DOCS/name).read_bytes()
    for image in (DOCS/'assets').glob('revh-retainers-*.png'):
        files['Guide/assets/'+image.name]=image.read_bytes()
    for path in (OUT/'print').iterdir():
        if path.is_file():files['Print/'+path.name]=path.read_bytes()
    report_bytes=(json.dumps(report,indent=2)+'\n').encode()
    files['Evidence/release-report.json']=report_bytes
    files['START-HERE.txt']=('''REV H-R1 REMOVABLE RETAINERS — PROTOTYPE

Open Guide/START_HERE.html for illustrated fitting and installation.
First print Print/01_right_arm_fit_test.3mf and test it on your right arm.
Then print Print/00_four_retainer_parts.3mf once: both bars and both keepers.
The individual files 15-18 are alternatives, not additional required parts.
Keep the supplied orientation and scale. Use OrcaSlicer and re-slice for your ASA.

The fourteen original Rev H parts keep their geometry. This ZIP contains the
four add-on prints, coupon, complete native inspection model and review evidence.
Original Rev H print files remain at:
'''+SITE+'''#print

Orca_Review contains reviewed settings and G-code for inspection. Standard 3MFs
in Print contain geometry only. Physical fit, retention, stiffness and ASA creep
remain untested. Do the coupon and a supported trial before loading the mount.
''').encode()
    for license_path in [ROOT/'LICENSE',ROOT/'LICENSE.md']:
        if license_path.exists():files[license_path.name]=license_path.read_bytes()
    checks=''.join(sha(data)+'  '+name+'\n' for name,data in sorted(files.items()))
    files['SHA256SUMS.txt']=checks.encode()
    archive=DOCS/'downloads/Precision_5560_RevH_Removable_Retainers_R1.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for name,data in sorted(files.items()):z.writestr(name,data)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for line in z.read('SHA256SUMS.txt').decode().splitlines():
            digest,name=line.split('  ',1);assert sha(z.read(name))==digest
    report['download']={'file':archive.name,'bytes':archive.stat().st_size,'sha256':sha(archive.read_bytes())}
    (OUT/'release-report.json').write_text(json.dumps(report,indent=2)+'\n')
    shutil.copy2(OUT/'release-report.json',DOCS/'assets/revh-retainers-release.json')
    shutil.copy2(OUT/'validation.json',DOCS/'assets/revh-retainers-validation.json')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
