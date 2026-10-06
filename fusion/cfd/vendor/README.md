# CFD dependencies: provenance and integrity

The acquisition cache is local under `downloads/` and `openfoam/debs/` and is
excluded from Git. Audit manifests, verification scripts, installation results,
and reports are kept with the project. This is binary retention for repeatable
inspection, not a reproducible source build or a complete dependency SBOM.

## Evidence layers

| Component | Acquisition authentication | Integrity evidence | Remaining limitation |
| --- | --- | --- | --- |
| BARAM 26.3.0 | Official project HTTPS page links to the downloaded CloudFront URL | Wrapper/MSI SHA256 recorded; installed payload comparison is documented in BARAM audit | Wrapper and MSI unsigned; no independent BARAM publisher checksum found; exact release source-to-binary correspondence unverified |
| Bundled Microsoft MPI 10.1.12498.18 | Valid Microsoft Authenticode signature | Recorded SHA256; see BARAM audit for independent Microsoft WinGet manifest comparison | Installed successfully after renewed approval; two-process local MPI check passed |
| OpenCFD OpenFOAM v2412, package 2412.260127-1 | Scoped repository signing key; valid signed APT metadata | All 27 transaction archive hashes match authenticated APT metadata | Signing key initially obtained from official HTTPS, without independent out-of-band fingerprint confirmation |

Read [BARAM audit](BARAM_AUDIT.md), [BARAM acquisition manifest](audit.json),
[installed BARAM comparison](baram_installed_payload_summary.json),
[OpenFOAM audit](openfoam/OPENFOAM_AUDIT.md),
[OpenFOAM package audit](openfoam/package_audit.json), and
[OpenFOAM runtime checks](../verification/README.md). The manifests distinguish
self-computed identities from publisher-authenticated checksums. A matching hash
alone is not a malware assessment. No exhaustive CVE or constituent-license scan
has been performed.

The full BARAM comparison found **15,186 of 15,186 installed files matching the
MSI cabinet by SHA256**, with no missing, changed or extra files. Case-sensitive
CAB member names that collided during Windows extraction were streamed directly
from the cabinet for comparison. The [complete per-file manifest](baram_installed_payload_manifest.json)
and `verify_baram_payload.py` preserve that evidence and method.

The [installed OpenFOAM package check](openfoam/installed_integrity.json) covered
all 27 transaction packages and 12,783 package checksum entries. Versions match.
Its only two content differences are package-local `etc/bashrc` and `etc/cshrc`;
the vendor installer adjusts these to the installation path. Exact differences
and hashes are preserved in [configuration evidence](openfoam/configuration_differences.json).
These checks use dpkg's local package checksum metadata, principally MD5; archive
authentication and SHA256 verification are separate evidence above.

## Repeat the retained-download check

From the repository root:

```powershell
python fusion/cfd/vendor/verify_vendor.py --output fusion/cfd/vendor/retained_artifact_verification.json
```

This streams SHA256 over the retained installer, MSI, MPI installer, selected
signed runtime DLLs, pinned source files, four OpenFOAM archives, acquisition
script and signing key. It executes no vendor code and fails on missing or
changed artifacts. The acquisition script is retained for inspection; repository
setup used the explicit scoped `openfoam/setup_repo.sh` instead.

The current [retained-artifact result](retained_artifact_verification.json)
reports **17 of 17 matches**. This check uses expected identities from the
acquisition audit and hardcoded key/script hashes; it does not establish new
publisher trust. Preserve these reports alongside the original artifacts.

## Installation state

BARAM's explicit per-user MSI transaction completed with exit code 0 at
`C:\Users\USER\AppData\Local\Programs\BARAM-26.3.0`; see
[installation result](baram_install.json). Its wrapper was not executed.
After renewed user approval, Microsoft MPI installed successfully (exit 0,
DLL version 10.1.12498.18), and two local MPI child processes ran successfully.
See [MPI installation result](mpi_install.json).

Both BaramFlow and BaramMesh subsequently reached their normal start screens.
The first launch failed because the automation environment omitted USERPROFILE;
after correcting that, stale MPI environment data required refreshing MSMPI_BIN
and the MPI PATH entry for the child process. [Launch-BARAM.ps1](../Launch-BARAM.ps1)
provides these process-local settings, without changing vendor files or global
environment variables. The original traceback is retained in
`baram_startup_dialog.json`. Both applications' analytics consent files were
read back with `consent: false`.

BARAM's bundled Windows blockMesh/checkMesh/icoFoam passed an isolated 400-cell
cavity test to 0.05 seconds. Logs and exit codes are in
`../verification/tutorial_cavity_baram_windows/`; the reproducible runner is
`../verification/smoke_baram.ps1`. This verifies basic runtime operation, not the
mount's CFD geometry or predicted cooling performance.

OpenFOAM is installed inside the existing WSL Ubuntu distribution and passed an
isolated official 400-cell cavity mesh/solver smoke test. No mount/laptop CFD
solution is claimed. No global shell startup edits were needed. The repository
key is restricted with `signed-by`, and repository preferences limit its package
priority; setup and exact installation commands are preserved under `openfoam/`.

BARAM bundles NextFOAM and is not the same binary distribution as the standalone
OpenCFD installation. ParaView remains a separate post-processing dependency;
its installation has not been verified here. Static inspection found analytics
consent handling in BARAM; no analytics opt-in was authorized or enabled by this
setup, and runtime network behavior has not been audited.
