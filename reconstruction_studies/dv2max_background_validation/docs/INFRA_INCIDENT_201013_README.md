# Quarantined runs from PBS job 201013 (Stage 1 pilot), 2026-11-03

Moved here intact (wirecell output dirs + lar/container logs); nothing deleted.  Classification of every
started run: `runs_classified.csv` (status CLEAN stays in W/runs, COMPROMISED moved here).

Cause (infrastructure, not reconstruction): the PBS job cgroup `pids.max = 1024`
(`/sys/fs/cgroup/pids/jobs/201013/pids.max` on sophia-gpu-08; `pids.events` max = 8926 at qdel time).
LANES=12 concurrent lar processes (64-97 threads each) + their apptainer starter/squashfuse processes exceeded it.
Symptoms: `pthread_create failed: Resource temporarily unavailable` (OpenBLAS, std::thread, Go runtime/cgo),
`fork: retry`, `popen failure`; lar exit 134 (std::runtime_error "pthread_create has failed" at finalization),
139, 129; four ARM D lar processes deadlocked in futex_wait (thread pools waiting for never-created workers;
0.5-0.8 % CPU for ~100 min) -> job deleted with qdel (Exit_status 143).
All failures started in the first 14 min while all 12 lanes were busy.  The 18 sentinel runs (job 200949,
LANES=6) and all signal-study runs are free of these messages.
Rerun: same template / environment / lar command, LANES=5 (jobs 201062 and 201131; max pids.current 460 / 482) with a
pids-headroom throttle, dynamic queue, per-run timeout and a
post-run resource-message scan (scripts/run_bg_batch.pbs, 2026-11-03 revision).

`clean_but_same_job/`: the 58 runs of job 201013 classified CLEAN (lar exit 0, done marker, no resource message)
were ALSO moved out of W/runs, so that the whole Stage 1 sample comes from healthy jobs only (thread starvation
can in principle act silently).  They are kept as a reproducibility reference against the reruns.
