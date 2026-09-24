# Infrastructure: what is real

**The one deployable description of this system is `backend/deployment/docker-compose.yml`**
(five services: app, worker, beat, db, redis). It is what every measurement in `bench/results/`
ran against, what `bench/rebuild_images.sh` builds, and what the tests in `backend/tests/e2e`
talk to. Every knob it exposes is an environment variable with a measured default (worker
concurrency 3 × 2 threads, task and memory recycling, `UPLOAD_MAX_INFLIGHT`).

Removed on 2026-09-24 because each described a different system and none ran a worker:
`docker-compose.celery.yml` (queues nothing routes to), `backend/deployment/formiq.conf`
(started `python -m app.worker`, which does not exist), `infrastructure/docker/docker-compose*.yml`
(frontend/backend/nginx stacks with no Celery worker or beat).

What remains here is **not deployed and not verified**:

- `kubernetes/backend/` — a Deployment/Service/Ingress sketch for the API only (no worker, no
  beat). Probe paths corrected to the routes that exist (`/health/live`, `/health/ready`).
- `terraform/` — an AWS sketch (ECS cluster, CloudFront, S3, ACM, monitoring). It defines no ECS
  service, so it does not plan as a whole; the auto-scaling block that targeted the missing
  service was removed.
- `monitoring/` — Prometheus/Alertmanager configs with no scrape target in the compose stack.
- `docker/nginx/` — nginx configs and **self-signed, expired certificates and private keys**
  (`ssl/*.key`, CN=formiq-app.com, expired 2026-04-10). Nothing uses them; they are flagged for
  removal and are not secrets that protect anything.

Before any of these is used it needs the worker and beat added, an image build from the
`backend/Dockerfile`, and the `bench/` acceptance run against it.
