"""Compare reconstructed CPU/GPU fields on an identical mesh and saved time.

Run with Python and NumPy. This is a solver-equivalence check,
not spatial convergence, temporal convergence or hardware validation.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

import numpy as np


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def fields(case,time):
    # Read original doubles directly. VTK can round cell fields to float32,
    # even when its point-coordinate option Use64BitFloats is enabled.
    folders=[]
    for path in case.iterdir():
        if path.is_dir():
            try:
                if float(path.name)==time:folders.append(path)
            except ValueError:pass
    assert len(folders)==1, 'Saved time missing or ambiguous'
    data={}
    for name in ['U','p','k','omega','nut']:
        raw=(folders[0]/name).read_bytes()
        match=re.search(rb'internalField\s+nonuniform\s+List<(scalar|vector)>\s*(\d+)\s*\(',raw)
        assert match, 'Expected a nonuniform scalar/vector field: '+name
        head=raw[:match.start()]
        assert re.search(rb'format\s+binary\s*;',head), 'Expected binary field: '+name
        arch=re.search(rb'arch\s+"(LSB|MSB);label=\d+;scalar=(32|64)"',head)
        assert arch, 'Missing binary architecture: '+name
        components=3 if match[1]==b'vector' else 1
        count=int(match[2])*components
        dtype=np.dtype(('<' if arch[1]==b'LSB' else '>')+'f'+str(int(arch[2])//8))
        end=match.end()+count*dtype.itemsize
        assert raw[end:end+3].lstrip().startswith(b')'), 'Unexpected binary payload length: '+name
        array=np.frombuffer(raw,dtype=dtype,count=count,offset=match.end()).copy().astype(np.float64)
        data[name]=array.reshape(-1,components) if components==3 else array
    return data


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',type=Path,required=True)
    parser.add_argument('--candidate',type=Path,required=True)
    parser.add_argument('--time',type=float,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--rtol',type=float,default=1e-4)
    parser.add_argument('--atol',type=float,default=1e-7)
    args=parser.parse_args()
    cases=[args.reference.resolve(),args.candidate.resolve()]
    hashes={}
    for rel in [f'constant/polyMesh/{name}' for name in ['points','faces','owner','neighbour','boundary','cellZones']]+[f'0/{name}' for name in ['U','p','k','omega','nut']]+['constant/fvOptions','constant/transportProperties','constant/turbulenceProperties','system/fvSchemes']:
        pair=[digest(case/rel) for case in cases]
        assert pair[0]==pair[1], 'Mesh or initialization differs: '+rel
        hashes[rel]=pair[0]
    a,b=[fields(case,args.time) for case in cases]
    results={}
    for name in a:
        assert a[name].shape==b[name].shape
        finite=bool(np.isfinite(a[name]).all() and np.isfinite(b[name]).all())
        error=b[name]-a[name]
        rms_ref=float(np.sqrt(np.mean(a[name]**2)))
        rms_error=float(np.sqrt(np.mean(error**2)))
        max_ref=float(np.max(np.abs(a[name])))
        max_error=float(np.max(np.abs(error)))
        worst_index=np.unravel_index(np.argmax(np.abs(error)),error.shape)
        results[name]={'finite':finite,'values':int(a[name].size),
                       'reference_rms':rms_ref,'error_rms':rms_error,
                       'reference_max_abs':max_ref,'max_abs_error':max_error,
                       'max_error_cell':int(worst_index[0]),
                       'pass':finite and rms_error<=args.atol+args.rtol*rms_ref and max_error<=args.atol+args.rtol*max_ref}
    report={'reference':str(cases[0]),'candidate':str(cases[1]),'physical_time_s':args.time,
            'relative_tolerance':args.rtol,'absolute_tolerance':args.atol,
            'criterion':'Both RMS and maximum field error <= atol + rtol times the corresponding reference magnitude.',
            'reader':'Native OpenFOAM binary internalField values; no VTK field conversion.',
            'identical_input_hashes':hashes,'fields':results,'passed':all(v['pass'] for v in results.values()),
            'scope':'CPU/GPU field comparison only; not CFD validation or independence.'}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    if not report['passed']:raise SystemExit(1)


if __name__=='__main__':main()
