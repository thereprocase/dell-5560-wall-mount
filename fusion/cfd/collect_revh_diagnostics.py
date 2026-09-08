"""Copy a time-bounded diagnostic snapshot from the live WSL CFD case.

The solver remains untouched. Rows and log blocks are limited to the latest
physical time in the already-rendered hourly progress.json. Raw full histories
remain in the case; these published excerpts are hashed separately.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import math
from pathlib import Path
import re

NUMBER=r'[-+]?(?:\d*\.)?\d+(?:[eE][-+]?\d+)?'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();out=args.output
    progress=json.loads((out/'progress.json').read_text());end=progress['last_time_s']
    manifest=json.loads((args.case/'case_manifest.json').read_text())
    warm=manifest.get('initialization_kind')=='steady_solver'
    start_folder='0' if warm else '0.0001'
    raw=out/'diagnostic-raw';raw.mkdir(exist_ok=False)
    excerpts={};hashes={};unavailable=[]
    for function,files in {'probes':['p','U'],'extrema':['fieldMinMax.dat'],
                           'ambient_flux':['surfaceFieldValue.dat'],
                           'ambient_abs_flux':['surfaceFieldValue.dat'],'yPlus':['yPlus.dat']}.items():
        for name in files:
            source=args.case/'postProcessing'/function/start_folder/name
            if function=='yPlus' and not source.is_file():
                unavailable.append('yPlus: no full-field write yet');continue
            selected=[]
            for line in source.read_text().splitlines():
                if line.startswith('#') or not line.strip():selected.append(line)
                elif float(line.split()[0])<=end+1e-13:selected.append(line)
            text='\n'.join(selected)+'\n';destination=raw/(function+'-'+name+'.txt')
            destination.write_text(text)
            excerpts[(function,name)]=text
            hashes[destination.relative_to(out).as_posix()]=hashlib.sha256(text.encode()).hexdigest()
    log=(args.case/'log.pimpleFoam.fourhour').read_text(errors='replace')
    entries=list(re.finditer(r'^Time = ('+NUMBER+r')\s*\n(.*?)(?=^Time = |\Z)',log,re.M|re.S))
    included=[m for m in entries if float(m[1])<=end+1e-13 and 'ExecutionTime =' in m[2]]
    assert included
    log=log[:included[-1].end()]
    (raw/'solver-log.txt').write_text(log)
    hashes['diagnostic-raw/solver-log.txt']=hashlib.sha256(log.encode()).hexdigest()
    history=[]
    for entry in included:
        body=entry[2]
        def last(pattern):
            matches=re.findall(pattern,body)
            return float(matches[-1]) if matches else None
        row={'time_s':float(entry[1]),'solver_wall_seconds':last(r'ClockTime = ('+NUMBER+')'),
             'max_speed_m_s':last(r'max\(mag\(U\)\) = ('+NUMBER+')'),
             'min_pressure_Pa':last(r'min\(p\) = ('+NUMBER+')'),
             'max_pressure_Pa':last(r'max\(p\) = ('+NUMBER+')'),
             'max_Courant_after_step':last(r'Courant Number mean: [^ ]+ max: ('+NUMBER+')'),
             'ambient_net_flux_m3_s':last(r'sum\(ambient_openings\) of phi = ('+NUMBER+')'),
             'ambient_absolute_flux_m3_s':last(r'sumMag\(ambient_openings\) of phi = ('+NUMBER+')')}
        for key in ['min_pressure_Pa','max_pressure_Pa']:row[key]*=1.2
        row['ambient_net_to_absolute_flux_ratio']=abs(row['ambient_net_flux_m3_s'])/row['ambient_absolute_flux_m3_s']
        assert all(v is None or math.isfinite(v) for v in row.values())
        history.append(row)
    probe_data={}
    for field in ['p','U']:
        rows=[]
        for line in excerpts[('probes',field)].splitlines():
            if not line.strip() or line.startswith('#'):continue
            values=[float(v) for v in re.findall(NUMBER,line)]
            assert len(values)==1+len(manifest['probes'])*(1 if field=='p' else 3)
            assert all(math.isfinite(v) and abs(v)<1e100 for v in values)
            rows.append(values)
        probe_data[field]=rows
    assert [r[0] for r in probe_data['p']]==[r[0] for r in probe_data['U']]
    assert abs(probe_data['p'][-1][0]-end)<1e-12
    probes=[]
    for i,location in enumerate(manifest['probes']):
        pressures=[r[i+1]*1.2 for r in probe_data['p']]
        velocity=[r[1+3*i:4+3*i] for r in probe_data['U']]
        probes.append({**location,'pressure_Pa':pressures,'velocity_m_s':velocity,
                       'speed_m_s':[math.sqrt(sum(v*v for v in row)) for row in velocity]})
    bounds=[{'field':field,'minimum':float(value)} for field,value in re.findall(r'^bounding (\w+), min: ('+NUMBER+')',log,re.M)]
    report={'captured_utc':datetime.now(timezone.utc).isoformat(),'through_time_s':end,
            'initialization_kind':manifest.get('initialization_kind','native_transient_startup'),
            'unavailable_diagnostics':unavailable,
            'hour_checkpoint':progress['hour_checkpoint'],'density_kg_m3':1.2,
            'history':history,'probe_times_s':[r[0] for r in probe_data['p']],'probes':probes,
            'new_bounding_events':len(re.findall(r'^bounding ',log,re.M)),
            'negative_value_bounding_events':sum(b['minimum']<0 for b in bounds),
            'positive_floor_bounding_events':sum(b['minimum']>=0 for b in bounds),
            'bounding_details':bounds,
            'final_diagnostics':history[-1],'raw_excerpt_sha256':hashes,
            'raw_excerpt_definition':'Complete text lines and solver time blocks through the last video sample; full source files preserved locally.'}
    (out/'diagnostics.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'hour':progress['hour_checkpoint'],'through_time_s':end,'rows':len(history),
                      'final':history[-1],'bounding_events':report['new_bounding_events']},indent=2))


if __name__=='__main__':main()
