# Upload streaming (G-36, plan D4a / execution plan item 9) — 2026-09-24

## Change (`audit/upload-streaming`)

- `StorageService.upload_file` and `upload_file_and_get_key` no longer do `await file.read()` +
  `BytesIO(...)`; they rewind and hand the provider the `UploadFile`'s own spooled file (Starlette
  spools multipart bodies to disk past 1 MiB). The local provider copies it in `HASH_CHUNK_BYTES`
  (1 MiB) pieces instead of `file_obj.read()` whole. The S3 provider already passes the object to
  `put_object(Body=...)`; streaming through boto is not verified here (no S3 in this environment).
- `Dockerfile` CMD: `--timeout 120 --graceful-timeout 30 --max-requests 500 --max-requests-jitter 50`
  (takes effect on the next image build; the running container still has the old CMD).
- `docker-compose.yml` app env: `UPLOAD_MAX_INFLIGHT=${UPLOAD_MAX_INFLIGHT:-4}` so the G-36 bound is
  a deploy-time knob.
- Tests: `tests/unit/test_upload_streaming.py` (3): the provider receives the upload's own file
  object rewound to 0, not a copy, on both service methods; the local provider's reads are all
  bounded by `HASH_CHUNK_BYTES` and the bytes written are identical. 45 passed with the replay-key,
  backpressure, S3 and idempotency tests in the worker image.

## Measurement: 20 simultaneous uploads, 8 slots per API process, before and after

```bash
# compose app env UPLOAD_MAX_INFLIGHT=8 (docker compose up -d app), then, for each arm:
SUBMIT_STAGGER=0 N=20 TIMEOUT_S=900 EMAIL="up{b,a}_$(date +%s)@example.com" bash bench/phase1_concurrent_batch.sh
# with `docker stats --no-stream --format '{{.MemUsage}}' deployment-app-1` sampled in a loop, and
# `docker compose logs app --since <run>` grepped for SIGKILL / Booting worker afterwards
```

Environment: API = 4 gunicorn UvicornWorkers (`deployment-app`, bind-mounted code, restarted between
arms), worker 3×2 running the accepted videos, Docker Desktop 8 vCPU / 7.65 GiB, host on battery.

| arm | submitted (202) | dropped (`curl_rc=52`, empty reply) | 503 | app peak memory | gunicorn workers SIGKILLed |
|---|---|---|---|---|---|
| before (`upb_`) | 14 / 20 | 6 | 0 | 4,656 MiB (80 samples) | 1 (`Worker (pid:10) was sent SIGKILL! Perhaps out of memory?`) |
| after (`upa_`) | 12 / 20 | 8 (one `http=100` then dropped) | 0 | 4,322 MiB (63 samples) | 1 (`pid:8`) |

**Negative.** The copy is gone (unit-tested), the peak moved 4,656 → 4,322 MiB, and the failure
mode did not change: one worker killed, its in-flight requests answered with an empty reply. The
503 gate never fired because the requests never reached it — the kill comes first. Every accepted
video reached a terminal state (0 stuck) in both arms.

## Where the memory actually is (found while writing this up)

The container's memory series after the burst is flat at ≈ 4,067 MiB and never comes down, and
`docker top` shows the three surviving workers at 1,240 / 1,039 / 1,444 MiB RSS with the freshly
booted replacement at 317 MiB. Memory that is not returned when the uploads end is not an upload
buffer. A single 0.5 MB upload on a freshly restarted API:

```
idle after restart + 1 health call:   315 / 316 / 315 / 315 MiB per worker
after register + login:               315 / 316 / 320 / 315
after ONE upload (202 in 2.03 s):     722 / 316 / 320 / 315      <- +407 MiB, permanent
```

The request path constructs `AIService()` — MediaPipe Pose at complexity 2, torch, the model
loaders — as a per-process singleton on the first request that resolves the form-check service
(`app/api/deps.py:144`), although the API never runs inference: the worker does. Four API workers
initialising it at once under a burst is the OOM. Filed as **G-54**; fixed on `audit/g54-api-loads-ml`
with its own measurement.
