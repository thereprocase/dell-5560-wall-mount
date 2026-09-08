"""Provision an unprivileged Ubuntu 24.04 x86_64 topology environment.

Extracts hash-pinned distro packages locally. Does not use apt or alter /usr.
"""
import hashlib,json,subprocess,sys,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parent
RUNTIME=ROOT/'runtime'
def main():
    RUNTIME.mkdir(exist_ok=True)
    packages=json.loads((ROOT/'packages.json').read_text())
    for d in packages:
        p=RUNTIME/Path(d['url']).name
        if not p.exists():
            with urllib.request.urlopen(d['url']) as r:p.write_bytes(r.read())
        if hashlib.sha256(p.read_bytes()).hexdigest()!=d['sha256']:raise RuntimeError('Checksum mismatch: '+str(p))
        subprocess.run(['dpkg-deb','-x',str(p),str(RUNTIME)],check=True)
    beso=RUNTIME/'beso'
    if not beso.exists():subprocess.run(['git','clone','https://github.com/calculix/beso.git',str(beso)],check=True)
    sha=json.loads((ROOT/'results/environment.json').read_text())['beso_commit']
    subprocess.run(['git','-C',str(beso),'checkout','--detach',sha],check=True)
    venv=RUNTIME/'venv'
    if not venv.exists():subprocess.run([sys.executable,'-m','venv',str(venv)],check=True)
    subprocess.run([str(venv/'bin/python'),'-m','pip','install','-r',str(ROOT/'requirements.txt')],check=True)
    print('Run: '+str(venv/'bin/python')+' '+str(ROOT/'run_pipeline.py'))
if __name__=='__main__':main()
