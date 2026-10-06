# BARAM Windows builder-path investigation

Verified 2026-09-07 after the first GUI launch displayed a Python startup error.

The public evidence directly connects the Windows username `jakej` to **Jake
Yun**, GitHub account **jiban**, who lists NEXTFOAM on his public profile and
provides BARAM development/support responses in the official project.

- [Public GitHub profile](https://github.com/jiban): display name Jake Yun,
  affiliation nextfoam.
- [Official BARAM discussion 64](https://github.com/nextfoam/baram/discussions/64):
  on April 1, 2024, jiban posted his own Windows solver configuration using
  `C:\Users\USER\Documents\workspace\baram\solvers\openfoam` and the corresponding
  mingw64 path. This is the direct username-to-project-account connection.
- [Official BARAM forum](https://baramcfd.org/en/forum-2/topic/how-to-replicate-baramflow-using-nextfoam-from-the-command-line/):
  Jake identifies himself as being from NEXTFOAM while supporting solver usage.
- [Earlier release issue 248](https://github.com/nextfoam/baram/issues/248):
  another user's BARAM 26.1.1 traceback already contains the same
  `C:\Users\USER\Documents\workspace\baram-release` build path.

Read-only inspection of our installed `lib/analytics/client.pyc` found the
embedded source filename under `baram-release/analytics/client.py`; inspection
of `lib/filelock/__init__.pyc` found its virtual-environment source path under
the same release workspace. These files passed the earlier complete installed
payload SHA256 comparison. The install location remains the repro user's
AppData/Local/Programs/BARAM-26.3.0 directory.

Conclusion: the unexpected path is consistent with the established BARAM
developer's Windows release workspace. This resolves the unknown-builder-name
concern. It does not cryptographically identify who produced this exact unsigned
26.3.0 installer, establish source-to-binary equivalence, or certify absence of
malware. The authentication limitations in BARAM_AUDIT.md remain applicable.

Separate setup status: MPI installation subsequently succeeded (mpi_install.json,
exit 0, DLL version 10.1.12498.18); two local mpiexec child processes ran. BARAM's
first GUI launch failed with a cx_Freeze Python error. Its complete traceback was
not captured before the dialog closed; the actual startup cause is unresolved.
