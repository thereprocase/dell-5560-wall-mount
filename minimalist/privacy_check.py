"""Scan the new public source, CAD metadata and nested delivery archives."""
from pathlib import Path
import hashlib
import io
import json
import re
import zipfile

ROOT=Path(__file__).resolve().parent
patterns={
    'personal_unix_path':re.compile(r'/(?:home|Users)/[A-Za-z0-9_.-]+/'),
    'personal_windows_path':re.compile(r'[A-Za-z]:[/\\](?:Users|Code)[/\\]',re.I),
    'wsl_host_path':re.compile(r'/mnt/[a-z]/',re.I),
    'private_ipv4':re.compile(r'(?<![\w.-])(?:10\.\d{1,3}|192\.168|172\.(?:1[6-9]|2\d|3[01])|100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7]))\.\d{1,3}\.\d{1,3}(?![\w.-])'),
    'private_key':re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'credential_literal':re.compile(r'''(?i)(?:api[_-]?key|password|access[_-]?token|access[_-]?code)\s*["']?\s*[:=]\s*["']([^\s"',}]{8,})'''),
}
text_suffixes={'.py','.md','.txt','.html','.css','.js','.cjs','.json','.xml','.config','.gcode','.step','.stp','.svg'}
archive_suffixes={'.zip','.3mf','.fcstd'}
seen=set();findings=[];counts={'unique_payloads':0,'text_payloads':0,'archive_payloads':0}


def scan(name,data,depth=0):
    digest=hashlib.sha256(data).hexdigest()
    if digest in seen:return
    seen.add(digest);counts['unique_payloads']+=1
    suffix=Path(name).suffix.lower()
    if suffix in archive_suffixes:
        assert depth<4,name
        counts['archive_payloads']+=1
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            assert z.testzip() is None
            for member in z.namelist():
                if not member.endswith('/'):scan(name+'!'+member,z.read(member),depth+1)
    elif suffix in text_suffixes:
        counts['text_payloads']+=1
        text=data.decode('utf8',errors='replace')
        for kind,pattern in patterns.items():
            if pattern.search(text):findings.append({'file':name,'kind':kind})


paths=[]
for p in ROOT.rglob('*'):
    if not p.is_file():continue
    rel=p.relative_to(ROOT)
    if any(s in ('scratch','snapshots','slices','__pycache__') for s in rel.parts):continue
    if rel.parts[0]=='browser' and p.suffix=='.png':continue
    paths.append(p)
docs=ROOT.parent/'docs'
paths += [docs/p for p in ['index.html','minimalist-guide.html','minimalist-viewer.js','minimalist.css']]
paths += [ROOT.parent/'README.md',ROOT.parent/'MINIMALIST_SPRINT.md']
paths += list((docs/'assets').glob('minimalist-*'))
paths += list((docs/'downloads').glob('Minimalist_M1_*.zip'))
paths += list((ROOT.parent/'print_release_step').rglob('*'))
for p in paths:
    if p.is_file():scan(str(p.relative_to(ROOT.parent)),p.read_bytes())
result={**counts,'findings':findings,'pass':not findings,
    'scope':'New Minimalist source/preset metadata, root README and journal, published M1 assets, nested delivery archives, and Rev H STEP/Orca supplement. Generated local scratch, logs and raw slicer working directories excluded from publication.',
    'image_review':'New published images are native geometry renders, a vector schematic and a toolpath plot; visually reviewed without application chrome or personal data.'}
(ROOT/'reports/privacy-review.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2),flush=True)
if findings:raise SystemExit(1)
