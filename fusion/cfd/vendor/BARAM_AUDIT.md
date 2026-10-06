# BARAM 26.3.0 Windows installer audit

2026-09-07 UTC. Download and static inspection only: no installer, bundled executable, DLL or Python bytecode was executed. Existing 7-Zip extracted archives; Windows Installer COM opened the MSI database read-only. Machine-readable findings: [audit.json](audit.json).

## Provenance and artifact identity

The [NEXTfoam BARAM repository](https://github.com/nextfoam/baram) identifies baramcfd.org as its project site. Its [English download page](https://baramcfd.org/en/download-en/) advertises 26.3.0 and links to [the download form](https://baramcfd.org/en/baram-download-en/). That page's HTML contains this installer URL:

`https://d3c6e16xufx1gb.cloudfront.net/baram/BARAM-26.3.0-setup.exe`

The installer was downloaded directly from that published URL. No form was submitted or personal information sent. Saved HTML and HTTP headers are under `downloads/`. Response: HTTP 200, 623,211,563 bytes, Last-Modified `Mon, 31 Aug 2026 10:48:05 GMT`. Its multipart S3 ETag is not a publisher SHA256.

| Artifact, relative to this directory | SHA256 | Authenticode |
| --- | --- | --- |
| `downloads/BARAM-26.3.0-setup.exe` | `18F81640DE73891248E3ED147483F96D4C70359DA1F5DF5F06E6CC6A8294FB72` | NotSigned |
| `downloads/baram-extracted/$TEMP/BARAM-26.3.0-win64.msi` | `FF87AEA71706425F76A098BDBD3B648F3C2247F1B1D82E02A358B5FC126075BE` | NotSigned |
| `downloads/baram-extracted/$TEMP/msmpisetup.exe` | `C305CE3F05D142D519F8DD800D83A4B894FC31BCAD30512CEFB557FEACCBE8B4` | Valid, Microsoft Corporation |

These are self-computed hashes for reproducible identity. No independently published checksum was found on the inspected download/release pages, GitHub releases, or exact-filename checksum search. Thus BARAM provenance rests on its official HTTPS link chain, without a verified publisher signature or separate digest. This is not a malware-free certification.

## Package contents and dependencies

7-Zip identifies an NSIS-3 Unicode wrapper containing the MSI plus Microsoft MPI setup. MSI properties confirm ProductVersion `26.3.0`, ProductCode `{3BB556D3-DAB2-44C7-9465-FB491D1FA1EF}`, UpgradeCode `{32D8E4F2-832D-407F-B1F3-ABE5FC589188}`. Manufacturer is `UNKNOWN`; MSI summary author is `nextfoam`.

The MSI File table contains 15,186 files totaling 2,363,569,822 uncompressed bytes. It includes BaramFlow/BaramMesh launchers, Python runtime, Qt/PySide6, VTK, MinGW64, and `solvers/openfoam` executables, including the standard and NEXTfoam variants of simple and buoyant/CHT solvers. No separate system Python installation is indicated for this frozen binary. ParaView is external post-processing software, per the official download page.

Read-only extracted PE metadata confirms CPython **3.11.9** and Qt **6.9.2**, both with valid Authenticode signatures. VTK DLL filenames identify **9.4.2**. Bundled MS-MPI setup is **10.1.12498.18**, validly signed by Microsoft Corporation with a Microsoft timestamp. Certificate details, hashes, and expiration values are in `downloads/baram-all-binary-signatures.json`. These versions are observations, not assertions that every dependency is current or free of known vulnerabilities; no exhaustive CVE scan was performed.

## Source, license and telemetry

Public source was pinned at `be140c7a2eca79fc447606f321c121057737a9b7`; selected files and hashes are preserved locally. Its `app_properties.py` says **26.2.1**, whereas the package's `library.zip/app_properties.pyc` contains **26.3.0**. The [GitHub releases page](https://github.com/nextfoam/baram/releases) displayed no releases. Exact release-source correspondence is unverified. Repository license text is GPL version 3; the [solver repository](https://github.com/nextfoam/nextfoam-cfd) describes GPLv3-or-later NextFOAM based on OpenCFD OpenFOAM. This was not a complete constituent-license review.

Packaged files include analytics consent/client modules and PostHog. Static strings from the packaged launch modules include `ensureConsent`; client/consent strings match the public source's opt-in design, consent-file name and methods. The packaged endpoint is `https://eu.i.posthog.com`. Public source defaults consent to false and checks it before initializing/capturing telemetry; it prompts separately for each application when analytics is configured. **Packaged control flow and runtime network behavior were not executed or proven.** Source initializes PostHog with geolocation enabled after consent. Evidence: `downloads/baram-packaged-telemetry-strings.json` plus the pinned source files. No analytics API key is reproduced in the audit.

The official release-note page displays September 01 2025 for 26.3.0, inconsistent with the current binary's August 2026 CDN timestamp. This discrepancy is retained rather than silently corrected.

## Installation handoff, not executed

Absolute MSI path:

`F:\Code\dell-5560-wall-mount\fusion\cfd\vendor\downloads\baram-extracted\$TEMP\BARAM-26.3.0-win64.msi`

Absolute MPI path:

`F:\Code\dell-5560-wall-mount\fusion\cfd\vendor\downloads\baram-extracted\$TEMP\msmpisetup.exe`

The literal `$TEMP` directory is part of the extraction path: use literal/single-quoted PowerShell paths.

For BARAM, direct MSI installation is more inspectable than relying on NSIS to forward silent flags. [Microsoft documents](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/msiexec) `/i`, `/qn`, `/norestart`, `/L*v`, and public properties. Proposed arguments: `/i <absolute MSI> /qn /norestart /L*v <absolute log> TARGETDIR=<absolute user-local target> ALLUSERS=2 MSIINSTALLPERUSER=1`. Preserve MSI logs and verify installation results afterward. The MSI default sets TARGETDIR to ProgramFiles64Folder/BARAM only when TARGETDIR is empty; an explicit target overrides it.

Per-user properties are present, but Summary WordCount is 2, without the LUA/no-elevation bit. Non-elevated install is **not guaranteed** by static inspection. MPI privilege and startup flags were not tested. NSIS's [generic `/S` and `/D` flags](https://nsis.sourceforge.io/Docs/Chapter3.html) do not prove that silence or target selection reaches this wrapper's nested MSI. Do not disable integrity checking with `/NCRC`.

The MSI adds TARGETDIR to PATH and defines four shortcuts (Start menu and desktop for both apps). Its only CustomAction entries set TARGETDIR and REINSTALLMODE; its Registry and LaunchCondition tables are empty. Standard install/upgrade actions remain, so avoid assuming it cannot affect an existing related BARAM installation. Launchers are `<TARGETDIR>\BaramFlow.exe` and `<TARGETDIR>\BaramMesh.exe`; application command-line flags were not established. Root agent owns installation, consent handling, and end-to-end checks.

## Subsequent installation and complete file verification

This section records work after the original static audit above. The root agent installed the retained MSI into `C:\Users\USER\AppData\Local\Programs\BARAM-26.3.0`; [baram_install.json](baram_install.json) records MSI SHA256 `FF87AEA71706425F76A098BDBD3B648F3C2247F1B1D82E02A358B5FC126075BE` and exit code **0**. This follow-up audit did not launch the application or perform another installation.

**All 15,186 MSI-listed files matched the installed files by SHA256. Missing: 0. Changed: 0. Extra files under the installation directory: 0.** Paths were reconstructed from the MSI's File, Component and Directory tables; both source and installed file sizes were also checked. This establishes package fidelity at the recorded verification time, not runtime correctness, absence of malware, or matching published source.

The CAB uses case-sensitive file identifiers, including 19 pairs such as `Image.pyc`/`image.pyc` that alias when flattened onto Windows. The first comparison identified these extraction aliases, not installed corruption. The final verifier hashes all 38 affected members using 7-Zip exact-case binary stdout (`-ssc -spd -so`); remaining members use ordinary retained extraction. The Component mapping also preserves identifier case. No installed files were changed to obtain a match.

Reproduce with `python fusion/cfd/vendor/verify_baram_payload.py`. Evidence: [full manifest](baram_installed_payload_manifest.json), [compact summary](baram_installed_payload_summary.json), and [verifier source](verify_baram_payload.py). The full manifest includes each installed relative path, case-sensitive CAB identifier, expected size, source and installed SHA256, read method, and result. It also records the verifier's hash and reference MSI hash. Registry, environment, shortcuts and runtime-generated user configuration are outside this file comparison.

### Independent Microsoft MPI digest confirmation

The bundled MPI installer SHA256 **matches** the independently published `InstallerSha256` in [Microsoft's WinGet community repository manifest](https://github.com/microsoft/winget-pkgs/blob/f82e821082e59b30db90a0625a04f262c800e665/manifests/m/Microsoft/msmpi/10.1.12498.18/Microsoft.msmpi.installer.yaml), pinned at commit `f82e821082e59b30db90a0625a04f262c800e665`. That manifest targets Microsoft MPI `10.1.12498.18`, points to `download.microsoft.com`, and specifies `C305CE3F05D142D519F8DD800D83A4B894FC31BCAD30512CEFB557FEACCBE8B4`. The downloaded manifest, its hash, and provenance are retained in the manifest/summary evidence. This supplements the valid Microsoft Authenticode signature; it does not independently authenticate the unsigned BARAM MSI.

The root agent reported that the earlier MPI elevation prompt was canceled by the user. **No MPI installation was retried during this audit.** The digest check is read-only and does not imply MPI is installed or working.
