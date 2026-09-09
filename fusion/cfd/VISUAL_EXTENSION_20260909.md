# Startup video continuation, 9 September 2026

The user requested a continuation from the currently published startup video's
tail, with appearance and temporal progress prioritized over timestep accuracy.
The initial trial adds five video frames at fixed 80.930025 microsecond steps.

Native case: `/home/repro/code/dell5560-cfd-gpu-20260908/revh_visual_81us_20260909_a3`.
Local mirror: `fusion/cfd/runs/revh_visual_81us_20260909_a3` in the
`dell-5560-wall-mount-cfd-tracers` worktree. Full run records, resource proofs,
solver logs and field hashes are retained there.

The old video ended at 0.03831884948 s. Its prior full native checkpoint was
0.03772391061 s. Current and previous-step internal fields were verified exactly
after repartitioning from four to twelve workers. A 36-step replay reached the
video tail in 470.64 seconds, followed by five coarse steps in 81.59 seconds.
The coarse phase averaged 14.25 seconds per step after its first step and reached
maximum Courant number 2.4437, with no logged turbulence bounding or nonfinite
solver values. This short trial does not establish timestep accuracy.

The final native checkpoint is **0.038723499605432 s**, with all twelve ranks,
previous-step history and native time metadata verified. All workers stopped.
This is the checkpoint to use for the next visual extension; do not substitute
the older adaptive startup's later saved fields. The visual runner creates a
fresh branch and is not a general in-place resume command. For a future resume,
use `startFrom latestTime`, retain fixed 80.930025 microsecond steps and sampling
every step, set a new end time, and verify the saved field hashes before launch.
Source the same OpenFOAM v2412 environment and run the launch script through
`lower_priority()` so the shared resource controls apply.

All twelve workers ran at nice +19, SCHED_IDLE and idle I/O priority inside
`cfd.slice`. Its collective memory cap was 28 GiB with no early throttling and
no swap. Peak usage was **10,610,270,208 bytes (9.88 GiB)**, with zero memory-limit
or OOM events. Rendering followed solver completion at Windows Idle priority.

Presentation retains all 918 original published samples and appends exactly
five new samples. Original sample hashes were verified. The 473 original
particle motion frames retain their timing, including the old forced endpoint;
five motion frames follow, then a six-frame final hold (484 frames at 60 fps).
The original arrow-renderer scripts differed only in newline encoding between
worktrees; 99 regenerated PNGs matched the old cache byte for byte before the
remaining immutable cached PNGs were reused.

The prior twelve-worker adaptive trial, the two incomplete visual preparations,
both original native simulations and all earlier public archives are retained.
The old hourly publisher remains suspended and must not be restarted with its
expired deadline.
