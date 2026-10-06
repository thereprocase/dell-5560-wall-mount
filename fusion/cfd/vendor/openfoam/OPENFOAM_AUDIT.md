# OpenFOAM installation integrity audit

2026-09-07. **No unexplained package-file differences were found in the checked installation.** This is bounded integrity evidence, not an independent publisher-identity or malware audit. Installation files were not changed by this audit.

## Download and repository evidence

[package_audit.json](package_audit.json) records **27 downloaded package SHA256 values**, each matching the authenticated APT package metadata, with package versions and repository origins. OpenFOAM's retained `InRelease` verifies with the configured key; the signature was rechecked during this audit. APT's trust chain authenticates repository indexes and the referenced package hashes, rather than asserting that each package is independently signed or harmless. See [Debian apt-secure](https://manpages.debian.org/unstable/apt/apt-secure.8.en.html).

The scoped repository configuration was read back and hashed in [installed_integrity.json](installed_integrity.json):

- Source: `https://dl.openfoam.com/repos/deb`, Ubuntu `noble`, `amd64`.
- `signed-by=/usr/share/keyrings/dell5560-openfoam.gpg` in `/etc/apt/sources.list.d/dell5560-openfoam.list`; no global APT trust-store addition is used by this setup.
- Origin pin: priority 600 for `openfoam*`, 100 for other packages from `dl.openfoam.com`. This narrows package preference; it is not a sandbox or a permanent version hold.
- Key fingerprint: `DC93C096174122E256DA24063386DD74948D208F`.

`Signed-By` selects the key allowed to authenticate that repository, as described in [APT sources documentation](https://manpages.debian.org/trixie/apt/sources.list.5.en.html). **The initial key came from the official OpenFOAM HTTPS endpoint, without separate out-of-band fingerprint confirmation.** Subsequent signature/hash checks therefore rely on that bootstrap; they do not independently establish the publisher's identity.

## Installed-file results and the two explained differences

All **27 installed versions match** the audited archive versions. The four OpenFOAM packages—`openfoam2412`, `openfoam2412-common`, `openfoam2412-tools`, `openfoam2412-tutorials`—are **2412.260127-1**. Exact dependency versions are in the JSON reports.

`dpkg --verify PACKAGE` was run for every package, covering metadata with **12,783 MD5 entries**. Twenty-six packages reported no discrepancies. `openfoam2412-common` reported two content changes:

| Installed file | Complete observed change |
| --- | --- |
| `/usr/lib/openfoam/openfoam2412/etc/bashrc` | Disable automatic installation-path discovery with `##IGNORE##` comments; set `WM_PROJECT_DIR` to `/usr/lib/openfoam/openfoam2412`. |
| `/usr/lib/openfoam/openfoam2412/etc/cshrc` | The equivalent csh path-discovery comments and fixed installation path. |

Both files were compared against the retained **SHA256-verified common-package archive**. Their complete diffs and hashes are preserved in [configuration_differences.json](configuration_differences.json) and [configuration_differences.diff](configuration_differences.diff). The runtime package's audited `postinst` invokes `foamConfigurePaths -project-path`; the verified installed helper explicitly performs these exact substitutions. [install.log](install.log) records the same four changes. These are explained installer transformations, not unexplained solver-binary changes. The raw report deliberately retains `all_dpkg_verifications_report_no_discrepancies: false` rather than hiding them.

[dpkg verification](https://manpages.debian.org/testing/dpkg/dpkg.1.en.html) compares current file contents with local installed-package checksum metadata, principally MD5. It does not comprehensively cover generated/untracked files and does not provide a new publisher assurance. A local metadata compromise could undermine this check; the independent archive SHA256 evidence is retained separately.

## Runtime and exact audit commands

The installed executable reports **OpenFOAM 2412**, build `_b8cf4d35-20260127`, patch 260127. The official 400-cell cavity copied into [verification](../../verification/README.md) passed mesh checks and ten `icoFoam` steps. This proves a basic runtime works, not CFD accuracy or security. Benchmark surface intersections remain a separate geometry issue; no mount/laptop production flow solve was performed.

```powershell
wsl -d Ubuntu -- python3 /mnt/f/Code/dell-5560-wall-mount/fusion/cfd/vendor/openfoam/verify_installed.py
wsl -d Ubuntu -- python3 /mnt/f/Code/dell-5560-wall-mount/fusion/cfd/vendor/openfoam/inspect_configuration_differences.py
```

These scripts use read-only package queries, `dpkg --verify`, signature verification and archive reads, writing evidence only in this workspace. The first refuses to overwrite an existing integrity report.
