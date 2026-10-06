"""Recheck retained download identities; does not install or execute payloads.

Expected hashes come from the preserved acquisition audit. A match detects drift
since acquisition; it does not independently authenticate an unsigned publisher.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def verify():
    baram = json.loads((ROOT / 'audit.json').read_text(encoding='utf-8-sig'))
    expected = []
    for row in baram['binaries']:
        relative = row['path'].split('fusion/cfd/vendor/', 1)[1]
        expected.append((relative, row['sha256']))
    for row in baram['source']['pinned_files']:
        expected.append((row['path'], row['sha256']))
    openfoam = json.loads((ROOT / 'openfoam/package_audit.json').read_text())
    for row in openfoam['packages']:
        if row['package'].startswith('openfoam2412'):
            expected.append(('openfoam/debs/' + row['filename'], row['sha256']))
    expected += [
        ('openfoam/pubkey.gpg', 'E6DDD89ED33131A4FC63460CB131AE7416A2A0062B590F4237121598626EDF86'),
        ('openfoam/add-debian-repo.sh', 'F7FA288327E936B5A85E3E4A0B29BF039C06D214916F39400B830B63A3310B5B'),
    ]
    results = []
    for relative, wanted in expected:
        path = ROOT / relative
        actual = sha256(path) if path.is_file() else None
        results.append({'path': relative, 'expected_sha256': wanted.lower(),
                        'actual_sha256': actual, 'matches': actual == wanted.lower()})
    return {'scope': 'Retained acquisition artifacts; no payload execution or new publisher authentication',
            'all_match': all(row['matches'] for row in results), 'files': results}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = verify()
    encoded = json.dumps(report, indent=2)
    if args.output:
        args.output.write_text(encoded + '\n', encoding='utf-8')
    print(f"{sum(row['matches'] for row in report['files'])}/{len(report['files'])} retained artifact hashes match")
    for row in report['files']:
        if not row['matches']:
            print('MISMATCH OR MISSING:', row['path'])
    raise SystemExit(0 if report['all_match'] else 1)
