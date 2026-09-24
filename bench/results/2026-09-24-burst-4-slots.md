# The 20-upload burst at the default 4 slots, on the G-54 code — 2026-09-24

The plan-D row "API under load: 20 concurrent uploads → 202 + 503 = 20, 0 dropped sockets, 0 SIGKILL"
had been measured at 4 slots only before G-54 (17 × 202 + 3 × 503 with the worker kill still present)
and at 8 slots after it (20 × 202, no 503 because 4 × 8 slots exceed 20). This is the row at the
shipped default.

## Command

```bash
# app container as rebuilt today (UPLOAD_MAX_INFLIGHT=4 in the container, gunicorn 4 workers)
SUBMIT_STAGGER=0 N=20 TIMEOUT_S=900 EMAIL="up4_$(date +%s)@example.com" bash bench/phase1_concurrent_batch.sh
# docker stats --no-stream '{{.MemUsage}}' sampled in a loop; app log grepped for SIGKILL / Booting / " 503 "
```

Environment: `deployment-app` from the image rebuilt 2026-09-24 (gunicorn `--timeout 120
--graceful-timeout 30 --max-requests 500`), code at `fdcc219`, worker 3×2 taking the accepted videos,
Docker Desktop 8 vCPU / 7.65 GiB, host on battery with Low Power Mode.

## Raw output

```
submitted 14/20 in 4s
stuck (PENDING/PROC)  : 0
--- http codes / curl rc ---
  14 http=202
   6 http=503
  20 curl_rc=0
--- app peak memory ---
peak 1072 MiB over 52 samples
--- app worker deaths/boots since the harness started ---
0
--- 503 responses in the app log during the run ---
6
```

## Result

| quantity | want | got |
|---|---|---|
| 202 + 503 | 20 | 14 + 6 = 20 |
| dropped sockets (`curl_rc` ≠ 0) | 0 | 0 |
| gunicorn workers SIGKILLed | 0 | 0 |
| app peak memory | — | 1,072 MiB (was 4,656 MiB before G-54 at 8 slots) |
| accepted videos reaching a terminal state | all | 14 / 14, 0 stuck |

The row holds at the default. The six 503s carry `Retry-After: 5` (G-36 backpressure); the harness
does not retry, so 14 videos were processed and 6 clients were told to come back, which is the
intended behaviour under a burst larger than the API's in-flight budget.
