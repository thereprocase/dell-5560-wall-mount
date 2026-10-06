"""Prepare a 600-cell box to verify new transient dictionary/function-object IO."""
from pathlib import Path
import json
import re
import shutil
import argparse
from generate_case import foam_header

BASE=Path(__file__).resolve().parent
source=BASE/'runs/revh_transient_04'
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--case',type=Path,default=BASE/'runs/pimple_runtime_smoke_01')
args=parser.parse_args()
case=args.case.resolve()
case.mkdir(parents=True,exist_ok=False)
for folder in ['0','constant','system']:(case/folder).mkdir()
for name in ['U','p','k','omega','nut']:
    initial=source/'initial_fields_before_mapping'
    if not initial.exists():initial=source/'0'
    shutil.copy2(initial/name,case/'0'/name)
p=case/'0/U'
p.write_text(re.sub(r'internalField\s+uniform\s+\([^)]*\)','internalField uniform (0 0 .1)',p.read_text()))
for name in ['controlDict','fvSchemes','fvSolution','decomposeParDict']:
    shutil.copy2(source/'system'/name,case/'system'/name)
# The fine-run sample boxes are thinner than these coarse box cells. Expand only
# the smoke-case clipping bounds so the IO test exercises nonempty surfaces.
p=case/'system/controlDict'
text,count=re.subn(r'bounds\s+\([^)]*\)\s+\([^)]*\);',
                  'bounds (-.432 -.032 -.336) (.432 .480 .528);',p.read_text())
assert count==4
p.write_text(text)
for name in ['turbulenceProperties','transportProperties']:
    shutil.copy2(source/'constant'/name,case/'constant'/name)
(case/'system/blockMeshDict').write_text(foam_header('blockMeshDict')+'''
scale 1;
vertices ((-.432 -.032 -.336) (.432 -.032 -.336) (.432 .480 -.336) (-.432 .480 -.336)
          (-.432 -.032 .528) (.432 -.032 .528) (.432 .480 .528) (-.432 .480 .528));
blocks (hex (0 1 2 3 4 5 6 7) (10 6 10) simpleGrading (1 1 1));
edges ();
boundary (
 printed {type wall; faces ((0 4 7 3));}
 laptop {type wall; faces ((1 2 6 5));}
 noctua {type wall; faces ((3 7 6 2));}
 wall_plane {type wall; faces ((0 1 5 4) (0 3 2 1));}
 ambient_openings {type patch; faces ((4 5 6 7));}
);
mergePatchPairs ();
''')
(case/'case.foam').touch()
(case/'case_manifest.json').write_text(json.dumps({'scope':'runtime_smoke_only','cells':600,
    'purpose':'Test pimpleFoam SST, backward/linearUpwind schemes, Spalding walls and the actual probe/section function dictionaries.',
    'limitations':'Box geometry without actuators or prism layers; sample clipping boxes expanded to span coarse cells. Not airflow-model, parallel-solver or fine-mesh validation.',
    'dictionary_source':source.name},indent=2)+'\n')
print(case)
