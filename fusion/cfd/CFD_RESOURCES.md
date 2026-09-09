# Desktop-friendly CFD execution

Linux CFD launchers now enter a shared user systemd `cfd.slice`. The installed
drop-in is `~/.config/systemd/user/cfd.slice.d/resources.conf`:

```ini
[Slice]
CPUAccounting=yes
CPUWeight=1
IOAccounting=yes
IOWeight=1
MemoryAccounting=yes
MemoryHigh=infinity
MemoryMax=28G
MemorySwapMax=0
```

The 28 GiB RAM cap applies to all jobs in this slice together, including child
MPI processes. There is no CPU quota or early memory-throttling threshold.
Swap is disabled for these jobs. The hard cap is a last boundary; a job needing
more than it can fail, so the visual runner records current/peak memory and
memory-limit/OOM events. Existing WSL-wide settings remain 32 GiB RAM, 12 logical
CPUs, 8 GiB swap and gradual cache reclamation.

`lower_priority()` re-executes script-based launchers inside the slice, then
sets nice +19, SCHED_IDLE and `ionice -c 3`. This installation does not expose
`io.weight` in the user slice; the per-process idle I/O setting still applies.
Windows CFD rendering and encoding launchers use Idle process priority.
Rendering follows solver completion for this visual extension.

The policies prioritize other runnable work and allow spare CPU capacity to be
used. They do not establish a particular speedup or desktop-latency guarantee.
All old paused solvers and the old hourly publisher remain stopped/suspended.
