"""Independently screen the four supplied C1 plate layouts' deposited paths."""
from pathlib import Path
import json
import hashlib
import shutil
import sys
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'revh_cables'
sys.path.insert(0,str(ROOT/'minimalist'))
from gcode_audit import audit


def main():
    reports=OUT/'reports';reports.mkdir(exist_ok=True)
    rows=[]
    for group in ['full','coupon']:
        summary=json.loads((OUT/'slices'/group/'slice_summary.json').read_text())
        for row in summary:
            assert row['exit_code']==0,row
            name=Path(row['source']).stem;folder=OUT/'slices'/group/name
            output=reports/(name+'-toolpath.json');plot=reports/(name+'-toolpath.png')
            digest=hashlib.sha256((folder/'preview.gcode').read_bytes()).hexdigest()
            result=json.loads(output.read_text()) if '--reuse-unchanged' in sys.argv and output.exists() and plot.exists() else None
            if result is None or result['source_gcode_sha256']!=digest:
                result=audit(folder/'preview.gcode',plot)
                output.write_text(json.dumps(result,indent=2)+'\n')
            receipt={'plate':name,'floating_components':len(result['floating_components']),
                     'bridge_max_mm':result['max_unsupported_bridge_span_mm'],
                     'all_feature_max_mm':result['max_unsupported_deposition_span_mm']}
            rows.append(receipt);print(json.dumps(receipt),flush=True)
    assert len(rows)==4
    (reports/'toolpath-summary.json').write_text(json.dumps(rows,indent=2)+'\n')
    shutil.copy2(reports/'00_cable_fit_coupon-toolpath.png',ROOT/'docs/assets/revh-cables-toolpaths.png')
    assert not any(r['floating_components'] for r in rows),rows
    assert all(r['all_feature_max_mm']<10 for r in rows),rows


if __name__=='__main__':main()
