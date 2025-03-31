"""Test configuration module."""
import os
from typing import Generator, Dict, AsyncGenerator, AsyncIterator
from pathlib import Path
import contextlib

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.base import Base
from app.main import app, create_application
from app.models.user import User
from app.models.workout import Workout, Exercise, WorkoutPlan
from app.core.security import create_access_token, get_password_hash
from app.core.cache import cache_service
from app.core.database import get_async_db, async_engine as app_engine
from tests.test_utils import MockRedis
from datetime import datetime, timedelta
from dotenv import load_dotenv
from app.db.session import async_session
from app.core import security
from app.repositories.user_repository import UserRepository

# Load test environment variables
test_env_path = Path(__file__).parent / ".env.test"
load_dotenv(test_env_path)

# Set test environment
os.environ["ENVIRONMENT"] = "test"

# Use SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

test_engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

@pytest.fixture(scope="session", autouse=True)
def override_app_engine():
    """Override the application's database engine with the test engine."""
    original_engine = app_engine
    app.state.engine = test_engine  # Set the test engine on the app state
    yield
    app.state.engine = original_engine  # Restore the original engine

@pytest.fixture(scope="session")
async def test_db_engine():
    """Create a test database engine."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield test_engine
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture(scope="function")
async def test_db(test_db_engine) -> AsyncSession:
    """Create a fresh database session for each test."""
    async with TestingSessionLocal() as session:
        yield session

@pytest.fixture
async def client() -> AsyncClient:
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session

@pytest.fixture
async def test_user(test_db: AsyncSession) -> AsyncGenerator[User, None]:
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password=get_password_hash("testpassword"),
        is_active=True,
        is_verified=True,
        subscription_tier="PRO",
        created_at=datetime.now()
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    yield user
    await test_db.delete(user)
    await test_db.commit()

@pytest.fixture
async def test_token(test_user: User) -> str:
    return create_access_token(str(test_user.id))

@pytest.fixture
async def test_headers(test_token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {test_token}"}

@pytest.fixture(scope="session")
def test_app():
    """Create test application instance."""
    settings.ENVIRONMENT = "test"
    return create_application()

@pytest.fixture(scope="session")
def mock_redis():
    """Create mock Redis client."""
    return MockRedis()

@pytest.fixture(scope="function")
async def test_admin(test_db) -> User:
    """Create a test admin user"""
    admin = User(
        email="admin@example.com",
        username="admin",
        hashed_password=get_password_hash("adminpassword"),
        is_active=True,
        is_verified=True,
        is_superuser=True,
        subscription_tier="PRO",
        created_at=datetime.now()
    )
    test_db.add(admin)
    await test_db.commit()
    await test_db.refresh(admin)
    return admin

@pytest.fixture(scope="function")
async def test_admin_token(test_admin) -> str:
    """Create a test admin JWT token."""
    admin = await test_admin
    return create_access_token(str(admin.id))

@pytest.fixture(scope="function")
async def test_admin_headers(test_admin_token) -> Dict[str, str]:
    """Create test headers with admin JWT token."""
    token = await test_admin_token
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(scope="function")
async def test_workout(test_db, test_user) -> Workout:
    """Create a test workout."""
    user = await test_user
    workout = Workout(
        name="Test Workout",
        description="Test workout description",
        user_id=user.id,
        created_at=datetime.now()
    )
    test_db.add(workout)
    await test_db.commit()
    await test_db.refresh(workout)
    return workout

@pytest.fixture(scope="function")
async def test_exercise(test_db, test_workout) -> Exercise:
    """Create a test exercise."""
    workout = await test_workout
    exercise = Exercise(
        name="Test Exercise",
        description="Test exercise description",
        sets=3,
        reps=10,
        workout_id=workout.id,
        created_at=datetime.now()
    )
    test_db.add(exercise)
    await test_db.commit()
    await test_db.refresh(exercise)
    return exercise

@pytest.fixture(scope="function")
async def test_workout_plan(test_db, test_user) -> WorkoutPlan:
    """Create a test workout plan."""
    user = await test_user
    plan = WorkoutPlan(
        name="Test Plan",
        description="Test plan description",
        user_id=user.id,
        created_at=datetime.now()
    )
    test_db.add(plan)
    await test_db.commit()
    await test_db.refresh(plan)
    return plan

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "e2e: mark test as end-to-end test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "security: mark test as security test")
    config.addinivalue_line("markers", "performance: mark test as performance test") 