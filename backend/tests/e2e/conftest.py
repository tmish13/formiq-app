"""
Fixtures for E2E golden-path tests.

Requires docker-compose services:
  docker compose -f tests/docker-compose.test.yml up -d

Run:
  cd backend
  pytest -q -m e2e tests/e2e/ \\
    --override-ini="addopts=-q --asyncio-mode=auto"

These fixtures combine the patterns from both integration test packages:
  - tests/integration/videos/conftest.py
  - tests/integration/form_checks/conftest.py

Both video and form-check dependencies are overridden so the full request
path exercises real Postgres + Redis with mocked S3 and Celery.
"""
import asyncio
import io
import os
import uuid

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from unittest.mock import AsyncMock, MagicMock, patch

# ---------------------------------------------------------------------------
# Env vars must be set BEFORE any app imports
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
import app.db.base as _register_models  # noqa: F401 – populates Base.metadata
from app.core.database import Base, get_async_db
from app.api import deps
from app.models.user import User
from app.models.exercise import ExerciseTemplate
from app.core.password import get_password_hash
from app.core.config import settings as app_settings
from app.services.storage_service import StorageService
from app.services.video_service import VideoService

_PG_URL = os.environ["TEST_DATABASE_URL"]


# ---------------------------------------------------------------------------
# Session-scoped event loop
# Required so that session-scoped async fixtures (pg_engine, e2e_user, etc.)
# all share the same event loop.  Mirrors tests/integration/conftest.py.
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def event_loop():
    """Force a session-scoped event loop for session-scoped async fixtures."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---------------------------------------------------------------------------
# Session-scoped: engine + schema lifecycle
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
async def pg_engine():
    """Create all tables once per test session; drop on teardown."""
    engine = create_async_engine(_PG_URL, poolclass=NullPool, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture(scope="session")
def pg_factory(pg_engine):
    """Async session factory bound to the test engine."""
    return async_sessionmaker(
        pg_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=True,
    )


# ---------------------------------------------------------------------------
# Session-scoped: seeded reference data
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
async def e2e_user(pg_factory) -> User:
    """Seed one test user (unique per session)."""
    suffix = uuid.uuid4().hex[:8]
    async with pg_factory() as session:
        user = User(
            email=f"e2e_{suffix}@formiq.com",
            username=f"e2e_{suffix}",
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
# Function-scoped: mock storage + Celery tasks
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_storage() -> MagicMock:
    """A mock StorageService that returns unique URLs and never touches S3."""
    storage = MagicMock(spec=StorageService)
    storage.generate_presigned_upload_url = AsyncMock(
        return_value={"url": "https://s3.example.com/upload/e2e.mp4", "fields": {}}
    )
    storage.get_public_url = AsyncMock(
        return_value="https://s3.example.com/public/e2e.mp4"
    )
    # form-check submit uploads the video bytes; return a unique object key each call
    storage.upload_file = AsyncMock(
        side_effect=lambda *a, **kw: f"https://s3.example.com/test/{uuid.uuid4().hex}.mp4"
    )
    storage.delete_file = AsyncMock(return_value=None)
    return storage


# ---------------------------------------------------------------------------
# Function-scoped: combined auth client
# Overrides:
#   deps.get_async_db          → real Postgres test session
#   deps.get_current_user      → seeded e2e_user  (video endpoints)
#   deps.get_current_active_user → seeded e2e_user  (form-check endpoints)
#   deps.get_video_service     → VideoService with mock storage
#   deps.get_storage_service   → mock storage (form-check submit upload)
#   video Celery task          → MagicMock (no real worker)
#   form-check Celery task     → MagicMock (no real worker)
# ---------------------------------------------------------------------------

@pytest.fixture
async def e2e_client(pg_factory, e2e_user, squat_template, mock_storage):
    """AsyncClient for the full golden-path E2E test."""
    from app.main import app

    captured_user = e2e_user

    async def _override_db():
        async with pg_factory() as session:
            yield session

    def _override_user():
        return captured_user

    async def _override_video_service():
        async with pg_factory() as session:
            yield VideoService(
                db=session,
                storage_service=mock_storage,
                app_settings=app_settings,
            )

    def _override_storage():
        return mock_storage

    app.dependency_overrides[deps.get_async_db] = _override_db
    app.dependency_overrides[deps.get_current_user] = _override_user
    app.dependency_overrides[deps.get_current_active_user] = _override_user
    app.dependency_overrides[deps.get_video_service] = _override_video_service
    app.dependency_overrides[deps.get_storage_service] = _override_storage

    with (
        patch("app.tasks.video_tasks.process_video_celery_task") as mock_vid_task,
        patch("app.tasks.analysis_tasks.process_form_check_task") as mock_fc_task,
    ):
        mock_vid_task.delay = MagicMock(return_value=MagicMock(id="fake-video-task"))
        mock_fc_task.delay = MagicMock(return_value=None)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac

    # Always clean up overrides
    app.dependency_overrides.pop(deps.get_async_db, None)
    app.dependency_overrides.pop(deps.get_current_user, None)
    app.dependency_overrides.pop(deps.get_current_active_user, None)
    app.dependency_overrides.pop(deps.get_video_service, None)
    app.dependency_overrides.pop(deps.get_storage_service, None)
