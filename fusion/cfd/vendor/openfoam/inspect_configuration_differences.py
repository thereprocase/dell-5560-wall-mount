"""Compare the two dpkg discrepancies with the authenticated .deb payload."""
from datetime import datetime, timezone
import difflib
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile

root = Path(__file__).resolve().parent
audit = json.loads((root / "package_audit.json").read_text())
package = next(p for p in audit["packages"] if p["package"] == "openfoam2412-common")
archive = root / "debs" / package["filename"]
assert hashlib.sha256(archive.read_bytes()).hexdigest() == package["sha256"]
payload = subprocess.check_output(["dpkg-deb", "--fsys-tarfile", str(archive)])
rows, diffs = [], []
with tarfile.open(fileobj=io.BytesIO(payload)) as tar:
    for basename in ("bashrc", "cshrc"):
        path = Path("/usr/lib/openfoam/openfoam2412/etc") / basename
        member = tar.getmember("." + str(path))
        original = tar.extractfile(member).read()
        installed = path.read_bytes()
        difference = "".join(difflib.unified_diff(
            original.decode().splitlines(keepends=True), installed.decode().splitlines(keepends=True),
            fromfile=f"authenticated-deb/{basename}", tofile=f"installed/{basename}",
        ))
        rows.append({"path": str(path), "archive_sha256": hashlib.sha256(original).hexdigest(),
                     "installed_sha256": hashlib.sha256(installed).hexdigest(), "diff": difference})
        diffs.append(difference)
report = {"audited_at_utc": datetime.now(timezone.utc).isoformat(),
          "source_deb": package["filename"], "source_deb_sha256_verified": package["sha256"],
          "files": rows, "explanation": "Inspect against runtime postinst foamConfigurePaths -project-path and install.log; no installation changes made."}
configure_path = Path("/usr/lib/openfoam/openfoam2412/bin/tools/foamConfigurePaths")
configure_lines = configure_path.read_text().splitlines()
selected_lines = set()
for index, line in enumerate(configure_lines):
    if "IGNORE" in line or "WM_PROJECT_DIR" in line:
        selected_lines.update(range(max(0, index - 3), min(len(configure_lines), index + 5)))
report["foamConfigurePaths_sha256"] = hashlib.sha256(configure_path.read_bytes()).hexdigest()
report["foamConfigurePaths_relevant_source"] = [f"{i+1}: {configure_lines[i]}" for i in sorted(selected_lines)]
(root / "configuration_differences.json").write_text(json.dumps(report, indent=2) + "\n")
(root / "configuration_differences.diff").write_text("\n".join(diffs))
print("\n".join(diffs))
print("\n".join(report["foamConfigurePaths_relevant_source"]))
