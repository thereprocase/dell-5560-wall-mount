# Revision H continuation and restart

The visual startup is running through **2026-09-09 20:00 UTC (4 p.m. EDT)**,
with automatic hourly publication and a final update after its checkpoint and
stop. See [the current schedule and stop procedure](VISUAL_AUTORUN_20260909.md).
The two original adaptive cases remain paused. Their former overnight deadline
was 12:00 UTC (8 a.m. EDT); it is not their active schedule.

The latest published startup continuation uses the isolated 12-worker case
`revh_visual_81us_20260909_a3`, resumed from **0.038723499605432 s**. The initial trial replayed the
prior native checkpoint to the old video's 0.03831884948 s endpoint, then adds
five fixed 80.930025 microsecond steps. New native checkpoints are written every
half hour and at the final stop; consult its current `resume-checkpoint.json`
and verify the native fields before a later resume. Preserve `uniform/time`, previous-step fields and
12-way decomposition. See [the continuation record](VISUAL_EXTENSION_20260909.md).

The original four-worker startup and eight-worker flowing-field transient are
also retained, with separate physical clocks. The original startup's later
unpublished fields are not part of the new visual branch.

CFD supervisors and solver workers use CPU nice +19 and idle disk-I/O priority.
The Windows hourly publisher and its rendering jobs use Idle priority;
new WSL diagnostic jobs also use nice +19 and idle I/O. New Linux launches also use SCHED_IDLE and the shared 28 GiB cfd.slice memory cap.
These settings preserve worker counts and yield to other work. See CFD_RESOURCES.md.

The WSL cases live under `/home/repro/code/dell5560-cfd-gpu-20260908`:

- `revh_fourhour_08`: original startup, native continuation from 0.1 ms.
- `revh_flowing_12`: transient from unconverged steady iteration 400, clock reset
  only at its original initialization. Its later rank changes and restarts do not
  reset physical time or discard backward-scheme history.

`run-status.json` records progress and the authorized UTC deadline.
`run-control.json` supplies that deadline and the graceful stop flag. Full native
fields are written every half-hour, with `purgeWrite 0`. They retain native binary
precision: OpenFOAM v2412 disables gzip for non-ascii output. A separate lossless
compression trial saved only about 5%. At a normal stop, `resume-checkpoint.json` records the latest time,
worker count, mesh hashes, native time metadata, and hashes of the exact
uncompressed current and previous-step field bytes. Older checkpoints remain.

## Stop the original adaptive cases, preserving a restart

Run this from WSL:

```bash
python3 /mnt/f/Code/dell-5560-wall-mount-cfd/fusion/cfd/stop_revh.py \
  --root /home/repro/code/dell5560-cfd-gpu-20260908 \
  --mirror-root /mnt/f/Code/dell-5560-wall-mount-cfd/fusion/cfd/runs \
  --controller /mnt/f/Code/dell-5560-wall-mount-cfd/fusion/cfd/runs/revh_overnight_16
```

Each supervisor asks its verified OpenFOAM workers to write and stop at the next
completed step. Do not send the OpenFOAM signal to `mpirun`. The hourly publisher
then records a final cumulative checkpoint.

## Add another hour to an original adaptive case later

Source the same OpenFOAM environment, then run either case (or both in separate
terminals). The helper checks the saved native fields and uses `latestTime` with
the same worker count. It appends logs and samples and excludes idle time between
completed sessions from supervised wall-time accounting.

```bash
source /usr/lib/openfoam/openfoam2412/etc/bashrc
python3 /mnt/f/Code/dell-5560-wall-mount-cfd/fusion/cfd/resume_revh.py \
  --case /home/repro/code/dell5560-cfd-gpu-20260908/revh_flowing_12 \
  --mirror /mnt/f/Code/dell-5560-wall-mount-cfd/fusion/cfd/runs/revh_flowing_12 \
  --seconds 3600
```

Replace both case names with `revh_fourhour_08` to continue the original adaptive
startup branch, not the new visual continuation.
An explicit `--until 2026-09-09T12:00:00Z` can replace `--seconds`. Running this on
an active case first creates a native checkpoint. Keep the mesh, forcing,
processor count, old-step fields, and `uniform/time` together; do not initialize a
new time-zero case from the saved velocity alone.

## Hourly publication

The Windows controller is `watch_revh_overnight.py`. Its durable status and logs
are in `fusion/cfd/runs/revh_overnight_16/`. It publishes every hour from the
original 12:12 p.m. start, then a final checkpoint at 8 a.m. It retains every
actual sampled state, encodes H.264 directly from cached lossless plots, and uses
lossless gzip for new diagnostic downloads. Existing published archives remain
unchanged. Local and deployed playback checks verify the exact expected video
hash, real decoded flow frames, links, and mobile layout before marking a
publication successful.

A failed publication preserves its sources and leaves the solvers running. After
resolving the reported issue, restart the controller with its original arguments
and `--resume`. A later, separate compute session can use a new `--state-root` and
new deadline; archive numbering continues from the published checkpoints.

The mesh remains provisional. Restartability and numerical field equivalence do
not establish mesh independence, periodic shedding, or a temperature prediction.
