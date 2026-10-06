"""Refuse wrong/missing/disconnected fluid boundaries before solving."""
from pathlib import Path
import re
expected = {"fan_left", "fan_right", "outlet", "laptop_shell", "wall_plane", "assumed_side_seals", "printed_or_model_walls"}
text = Path("constant/polyMesh/boundary").read_text()
text = re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)
found = {}
for name, body in re.findall(r"([A-Za-z_][A-Za-z_0-9]*)\s*\{([^{}]*)\}", text):
    count = re.search(r"\bnFaces\s+(\d+)\s*;", body)
    kind = re.search(r"\btype\s+(\w+)\s*;", body)
    if count:
        found[name] = (int(count.group(1)), kind.group(1) if kind else "")
for name in expected:
    if name not in found or found[name][0] <= 0:
        raise SystemExit("Missing/empty required mesh patch: " + name)
    target = "patch" if name in {"fan_left", "fan_right", "outlet"} else "wall"
    if found[name][1] != target:
        raise SystemExit("Incorrect mesh patch type: " + name)
for name, (count, _) in found.items():
    if name not in expected and count:
        raise SystemExit("Unexpected nonempty patch (fluid selection/leak risk): " + name)
report = Path("log.checkMesh").read_text()
if not re.search(r"Number of regions:\s+1\b", report):
    raise SystemExit("Single connected fluid region not established by checkMesh")
print("Seven nonempty named patches and one connected region confirmed.")
