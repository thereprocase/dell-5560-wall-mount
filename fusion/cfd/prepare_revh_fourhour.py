"""Prepare a fresh monitored Rev H continuation, retaining restart history."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--case',type=Path,required=True)
    p.add_argument('--source-time',default='0.0001')
    p.add_argument('--mirror',type=Path,required=True)
    args=p.parse_args();source=args.source.resolve();case=args.case.resolve()
    assert (source/args.source_time/'U').is_file()
    case.mkdir(parents=True,exist_ok=False)
    for name in ['constant','system',args.source_time]:shutil.copytree(source/name,case/name)
    for rank in range(4):
        for name in ['constant',args.source_time]:
            shutil.copytree(source/f'processor{rank}'/name,case/f'processor{rank}'/name)
    for name in ['case_manifest.json','log.checkMesh.standard','log.checkMesh.expanded']:
        if (source/name).exists():shutil.copy2(source/name,case/name)
    (case/'case.foam').touch()
    meta=json.loads((case/'case_manifest.json').read_text())
    initial_hashes={path.relative_to(case).as_posix():hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in sorted((case/args.source_time).rglob('*')) if path.is_file()}
    control=case/'system/controlDict';text=control.read_text()
    # The physical horizon is a backstop; the driver enforces the wall budget.
    text=re.sub(r'endTime\s+[^;]+;', 'endTime 10;',text,count=1)
    text=re.sub(r'deltaT\s+[^;]+;', 'deltaT .000025;',text,count=1)
    text=text.replace('adjustTimeStep no;','adjustTimeStep yes;')
    text=re.sub(r'maxCo\s+[^;]+;', 'maxCo .5;',text,count=1)
    text=re.sub(r'maxDeltaT\s+[^;]+;', 'maxDeltaT .000025;',text,count=1)
    text=re.sub(r'writeControl\s+[^;]+;', 'writeControl clockTime;',text,count=1)
    text=re.sub(r'writeInterval\s+[^;]+;', 'writeInterval 1800;',text,count=1)
    text=text.replace('runTimeModifiable true;','runTimeModifiable false;')
    # Replace function objects so sampling has no narrow bounds that discard
    # coarse cut cells. Both complete planes can support multiple close-ups.
    text=text[:text.index('functions {')]
    probes=meta.get('probes',[])
    probe_locations='\n'.join('('+' '.join(str(v) for v in q['point_m'])+')' for q in probes)
    text+='''functions {
 extrema {type fieldMinMax; libs (fieldFunctionObjects); fields (U p k omega); writeControl timeStep; writeInterval 1;}
 vorticity {type vorticity; libs (fieldFunctionObjects); executeControl timeStep; executeInterval 2; writeControl writeTime;}
 Q {type Q; libs (fieldFunctionObjects); executeControl timeStep; executeInterval 2; writeControl writeTime;}
 yPlus {type yPlus; libs (fieldFunctionObjects); executeControl writeTime; writeControl writeTime;}
 ambient_flux {type surfaceFieldValue; libs (fieldFunctionObjects); regionType patch; name ambient_openings;
  operation sum; fields (phi); writeFields false; writeControl timeStep; writeInterval 1;}
 ambient_abs_flux {type surfaceFieldValue; libs (fieldFunctionObjects); regionType patch; name ambient_openings;
  operation sumMag; fields (phi); writeFields false; writeControl timeStep; writeInterval 1;}
 edge_sections {type surfaces; libs (sampling); writeControl timeStep; writeInterval 2;
  surfaceFormat vtk; interpolationScheme cellPoint; fields (p U vorticity Q);
  surfaces {
   right_section {type cuttingPlane; planeType pointAndNormal;
    pointAndNormalDict {point (.111 0 0); normal (1 0 0);} interpolate true;}
   left_section {type cuttingPlane; planeType pointAndNormal;
    pointAndNormalDict {point (-.111 0 0); normal (1 0 0);} interpolate true;}
  }
 }
'''
    if probes:text+='probes {type probes; libs (sampling); fields (p U); interpolationScheme cellPoint; writeControl timeStep; writeInterval 1; probeLocations ('+probe_locations+');}\n'
    text+='}\n'
    control.write_text(text)
    meta.update(scope='Extended exploratory startup; known mesh defects; not validation.',
                continuation={'source_case':source.name,'source_time_s':float(args.source_time),
                              'initialization':'Exact same-Rev-H CPU fields including U_0, phi_0, k_0, omega_0 and uniform time history; no Revision F mapping.',
                              'field_hashes':initial_hashes},
                mesh_source='revh_sequence_05',ranks=4,
                requested_max_Co=.5,requested_max_deltaT_s=25e-6,
                section_output={'planes':[-.111,.111],'bounds':None,'interval_steps':2,
                                'fields':['p','U','vorticity','Q'],'format':'VTK XML polydata'},
                publication='Hourly real-sample video checkpoints; no interpolated CFD states.')
    (case/'case_manifest.json').write_text(json.dumps(meta,indent=2)+'\n')
    (case/'quality-disposition.json').write_text(json.dumps({
        'case':case.name,'disposition':'commissioning_only','validation_accepted':False,
        'mesh':'revh_sequence_05, 3193565 cells','known_defects':'4 low-determinant cells, 71820 concave cells, poor wall-layer coverage',
        'purpose':'User-authorized four-hour monitored exploratory continuation and hourly videos.',
        'guards':'Adaptive maxCo .5, maxDeltaT 25us, field extrema and flux histories, half-hour full checkpoints, wall-time stop.',
        'interpretation':'Three visible cycles would be an observation, not established periodic statistics or hardware validation.'},indent=2)+'\n')
    args.mirror.mkdir(parents=True,exist_ok=False)
    shutil.copy2(case/'case_manifest.json',args.mirror/'case_manifest.json')
    shutil.copy2(case/'quality-disposition.json',args.mirror/'quality-disposition.json')
    print(json.dumps({'case':str(case),'mirror':str(args.mirror),'start_time_s':float(args.source_time)},indent=2))


if __name__=='__main__':main()
