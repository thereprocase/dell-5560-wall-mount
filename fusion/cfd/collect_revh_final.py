"""Export existing final samples and diagnostic histories. Never runs OpenFOAM."""
import argparse,csv,gzip,hashlib,json,math,os,re,shutil
from pathlib import Path
NUMBER=r'[-+]?(?:\d*\.)?\d+(?:[eE][-+]?\d+)?'
JOIN=.038318849480432
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def key(t): return round(t,10)
def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    os.nice(19)
    if hasattr(os,'sched_setaffinity'):os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[-2:])
    plan={'startup': [('revh_fourhour_08',0,JOIN,'log.pimpleFoam.fourhour'),('revh_visual_81us_20260909_a3',JOIN,.096264747380438,'log.coarse_visual_extension')],
          'flowing':[('revh_flowing_12',0,.0694402361,'log.pimpleFoam.fourhour')]}
    for phase,segments in plan.items():
        out=args.output/phase;out.mkdir(parents=True,exist_ok=True)
        fields={'p':{},'U':{}};history={};sources={}
        # The current log starts at a restart; immutable hourly exports retain
        # earlier completed log rows. Native rows below supersede overlaps.
        if phase=='startup':
            archives=sorted(args.output.parent.glob('hour-*/diagnostics.json.gz'),key=lambda p:int(p.parent.name.split('-')[-1]))
            for archive in archives:
                with gzip.open(archive,'rt',encoding='utf-8') as f:old=json.load(f)
                sources['published/'+archive.parent.name+'/'+archive.name]=digest(archive)
                for row in old['history']:
                    if row['time_s']>JOIN+1e-10:continue
                    history[key(row['time_s'])]={k:row.get('max_Courant_after_step' if k=='max_Courant_reported' else k) for k in ['time_s','max_speed_m_s','min_pressure_Pa','max_pressure_Pa','max_Courant_reported','ambient_net_flux_m3_s','ambient_absolute_flux_m3_s']}
        for name,lo,hi,logname in segments:
            case=args.root/name;manifest=json.loads((case/'case_manifest.json').read_text())
            for field in fields:
                for source in sorted((case/'postProcessing/probes').glob('*/'+field),key=lambda p:float(p.parent.name)):
                    sources[name+'/'+source.relative_to(case).as_posix()]=digest(source)
                    for line in source.read_text().splitlines():
                        if not line.strip() or line.startswith('#'):continue
                        values=[float(v) for v in re.findall(NUMBER,line)];t=values[0]
                        if t<lo-1e-10 or t>hi+1e-10:continue
                        assert len(values)==1+len(manifest['probes'])*(1 if field=='p' else 3)
                        assert all(math.isfinite(v) and abs(v)<1e100 for v in values)
                        fields[field][key(t)]=values
            lognames=[logname]+(['log.pimpleFoam.fourhour'] if logname=='log.coarse_visual_extension' else [])
            logtext=''
            for filename in lognames:
                source=case/filename;sources[name+'/'+filename]=digest(source)
                logtext+=source.read_text(errors='replace')+'\n'
            for match in re.finditer(r'^Time = ('+NUMBER+r')\s*\n(.*?)(?=^Time = |\Z)',logtext,re.M|re.S):
                t=float(match[1]);body=match[2]
                if t<lo-1e-10 or t>hi+1e-10 or 'ExecutionTime =' not in body:continue
                def last(pattern):
                    hits=re.findall(pattern,body);return float(hits[-1]) if hits else None
                row={'time_s':t,'max_speed_m_s':last(r'max\(mag\(U\)\) = ('+NUMBER+')'),
                     'min_pressure_Pa':last(r'min\(p\) = ('+NUMBER+')'),'max_pressure_Pa':last(r'max\(p\) = ('+NUMBER+')'),
                     'max_Courant_reported':last(r'Courant Number mean: [^ ]+ max: ('+NUMBER+')'),
                     'ambient_net_flux_m3_s':last(r'sum\(ambient_openings\) of phi = ('+NUMBER+')'),
                     'ambient_absolute_flux_m3_s':last(r'sumMag\(ambient_openings\) of phi = ('+NUMBER+')')}
                for k in ['min_pressure_Pa','max_pressure_Pa']:
                    if row[k] is not None:row[k]*=1.2
                history[key(t)]=row
        assert fields['p'].keys()==fields['U'].keys()
        keys=sorted(fields['p']);times=[fields['p'][k][0] for k in keys]
        assert all(a<b for a,b in zip(times,times[1:]))
        assert abs(times[-1]-segments[-1][2])<1e-10
        probes=[]
        for i,probe in enumerate(manifest['probes']):
            velocity=[fields['U'][k][1+3*i:4+3*i] for k in keys]
            probes.append({**probe,'pressure_Pa':[fields['p'][k][i+1]*1.2 for k in keys],
                           'velocity_m_s':velocity,'speed_m_s':[math.sqrt(sum(v*v for v in u)) for u in velocity]})
        rows=[history[k] for k in sorted(history)]
        end_case=args.root/segments[-1][0]
        folders=sorted((end_case/'postProcessing/edge_sections').glob('*'),key=lambda p:float(p.name))
        final=folders[-1];assert abs(float(final.name)-segments[-1][2])<1e-10
        for side in ['left','right']:
            source=final/(side+'_section.vtp');shutil.copy2(source,out/source.name)
            sources[end_case.name+'/'+source.relative_to(end_case).as_posix()]=digest(source)
        report={'phase':phase,'density_kg_m3':1.2,'through_time_s':float(final.name),'probe_times_s':times,'probes':probes,'history':rows,
                'source_sha256':sources,'visual_timestep_change_s':JOIN if phase=='startup' else None,
                'time_merge_policy':'Select startup through the video join, then its visual continuation. Restart overlaps use the newer file. Timestamp keys round to 0.1 ns to reconcile text precision.',
                'scope':'Existing saved solver output only; no simulation or meshing performed. Separate physical clocks for startup and flowing initialization.'}
        with gzip.open(out/'diagnostics.json.gz','wt',encoding='utf-8') as f:json.dump(report,f,separators=(',',':'))
        with gzip.open(out/'solver-history.csv.gz','wt',encoding='utf-8',newline='') as f:
            w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
        with gzip.open(out/'probes.csv.gz','wt',encoding='utf-8',newline='') as f:
            w=csv.writer(f);w.writerow(['time_s','probe','pressure_Pa','U_x_m_s','U_y_m_s','U_z_m_s','speed_m_s'])
            for i,t in enumerate(times):
                for probe in probes:w.writerow([t,probe['name'],probe['pressure_Pa'][i],*probe['velocity_m_s'][i],probe['speed_m_s'][i]])
        print(json.dumps({'phase':phase,'through_time_s':float(final.name),'probe_samples':len(times),'solver_rows':len(rows)}),flush=True)
if __name__=='__main__':main()
