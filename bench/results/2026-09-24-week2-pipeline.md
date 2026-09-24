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

## 6. Validation of the chosen cell at n=600 — NOT YET RUN TO COMPLETION

Started 02:16 PDT as `w2val_<ts>@example.com` and stopped at the user's request at 02:22 after 86
of 600 submissions (the 61 already queued drain on their own; the trail keeps them). The kill count
under 3 × 2 with recycling, against the 7-in-900 baseline, therefore stands at **0 in 566 videos so
far** (480 matrix + 86 here) and is not yet a like-for-like number. To finish:

```bash
SEL=bench/results/gate1b_selection.json N=600 TIMEOUT_S=7200 SUBMIT_STAGGER=2 \
    EMAIL="w2val_$(date +%s)@example.com" bash bench/stage_a_decision_trail.sh
bash bench/trail_report.sh 'w2val_%'
docker compose -f backend/deployment/docker-compose.yml logs --since 3h worker | grep -c "exited with 'signal 9"
```
