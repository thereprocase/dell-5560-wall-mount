"""Read-only audit of installed files against local dpkg package metadata.

This complements the authenticated-APT archive SHA256 check; it does not create
independent publisher trust or guarantee that software is harmless.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parent
archive_audit = json.loads((root / "package_audit.json").read_text())
rows = []
for expected in archive_audit["packages"]:
    name = expected["package"]
    query = subprocess.run(
        ["dpkg-query", "-W", "-f=${Package}\t${Version}\t${Architecture}\t${Status}\n", name],
        capture_output=True, text=True,
    )
    fields = query.stdout.strip().split("\t")
    verify = subprocess.run(["dpkg", "--verify", name], capture_output=True, text=True)
    md5_paths = [Path("/var/lib/dpkg/info") / f"{name}.md5sums"]
    if len(fields) == 4:
        md5_paths.append(Path("/var/lib/dpkg/info") / f"{name}:{fields[2]}.md5sums")
    md5_path = next((path for path in md5_paths if path.is_file()), None)
    metadata = md5_path.read_bytes() if md5_path else None
    rows.append({
        "package": name,
        "expected_version_from_archive_audit": expected["version"],
        "installed_version": fields[1] if len(fields) == 4 else None,
        "installed_status": fields[3] if len(fields) == 4 else None,
        "version_matches": len(fields) == 4 and fields[1] == expected["version"],
        "query_exit_code": query.returncode,
        "query_stderr": query.stderr,
        "verify_command": ["dpkg", "--verify", name],
        "verify_exit_code": verify.returncode,
        "verify_stdout": verify.stdout,
        "verify_stderr": verify.stderr,
        "no_discrepancies_reported": verify.returncode == 0 and not verify.stdout.strip() and not verify.stderr.strip(),
        "dpkg_md5sums_file": str(md5_path) if md5_path else None,
        "dpkg_md5sums_sha256": hashlib.sha256(metadata).hexdigest() if metadata else None,
        "tracked_md5_entries": len(metadata.splitlines()) if metadata else 0,
    })

configuration = []
for filename in (
    "/usr/share/keyrings/dell5560-openfoam.gpg",
    "/etc/apt/sources.list.d/dell5560-openfoam.list",
    "/etc/apt/preferences.d/dell5560-openfoam",
):
    path = Path(filename)
    content = path.read_bytes()
    configuration.append({
        "path": str(path), "sha256": hashlib.sha256(content).hexdigest(),
        "content": content.decode() if path.suffix != ".gpg" else "binary keyring; fingerprint in preinstall audit",
    })

signature = subprocess.run(
    ["gpgv", "--keyring", "/usr/share/keyrings/dell5560-openfoam.gpg", str(root / "InRelease")],
    capture_output=True, text=True,
)
report = {
    "audited_at_utc": datetime.now(timezone.utc).isoformat(),
    "scope": "27 packages in original authenticated-APT installation plan; read-only installed-file verification",
    "package_audit_sha256": hashlib.sha256((root / "package_audit.json").read_bytes()).hexdigest(),
    "package_count": len(rows),
    "openfoam_packages": [r["package"] for r in rows if r["package"].startswith("openfoam")],
    "all_installed_versions_match_archive_audit": all(r["version_matches"] and r["installed_status"] == "install ok installed" for r in rows),
    "all_dpkg_verifications_report_no_discrepancies": all(r["no_discrepancies_reported"] for r in rows),
    "tracked_md5_entry_count": sum(r["tracked_md5_entries"] for r in rows),
    "packages": rows,
    "repository_configuration": configuration,
    "retained_inrelease_signature_recheck": {"exit_code": signature.returncode, "stdout": signature.stdout, "stderr": signature.stderr},
    "limitations": [
        "dpkg verification compares current files to local installed-package metadata, principally MD5 content records; it is not an independent signature check on each installed file.",
        "Files absent from package checksum metadata, generated caches and every system configuration file are not comprehensively covered.",
        "The archive SHA256 trust chain is recorded separately in package_audit.json; this report does not establish an independent publisher identity.",
        "The OpenFOAM key was bootstrapped from the official HTTPS endpoint without separate out-of-band fingerprint authentication.",
        "A content match is integrity evidence, not a malware audit or proof of numerical correctness.",
    ],
}
path = root / "installed_integrity.json"
if path.exists():
    raise SystemExit(f"Refusing to overwrite prior integrity report: {path}")
path.write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({k: report[k] for k in (
    "package_count", "openfoam_packages", "all_installed_versions_match_archive_audit",
    "all_dpkg_verifications_report_no_discrepancies", "tracked_md5_entry_count",
)}, indent=2))
for row in rows:
    if not row["no_discrepancies_reported"]:
        print(row["package"], row["verify_stdout"], row["verify_stderr"])
