import os
# Ensure ENVIRONMENT is set to 'test' BEFORE any application code (especially config) is imported.
# This is crucial for get_settings() to load the correct .env file or test defaults.
# if os.getenv("PYTEST_CURRENT_TEST"):
#     os.environ["ENVIRONMENT"] = "test"

import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from unittest.mock import patch
from contextlib import asynccontextmanager
import logging
from typing import AsyncGenerator, Generator
from unittest.mock import MagicMock, AsyncMock

# Now import application code
from app.core.database import Base  # BaseModel for metadata
from app.core.config import Settings, get_settings # To potentially get test DB URL or settings

# Import all models so they are registered with Base.metadata before create_all
import app.db.base # This should import all model modules that define tables

logger = logging.getLogger(__name__)

# This settings instance should now correctly reflect the test environment
settings: Settings = get_settings()

# The following explicit URL manipulation is removed as settings object 
# should already provide the correct test DB URL when ENVIRONMENT=test.
# if settings.ASYNC_DATABASE_URL is None:
#     logger.warning("ASYNC_DATABASE_URL was None in settings, falling back to default for test URL construction.")
#     pass 
# test_integration_db_url = settings.ASYNC_DATABASE_URL.replace(
#     "formiq_db", "formiq_test_integration_db"
# ) if settings.ASYNC_DATABASE_URL else f"sqlite+aiosqlite:///./formiq_test_integration.db"
# settings.ASYNC_DATABASE_URL = test_integration_db_url
# if settings.SQLALCHEMY_DATABASE_URI:
#     settings.SQLALCHEMY_DATABASE_URI = settings.SQLALCHEMY_DATABASE_URI.replace(
#         "formiq_db", "formiq_test_integration_db"
#     )
# else:
#     logger.warning("SQLALCHEMY_DATABASE_URI was None, setting default for test session.")
#     settings.SQLALCHEMY_DATABASE_URI = f"sqlite:///./formiq_test_integration.db"

@pytest.fixture(scope="session")
def event_loop():
    """Force a session-scoped event loop."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def db_engine(
    event_loop  # Ensure event_loop is created before engine
):
    logger.info(f"db_engine: Using ASYNC_DATABASE_URL from settings: {settings.ASYNC_DATABASE_URL}")
    if not settings.ASYNC_DATABASE_URL or not settings.ASYNC_DATABASE_URL.startswith("sqlite"):
        logger.error(
            f"CRITICAL: Test environment is not using a SQLite database. "
            f"ASYNC_DATABASE_URL: {settings.ASYNC_DATABASE_URL}. "
            f"Ensure ENVIRONMENT=test is set (e.g., via shell or .env file before config loads) AND "
            f".env.test (if used) provides a SQLite URL for TEST_DATABASE_URL, or config.py defaults to SQLite for test env."
        )
        # Forcing a default test DB URL here if still not SQLite, as a last resort safeguard
        # This indicates a misconfiguration in how ENVIRONMENT or .env files are handled.
        effective_db_url = "sqlite+aiosqlite:///./fallback_conftest_test_db.db"
        logger.warning(f"Overriding DB URL to: {effective_db_url} as a safeguard.")
    else:
        effective_db_url = settings.ASYNC_DATABASE_URL

    engine = create_async_engine(effective_db_url, echo=settings.DB_ECHO)
    TestAsyncSessionFactory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    # This is the new mock context manager for ai_tasks
    @asynccontextmanager
    async def mock_get_db_session_for_ai_tasks():
        async with TestAsyncSessionFactory() as session:
            yield session

    # Patch ONLY the AI tasks session context for now to simplify
    with patch("app.tasks.ai_tasks.get_celery_db_session_context", mock_get_db_session_for_ai_tasks):
        # The video_tasks patch is temporarily removed:
        # patch("app.tasks.video_tasks.async_session_factory", TestAsyncSessionFactory):
        async with engine.begin() as conn:
            logger.info("Dropping all tables in test integration database.")
            await conn.run_sync(Base.metadata.drop_all)
            logger.info("Creating all tables in test integration database.")
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Yielding test integration database engine and session factory.")
        yield engine, TestAsyncSessionFactory # Yield for test_async_session_factory and db_session

        logger.info("Disposing test integration database engine.")
        await engine.dispose()

    # If you need to remove the SQLite file after tests (optional)
    # db_path = test_integration_db_url.split("sqlite+aiosqlite:///")[-1]
    # if os.path.exists(db_path):
    #     logger.info(f"Removing test integration database file: {db_path}")
    #     os.remove(db_path)

@pytest.fixture(scope="session") # Changed to session scope to match db_engine
async def test_async_session_factory(db_engine):
    """Provides the test-specific async_sessionmaker, already bound to the test engine."""
    _, factory = db_engine # Unpack the tuple yielded by db_engine
    return factory


@pytest.fixture(scope="function")
async def db_session(db_engine) -> AsyncSession: # Removed type hint for AsyncGenerator
    logger.debug("Creating new DB session for test function (from db_engine).")
    _, TestSessionFactoryFromEngine = db_engine # Correctly unpack factory

    # The db_engine fixture already creates and drops tables once per session.
    # For function-scoped sessions, we just need a new session.
    # We don't need to clear individual tables here as each test function gets a clean start
    # if the task commits are properly managed or rolled back by the test setup.

    # Use the session factory yielded by db_engine
    async with TestSessionFactoryFromEngine() as session:
        logger.debug(f"DB Session {session} created for test function.")
        try:
            yield session
            # Attempt to commit if the session is still active and not rolled back by the test.
            # This is to ensure data from direct db_session usage in tests is saved if no error occurred.
            if session.is_active:
                await session.commit()
                logger.debug(f"DB Session {session} committed after test function.")
        except Exception:
            logger.error(f"Exception in test, rolling back DB session {session}.", exc_info=True)
            await session.rollback()
            raise
        finally:
            # The session is automatically closed by the async with TestSessionFactoryFromEngine() block.
            logger.debug(f"DB Session {session} closed after test function.")

# Mock for get_settings_override used in tasks
@pytest.fixture(scope='function')
def mock_get_settings_override_for_tasks(monkeypatch):
    mock_settings = get_settings() # Get a real settings object
    # Modify any specific settings for tasks if needed, e.g., for retry logic
    mock_settings.CELERY_TASK_ALWAYS_EAGER = True # Example, may already be default
    mock_settings.AI_MIN_DETECTION_CONFIDENCE = 0.5 # Example default
    # monkeypatch.setattr("app.tasks.ai_tasks.get_settings_override", lambda: mock_settings)
    # monkeypatch.setattr("app.tasks.video_tasks.get_settings_override", lambda: mock_settings)
    # Let individual tests patch get_settings_override if they need specific values beyond these defaults
    return mock_settings


# If your tasks get settings via a direct import like `from app.core.config import get_settings`
# then you'd patch `app.tasks.ai_tasks.get_settings` directly.
# However, ai_tasks.py uses `from app.db.session import get_settings_override`
# and `from app.core.config import Settings` with `Settings()` or `get_app_settings` (which calls Settings())
# `get_settings_override` is ALREADY patched by the main conftest.py (application level)
# The tests themselves often patch `app.tasks.ai_tasks.get_settings_override` for fine-grained control.


# Example of a fixture to mock settings specifically for AI tasks if needed
@pytest.fixture
def mock_ai_task_settings():
    original_settings = get_settings()
    test_settings = original_settings.copy(deep=True)
    test_settings.AI_MIN_DETECTION_CONFIDENCE = 0.5 # Default for tests
    # Add other specific AI task settings overrides here
    with patch('app.tasks.ai_tasks.get_settings_override', return_value=test_settings):
        # Ensure ai_tasks.get_settings_override is what's actually used by the task for settings.
        # ai_tasks.py shows: `settings_instance = get_settings_override()` at task level
        # And some `get_app_settings()` which calls `Settings()`
        # So patching `get_settings_override` at the task module level is key if tasks use that.
        # If tasks construct `Settings()` directly, that's harder to patch per-test without
        # also patching the Settings class or its `__init__`.
        # The current mock patches get_settings_override which is used in the tasks.
        yield test_settings 