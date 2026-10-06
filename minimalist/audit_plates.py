"""Audit all feature types, reusing only byte-identical parsed extrusion paths."""
from pathlib import Path
import concurrent.futures
import hashlib
import json
import shutil
import time
from gcode_audit import read_paths, audit

ROOT=Path(__file__).resolve().parent


def run(path):
    folder=Path(path).parent
    report=audit(Path(path),folder/'bridge-review.png')
    (folder/'toolpath-audit.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def main():
    groups={}
    for path in sorted((ROOT/'slices').glob('*/*/preview.gcode')):
        layers,header=read_paths(path)
        digest=hashlib.sha256(json.dumps(layers,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        comments=[l for l in header if any(t in l for t in ('model printing time:','estimated printing time','filament used [g]','total filament weight','filament used [mm]','filament used [cm3]'))]
        groups.setdefault(digest,[]).append((path,comments))
    print('Auditing',sum(map(len,groups.values())),'plates as',len(groups),'unique deposited-path traces',flush=True)
    tasks=[]
    with concurrent.futures.ProcessPoolExecutor(max_workers=3) as pool:
        for digest,items in groups.items():
            representative=None
            for path,comments in items:
                dest=path.parent/'toolpath-audit.json'
                if dest.exists():
                    existing=json.loads(dest.read_text())
                    if 'max_unsupported_deposition_span_mm' in existing and existing.get('source_gcode_sha256')==hashlib.sha256(path.read_bytes()).hexdigest():
                        representative=(path,existing)
                        break
            if representative:
                future=concurrent.futures.Future();future.set_result(representative[1])
                tasks.append((future,digest,items,representative[0]))
            else:
                first=items[0][0]
                tasks.append((pool.submit(run,str(first)),digest,items,first))
        for future,digest,items,source in tasks:
            report=future.result()
            for path,comments in items:
                result={**report,'source_gcode_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                        'analysis_geometry_sha256':digest,'time_and_material_comments':comments}
                if path!=source:
                    result['identical_deposited_path_trace_as']=str(source.relative_to(ROOT/'slices'))
                    shutil.copy2(source.parent/'bridge-review.png',path.parent/'bridge-review.png')
                (path.parent/'toolpath-audit.json').write_text(json.dumps(result,indent=2)+'\n')
            print(str(source.relative_to(ROOT/'slices')),'all-feature span',round(report['max_unsupported_deposition_span_mm'],3),'floating',len(report['floating_components']),'reused',len(items)-1,flush=True)


if __name__=='__main__':main()
