#!/usr/bin/env bash
# The API container's start: migrate, then serve.
#
# G-23: Alembic owns the schema. The app used to call Base.metadata.create_all() at startup in
# development, so the compose stack (ENVIRONMENT=development by default) had two sources of truth for
# the schema and a first boot never ran the migration chain. Now the API runs `alembic upgrade head`
# before gunicorn; the app only creates tables itself under ENVIRONMENT=test (SQLite unit tests).
# Worker and beat override `command:` in docker-compose.yml and never run this file.
#
# compose `depends_on` does not wait for Postgres readiness, so we do.
set -euo pipefail
cd /app

for i in $(seq 1 30); do
  if alembic current >/dev/null 2>&1; then break; fi
  echo "entrypoint: waiting for postgres ($i/30)"
  sleep 2
done

echo "entrypoint: alembic upgrade head"
alembic upgrade head
echo "entrypoint: schema at $(alembic current 2>/dev/null | tail -1)"

exec gunicorn --bind 0.0.0.0:8000 --workers "${GUNICORN_WORKERS:-4}" \
  --worker-class uvicorn.workers.UvicornWorker \
  --timeout 120 --graceful-timeout 30 --max-requests 500 --max-requests-jitter 50 \
  app.main:app
