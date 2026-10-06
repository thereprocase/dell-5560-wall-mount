"""Read-only installed BARAM audit against the retained MSI's cabinet payload.

Requires locally retained MSI File/Directory tables, Component mapping, and
7-Zip extraction of downloads/baram-cabinet/distfiles. Never executes payloads.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess


BASE = Path(__file__).resolve().parent


def read_json(path):
    raw = path.read_bytes()
    return json.loads(raw.decode("utf-16" if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else "utf-8-sig"))


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify(target):
    source = BASE / "downloads/baram-complete-cabinet-payload"
    tables = read_json(BASE / "downloads/baram-msi-tables.json")
    components = read_json(BASE / "downloads/baram-msi-components.json")
    directories = {r[0]: (r[1], r[2]) for r in tables["Directory"]}
    id_counts = Counter(r[0].casefold() for r in tables["File"])

    def directory_path(key):
        if key == "TARGETDIR":
            return Path()
        parent, raw_name = directories[key]
        if not parent:
            raise ValueError("Unexpected root directory: " + key)
        name = raw_name.split(":", 1)[0].split("|")[-1]
        return directory_path(parent) / ("" if name == "." else name)

    def check(row):
        file_key, component, name, expected_size = row[:4]
        rel = directory_path(components[component]) / name.split("|")[-1]
        original = source / file_key
        installed = target / rel
        if not original.resolve().is_relative_to(source.resolve()) or not installed.resolve().is_relative_to(target):
            raise ValueError("Path escaped retained payload or install root")
        result = {"path": rel.as_posix(), "cabinet_file_id": file_key,
                  "msi_size_bytes": int(expected_size)}
        if id_counts[file_key.casefold()] > 1:
            # CAB File identifiers are case-sensitive; a flat Windows extraction
            # aliases pairs such as Image.pyc/image.pyc from distinct directories.
            # Stream the exact-case member instead, without executing its bytes.
            command = ["C:/Program Files/7-Zip/7z.exe", "x", "-so", "-ssc", "-spd",
                       "-bso0", "-bsp0", str(BASE / "downloads/baram-cabinet/distfiles"), file_key]
            payload = subprocess.run(command, capture_output=True, check=True).stdout
            result["payload_read_method"] = "exact-case cabinet member stream"
            result["payload_size_bytes"] = len(payload)
            result["payload_sha256"] = hashlib.sha256(payload).hexdigest()
        elif not original.is_file():
            result["status"] = "source_missing"
            return result
        else:
            result["payload_read_method"] = "extracted cabinet file"
            result["payload_size_bytes"] = original.stat().st_size
            result["payload_sha256"] = sha256(original)
        if not installed.is_file():
            result["status"] = "installed_missing"
            return result
        result["installed_size_bytes"] = installed.stat().st_size
        result["installed_sha256"] = sha256(installed)
        if result["payload_size_bytes"] != result["msi_size_bytes"]:
            result["status"] = "source_size_mismatch"
        elif result["payload_sha256"] != result["installed_sha256"]:
            result["status"] = "hash_mismatch"
        else:
            result["status"] = "match"
        return result

    with ThreadPoolExecutor(max_workers=8) as pool:
        files = sorted(pool.map(check, tables["File"]), key=lambda r: r["path"].casefold())
    expected = {r["path"].casefold() for r in files}
    extras = [{"path": p.relative_to(target).as_posix(), "size_bytes": p.stat().st_size,
               "sha256": sha256(p)} for p in sorted(target.rglob("*"))
              if p.is_file() and p.relative_to(target).as_posix().casefold() not in expected]
    counts = {status: sum(r["status"] == status for r in files) for status in sorted({r["status"] for r in files})}
    mpi_manifest = BASE / "downloads/Microsoft.msmpi-10.1.12498.18.installer.yaml"
    published = re.search(r"InstallerSha256:\s*([0-9A-Fa-f]{64})", mpi_manifest.read_text()).group(1).lower()
    mpi_path = BASE / "downloads/baram-extracted/$TEMP/msmpisetup.exe"
    mpi_actual = sha256(mpi_path)
    result = {
        "schema_version": 1, "verified_utc": datetime.now(timezone.utc).isoformat(),
        "target": str(target), "installation_evidence": read_json(BASE / "baram_install.json"),
        "method": "MSI File+Component+Directory mapping; SHA256 of all retained cabinet files versus installed counterparts. No application execution.",
        "reference_msi_sha256": sha256(BASE / "downloads/baram-extracted/$TEMP/BARAM-26.3.0-win64.msi"),
        "script_sha256": sha256(Path(__file__)), "expected_count": len(files),
        "unique_expected_paths": len(expected), "counts": counts, "extra_count": len(extras),
        "files": files, "extras": extras,
        "mpi_published_digest_check": {"provenance": read_json(BASE / "downloads/mpi-winget-provenance.json"),
            "manifest_sha256": sha256(mpi_manifest), "published_installer_sha256": published,
            "bundled_installer_sha256": mpi_actual, "match": published == mpi_actual,
            "repository_scope": "Microsoft-hosted community WinGet repository; independent published package manifest plus separately checked Microsoft Authenticode signature.",
            "installation_attempted_during_this_audit": False,
            "prior_installation_attempt": "Root agent reports MPI elevation prompt canceled by user; no retry in this audit."},
        "limits": "Package fidelity only, not malware/CVE/source-equivalence or runtime certification. Extra files listed without deletion. Registry, PATH and shortcuts not compared here."
    }
    out = BASE / "baram_installed_payload_manifest.json"
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    summary = {k: v for k, v in result.items() if k not in ("files", "extras")}
    summary["differences"] = [r for r in files if r["status"] != "match"]
    summary["extras"] = extras
    (BASE / "baram_installed_payload_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"manifest": str(out), "counts": counts, "expected_count": len(files),
                      "extra_count": len(extras), "mpi_hash_matches_published": published == mpi_actual}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path,
                        default=Path.home()/"AppData/Local/Programs/BARAM-26.3.0")
    args = parser.parse_args()
    verify(args.target.resolve())
