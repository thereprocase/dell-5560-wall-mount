"""Build the public D4 hotpatch download and its Gridline guide."""
from pathlib import Path
import hashlib,html,json,re,shutil,zipfile
R=Path(__file__).resolve().parents[1];O=Path(__file__).resolve().parent;D=R/'docs'
NAME='Precision_5560_RevH_D4_Socket_Hotpatch.zip'
TAG='revh-d4-socket-hotpatch-2026-09-09'
REPO='https://github.com/thereprocase/dell-5560-wall-mount'
SITE='https://thereprocase.github.io/dell-5560-wall-mount/'
P=O/'package';P.mkdir(exist_ok=True)
assert not list(P.iterdir()),'Use a fresh package directory; preserve any prior build'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def copy(source,target):
 dest=P/target;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest);return dest
native=O/'Precision_5560_RevH_D4_Current.FCStd'
validation=json.loads((O/'final-validation.json').read_text())
assert validation['passed'] and validation['current_sha256']==sha(native)
assert json.loads((O/'parameter-validation.json').read_text())['all_defaults_restored']
copy(native,'CAD/'+native.name);copy(R/'LICENSE','LICENSE.txt')
for name in ['build-report.json','final-validation.json','parameter-validation.json','printed-repair-validation.json','gui-preservation.json','boolean-probe.json','parameter-placement-probe.json','preset-provenance.json']:
 copy(O/name,'Evidence/'+name)
copy(O/'evidence/pin-hole-obstruction.json','Evidence/pin-hole-obstruction.json')
projects=[]
for key in ['03_left_fan_duct','04_right_fan_duct']:
 project=O/'slices'/key/(key+'.gcode.3mf');audit=json.loads((O/'reports'/(key+'.json')).read_text())
 assert all(audit['acceptance'].values()) and sha(project)==audit['mesh_equivalence'][-1]['sha256']
 with zipfile.ZipFile(project) as z:
  assert z.testzip() is None
  code=z.read(next(n for n in z.namelist() if n.endswith('.gcode')))
  assert hashlib.sha256(code).hexdigest()==audit['source_gcode_sha256']
  g=code.decode();time=re.search(r'total estimated time: ([^\n\r]+)',g)[1];mass=float(re.search(r'filament used \[g\] = ([\d.]+)',g)[1])
 file=key+'_D4.3mf';copy(project,'Orca/'+file)
 for ext in ['stl','step','3mf']:copy(O/'print'/(key+'.'+ext),'Print/'+key+'_D4.'+ext)
 copy(O/'reports'/(key+'.json'),'Evidence/'+key+'-toolpaths.json')
 projects.append({'part':key,'file':file,'estimated_time':time,'estimated_grams':mass,'sha256':sha(project),'max_unsupported_mm':audit['max_unsupported_deposition_span_mm']})
for name in ['D4-current-assembly.png','socket-before-after.png','pin-hole-obstruction.png']:
 copy(O/'images'/name,'Images/'+name)
 target=D/'assets'/('revh-duct-d4-'+name);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(O/'images'/name,target)
for source in (D/'gridline').rglob('*'):
 if source.is_file():copy(source,'gridline/'+source.relative_to(D/'gridline').as_posix())
repair=(O/'REPAIR.md').read_text().replace('(printed-repair-validation.json)','(Evidence/printed-repair-validation.json)').replace('(evidence/pin-hole-obstruction.json)','(Evidence/pin-hole-obstruction.json)')
for p in projects:repair=repair.replace('slices/'+p['part']+'/'+p['part']+'.gcode.3mf','Orca/'+p['file'])
(P/'REPAIR.md').write_text(repair)

def guide(online):
 def image(name):return ('assets/revh-duct-d4-' if online else 'Images/')+name
 native_link=REPO+'/releases/download/'+TAG+'/'+native.name if online else 'CAD/'+native.name
 evidence_link=REPO+'/blob/main/revh_duct_r4/final-validation.json' if online else 'Evidence/final-validation.json'
 checksum= 'assets/revh-duct-d4-release.json' if online else 'SHA256SUMS.txt'
 home='index.html' if online else SITE
 download=('<a class="gl-button" href="downloads/'+NAME+'" download>Download the complete D4 hotpatch ZIP ↓</a>' if online else '<a class="gl-button" href="#print">Choose the left and right Orca projects</a>')
 cards=''
 for row in projects:
  href=REPO+'/releases/download/'+TAG+'/'+row['file'] if online else 'Orca/'+row['file']
  side='Left' if 'left' in row['part'] else 'Right'
  cards+='<article><h3>'+side+' duct · D4</h3><p>'+html.escape(row['estimated_time'])+' · '+str(row['estimated_grams'])+' g estimated PolyLite ASA</p><p><a class="gl-button" href="'+href+'">Open '+side.lower()+' Orca project ↓</a></p><p class="filename">'+row['file']+'</p></article>'
 return '''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Rev H D4 — fan-cover socket hotpatch</title><meta name="gridline-version" content="2026-09-09"><link rel="stylesheet" href="gridline/gridline.css"><link rel="stylesheet" href="gridline/responsive.css"><link rel="stylesheet" href="gridline/interaction.css"><link rel="stylesheet" href="gridline/themes.css"><link rel="icon" href="gridline/logo.svg"><style>
.d4{max-width:1280px}.d4 .gl-brand::after{display:none!important}.d4 h1{font-size:clamp(26px,4vw,42px);line-height:1.15;margin:12px 0 20px}.d4 .intro{margin-bottom:24px}.d4 .intro p{margin-bottom:16px;max-width:75ch}.d4 .gl-pane-title{scroll-margin-top:20px}.d4 .gl-prose p:last-child{margin-bottom:0}.d4 .gl-featured p{min-height:0;margin:12px 0}.d4 .filename{font:12px var(--gl-mono);overflow-wrap:anywhere}.d4 .gl-detail-render img{max-height:610px}.d4 .gl-directory nav a{min-height:44px}.d4 .gl-prose ol{padding-left:22px}.d4 .gl-prose li{margin:12px 0}.d4 .gl-statusbar{flex-wrap:wrap}.d4 .gl-statusbar a{overflow-wrap:anywhere}.d4 .gl-pane-title h2{font:inherit}.d4 .gl-featured article{padding:20px}.d4 .gl-titlebar{flex-wrap:wrap;gap:8px 24px}
@media(max-width:640px){.d4 .gl-featured{grid-template-columns:minmax(0,1fr)}.d4 .gl-featured article{border-right:0;border-bottom:1px solid var(--gl-rule)}.d4 .gl-featured article:last-child{border-bottom:0}}
</style></head><body class="gridline" data-project="dell-5560-wall-mount"><a class="gl-skip" href="#content">Skip to content</a><div class="gl-desktop d4"><div class="gl-titlebar"><a class="gl-brand" href="'''+home+'''"><img src="gridline/logo-white.svg" alt="" width="20" height="20">Laptop wall mount</a><span>REV H / D4 SOCKET HOTPATCH</span></div><nav class="gl-menu" aria-label="Project navigation"><a href="'''+home+'''">Project home</a><a href="#print">Downloads</a><a href="#repair">Repair printed ducts</a><a href="#evidence">Validation</a><a href="'''+REPO+'''/tree/main/revh_duct_r4">Source ↗</a></nav><div class="gl-workspace"><aside class="gl-directory"><div class="gl-caption">D4 · 9 SEPTEMBER 2026</div><nav aria-label="Contents"><a href="#change">What changed</a><a href="#print">Print replacements</a><a href="#repair">Clear existing prints</a><a href="#evidence">Checks and limits</a></nav><div class="gl-directory-note"><strong>Ducted Rev H</strong><p>Two replacement ducts. Four blind fan-cover pin sockets.</p></div></aside><main class="gl-content" id="content"><div class="intro"><p class="gl-kicker">REV H D4 / PROTOTYPE HOTPATCH</p><h1>Clear fan-cover pin sockets.</h1><p>D4 removes the duct-wall material that crossed the four pin sockets. It keeps their original 4.1 mm diameter and blind bottoms.</p>'''+download+'''<p style="margin-top:16px"><a href="'''+native_link+'''">Download the current editable FreeCAD model ↓</a></p></div><p class="gl-caution">CAD and Orca toolpath checks pass. Physical pin seating, retention and removal after this correction still need confirmation.</p><section class="gl-pane" id="change"><div class="gl-pane-title"><h2>What changed</h2></div><div class="gl-prose"><p>The earlier construction cut the bosses, then added the sloping duct shell. That union restored plastic inside the holes. D4 repeats the original bore cuts after the finished duct union.</p><p>The fix removes about <strong>42.08 mm³ per duct</strong> within the original bores. The arm interfaces and tray grooves are preserved. All other installed parts match the bundled prepatch model.</p></div><figure class="gl-detail-render"><img src="'''+image('socket-before-after.png')+'''" alt="Actual old and D4 Orca paths: the old shell crosses the socket and the corrected passage is clear"><figcaption>Actual G-code centerlines at one formerly blocked socket. The audit checks all four sockets; the dashed outline marks the nominal blind bore.</figcaption></figure></section><section class="gl-pane" id="print"><div class="gl-pane-title"><h2>Print two replacement ducts</h2></div><div class="gl-prose"><p>Open each <strong>.3mf as an OrcaSlicer project</strong> to keep its geometry, orientation, support enforcer and reviewed settings. The projects use a Bambu Lab P1S, 0.4 mm nozzle, Polymaker PolyLite ASA, 0.20 mm layers, six walls and 100% rectilinear infill. Review the settings for the actual printer and spool before printing.</p><p>The ZIP also includes STL, STEP and geometry-only 3MF alternatives. Those formats do not include the complete process setup.</p></div><div class="gl-featured">'''+cards+'''</div><div class="gl-prose"><p><strong>Native-model scope:</strong> the full assembly includes the earlier D3 duct reinforcement, T3 selected tray fit, R2 retainers/keepers and two optional B1 rear baffles. Those fit revisions are newer than the older public C1 snapshot. This hotpatch supplies only the two duct prints; the exact prepatch source and checks are included in the repository.</p></div><figure class="gl-detail-render"><img src="'''+image('D4-current-assembly.png')+'''" alt="D4 current FreeCAD assembly with grey arms, teal ducts and orange covers and retainers"><figcaption>The current native assembly reopened in FreeCAD, with its saved appearance restored. The socket correction is internal.</figcaption></figure></section><section class="gl-pane" id="repair"><div class="gl-pane-title"><h2>Clear the sockets in an existing print</h2></div><div class="gl-prose"><p>A controlled cleanup may recover an existing duct. The following dimensions were checked in the nominal model; the physical result is still unconfirmed.</p><ol><li>Use a cooled duct on the bench, with its cover and pin removed. Guide a <strong>4.1 mm drill bit in a hand pin vise</strong> through the existing round opening.</li><li>Set a firm stop so the <strong>tip enters at most 6.0 mm from the flat duct socket face</strong>. Keep the bit aligned with the hole, turn slowly by hand and clear chips.</li><li>Repeat for all four sockets, two per duct. These are <strong>blind holes</strong>. Their CAD bottom is 7.7 mm deep; that is not a drilling target.</li><li>Refit the cover and pin. Confirm seating, retention and removal by hand. Stop if it binds; do not hammer the pin or deepen the hole past the stop.</li></ol><p>The 6.0 mm limit includes the pointed tip. Model checks with 90°, 118° and 135° drill points leave at least 1.7 mm to the blind bottom, clear the unwanted pin obstruction and preserve intended crown contact. Plastic can remain behind the pin tip without obstructing it.</p></div></section><section class="gl-pane" id="evidence"><div class="gl-pane-title"><h2>Checks and limits</h2></div><div class="gl-prose"><ul><li>20 valid installed solids; only the two ducts change against the prepatch assembly.</li><li>Both local bores are clear through their nominal depth. Four pins pass nine sampled withdrawal positions with no contact outside the intended split crown.</li><li>Socket diameter and duct-root radius edits restore successfully. Socket diameter drives the matching pins as well as their bores.</li><li>Exported, prepared and sliced meshes match. No floating model or support islands were detected; maximum unsupported deposition span is about 6.44 mm.</li><li>The same sampled toolpath test detects the old socket obstruction and finds no model or support extrusion in the D4 passage samples.</li></ul><p style="margin-top:20px">These checks do not establish printed dimensions, support removal, strength, ASA creep or physical pin forces. <a href="'''+evidence_link+'''">Read the native validation</a> · <a href="'''+checksum+'''">Checksums and release record</a>.</p></div></section></main></div><footer class="gl-statusbar"><span>Rev H D4</span><span>CAD + toolpaths checked</span><span>Physical pin fit pending</span><a href="'''+REPO+'''/tree/main/revh_duct_r4">Source and evidence ↗</a></footer></div></body></html>'''

(P/'START_HERE.html').write_text(guide(False))
(D/'revh-duct-d4.html').write_text(guide(True))
rows={f.relative_to(P).as_posix():sha(f) for f in sorted(P.rglob('*')) if f.is_file()}
(P/'SHA256SUMS.txt').write_text(''.join(digest+'  '+name+'\n' for name,digest in rows.items()))
zip_path=D/'downloads'/NAME;zip_path.parent.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
 for f in sorted(P.rglob('*')):
  if f.is_file():
   info=zipfile.ZipInfo(f.relative_to(P).as_posix(),date_time=(2026,9,9,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,f.read_bytes())
with zipfile.ZipFile(zip_path) as z:
 assert z.testzip() is None
 for name,digest in rows.items():assert hashlib.sha256(z.read(name)).hexdigest()==digest,name
report={'revision':'H-D4 socket hotpatch','tag':TAG,'native_sha256':sha(native),'source_prepatch_sha256':validation['previous_current_sha256'],'qualification':'CAD and toolpath checks passed; physical pin seating, retention and removal pending.','projects':projects,'download':{'file':NAME,'bytes':zip_path.stat().st_size,'sha256':sha(zip_path),'members':len(rows)+1,'all_member_hashes_verified':True}}
(O/'release-report.json').write_text(json.dumps(report,indent=2)+'\n');(D/'assets/revh-duct-d4-release.json').write_text(json.dumps(report,indent=2)+'\n')
assets=O/'release-assets';assets.mkdir(exist_ok=True)
for f in [zip_path,native]:shutil.copy2(f,assets/f.name)
for row in projects:shutil.copy2(P/'Orca'/row['file'],assets/row['file'])
(assets/'SHA256SUMS.txt').write_text(''.join(sha(f)+'  '+f.name+'\n' for f in sorted(assets.iterdir()) if f.is_file() and f.name!='SHA256SUMS.txt'))
for key in ['03_left_fan_duct','04_right_fan_duct']:shutil.copy2(O/'print'/(key+'.stl'),D/'downloads'/(key+'_D4.stl'))
print(json.dumps(report,indent=2))
