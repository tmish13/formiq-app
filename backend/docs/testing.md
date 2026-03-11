# FormIQ Backend — Testing Guide

> **TL;DR**
> - No Docker? → `make test-unit` (fast, always works)
> - Have Docker? → `make test-integration` and/or `make test-e2e`

---

## 1. Test Layers & Markers

| Layer | Marker | Docker? | What runs |
|---|---|---|---|
| **Unit / API** | _(default — no marker)_ | No | Pure unit tests + FastAPI contract tests with dependency overrides |
| **Integration** | `@pytest.mark.integration` | **Yes** | Real Postgres + Redis; video upload + form-check flows; Celery `.delay` is dispatched |
| **E2E** | `@pytest.mark.e2e` | **Yes** | Golden-path user journey: upload-url → upload-complete → form-check submit → history |

The default `addopts` in `pytest.ini` already excludes `integration`, `e2e`, and `slow` markers, so a bare `pytest` is always safe to run without Docker.

---

## 2. Quick Commands

All commands assume you are in `backend/`.

### Unit / API gate — no Docker required

```bash
cd backend
make test-unit
# equivalent: pytest -q -m "not integration and not e2e and not slow"
```

### Integration gate

> **IMPORTANT: Docker must be running.**
> Start Docker Desktop (macOS/Windows) or `sudo systemctl start docker` (Linux) before running this.

```bash
cd backend
make test-integration
```

`make test-integration` will:
1. Verify the Docker daemon is reachable (fails fast with a clear message if not).
2. Bring up `tests/docker-compose.test.yml` (Postgres on port 5434, Redis on port 6380).
3. Run `pytest -q -m integration tests/integration/form_checks/ tests/integration/videos/`.
4. Tear the stack down (`docker compose down -v`) — even if tests fail.

### E2E gate

> **IMPORTANT: Docker must be running** (same requirement as integration).

```bash
cd backend
make test-e2e
```

`make test-e2e` will:
1. Verify Docker daemon.
2. Bring up the same docker-compose stack.
3. Run `pytest -q -m e2e tests/e2e/test_full_flow.py`.
4. Tear the stack down.

---

## 3. What Each Gate Proves

### Unit / API (444 tests)
- **Core logic**: service methods, data transformations, ML feature computation.
- **HTTP contracts**: every FastAPI endpoint returns the right status code and schema when dependencies are mocked via `app.dependency_overrides`.
- Runs in ~10 s on a laptop; no network I/O.

### Integration (15 tests)
- **Real database**: SQLAlchemy async sessions against a live Postgres instance; schema is created fresh via Alembic / `create_all`.
- **Real Redis**: auth lock-out and cache behaviour verified against a live Redis.
- **Video lifecycle**: upload-url → upload-complete → Celery task dispatched; DB record reflects correct status.
- **Form-check lifecycle**: submit → pending status in DB; history endpoint returns the record; detail endpoint returns correct payload.

### E2E (1 test — `test_full_video_to_form_check_flow`)
- Chains the complete happy path a real user would take:
  1. `POST /api/v1/videos/upload-url` — presigned URL returned.
  2. `POST /api/v1/videos/upload-complete` — video marked `processing`.
  3. `POST /api/v1/form-checks/submit` — form check created with `pending` status.
  4. `GET /api/v1/form-checks/history` — new form check appears in list.
- Storage and Celery are mocked so no real S3 or worker is needed.

---

## 4. CI Mapping

The GitHub Actions workflow (`.github/workflows/backend-tests.yml`) mirrors the three make targets exactly:

| CI Job | Trigger | Equivalent command |
|---|---|---|
| `unit_api_tests` | Every push / PR | `make test-unit` |
| `integration_tests` | Pushes to `main`, PRs labelled `run-integration`, manual dispatch | `make test-integration` |
| `e2e_tests` | Manual dispatch, pushes to `staging` branch | `make test-e2e` |

The CI jobs start their own docker-compose stack (defined in `tests/docker-compose.test.yml`) and tear it down in an `always()` step so infra is never left dangling.

---

## 5. Docker Stack Details

File: `tests/docker-compose.test.yml`

| Service | Image | Port |
|---|---|---|
| `test-postgres` | `postgres:15-alpine` | `5434` (host) → `5432` (container) |
| `test-redis` | `redis:7-alpine` | `6380` (host) → `6379` (container) |

Env vars used by the integration conftest (`tests/integration/conftest.py`):

```
TEST_DATABASE_URL=postgresql+asyncpg://formiq_test:formiq_test@localhost:5434/formiq_test
TEST_REDIS_URL=redis://localhost:6380/0
```

These are set automatically by the conftest; you do not need to export them manually.

---

## 6. Adding New Tests

| Test type | Where to put it | Marker to add |
|---|---|---|
| Pure unit / mock-only | `tests/unit/` | _(none — excluded by default)_ |
| API contract | `tests/api/` | _(none)_ |
| Needs real DB/Redis | `tests/integration/` | `pytestmark = pytest.mark.integration` at module top |
| Golden-path journey | `tests/e2e/` | `pytestmark = pytest.mark.e2e` at module top |

Dead or drifted tests live in `tests/legacy/` and are excluded from all collection via `norecursedirs` in `pytest.ini`.
