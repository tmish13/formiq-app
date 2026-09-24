# G-23: the schema has one owner — 2026-09-24

## Finding

`app/core/lifespan.py` called `init_db()` → `Base.metadata.create_all()` on every boot when
`ENVIRONMENT` was `development` or `test`. The only deployable stack (`backend/deployment/docker-compose.yml`)
defaults to `development`, so the API created tables from the models on every start while the
migration chain was never run at boot: two sources of truth for the schema, and a first boot of an
empty database that Alembic never saw (the reason `alembic check` could stay red for months, G-38).

## Change (`audit/g23-schema-owner`)

- `backend/deployment/entrypoint.sh` (new, the API image's `CMD`): wait for Postgres, `alembic upgrade
  head`, then `exec gunicorn` with the flags that used to live in the Dockerfile `CMD`
  (`GUNICORN_WORKERS` env, default 4). Worker and beat override `command:` in compose and never run it.
- `app/core/lifespan.py`: `schema_owner_is_alembic(environment)` — `create_all()` only under
  `ENVIRONMENT=test` (the SQLite unit tests); every other environment gets its schema from Alembic.
- `tests/unit/test_schema_owner.py`: the gate per environment; the image starts through the
  entrypoint and the entrypoint migrates before it serves.

## Evidence

The migration chain alone builds the schema (checked first on a scratch `postgres:15`, from the
worker image):

```
alembic upgrade head   -> 13 revisions applied
alembic current        -> 0013_reconcile_schema (head)
alembic check          -> No new upgrade operations detected.
tables from migrations alone: 20   (= the live database)
```

The API boots through the entrypoint against an empty database (scratch `postgres:15` on the compose
network, the current `deployment-app` image with the code bind-mounted, `ENVIRONMENT=development`,
`GUNICORN_WORKERS=1`; the live stack and its data untouched):

```
entrypoint: alembic upgrade head
Running upgrade  -> 0001_baseline ... -> 0013_reconcile_schema
alembic current in the fresh container: 0013_reconcile_schema (head)
tables: 20
health/ready 200        (ready ~4 s after start)
```

Unit tests: 5 passed in the worker image.

## Follow-through

- The `CMD` change lives in the image: `bench/rebuild_images.sh app` rebuilds it (done as part of
  this branch's verification; the compose `app` service has no `command:` override, so the rebuilt
  container starts through the entrypoint).
- `docker compose down -v` was **not** run on the live stack: its database holds the label store and
  the decision trail every note cites. The scratch-database boot above is the same path.
