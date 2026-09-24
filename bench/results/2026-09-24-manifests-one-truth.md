# One deployable description (plan D5b / execution plan item 11) — 2026-09-24

## Finding

Four files claimed to describe how FORMIQ runs, and no two agreed: `docker-compose.celery.yml`
(worker consuming queues nothing routes to, G-11; beat; flower), `backend/deployment/formiq.conf`
(supervisor starting `python -m app.worker`, a module that does not exist), and
`infrastructure/docker/docker-compose{,.prod,.override}.yml` (frontend/backend/nginx/db stacks
with **no worker and no beat**, so the pipeline could not run at all). The Kubernetes sketch probed
`/health` and `/ready`; the router has no root route and `/ready` never existed (G-15). The
Terraform sketch scaled `aws_ecs_service.backend`, which no file defines, so it could not plan.

## Change (`audit/manifests-one-truth`)

- Deleted: `docker-compose.celery.yml`, `backend/deployment/formiq.conf`,
  `infrastructure/docker/docker-compose.yml`, `docker-compose.prod.yml`, `docker-compose.override.yml`.
  Nothing in the repo referenced them except the audit's own inventory (kept as history).
- `infrastructure/kubernetes/backend/deployment.yaml`: liveness `/health` → `/health/live`,
  readiness `/ready` → `/health/ready` (the routes that exist, `health.py:356,420`).
- `infrastructure/terraform/performance.tf`: the `aws_appautoscaling_target/policy` pair removed,
  with a comment saying why.
- `infrastructure/README.md`: `backend/deployment/docker-compose.yml` is the only deployable
  description; what remains under `infrastructure/` is a sketch, not deployed, not verified — and
  the committed self-signed, expired key pairs under `docker/nginx/ssl/` are flagged.

## Verification

```bash
docker compose -f backend/deployment/docker-compose.yml config -q; echo $?        # 0
git ls-files | grep -c 'docker-compose.*\.yml'                                     # 2
#   backend/deployment/docker-compose.yml  backend/tests/docker-compose.test.yml
python3 -c "import yaml; ...deployment.yaml..."   # probes: /health/live /health/ready
grep -c aws_appautoscaling infrastructure/terraform/performance.tf                 # 0
```

`kubectl apply --dry-run=client` needs a reachable cluster (the local kubeconfig asks for
credentials) and `terraform` is not installed here, so the k8s and terraform files are validated
structurally only (YAML parses; the dangling reference is gone). They remain sketches.

## Not done

- The k8s and terraform sketches still describe an API-only system (no worker, no beat). Making
  either deployable is a project, not a cleanup, and there is no deployment target today.
- `infrastructure/docker/nginx/ssl/*.key`: self-signed private keys (CN=formiq-app.com, issued
  2025-04-10, expired 2026-04-10, committed 2025-04-11). They protect nothing and trust nothing,
  but they are private keys in a repository; deleting them is the user's call (G-55, filed).
