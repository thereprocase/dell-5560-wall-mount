"""One-request-at-a-time Onshape exploration; durable hard cap, no retries.

Usage: python onshape/explore_native.py LABEL METHOD SUFFIX [BODY.json]
SUFFIX is relative to the fixed target Part Studio. Credentials never enter logs.
"""
import base64
import json
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'onshape' / 'exploration_20'
TARGET = '/api/v9/partstudios/d/c452b7f3224726ea2f11cdda/w/3231ffbfcf00782c1dba2494/e/cf9a24a5d90f7bf7ae0d3004'
CAP = 40  # User raised this exploration's total cap from 20 to 40.

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def main():
    label, method, suffix, *bodyfile = sys.argv[1:]
    OUT.mkdir(exist_ok=True)
    ledger = OUT / 'requests.jsonl'
    count = len(ledger.read_text().splitlines()) if ledger.exists() else 0
    if count >= CAP:
        raise SystemExit(f'{CAP}-request cap reached')
    if any(OUT.glob(f'*-{label}.json')):
        raise SystemExit('Label already used; inspect checkpoint before repeating')
    env = {}
    for line in (ROOT / '.env').read_text().splitlines():
        if '=' in line and not line.lstrip().startswith('#'):
            key, value = line.split('=', 1)
            env[key.strip()] = value.strip().strip('\"\'')
    body = Path(bodyfile[0]).read_bytes() if bodyfile else None
    if body is not None:
        json.loads(body)
    path = suffix if suffix.startswith('/api/') else TARGET + suffix
    known_translation_paths = set()
    for saved in OUT.glob('*.json'):
        try:
            data = json.loads(saved.read_text()).get('data', {})
            if isinstance(data, dict) and data.get('documentId') == 'c452b7f3224726ea2f11cdda' and data.get('href','').startswith('https://cad.onshape.com/api/') and '/translations/' in data['href']:
                known_translation_paths.add(data['href'].removeprefix('https://cad.onshape.com'))
        except (ValueError, AttributeError):
            pass
    if '/d/c452b7f3224726ea2f11cdda/' not in path and path not in known_translation_paths:
        raise SystemExit('Only the authorized document is allowed')
    auth = base64.b64encode((env['ONSHAPE_ACCESS_KEY'] + ':' + env['ONSHAPE_SECRET_KEY']).encode()).decode()
    req = urllib.request.Request('https://cad.onshape.com' + path, data=body, method=method,
        headers={'Authorization': 'Basic ' + auth, 'Accept': 'application/json', 'Content-Type': 'application/json'})
    n = count + 1
    record = dict(attempt=n, label=label, method=method, path=path,
                  timestamp=datetime.now(timezone.utc).isoformat())
    if body is not None:
        (OUT / f'{n:02}-{label}-request.json').write_bytes(body)
    # Reserve before I/O; timeout or uncertain result still consumes the attempt.
    with ledger.open('a') as f:
        f.write(json.dumps(record) + '\n')
        f.flush()
    try:
        response = urllib.request.build_opener(NoRedirect).open(req, timeout=90)
        status, raw = response.status, response.read()
    except urllib.error.HTTPError as e:
        status, raw = e.code, e.read()
    except Exception as e:
        print(json.dumps(dict(attempt=n, error=type(e).__name__, status='uncertain; do not retry automatically')))
        return
    if raw.startswith(b'ISO-10303-21;'):
        artifact = OUT / f'{n:02}-{label}.step'
        artifact.write_bytes(raw)
        result = {'artifact': artifact.name, 'bytes': len(raw)}
    else:
        try:
            result = json.loads(raw)
        except ValueError:
            result = {'body': raw.decode(errors='replace')}
    (OUT / f'{n:02}-{label}.json').write_text(json.dumps({'status': status, 'data': result}, indent=2))
    print(json.dumps(dict(attempt=n, remaining=CAP-n, status=status, data=result)))

if __name__ == '__main__':
    main()
