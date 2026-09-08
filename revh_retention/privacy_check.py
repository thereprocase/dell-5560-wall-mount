"""Apply the project's public-artifact privacy screen to the H-R1 addition."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
checker=ROOT/'minimalist/privacy_check.py'
# Reuse the existing pattern and nested-archive scanner without running its
# separate Minimalist release entry point or rewriting its historical report.
namespace={'__file__':str(checker)}
exec(compile(checker.read_text().split('\npaths=[]')[0],str(checker),'exec'),namespace)
paths=[]
for p in (ROOT/'revh_retention').rglob('*'):
    if not p.is_file() or any(s in ('slices','__pycache__') for s in p.parts):continue
    if p.suffix.lower() in ('.fcstd1','.fcbak') or '.FCStd' in p.name and p.suffix!='.FCStd':continue
    if p.name=='privacy-review.json' or p.parent.name=='browser' and p.suffix=='.png':continue
    paths.append(p)
paths += [ROOT/'README.md',ROOT/'docs/index.html',ROOT/'docs/revh-retainers.html',ROOT/'docs/retainers.js']
paths += list((ROOT/'docs/assets').glob('revh-retainers-*'))
paths += list((ROOT/'docs/models/retainers').rglob('*'))
paths += [ROOT/'docs/downloads/Precision_5560_RevH_Removable_Retainers_R1.zip']
for p in paths:
    if p.is_file():namespace['scan'](str(p.relative_to(ROOT)),p.read_bytes())
result={**namespace['counts'],'findings':namespace['findings'],'pass':not namespace['findings'],
        'scope':'H-R1 source, native metadata, print files, reports, root README, main and retainer pages, model assets and nested delivery archive.',
        'images':'Published images are native CAD renders and an actual deposited-path plot; reviewed without application chrome or personal data.'}
(ROOT/'revh_retention/reports/privacy-review.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
if not result['pass']:raise SystemExit(1)
