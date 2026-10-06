"""Inspect the cached official OpenAPI schema without Onshape requests."""
import json
import sys
from pathlib import Path
import yaml

P = Path(__file__).resolve().parent / 'research_sources'
CACHE = P / 'openapi.json'
if not CACHE.exists():
    schema = yaml.load((P / 'openapi.yaml').read_text(), Loader=getattr(yaml, 'CSafeLoader', yaml.SafeLoader))
    CACHE.write_text(json.dumps(schema, default=str))
else:
    schema = json.loads(CACHE.read_text())
for name in sys.argv[1:]:
    result = schema['paths'].get(name) if name.startswith('/') else schema['components']['schemas'].get(name)
    print(name, json.dumps(result, indent=2))
