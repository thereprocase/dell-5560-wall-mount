# Visual continuation through 4 p.m. Eastern, 9 September 2026

The user authorized continuing the existing visual startup branch through
**2026-09-09 20:00:00 UTC**, with automatic hourly website updates and a final
publication after its native checkpoint and stop. The older startup and
flowing-field simulations remain paused; their old publisher remains suspended.

The native case is
`/home/repro/code/dell5560-cfd-gpu-20260908/revh_visual_81us_20260909_a3`.
Its mirror is `fusion/cfd/runs/revh_visual_81us_20260909_a3` in the
`dell-5560-wall-mount-cfd-tracers` worktree. Continuation starts at the verified
0.038723499605432 s checkpoint, retaining all current and previous-step fields.
It uses twelve MPI workers, fixed 80.930025 microsecond steps, and one sampled
section pair per step. Native fields are written every 1,800 wall-clock seconds
with `purgeWrite 0`, and on the final OpenFOAM signal-driven stop.

The independent WSL user service is `cfd-visual-20260909-1600.service`, in the
shared 28 GiB `cfd.slice`. Nice +19, SCHED_IDLE and idle I/O are inherited by all
workers. The supervisor reads the UTC deadline and graceful stop flag from the
native `run-control.json`; status, memory peak and events are mirrored every
five seconds. The service survives closure of this chat's shell. Its journal
is available with `journalctl --user -u cfd-visual-20260909-1600.service`.

`resume_revh_visual.py` verifies the saved native field and mesh hashes before
launching the wall-budget supervisor. Source OpenFOAM's bashrc before enabling
`set -e`: that environment setup is not compatible with an already active
errexit setting on this installation. The first service initialization exited
before launching any CFD; the corrected launch started successfully.

`watch_revh_visual.py` runs on Windows at Idle priority. Its durable controller
directory is `fusion/cfd/runs/revh_visual_81us_20260909_a3/hourly-until-1600`.
It performs an immediate end-to-end publication, then hourly snapshots anchored
to the solver session start, and a final snapshot after the solver stops.
Rendering and deployment take additional time beyond each scheduled snapshot.
Status and errors are recorded in `publisher-status.json`; publications retry
after transient failures without stopping the independent solver.

The publisher keeps the original 918 samples and their hashes, then appends
complete fixed-step samples. It preserves the original particle frame pacing,
compresses the arrow video from lossless plots, rebuilds all startup aliases and
the README, checks local and deployed playback, and pushes to the existing
GitHub Pages repository without force. The separate flowing-field movie is
unchanged. The visual timestep is intentionally not an accuracy acceptance gate.

To request an earlier stop, set `stop_requested` to `true` in the native case's
`run-control.json` using an atomic JSON replacement. The supervisor then asks
the verified OpenFOAM workers to write and stop; the publisher detects completion
and publishes a final snapshot. Do not signal `mpirun` or resume the old suspended
hourly publisher. Allow one solver-step boundary and checkpoint writing after
the requested deadline; the supervisor bounds a stalled graceful stop at 180 s.

To resume a publisher after resolving an error, rerun `watch_revh_visual.py`
with the same case, steady case, state root and deadline arguments plus `--resume`.
Completed publications are skipped, and prepared samples or commits are reused.
