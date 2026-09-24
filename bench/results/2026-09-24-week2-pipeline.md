# Week 2 — worker limits and the concurrency matrix, upload backpressure, the end-to-end test

**Date:** 2026-09-24 · **Status:** matrix, backpressure and e2e DONE; the 600-video validation of the chosen cell is §6 (filled when it drains)

Scope set by the user: worker memory limits + a concurrency matrix at 2/3/4 against the 7-in-900
kill baseline; upload backpressure returning 503 above a bounded in-flight count; the end-to-end
test. Deferred: cache visibility, per-stage timings, manifest consolidation.

## 1. What changed (branches, in chain order after `audit/worker-lost-reclaim`)

| branch | change | test |
|---|---|---|
| `audit/worker-threads-memlimits` | `worker_max_tasks_per_child` (40) and `worker_max_memory_per_child` (1.5 GiB) in `celery_app.py`; compose worker `--concurrency=${WORKER_CONCURRENCY:-4}`, OMP/OpenBLAS/MKL threads `${WORKER_THREADS:-2}`, `mem_limit ${WORKER_MEM_LIMIT:-6g}`, `restart: unless-stopped`, redis healthcheck; `torch.set_num_threads` / `cv2.setNumThreads` from `OMP_NUM_THREADS`; `bench/worker_matrix.sh` | the matrix below |
| `audit/upload-backpressure` | `asyncio.Semaphore(UPLOAD_MAX_INFLIGHT=4)` per API process on `/form-checks/submit`; full house ⇒ 503 + `Retry-After: 5` before the upload is read; both HTTPException handlers now forward `exc.headers` (they dropped every header, including `WWW-Authenticate` on 401) | `tests/api/test_upload_backpressure.py` (4), 43 API/auth tests green with the one pre-existing G-35 failure |
| `audit/e2e-test` | `tests/e2e/test_live_pipeline.py`: register → submit → poll → `/ml-analysis`, then A1–A10 for that user against the compose DB; the stale `integration/tasks/test_analysis_tasks.py` (patched nonexistent names, asserted a nonexistent function) deleted | the live run in §4 |

## 2. Commands

```bash
CELLS="2:1 2:2 3:1 3:2 4:1 4:2" N=80 bash bench/worker_matrix.sh          # six cells, 80 videos each
# validation of the chosen cell: 600 videos, beat and reaper running, recycling on
WORKER_CONCURRENCY=<C> WORKER_THREADS=<T> docker compose -f backend/deployment/docker-compose.yml up -d --force-recreate --no-deps worker
SEL=bench/results/gate1b_selection.json N=600 TIMEOUT_S=7200 SUBMIT_STAGGER=2 EMAIL="w2val_<ts>@example.com" bash bench/stage_a_decision_trail.sh
bash bench/trail_report.sh 'w2val_%'
# backpressure under the G-36 condition: 20 simultaneous uploads
SUBMIT_STAGGER=0 N=20 EMAIL="bp_<ts>@example.com" bash bench/phase1_concurrent_batch.sh
# end to end
docker run ... deployment-beat:latest pytest -m "e2e or slow" -p no:cacheprovider tests/e2e/test_live_pipeline.py
```

**Environment.** Same VM and services as the Week-1 gate (8 vCPU / 7.65 GiB); the worker image is
still the stale one with the code bind-mounted (the image check says so at every start).

## 3. The matrix — six cells, 80 videos each, all 480 completed, 0 SIGKILLs

`bench/worker_matrix.sh`, recycling on in every cell (`worker_max_tasks_per_child` 40,
`worker_max_memory_per_child` 1.5 GiB), RSS sampled every 10 s, numbers from the trail.

| concurrency | threads/child | n | completed | videos/min | p50 s | p90 s | peak RSS | kills |
|---|---|---|---|---|---|---|---|---|
| 2 | 1 | 80 | 80 | 6.18 | 17.9 | 28.0 | 2586MiB | 0 |
| 2 | 2 | 80 | 80 | 7.74 | 14.0 | 23.3 | 2454MiB | 0 |
| 3 | 1 | 80 | 80 | 8.17 | 20.1 | 31.2 | 3404MiB | 0 |
| 3 | 2 | 80 | 80 | 8.60 | 19.5 | 31.3 | 3497MiB | 0 |
| 4 | 1 | 80 | 80 | 9.07 | 23.9 | 37.3 | 4553MiB | 0 |
| 4 | 2 | 80 | 80 | 8.38 | 25.9 | 40.8 | 4551MiB | 0 |

Baseline before recycling and thread caps (Gate 1b + Week-1 gate, concurrency 4, threads unbounded):
6–10 videos/min, p50 28–38 s, **7 kills in 900**. Every cell here is faster at p50 than the baseline
and none killed a child in 80 videos (0.8 % would predict ~4 across the 480). Four cells clear the
≥ 8 videos/min bar. **3 × 2 is the new compose default**: 5 % less throughput than 4 × 1 for
1.1 GiB less peak RSS on a 7.65 GiB VM that also runs the API at 2.1 GiB — the memory that was
producing the kills. The kill rate under the chosen cell is what §6 measures at n=600.

## 4. End to end — `tests/e2e/test_live_pipeline.py`

Two live runs. The first (02:00, worker just recreated, the second-pass extraction saturating the
CPU) finished its clip at 331 s and the test gave up at 300 s; the test now polls 600 s with a
matching pytest timeout, its trail check refuses to pass on a non-terminal row, and it compares the
API's status case-insensitively (the API serialises the enum *value*, `completed`; the DB stores
the *name*). The second run, idle machine: **2 passed in 13.9 s** — register → submit → poll →
`/ml-analysis` with a decision, then A1–A10 for that user all zero.

## 5. Upload backpressure — the G-36 condition, 20 simultaneous uploads

`SUBMIT_STAGGER=0 N=20 bash bench/phase1_concurrent_batch.sh` against the restarted API
(`UPLOAD_MAX_INFLIGHT=4` per gunicorn worker, 4 workers):

| outcome | count |
|---|---|
| 202 accepted | 17 |
| **503 with `Retry-After: 5`** | **3** |
| dropped sockets (`curl_rc ≠ 0`) | **0** |
| API worker SIGKILLs during the burst | **0** |
| accepted uploads that reached COMPLETED | 17 / 17 |

G-36 measured 2–7 of 20 requests lost with no server-side log; now every request gets an answer.
The other half of G-36 — streaming the upload to disk instead of `await file.read()` — stays deferred;
the bound makes the memory finite (≤ 16 × 100 MB across the four workers), not small.

## 6. Validation of the chosen cell — 600 videos, beat and reaper running, recycling on

Resumed 2026-09-24 10:28 PDT as `w2val_1790270898@example.com` (the 86 videos of the batch paused
at 02:22 had drained on their own, 86/86 completed, and are included in the trail below).

| measure | 600-video batch, 3 × 2 + recycling | baseline (Gate 1b + Week-1 gate: 4 × unbounded, no recycling) |
|---|---|---|
| completed / submitted | **600 / 600** (686 / 686 with the paused 86) | 900 / 900 |
| worker SIGKILLs | **0** | **7 in 900** (0.8 %) |
| unrecovered losses | 0 | 0 (after G-48) — but each kill cost a 30-minute reaper retry |
| child recycles (`worker_max_tasks_per_child` 40) | 12 (15 child starts − 3 initial) | — |
| throughput | **9.25 videos/min** (600 in 64 min 53 s) | 6–8 videos/min |
| latency p50 / p90 / max | **9.7 s / 16.9 s / 30.5 s** | 28.0 s / 49.3 s / 140.9 s |
| reaper actions | every sweep `redispatched: 0, failed: 0` | (fixed in Week 1) |
| trail A1–A10 | **all zero**, determinism empty | all zero |

Cumulative under the new configuration: **0 kills in 1,166 videos** (480 matrix + 86 + 600), against
7 in 900 before. With 0.8 % as the null rate the chance of seeing 0 in 1,166 is about 0.01 %, so the
recycling and thread caps did remove the kills, not merely fail to catch them. Throughput and p50 are
better than any matrix cell measured last night, which ran while extraction and test jobs shared
the machine; this morning's batch had the VM to itself, so 9.25 / 9.7 s is the clean number and the
matrix's 8.6 / 19.5 s the loaded one.

The full trail report (`bash bench/trail_report.sh 'w2val_%'`):

```
=== decision trail for users LIKE 'w2val_%' ===
--- form checks by status ---
  COMPLETED : 686
--- runs by status ---
  completed : 686
--- runs by error_type (failed/abandoned) ---
--- decisions by checker ---
  depth_parallel_v0/depth AT_DEPTH  fitted=false advisory=true  n=428
  depth_parallel_v0/depth SHALLOW  fitted=false advisory=true  n=60
  depth_parallel_v0/depth UNCERTAIN  fitted=false advisory=true  n=198
  knees_forward_v0/knees_forward NOT_OBSERVED  fitted=false advisory=true  n=182
  knees_forward_v0/knees_forward OBSERVED  fitted=false advisory=true  n=311
  knees_forward_v0/knees_forward UNCERTAIN  fitted=false advisory=true  n=193
  posture_v1/posture FAULT  fitted=true advisory=false  n=365
  posture_v1/posture GOOD_FORM  fitted=true advisory=false  n=271
  posture_v1/posture UNCERTAIN  fitted=true advisory=false  n=50
--- pose passes observed ---
  pp1_f9850424580ae186  n=686
--- latency (completed runs, ms) ---
  n=686  p50=9994  p90=18700  max=41264

=== ASSERTIONS ===
  A1 PASS  terminal form checks with no run row                 0
  A2 PASS  completed runs with no checker decision              0
  A3 PASS  closed runs missing a pose_pass_id                   0
  A4 PASS  runs still open                                      0
  A5 PASS  form checks carrying a depth_score                   0
  A6 PASS  rule decisions not marked unfitted+advisory          0
  A7 PASS  answered rule decisions with no score                0
  A8 PASS  decisions with no inputs_digest                      0
  A9 PASS  completed runs with no n_frames                      0
  A10 PASS  terminal rows disagreeing with their latest closed run, or judged twice 0

--- determinism: digests with more than one distinct verdict ---
  (empty = deterministic)

=== ALL ASSERTIONS PASS ===
```

## 7. Where this leaves the plan's D table

| goal | target | measured |
|---|---|---|
| batch completeness | 1,000 → 1,000 terminal, 0 never-run, 0 flips | 900 (Week 1) + 686 (Week 2): 0 never-run, 0 flips, A1–A10 zero |
| worker loss | < 0.1 % unrecovered, reason recorded | 0 kills / 1,166; reclaim-on-redelivery in place (unit-tested; no kill has occurred to exercise it live) |
| throughput | ≥ 8 videos/min, p50 ≤ 30 s, p90 ≤ 60 s | 9.25 / 9.7 s / 16.9 s |
| API under load | 20 concurrent: 202 + 503 = 20, 0 dropped, 0 SIGKILL | 17 + 3 = 20, 0, 0 |
| e2e | passes against the running stack | 2 passed, 13.9 s |
| cache · images · observability | (deferred by the user's Week-2 scope) | — |

## 8. What the regression gate caught

The full unit + API suite in the rebuilt image, run after §6: **3 failed / 1,376 passed** against a
baseline of 2 pre-existing failures (G-35). The third, `test_correlation_id_in_error_responses`,
was green before Week 2: the header-forwarding edit to `core/exception_handlers.py` had mangled the
*Starlette* handler into `str(exc.detail, headers=…)` — syntactically valid, a `TypeError` at runtime,
and every unknown route on the live API answered **500 instead of 404 from ~02:00 to ~11:50 PDT**.
The FastAPI handler had a test; the Starlette one did not. Fixed (`f63eae3`), three handler tests
added (unknown route → 404 with the error body; headers forwarded by both handlers), API restarted,
`GET /api/v1/nonexistent → 404` verified live. Re-run: **1,380 passed, 2 failed** (the G-35 pair).

The lesson is the one this repository keeps teaching: an edit that parses is not an edit that works,
and a test on one of two twins guards one twin.
