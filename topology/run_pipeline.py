"""Run both searches and the shell/infill assessment with the local runtime."""
import os,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parent;runtime=root/'runtime'
env={**os.environ,'CCX':str(runtime/'usr/bin/ccx'),'BESO_SOURCE':str(runtime/'beso'),
     'LD_LIBRARY_PATH':str(runtime/'usr/lib/x86_64-linux-gnu'),
     'OMP_NUM_THREADS':'2','OPENBLAS_NUM_THREADS':'1','MPLBACKEND':'Agg'}
for script in ['run_study.py','analyze_results.py']:
    subprocess.run([sys.executable,str(root/script)],env=env,cwd=root,check=True)
