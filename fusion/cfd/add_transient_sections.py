"""Add bounded high-frequency cut-plane outputs before the first solve."""
from pathlib import Path
import argparse
import json
import shutil

BASE=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--case',type=Path,default=BASE/'runs/revh_transient_04')
args=parser.parse_args()
case=args.case.resolve()
assert not (case/'log.pimpleFoam').exists()
control=case/'system/controlDict'
text=control.read_text()
assert 'edge_sections' not in text
shutil.copy2(control,case/'config/controlDict.before_sections')
planes=[]
for side,x in [('left',-.111),('right',.111)]:
    for region,a,b in [('front',(x-.001,.025,-.008),(x+.001,.075,.035)),('hinge',(x-.001,.025,.208),(x+.001,.075,.262))]:
        vec=lambda p:'('+' '.join(str(v) for v in p)+')'
        planes.append(f'''{side}_{region} {{type cuttingPlane; planeType pointAndNormal;
 pointAndNormalDict {{point ({x} 0 0); normal (1 0 0);}}
 bounds {vec(a)} {vec(b)}; interpolate true;}}''')
addition='''
 edge_sections {
  type surfaces; libs (sampling);
  writeControl runTime; writeInterval .0001;
  surfaceFormat vtk; interpolationScheme cellPoint;
  fields (p U vorticity Q);
  surfaces {'''+ '\n'.join(planes)+'''}
 }
'''
head,tail=text.rsplit('}',1)
control.write_text(head+addition+'}\n'+tail,encoding='ascii',newline='\n')
shutil.copy2(control,case/'config/controlDict.transient')
meta=json.loads((case/'case_manifest.json').read_text())
meta['section_output']={'interval_s':.0001,'fields':['p','U','vorticity','Q'],'format':'VTK','planes':4,
                        'purpose':'Local transient animation with actual recorded timestamps; complete 3D fields remain less frequent.'}
(case/'case_manifest.json').write_text(json.dumps(meta,indent=2)+'\n')
print('Added four bounded planes at 0.1 ms output intervals')
