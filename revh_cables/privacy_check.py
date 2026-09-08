"""Screen C1 source, native metadata, media and nested public download contents."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
checker=ROOT/'minimalist/privacy_check.py'
namespace={'__file__':str(checker)}
exec(compile(checker.read_text().split('\npaths=[]')[0],str(checker),'exec'),namespace)
paths=[]
for p in (ROOT/'revh_cables').rglob('*'):
    if not p.is_file() or any(s in ('slices','__pycache__') for s in p.parts):continue
    if p.suffix.lower() in ('.fcstd1','.fcbak'):continue
    if p.name=='privacy-review.json' or p.parent.name=='browser' and p.suffix=='.png':continue
    paths.append(p)
paths += [ROOT/p for p in ['README.md','MAKERWORLD_BRIEFING.md','docs/index.html','docs/revh-cables.html','docs/cables.js','docs/cables.css']]
paths += list((ROOT/'docs/assets').glob('revh-cables-*'))
paths += list((ROOT/'docs/models/cables').rglob('*'))
download=ROOT/'docs/downloads/Precision_5560_RevH_Cable_Management_C1.zip'
assert download.is_file(),'Build the final download before its public-content scan'
paths += [download]
for p in paths:
    if p.is_file():namespace['scan'](str(p.relative_to(ROOT)),p.read_bytes())
result={**namespace['counts'],'findings':namespace['findings'],'pass':not namespace['findings'],
    'scope':'C1 source, native metadata, print exports, reports, guides, root entry points, model assets and nested download archive.',
    'images':'Native CAD views, explicitly labeled reference cable and actual deposited-path plots; no application chrome.'}
(ROOT/'revh_cables/reports/privacy-review.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
if not result['pass']:raise SystemExit(1)
