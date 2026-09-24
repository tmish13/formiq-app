# Two health routes that returned 500 on every call (plan item C5) — 2026-09-24

## Finding

`GET /health/metrics` and `GET /health/rate-limits` built `HealthService()` without its three
constructor arguments and then called `get_prometheus_metrics()` / `get_rate_limit_metrics()`, the
first of which is defined nowhere. Both raised on every request. Nothing tested them: the only tests
that touched them lived in `tests/legacy/`, which `pytest.ini` excludes.

## Change (`audit/health-routes`)

- `/health/metrics` returns `prometheus_client.generate_latest()` with the Prometheus content type:
  the process/platform collectors plus whatever the app registers (the HTTP instrumentator is not
  installed — plan D8, no Prometheus stack — so this is a liveness-grade exposition, not a dashboard).
- `/health/rate-limits` removed: it reported on a middleware that has never been installed
  (`main_setup.py:58`, see the cache note).
- `tests/api/test_health_metrics.py` (2): 200 + `text/plain` + `# HELP` lines; 404 for the removed route.
  6 passed with the exception-handler tests in the worker image.

## Evidence on the rebuilt API

```
GET /health/metrics      -> 200 text/plain; version=1.0.0; charset=utf-8   (123 lines, 53 metric families)
GET /health/rate-limits  -> 404
```

Noted, not changed: the health router is also included by `api/v1/api.py` with a second `/health`
prefix on top of its own, so `/api/v1/health/metrics` is 404 and the working paths are the root ones
(`/health/ready`, `/health/live`, `/health/metrics`) — the ones the k8s sketch now probes.
