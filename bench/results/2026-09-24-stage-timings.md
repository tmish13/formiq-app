# Per-stage wall time on every run (plan D6) — 2026-09-24

Question: where do the seconds go inside one analysis task? Until this commit the answer in
`docs/architecture/2026-09-24-speed-and-decomposition.md` was a subtraction ("pose ≈ 50 %,
everything else ≈ 45 %"). The worker now writes seven stage marks into
`analysis_runs.settings_snapshot` as `{"stage_ms": {...}}` at `close_run`, so the split is a query.

## Command

```bash
# first batch (stg_): 52 videos, contaminated -- the unit suite and image builds ran alongside it
# clean batch (stg2_): 50 videos, started only after stg_ drained, nothing else running
SEL=bench/results/eval_batch_selection.json N=50 TIMEOUT_S=1800 SUBMIT_STAGGER=1 \
  EMAIL="stg2_$(date +%s)@example.com" bash bench/stage_a_decision_trail.sh
bash bench/pipeline_dashboard.sh 'stg2_%'
```

## Environment

- worker: `deployment-worker:latest` built 2026-09-24 18:55 UTC (image check 0 mismatches),
  3 prefork children × `OMP/OPENBLAS/MKL_NUM_THREADS=2`, `max_tasks_per_child=40`,
  `max_memory_per_child=1,500,000 KiB`, `mem_limit 6g`; code `1a53c7b`
- host: MacBook (Mac14,2, 8 cores), Docker Desktop 8 vCPU / 7.65 GiB.
  **On battery since 11:54:55 PDT with macOS Low Power Mode on** (`pmset -g` → `lowpowermode 1`)
  — see §"Absolute times" below; this is not the state the 600-video validation ran in.
- Postgres 15 in `formiq_db`; runs selected by user email `stg2_%`

## Raw output (clean batch)

```
=== ALL ASSERTIONS PASS ===
--- throughput ---
videos=50  videos/min=5.99  p50_ms=24591  p90_ms=45558
--- per-stage wall time, ms (runs that carry stage_ms) ---
pose_extract       n=50  p50=23475  p90=44356  share_of_p50_total=95.5%
posture_v1         n=49  p50=413  p90=859  share_of_p50_total=1.7%
after_model        n=50  p50=145  p90=324  share_of_p50_total=0.6%
claim              n=50  p50=76  p90=228  share_of_p50_total=0.3%
open_run           n=50  p50=70  p90=197  share_of_p50_total=0.3%
resolve_video      n=50  p50=57  p90=221  share_of_p50_total=0.2%
record_decisions   n=50  p50=25  p90=88  share_of_p50_total=0.1%
completed runs without stage_ms: 0
```

The contaminated first batch (`stg_%`, 52 videos, 5.04 videos/min, p50 29.7 s) gave the same
shape: pose_extract 97.8 % of the p50 total, posture_v1 1.5 %, everything else < 1 %.
`posture_v1 n=49`: one run abstained before the model (quality gate) and carries no model mark.

## What the split says

| stage | p50 | share of p50 total |
|---|---|---|
| pose_extract (MediaPipe, complexity 2, 300-frame cap) | 23.5 s | **95.5 %** |
| posture_v1 (features + model + calibration) | 0.41 s | 1.7 % |
| everything else (claim, open_run, resolve_video, post-model, record_decisions) | 0.37 s | 1.5 % |

- The doc's "≈ 45 % unexplained" row was a subtraction error. It scaled a single-process
  46 ms/frame figure (`2026-09-19-day1.md`) to a 3-child batch, where MediaPipe runs at 95 ms/frame
  on mains power (validation 600: p50 10.0 s over p50 107 frames) and worse under contention. There
  is nothing to win in decode, DB writes or finalize: together they are ≈ 0.4 s of a 10–25 s task.
- Decomposition (`docs/architecture/2026-09-24-speed-and-decomposition.md`) stands, now on a
  measurement: a service split would move the 95 % block to another machine, not shrink it.

## Absolute times: this batch ran 2.6× slower per frame than the validation, and why that is not the code

| batch (same 3×2 settings) | n | p50 frames | p50 latency | p50 ms/frame | machine state |
|---|---|---|---|---|---|
| `w2val` validation 600 (09:19 UTC) | 686 | 107 | 10.0 s | **95** | mains power, idle |
| `e2e` single video on the rebuilt image (12:10 PDT) | 1 | 96 | 12.2 s | 127 | battery, 15 min after unplugging |
| `stg` (13:23 PDT, contaminated) | 50 | 93 | 28.5 s | 303 | battery + Low Power Mode, suite running |
| `stg2` (13:33 PDT, clean) | 50 | 93 | 24.6 s | **257** | battery + Low Power Mode |

`pmset -g log` puts the switch to battery at 11:54:55 PDT; `pmset -g` reports `lowpowermode 1`
at the time of the clean batch. The rebuilt image is not the cause: the 12:10 e2e run on that image
sat at 127 ms/frame, and `stg2`'s videos share no content hash with `w2val`, so no paired
comparison exists. **Not isolated:** the 2.6× is consistent with the Low Power Mode CPU cap, but
the proof is a rerun of the same 50 videos on mains with Low Power Mode off, which this session
could not do. Until then, `9.25 videos/min, p50 9.7 s` is the mains-power, idle-machine number and
throughput on a battery-powered laptop should be expected to be 2–3× lower. The stage *split*
(pose ≥ 95 %) held in both states.

## Fixes in this commit

- `bench/pipeline_dashboard.sh`: the per-stage query silently returned nothing —
  `settings_snapshot` is a `json` column, and `round(double, int)` does not exist in Postgres;
  now `(settings_snapshot::json)->'stage_ms'` and `round((...)::numeric, 1)`.
- `docs/architecture/2026-09-24-speed-and-decomposition.md`: the subtraction rows replaced by the
  measured split; the "other 45 %" item withdrawn.
