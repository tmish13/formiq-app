"""
Fixtures for Form Check API integration tests.

Requires docker-compose services:
  docker compose -f tests/docker-compose.test.yml up -d

Run:
  cd backend
  pytest -q -m integration tests/integration/form_checks/ \
    --override-ini="addopts=-q --asyncio-mode=auto"
"""
import os
import uuid

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from unittest.mock import AsyncMock, MagicMock, patch

# ---------------------------------------------------------------------------
# Env vars must be set BEFORE app imports so that database.py module-level
# engine creation (if triggered) doesn't fail.  pytest.ini sets ENVIRONMENT=test;
# we just need TEST_DATABASE_URL to point at the docker PG service.
# These are no-ops if the caller already exported the vars.
# ---------------------------------------------------------------------------
os.environ.setdefault(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://formiq_test:formiq_test@localhost:5434/formiq_test_db",
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6380/0")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6380")

# ---------------------------------------------------------------------------
# App imports AFTER env-var setup
# ---------------------------------------------------------------------------
import app.db.base as _register_models  # noqa: F401 – side-effect: populates Base.metadata
from app.core.database import Base, get_async_db
from app.api import deps
from app.models.user import User
from app.models.exercise import ExerciseTemplate
from app.core.password import get_password_hash

_PG_URL = os.environ["TEST_DATABASE_URL"]


# ---------------------------------------------------------------------------
# Session-scoped engine + schema lifecycle
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
async def pg_engine():
    """
    Create all tables in the test PostgreSQL instance once per session,
    then drop them on teardown.
    """
    engine = create_async_engine(_PG_URL, poolclass=NullPool, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture(scope="session")
def pg_factory(pg_engine):
    """Async session factory bound to the test PostgreSQL engine."""
    return async_sessionmaker(
        pg_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=True,
    )


# ---------------------------------------------------------------------------
# Seeded data (session-scoped – created once, reused across tests)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
async def squat_template(pg_factory) -> ExerciseTemplate:
    """Seed one ExerciseTemplate(name='squat') for the session."""
    async with pg_factory() as session:
        template = ExerciseTemplate(
            name="squat",
            difficulty="beginner",
            muscle_group="legs",
        )
        session.add(template)
        await session.commit()
        await session.refresh(template)
        return template


@pytest.fixture(scope="session")
async def int_user(pg_factory) -> User:
    """Seed one test user (unique email/username per session)."""
    suffix = uuid.uuid4().hex[:8]
    async with pg_factory() as session:
        user = User(
            email=f"inttest_{suffix}@formiq.com",
            username=f"inttest_{suffix}",
            hashed_password=get_password_hash("PvOneShip2026!"),
            is_active=True,
            is_verified=True,
            is_email_verified=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


# ---------------------------------------------------------------------------
# HTTP clients (function-scoped – fresh dep-overrides per test)
# ---------------------------------------------------------------------------

@pytest.fixture
async def auth_client(pg_factory, int_user, squat_template):
    """
    AsyncClient with:
      - DB → real PostgreSQL test session
      - current_user → seeded int_user (no JWT needed)
      - StorageService.upload_file → AsyncMock (no S3 calls)
      - process_form_check_task.delay → MagicMock (no Celery)
    """
    from app.main import app
    from app.services.storage_service import StorageService

    captured_user = int_user  # snapshot for closure

    async def _override_db():
        async with pg_factory() as session:
            yield session

    def _override_user():
        return captured_user

    mock_storage = MagicMock(spec=StorageService)
    # Use side_effect to return a unique URL per call, avoiding the unique
    # constraint on videos.object_key when multiple tests call /submit.
    mock_storage.upload_file = AsyncMock(
        side_effect=lambda *a, **kw: f"https://s3.example.com/test/{uuid.uuid4().hex}.mp4"
    )
    mock_storage.delete_file = AsyncMock(return_value=None)

    def _override_storage():
        return mock_storage

    app.dependency_overrides[deps.get_async_db] = _override_db
    app.dependency_overrides[deps.get_current_active_user] = _override_user
    app.dependency_overrides[deps.get_current_user] = _override_user
    app.dependency_overrides[deps.get_storage_service] = _override_storage

    with patch("app.tasks.analysis_tasks.process_form_check_task") as mock_task:
        mock_task.delay = MagicMock(return_value=None)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac

    # Always clean up overrides so other tests aren't affected.
    app.dependency_overrides.pop(deps.get_async_db, None)
    app.dependency_overrides.pop(deps.get_current_active_user, None)
    app.dependency_overrides.pop(deps.get_current_user, None)
    app.dependency_overrides.pop(deps.get_storage_service, None)


@pytest.fixture
async def anon_client():
    """AsyncClient without auth override – requests will receive 401."""
    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
