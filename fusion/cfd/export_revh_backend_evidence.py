"""Export compact evidence from the isolated WSL CPU/GPU comparison.

Run in WSL after both benchmarks and native field comparison. Raw meshes and
volume fields remain in their original cases; this does not publish by itself.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--comparison',type=Path,required=True)
    p.add_argument('--smoke-comparison',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--mesh-root',type=Path)
    p.add_argument('--method',type=Path)
    args=p.parse_args();out=args.output;out.mkdir(parents=True,exist_ok=False)
    comparison=json.loads(args.comparison.read_text())
    comparison['reference']='duct_cpu_02';comparison['candidate']='duct_gpu_01'
    (out/'field-comparison.json').write_text(json.dumps(comparison,indent=2)+'\n')
    smoke=json.loads(args.smoke_comparison.read_text())
    smoke['reference']='smoke_cpu_02';smoke['candidate']='smoke_gpu_03'
    (out/'small-case-comparison.json').write_text(json.dumps(smoke,indent=2)+'\n')
    runs={}
    for label,case_name in [('cpu','duct_cpu_02'),('gpu','duct_gpu_01')]:
        case=args.root/case_name
        state=json.loads((case/'benchmark-status.json').read_text())
        assert state['state']=='completed_pending_field_comparison'
        log=(case/'log.pimpleFoam').read_text()
        entries=[]
        for line in (case/'gpu-samples.csv').read_text().splitlines():
            columns=line.split(',')
            if len(columns)==4:
                try:entries.append([int(columns[2]),int(columns[3])])
                except ValueError:pass
        net=float(re.findall(r'sum\(ambient_openings\) of phi = ([\d.e+-]+)',log)[-1])
        absolute=float(re.findall(r'sumMag\(ambient_openings\) of phi = ([\d.e+-]+)',log)[-1])
        clocks=state['reported_clock_times_s']
        runs[label]={
            'case':case_name,'backend':'OpenFOAM GAMG' if label=='cpu' else 'OGL CUDA GKOCG with block Jacobi',
            'solve_wall_seconds':state['phases']['solve']['wall_seconds'],
            'mean_step_seconds_after_first_three':(clocks[-1]-clocks[2])/(len(clocks)-3),
            'pressure_iterations_total':state['pressure_iterations_total'],
            'pressure_calls':state['pressure_calls'],'max_pressure_iterations':state['pressure_iterations_max'],
            'bounding_events':state['bounding_events'],'max_logged_Courant':max(state['courant_max_values']),
            'final_net_flux_m3_s':net,'final_sum_absolute_flux_m3_s':absolute,
            'final_relative_mass_imbalance':2*abs(net)/absolute,
            'observed_total_device_memory_MiB':[min(v[0] for v in entries),max(v[0] for v in entries)],
            'observed_device_utilization_percent':[min(v[1] for v in entries),max(v[1] for v in entries)]}
        state['source']='revh_sequence_05' if label=='cpu' else 'duct_cpu_02'
        (out/(label+'-run-status.json')).write_text(json.dumps(state,indent=2)+'\n')
        for name in ['log.pimpleFoam','gpu-samples.csv']:
            shutil.copy2(case/name,out/(label+'-'+name.replace('log.','')+'.txt' if name.startswith('log.') else label+'-'+name))
        for name in ['controlDict','fvSolution','fvSchemes','decomposeParDict']:
            shutil.copy2(case/'system'/name,out/(label+'-'+name+'.txt'))
        for name in ['fvOptions','transportProperties','turbulenceProperties']:
            shutil.copy2(case/'constant'/name,out/(label+'-'+name+'.txt'))
    report={
        'date_utc':'2026-09-08','recommendation':'Keep the CPU backend for the next run; tested GPU backend is not accepted.',
        'scope':'Backend commissioning on a mesh with known defects; not mesh convergence, hardware validation, sustained shedding or settled suction.',
        'mesh_cells':3193565,'source_mesh':'revh_sequence_05','steps':10,'dt_s':1e-5,'end_time_s':1e-4,
        'ranks':4,'initialization':'Identical quiescent U and identical p/k/omega/nut; no mapped Revision F fields.',
        'hardware':'NVIDIA GeForce RTX 3080 Ti, 12 GiB nominal, WSL CUDA 12.4',
        'openfoam':'2412 patch 260127; double precision, 32-bit labels',
        'OGL_commit':'d3e80f4651ebe8b7383af4b746a6c3a43f87bc3e',
        'Ginkgo_commit':'ac44187f33ed1aa0c0fe9436dc86b25a860374ba',
        'runs':runs,'gpu_over_cpu_wall_ratio':runs['gpu']['solve_wall_seconds']/runs['cpu']['solve_wall_seconds'],
        'field_comparison_passed':comparison['passed'],
        'comparison_detail':'All field RMS errors pass; maximum local errors in U and p exceed the preset atol 1e-7 plus rtol 1e-4 times the reference maximum.',
        'memory_timing_limits':'Single sequential run per backend on a shared desktop, not a repeated dedicated-machine performance study. Device memory/utilization are total-device 500 ms samples, including other applications. One 1.4 s geometry render ran near GPU-case setup. Timing includes solver startup, function objects and endpoint field writing; excludes mesh preparation, decomposition and reconstruction.',
        'other_trials':[{'case':'smoke_gpu_01','result':'Multigrid/scaling -1: CUDA illegal memory access.'},
                        {'case':'smoke_gpu_02','result':'Block Jacobi/scaling -1: exited zero but numerically rejected; pressure grew to billions.'},
                        {'case':'smoke_gpu_03','result':'Block Jacobi/scaling 1: all five fields pass against the 4800-cell CPU reference.'},
                        {'case':'smoke_gpu_04','result':'Multigrid/scaling 1/ranksPerGPU 4: CUDA illegal memory access.'},
                        {'case':'smoke_gpu_05','result':'Multigrid/scaling 1/ranksPerGPU 1: CUDA illegal memory access.'}],
        'source_mesh_limits':'Four low-determinant cells, 71820 concave cells and poor wall-layer coverage. Standard checks pass, expanded checks fail two. Used for a bounded backend benchmark only.',
        'long_video_status':'No replacement long sequence has been completed. The published startup movie still has four actual source frames.'}
    (out/'benchmark.json').write_text(json.dumps(report,indent=2)+'\n')
    if args.method:shutil.copy2(args.method,out/'METHOD.md')
    if args.mesh_root:
        for number in ['05','06','07']:
            target=out/('mesh-'+number);target.mkdir()
            for name in ['case_manifest.json','log.checkMesh.standard','log.checkMesh.expanded','status.mesh.json']:
                shutil.copy2(args.mesh_root/('revh_sequence_'+number)/name,target/name)
    paths=[path for path in sorted(out.rglob('*')) if path.is_file()]
    # Published text uses LF, consistent with this package's .gitattributes.
    # Original logs and binary input fields are retained in the source cases.
    for path in paths:path.write_bytes(path.read_bytes().replace(b'\r\n',b'\n'))
    hashes={path.relative_to(out).as_posix():digest(path) for path in paths}
    (out/'sha256.json').write_text(json.dumps(hashes,indent=2)+'\n')
    print(json.dumps({'runs':runs,'gpu_over_cpu_wall_ratio':report['gpu_over_cpu_wall_ratio'],'field_comparison_passed':comparison['passed']},indent=2))


if __name__=='__main__':main()
