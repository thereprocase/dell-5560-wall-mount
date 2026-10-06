"""Compare downloaded .deb hashes to authenticated APT package metadata."""
import apt
import hashlib
import json
import pathlib
import subprocess
import datetime
import shutil
import re
import io
import tarfile
root=pathlib.Path('/mnt/f/Code/dell-5560-wall-mount/fusion/cfd/vendor/openfoam')
cache=apt.Cache();rows=[]
planned=set(re.findall(r'^Inst (\S+)',(root/'install-plan.txt').read_text(),re.MULTILINE))
for path in sorted(pathlib.Path('/var/cache/apt/archives').glob('*.deb')):
    fields=subprocess.check_output(['dpkg-deb','-f',str(path),'Package','Version'],text=True).splitlines()
    metadata=dict(line.split(': ',1) for line in fields)
    name=metadata['Package'];version=metadata['Version']
    if name not in planned:continue
    if name not in cache:continue
    versions=[v for v in cache[name].versions if v.version==version]
    if not versions:continue
    published=versions[0].record.get('SHA256')
    actual=hashlib.sha256(path.read_bytes()).hexdigest()
    if not published:raise RuntimeError('Missing authenticated hash for '+name)
    row={'package':name,'version':version,'filename':path.name,'bytes':path.stat().st_size,
         'sha256':actual,'apt_index_sha256':published,'matches':actual==published,
         'origins':[{'site':o.site,'origin':o.origin,'archive':o.archive,'trusted':o.trusted} for o in versions[0].origins]}
    rows.append(row)
    if actual!=published:raise RuntimeError('HASH MISMATCH '+name)
    if name.startswith('openfoam2412'):
        (root/'debs').mkdir(exist_ok=True)
        shutil.copy2(path,root/'debs'/path.name)
        control=subprocess.check_output(['dpkg-deb','--ctrl-tarfile',str(path)])
        (root/(name+'-control.tar')).write_bytes(control)
        with tarfile.open(fileobj=io.BytesIO(control)) as archive:
            scripts={m.name:archive.extractfile(m).read().decode('utf-8') for m in archive.getmembers()
                     if m.name.rsplit('/',1)[-1] in ('preinst','postinst','prerm','postrm','triggers')}
            row['maintainer_scripts']=scripts
            for script,content in scripts.items():print(name,script,content[:4000])
inrelease=list(pathlib.Path('/var/lib/apt/lists').glob('*openfoam*InRelease'))
signatures=[]
for path in inrelease:
    p=subprocess.run(['gpgv','--keyring','/usr/share/keyrings/dell5560-openfoam.gpg',str(path)],capture_output=True,text=True)
    signatures.append({'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'returncode':p.returncode,'output':p.stderr})
    shutil.copy2(path,root/'InRelease')
    if p.returncode:raise RuntimeError('Repository signature verification failed')
report={'verified_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'key_fingerprint':'DC93C096174122E256DA24063386DD74948D208F',
        'key_bootstrap':'Official dl.openfoam.com HTTPS; no separate out-of-band fingerprint confirmation',
        'signatures':signatures,'packages':rows,'all_hashes_match':all(r['matches'] for r in rows)}
if not signatures or {r['package'] for r in rows}!=planned:raise RuntimeError('Incomplete audit')
(root/'package_audit.json').write_text(json.dumps(report,indent=2))
print(f'Verified {len(rows)} package hashes against signed indexes; OpenFOAM InRelease signature valid.')
