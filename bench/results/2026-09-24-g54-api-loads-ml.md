# G-54: the API built the ML stack per gunicorn worker on its first request — 2026-09-24

## Finding

The 20-upload OOM (G-36) survived backpressure and streaming because the memory was never the
upload. Every `/form-checks/submit` resolves `FormCheckService`, whose dependency list includes
`AIService`; `app/api/deps.py` built it as a per-process singleton on the first request that
needed it — MediaPipe Pose at complexity 2, torch, `MLModelService`, `EnhancedSquatModelLoader` —
although the API never runs inference (the Celery worker does; nothing on the submit path touches
`ai_service`). Four gunicorn workers each paid it, all at once under a burst.

Measured with one 0.5 MB upload on a freshly restarted API (`docker top`, RSS per worker):

```
before the fix   idle 315 316 315 315 MiB  ->  after ONE upload 722 316 320 315   (+407 MiB, permanent; submit 2.03 s)
after the fix    idle 316 313 312 309 MiB  ->  after ONE upload 320 324 315 319   (+4..11 MiB;           submit 0.27 s)
```

## Change (`audit/g54-api-loads-ml`)

- `app/core/deps.py`: `LazyAIService` — a proxy whose `__getattr__` builds the real `AIService`
  once per process on the first *method call*, never on injection; `lazy_ai_service` is the
  module-level instance; `get_ai_service()` returns it. `app/api/deps.py` returns the same proxy
  (its eager singleton removed). The legacy in-API analysis paths still work and still pay, when used.
- Tests `tests/unit/test_g54_api_ai_service_is_lazy.py` (3): injection constructs nothing (both
  dependency modules hand out one proxy); first use constructs once and delegates; constructing
  `FormCheckService` with the proxy stays cheap. 64 passed with the form-check API/contract,
  backpressure, idempotency and auth-flow tests in the worker image.

## Command

```bash
# API restarted on this branch (bind mount), UPLOAD_MAX_INFLIGHT=8 in the container, worker 3x2 idle
SUBMIT_STAGGER=0 N=20 TIMEOUT_S=900 EMAIL="upc_$(date +%s)@example.com" bash bench/phase1_concurrent_batch.sh
# docker stats --no-stream '{{.MemUsage}}' sampled in a loop; app log grepped for SIGKILL/Booting afterwards
```

## The same burst, three arms (20 simultaneous uploads, 8 slots per API process, 4 processes)

| arm | branch | 202 | dropped (`curl_rc=52`) | 503 | app peak memory | gunicorn workers SIGKILLed | every 202 terminal |
|---|---|---|---|---|---|---|---|
| baseline (`upb_`) | `audit/cache-is-the-db` | 14 | 6 | 0 | 4,656 MiB | 1 | yes |
| streaming (`upa_`) | `audit/upload-streaming` | 12 | 8 | 0 | 4,322 MiB | 1 | yes |
| **lazy AIService (`upc_`)** | `audit/g54-api-loads-ml` | **20** | **0** | 0 | **972 MiB** (100 samples) | **0** | yes (0 stuck) |

Workers after the burst: 334 / 330 / 333 / 332 MiB (before: 1,240 / 1,039 / 1,444). All 20
submits were accepted in 1 s; with 4 × 8 = 32 slots the 503 gate had no reason to fire.

Environment: `deployment-app` (4 UvicornWorkers, bind-mounted code), Docker Desktop 8 vCPU /
7.65 GiB, worker container 3×2 taking the accepted videos, host on battery with Low Power Mode.

## Plan-D table row, updated

"API under load: 20 concurrent uploads → 202 + 503 = 20, 0 dropped sockets, 0 SIGKILL" — met at
8 slots (20 + 0 = 20, 0 dropped, 0 SIGKILL). At the default 4 slots the earlier run gave
17 × 202 + 3 × 503 with the kill still present; that run should be repeated on this branch
before the row is quoted at 4 slots.
