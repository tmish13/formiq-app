# Phase 1 — worker execution model

**Date:** 2026-09-20 · **Branch:** `audit/phase1-worker-model`
**Closes:** G-02, G-03, G-10, G-19, G-31, G-32, G-34, G-37
**Opens:** G-33, G-35, G-36

## What started this

A 20-video concurrent run through API → Celery → Postgres produced two failures:

1. **17 of 20 tasks died and stayed `PENDING` forever.** `RuntimeError: asyncio.run() cannot
   be called from a running event loop` under `-P gevent`, where every task shares one thread.
   No `acks_late`, so the broker had already acked; no retry, so nothing recovered.
2. **Only 3 of 20 scores matched an offline run of the same code on the same bytes.**

Both are now explained and fixed. (2) turned out not to be a Celery problem at all.

---

## 1. The score depended on the previous video (G-31)

`AIService` is a per-worker singleton holding one `mp.solutions.pose.Pose(static_image_mode=False)`
— tracking mode, where each frame is seeded by the previous frame's landmarks. Correct *within*
a video, wrong *across* videos. Nothing reset it between tasks.

Same target video, one long-lived service, varying predecessor:

| condition | before | after |
|---|---|---|
| cold tracker, run 1 | 0.618214 | 0.618214 |
| cold tracker, run 2 | 0.618214 | 0.618214 |
| after `33348_2` | 0.439524 | **0.618214** |
| after `36049_2` | 0.652968 | **0.618214** |
| after itself | 0.586389 | **0.618214** |
| **spread** | **0.214** | **0.000000** |

The decision threshold is **0.525**. Before, the spread straddled it — the predecessor could
flip the verdict. After, every run equals the value a fresh process already gave.

**This was never a Celery bug.** `bench/celery_parity_offline.py` reused one `AIService` across
all 20 videos too. Both paths were wrong the same way; they disagreed only because they
processed the videos in different orders. That is the whole 3/20 match rate.

**Precision caveat:** `loader.py:604` applies `round(prob_fault, 6)`, so "0.000000" means
identical at 1e-6 — the resolution the pipeline reports and stores. Bit-equality below that is
not established here. Phase 0's numbers were rounded by the same line, so before/after is like
for like.

**Scope:** the published F1 / ablation / Penn-shortcut numbers are unaffected. Those scored
precomputed keypoint JSON, so MediaPipe was never invoked. Only video-decode paths carried it.

---

## 2. Worker execution model

| change | file |
|---|---|
| `-P gevent` → `-P prefork --concurrency=4` | `deployment/docker-compose.yml:47` |
| `task_acks_late=True`, `task_reject_on_worker_lost=True` | `core/celery_app.py` |
| time limits 180/300 → 300/360 | `core/celery_app.py` |
| Celery async engine built lazily and keyed on PID, never at import | `core/database.py` |

Prefork forks children **after** `app.core.database` is imported, so an import-time engine is
inherited by all four. NullPool means there were no live asyncpg sockets to inherit, which is
why this had not corrupted data — but the engine still must not be shared. A subprocess test
asserts the engine is `None` after import; another asserts a PID change yields a new object.

Worker banner after the change:

```
- *** --- * --- .> concurrency: 4 (prefork)
[tasks]
  . app.tasks.analysis_tasks.process_form_check
  . app.tasks.maintenance_tasks.reap_stuck_form_checks
```

Exactly two tasks. Config verified live: `acks_late=True reject_on_lost=True soft=300 hard=360
prefetch=1`.

---

## 3. The dead tasks never ran (G-19)

All four were `async def` under a plain `@app.task`. Celery has no await step: it calls the
function, gets a coroutine object back, and returns *that* as the result.

```
app.tasks.video_tasks.process_video_celery_task    -> coroutine
app.tasks.ai_tasks.detect_pose_celery_task         -> coroutine
app.tasks.ai_tasks.calculate_angles_celery_task    -> coroutine
ai.perform_form_analysis                           -> coroutine
app.tasks.analysis_tasks.process_form_check        -> dict        (the live one)
```

`perform_form_analysis_celery_task` is the trap: `autoretry_for` wraps it in a sync shim so
`inspect.iscoroutinefunction` reports **False**, yet calling it still returns a coroutine.

Implementations moved to `backend/archive/tasks_old/`; the module names survive as stubs that
raise. `POST /analysis/analyze-form/{id}` returns **501** before touching the DB.

`confirm_video_upload` deliberately does **not** 501: `POST /videos/upload-complete` is a live
frontend endpoint and dispatching was a side effect, not its purpose. It used to enqueue the
dead task, set the video `PROCESSING` and store a `celery_task_id` pointing at nothing — so
every video confirmed through it sat in `PROCESSING` forever. It now leaves the video
`UPLOADED`, which is what it is.

---

## 4. Acceptance: 20 videos through the real stack

Submitted through the API to a live worker, polled in Postgres until terminal.

| run | submit mode | submitted | terminal | stuck | distinct `content_hash` | NULL | wall |
|---|---|---|---|---|---|---|---|
| 2 | all at once | 20/20 | 20 COMPLETED | **0** | 12 | 8 | 226s |
| 3 | all at once | **13**/20 | 13 COMPLETED | **0** | 13 | 0 | 65s |
| 4 | 2s stagger | **20/20** | **20 COMPLETED** | **0** | **20** | **0** | **62s** |

Run 2's 8 NULL hashes were stale code: `gunicorn --workers 4` processes booted at 17:10, before
the idempotency commit. Some were respawned at 20:15–20:16 and those wrote hashes. The app was
restarted before runs 3 and 4.

Runs 2 and 3 lost submissions **before they reached the application** — see G-36 below. Run 4
staggers submits to stay under that API ceiling, which is what isolates the pipeline claim:

> **Every task that was dispatched reached a terminal state. 0 stuck, in all three runs.**

Per-task duration under concurrency 4 (run 2, n=19): **min 28s, p50 38s, max 65s** — well
inside the 300s soft limit. Notably slower than the 10–12 s/video measured serially, because
four complexity-2 MediaPipe tasks now share 8 cores.

---

## 5. Failure behaviour

```
=== 1. duplicate submit (same user, same bytes, same model) ===
first  submit -> 32d5fe51-9ddc-46ac-8def-2989c091d367
second submit -> 32d5fe51-9ddc-46ac-8def-2989c091d367
rows for it    : 1   (expect 1)
same id back   : YES

=== 2. corrupt video (permanent -> FAILED, no retry) ===
status : FAILED
reason : No analysis could be produced from this video: pose extraction returned
         0 usable frame(s) out of 0. The file may be unreadable, may not show a
         person clearly enough, or may be too short to analyse.

=== 3. stranded row (reaper) ===
planted PROCESSING row, last touched 2h ago
--- strike 1 ---
REAPER {"scanned": 1, "redispatched": 1, "failed": 0, "errors": 0}
details      : {"reaper_redispatch_count": 1, "reaper_stuck_from_status": "processing", ...}
final status : COMPLETED
--- strike 2 ---
REAPER {"scanned": 1, "redispatched": 0, "failed": 1, "errors": 0}
status after : FAILED
reason       : Recovered by the stuck-row reaper: Stuck in processing with no worker
               since 2026-09-20 18:57:53+00:00; already re-dispatched 1 time(s). Giving up.
```

That corrupt-video reason did not exist until G-37 was fixed. On the first attempt the same
file produced `FAILED` with **no reason at all**, because `error_details` is not a column on
`FormCheck` — six places assign to it and SQLAlchemy discards every one. Every failure this
system has ever reported was reason-less.

---

## 6. Migration

`0009_content_hash_idempotency`: three columns, a **partial** unique index
(`WHERE content_hash IS NOT NULL`, so pre-existing NULL rows stay out by intent rather than by
NULL-distinctness quirk), and `(status, updated_at)` for the reaper scan.

Verified up → down → up against Postgres 15; single head.

```
"ix_form_checks_status_updated_at" btree (status, updated_at)
"uq_form_checks_user_content_model_spec" UNIQUE, btree
    (user_id, content_hash, model_version, spec_hash) WHERE content_hash IS NOT NULL
```

The revision id is 29 characters because `alembic_version.version_num` is `varchar(32)`: a
longer id fails the final UPDATE *after* the DDL has run. Found the hard way; now asserted by a
test.

---

## 7. `FOR UPDATE` was rejected, deliberately

The plan proposed `SELECT … FOR UPDATE` on the PENDING→PROCESSING transition. Implemented as a
conditional `UPDATE … WHERE status='pending'` plus a `rowcount` check instead.

`FOR UPDATE` would hold a row lock for the entire analysis — minutes of pose extraction and
inference — against a NullPool connection. A worker killed mid-task would strand the lock until
its connection timed out, and the reaper would then block behind it. One conditional UPDATE is
atomic in a single statement, holds nothing past commit, and `rowcount` says exactly whether we
won.

---

## 8. Tests

**1120 passed**, 2 failed, across `tests/unit` + `tests/api`.

Both failures — `test_register_duplicate_email_returns_400` and
`test_multiple_concurrent_requests_unique_correlation_ids` — were verified failing at
`19d24e7` in a clean `git worktree` **before** any Phase 1 work. They are unrelated to this
branch and are recorded as G-35.

New: `test_pose_tracker_reset.py` (3, integration), `test_temp_file_cleanup.py` (6),
`test_retired_tasks.py` (9), `test_exception_classification.py` (23),
`test_maintenance_tasks.py` (20), `test_idempotency.py` (13),
`test_retired_endpoints.py` (4).

**`pytest` could not run inside the built image at all** until this branch: `pytest.ini:58`
lists `pytest-timeout` under `required_plugins` and `requirements.txt` never installed it, so
every in-container invocation aborted before collection. Every test result before today came
from a host venv, not the image. (G-32)

---

## 9. Environment

- Host: Darwin 25.4.0, 8 cores; Docker Desktop VM **7.65 GiB**
- Images: `deployment-app:latest`, `deployment-worker:latest`, python 3.11, CPU only
- Backend bind-mounted (`..:/app`), so code changes need a container **restart**, not a rebuild
- MediaPipe complexity 2 (G-21 fix in effect)
- Memory at rest: worker **2.75 GiB**, app **2.54 GiB**, db 117 MiB, redis 9 MiB
- Disk at run time: **17 GiB free (97% used)** — the plan wants 50 GiB before Phase 6

---

## 10. Commands

```bash
docker compose -f backend/deployment/docker-compose.yml up -d
docker compose -f backend/deployment/docker-compose.yml exec app alembic upgrade head

# unit + api, inside the image
docker run --rm -m 4g --network deployment_default \
  -v $PWD/backend:/app -e POSTGRES_SERVER=db -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=formiq \
  -e SECRET_KEY=dev-only-insecure-secret-key-32chars-minimum \
  -e REDIS_HOST=redis -e REDIS_PORT=6379 -w /app deployment-worker:latest \
  bash -lc 'pip install -q pytest-timeout==2.2.0; pytest -p no:randomly \
    --import-mode=importlib --override-ini="addopts=-m \"not integration and not e2e and not slow\" \
    --asyncio-mode=auto" -q tests/unit tests/api'

SUBMIT_STAGGER=2 bash bench/phase1_concurrent_batch.sh   # 20/20 terminal, 0 stuck
bash bench/phase1_recovery_checks.sh                     # dedupe, corrupt video, reaper
```

---

## 11. Not done, and why

- **No beat service in `backend/deployment/docker-compose.yml`.** The reaper is registered and
  works — proven above by invoking it directly — but nothing schedules it in this compose.
  `docker-compose.celery.yml:49` has a beat container. Adding a service is a deployment-manifest
  change and was not made unasked.
- **`test_worker_kill`** (`docker kill` mid-batch, restart, assert no loss or duplicates) is the
  one planned test not yet run. The mechanisms it covers are in place and individually verified
  — `acks_late`, `reject_on_worker_lost`, the atomic claim, and the reaper — but the combined
  kill-and-recover path has not been exercised end to end.
- **G-33** (`_process_frame_batch_parallel` / `_process_gpu_batch` share one tracker across
  threads) is filed, not fixed. It is a different defect from G-31, it is off the live path, and
  fixing unused code paths is how unused code paths come to be trusted.
