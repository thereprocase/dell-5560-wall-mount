"""Build the final saved-data report and link it from existing CFD landings."""
from pathlib import Path
import json,re
ROOT=Path(__file__).resolve().parents[2]
SEQ=ROOT/'docs/simulation/revh-transient/sequence';OUT=SEQ/'final'
data=json.loads((OUT/'summary.json').read_text(encoding='utf-8'))
original=(SEQ/'index.html').read_text(encoding='utf-8')
head=original.split('<main>')[0].replace('../../../','../../../../')
head=re.sub(r'<title>.*?</title>','<title>Final Rev H CFD results · thereprocase</title>',head)
head=re.sub(r'<nav class="gl-outline".*?</nav>','<nav class="gl-outline" aria-label="On this page"><span>CONTENTS</span><a href="#overview">Final record</a><a href="#lip">Lip measurements</a><a href="#startup">Startup</a><a href="#flowing">Already flowing</a><a href="#downloads">Downloads</a></nav>',head,flags=re.S)
def fig(href,alt,caption):return f'<figure><a href="{href}"><img src="{href}" alt="{alt}" loading="lazy" width="1980" height="1100"></a><figcaption>{caption} <a href="{href}">Open full image ↗</a></figcaption></figure>'
def links(items):return '<ul class="links">'+''.join(f'<li><a href="{href}">{label} ↗</a></li>' for label,href in items)+'</ul>'
parts=['''<main><nav><a href="../">← Final flow videos</a> · <a href="../../../../">Mount designs</a></nav><div class="eyebrow">REVISION H / FINAL SAVED RESULTS / 9 SEPTEMBER 2026</div><h1 id="overview">More from the recorded flow.</h1><p class="lede">Final pressure, speed and vorticity maps with velocity arrows, complete saved probe histories, and updated local lip-flow measurements. Everything here comes from existing output; no additional simulation was run.</p><div class="metrics"><div class="metric"><strong>96.26 ms</strong><span>Startup · 2,552 probe snapshots</span></div><div class="metric"><strong>69.44 ms</strong><span>Flowing initialization · 4,008 probe snapshots</span></div><div class="metric"><strong>22 probes</strong><span>Pressure + velocity at each saved probe time</span></div></div><p>The clocks belong to separate runs. The flowing-field maps use the final saved state at 69.44 ms; its particle video ends slightly earlier, at 68.09 ms. The startup video already reaches its final saved state.</p><h2 id="lip">What the lip measurements show</h2><p>Both final snapshots have outward and inward flow across the front opening at the sampled side sections. Net flow is outward. The late-window wall-side lip probes are below the ambient-reference probe; the magnitude depends on position and initialization.</p>''']
rows=[]
for phase,label in [('startup','Startup'),('flowing','Already flowing')]:
    d=data['phases'][phase]
    for side,x in [('left','-0.111'),('right','0.111')]:
        stats=next(p for p in d['probe_statistics'] if p['probe']=='front_lip_wallside_x'+x)
        rows.append(f'<tr><th scope="row">{label} / {side}</th><td>{d["window_s"][0]*1000:.2f}–{d["window_s"][1]*1000:.2f} ms</td><td>{stats["pressure_relative_ambient_Pa_mean"]:.3f} Pa</td><td>{stats["pressure_relative_ambient_Pa_rms_fluctuation"]:.3f} Pa</td></tr>')
parts.append('<div class="table-wrap"><table><thead><tr><th>Wall-side lip probe</th><th>Averaging window</th><th>Mean relative pressure</th><th>Pressure fluctuation RMS</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table></div><p class="small">Time-weighted mean and RMS over the final 10 ms, using piecewise-linear interpolation. These are local point measurements in the model, not a surface suction load.</p>')
rows=[]
for phase,label in [('startup','Startup'),('flowing','Already flowing')]:
    d=data['phases'][phase]
    for side in ['left','right']:
        front=d['final_section_flux'][side]['front_opening'];up=d['final_section_flux'][side]['upward_channel']
        rows.append(f'<tr><th scope="row">{label} / {side}</th><td>{front["positive_flux_m2_s"]:.5f}</td><td>{front["negative_flux_m2_s"]:.5f}</td><td>{front["net_flux_m2_s"]:.5f}</td><td>{up["net_flux_m2_s"]:.5f}</td></tr>')
parts.append('<h3>Final local volume flux per unit span / m²/s</h3><div class="table-wrap"><table><thead><tr><th>Section at X = ±111 mm</th><th>Front outward</th><th>Front inward</th><th>Front net outward</th><th>Channel net upward</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table></div><p>The front line joins the divider tip to the laptop nose shoulder. The upward cut is at Z = 20.001 mm. These line integrals are <b>per unit span</b>, not full-width L/s, fan delivery, or a closed three-dimensional flow balance. Exact definitions and covered fluid lengths are in the summary download.</p><p class="notice">The model is isothermal: it does not calculate battery, lid or surface cooling. Negative local pressure alone does not establish a Bernoulli mechanism. The mesh and faster visual timesteps remain exploratory; no validated shedding frequency or steady-state claim is made.</p>')
for phase,label in [('startup','Startup / final saved field'),('flowing','Already flowing / final saved field')]:
    d=data['phases'][phase]
    parts.append(f'<section id="{phase}"><h2>{label}</h2><p>Final sampled time: <b>{d["through_time_s"]*1000:.5f} ms</b>. Pressure maps use the solver reference and the same ±12 Pa scale. Arrows show actual in-plane velocity at X = +111 mm, with CAD outlines.</p>')
    parts.append(fig(phase+'/pressure-arrows.png',label+' pressure map with flow arrows','Complete air path, front lip and hinge discharge.'))
    parts.append(links([('Speed with arrows',phase+'/speed-arrows.png'),('Vorticity with arrows',phase+'/vorticity-arrows.png'),('Left sampled VTP',phase+'/left_section.vtp'),('Right sampled VTP',phase+'/right_section.vtp')]))
    parts.append(fig(phase+'/history.png',label+' pressure, speed, Courant and boundary-flux histories','Full saved histories. The green band marks the final 10 ms; plotted probe pressures are relative to the ambient probe.').replace('width="1980" height="1100"','width="1920" height="1200"'))
    if phase=='startup':parts.append('<p>The dashed line marks the change at 38.31885 ms to fixed 80.93 µs visual timesteps. The Courant axis includes the higher values in this extension instead of clipping them to the original adaptive limit.</p>')
    parts.append('</section>')
parts.append('<h2 id="downloads">Data, provenance and earlier evidence</h2><p>The CSV downloads retain all 22 probes, including left, center-right and right positions. JSON includes source hashes. Statistics use physical-time weighting, so the change in sampling interval does not overweight the earlier adaptive segment.</p>')
parts.append(links([('Combined summary JSON','summary.json')]))
for phase,label in [('startup','Startup'),('flowing','Already flowing')]:
    parts.append('<h3>'+label+'</h3>'+links([('Probe summary CSV',phase+'/probe-summary.csv'),('Full probes CSV · gzip',phase+'/probes.csv.gz'),('Solver history CSV · gzip',phase+'/solver-history.csv.gz'),('Diagnostics + source hashes · gzip',phase+'/diagnostics.json.gz')]))
parts.append('<p>The <a href="../#gl-section-7">iteration-400 steady images</a>, <a href="../#gl-section-9">early full-width opening integrals</a> and <a href="../../../installed-airflow-2026-09-07/">earlier installed-airflow package</a> retain their original labels and provenance. They represent different numerical states or earlier geometry, so their numbers are not relabeled as these final transient results.</p><p>Older compressed diagnostic downloads were rebuilt where decompression failed, using original checkpoint files and their recorded content hashes. <a href="archive-repair.json">Archive repair record</a>.</p><footer class="small">Simulation remains stopped and resumable. This report reads preserved output only. Source scripts: <a href="https://github.com/thereprocase/dell-5560-wall-mount/tree/main/fusion/cfd">CFD post-processing tools</a>.</footer></main></body></html>')
(OUT/'index.html').write_text(head+''.join(parts),encoding='utf-8')
entry='<p class="notice"><strong>Final saved-data report:</strong> <a href="final/">Updated arrow maps, full histories, lip-flow measurements and downloadable data</a> through 96.26 ms startup and 69.44 ms flowing initialization.</p>'
if 'href="final/"' not in original:
    original=original.replace('<h1>Revision H airflow, recorded.</h1>','<h1>Revision H airflow, recorded.</h1>'+entry)
    original=original.replace('<span>CONTENTS</span>','<span>CONTENTS</span><a href="final/">Final results &amp; data ↗</a>',1)
    (SEQ/'index.html').write_text(original,encoding='utf-8')
p=SEQ/'flowing/index.html';text=p.read_text(encoding='utf-8')
if 'href="../final/"' not in text:
    text=text.replace('<main>','<main><p class="notice"><a href="../final/#flowing">Final saved-field plots and complete probe histories</a> now cover 69.44 ms, including the saved tail after this video.</p>',1);p.write_text(text,encoding='utf-8')
p=ROOT/'README.md';text=p.read_text(encoding='utf-8')
if 'sequence/final/' not in text:
    text+='\n## Final CFD results\n\n[Final arrow maps, full probe histories and lip-flow data](https://thereprocase.github.io/dell-5560-wall-mount/simulation/revh-transient/sequence/final/) use preserved output through 96.26 ms startup and 69.44 ms flowing initialization. No further simulation was run. [Watch the final particle videos](https://thereprocase.github.io/dell-5560-wall-mount/simulation/revh-transient/sequence/).\n'
    p.write_text(text,encoding='utf-8')
print('Built final results page and existing landing links.')
