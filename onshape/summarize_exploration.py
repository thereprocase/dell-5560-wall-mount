"""Validate cached checkpoint evidence and write a compact machine-readable handoff."""
import json
from pathlib import Path

OUT=Path(__file__).resolve().parent/'exploration_20'
ledger=[json.loads(line) for line in (OUT/'requests.jsonl').read_text().splitlines()]
features=json.loads((OUT/'29-final-feature-tree.json').read_text())['data']
assembly=json.loads((OUT/'30-final-assembly.json').read_text())['data']['rootAssembly']
assert len(ledger)==34 and [r['attempt'] for r in ledger]==list(range(1,35))
assert len({r['label'] for r in ledger})==34
assert all(s['featureStatus']=='OK' for s in features['featureStates'].values())
assert len(features['features'])==4
assert len(assembly['instances'])==len(assembly['occurrences'])==4
assert sorted(round(o['transform'][3]*1000) for o in assembly['occurrences'])==[-135,-5,5,135]
summary=dict(attempts_used=34,authorized_total=40,remaining=6,
    http_responses=33,sandbox_blocked_attempts=1,mcp_calls=0,
    feature_ids=[dict(id=f['featureId'],type=f['featureType'],name=f['name'],
                     constraint_count=len(f.get('constraints',[]))) for f in features['features']],
    assembly_occurrence_paths=[o['path'] for o in assembly['occurrences']],
    shared_variables_assigned=38,nominal_restored=True,
    parameter_test='pinHeadRadius 4 -> 4.5 -> 4 mm; geometric response measured',
    limitations=['Only pin modeled; other ten distinct parts pending',
                 'Occurrences positioned but not fixed/mated',
                 'Split anchor remains fixed at nominal coordinates',
                 'Only head-radius perturbation tested; solver DOF not queried',
                 'OCCT direct volume integration discrepancy retained'],
    geometry_comparison=json.loads((OUT/'pin_geometry_comparison.json').read_text()))
(OUT/'checkpoint.json').write_text(json.dumps(summary,indent=2)+'\n')
print('Checkpoint verified: 34/40 attempts, 4 healthy native features, 4 positioned pin occurrences.')
