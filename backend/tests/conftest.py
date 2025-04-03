"""Test configuration module."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load test environment variables before importing other modules
test_env_path = Path(__file__).parent / ".env.test"
load_dotenv(test_env_path)

# Set test environment
os.environ["ENVIRONMENT"] = "test"

from typing import Generator, Dict, AsyncGenerator, AsyncIterator
import contextlib

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool

from app.core.config import settings, get_settings
from app.db.base_class import Base
from app.main import app, create_application
from app.models.user import User
from app.models.workout import Workout, Exercise, WorkoutPlan
from app.core.security import create_access_token, get_password_hash
from app.core.cache import cache_service
from app.core.database import get_db, get_async_db
from tests.test_utils import MockRedis
from datetime import datetime, timedelta
from app.db.session import async_session
from app.core import security
from app.repositories.user_repository import UserRepository
from app.models.exercise import ExerciseTemplate
from app.models.form_check import FormCheck
from app.models.subscription import Subscription

# Clear settings cache to reload with test environment
get_settings.cache_clear()

# Set up test database
TEST_DATABASE_URL = "sqlite:///./test.db"

# Create sync engine
sync_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# Create async engine
async_engine = create_async_engine(
    "sqlite+aiosqlite:///./test.db",
    connect_args={"check_same_thread": False}
)

TestingSessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=sync_engine
)

AsyncTestingSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Create a test async engine
test_async_engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URI.replace("sqlite://", "sqlite+aiosqlite://"),
    poolclass=NullPool,
    echo=False,
    connect_args={"check_same_thread": False}
)

# Create test async session
test_async_session_factory = sessionmaker(
    test_async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

@pytest.fixture(scope="session", autouse=True)
def override_app_engine():
    """Override the application's database engine with the test engine."""
    original_engine = get_async_db
    app.state.engine = async_engine  # Set the test engine on the app state
    yield
    app.state.engine = original_engine  # Restore the original engine

@pytest.fixture(scope="session")
def setup_db():
    # Create tables in the test database
    Base.metadata.create_all(bind=sync_engine)
    yield
    # Drop tables after tests
    Base.metadata.drop_all(bind=sync_engine)

@pytest.fixture(scope="function")
def db(setup_db):
    connection = sync_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")
async def async_db(setup_db):
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncTestingSessionLocal() as session:
        yield session
    
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
def client(db):
    # Override the get_db dependency to use the test database
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
async def async_client(async_db):
    # Override the get_async_db dependency
    async def override_get_async_db():
        try:
            yield async_db
        finally:
            pass
    
    app.dependency_overrides[get_async_db] = override_get_async_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
async def test_user(db: Session) -> AsyncGenerator[User, None]:
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password=get_password_hash("testpassword"),
        is_active=True,
        is_verified=True,
        subscription_tier="PRO",
        created_at=datetime.now()
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    yield user
    db.delete(user)
    db.commit()

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
async def test_admin(db) -> User:
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
    db.add(admin)
    db.commit()
    db.refresh(admin)
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
async def test_workout(db, test_user) -> Workout:
    """Create a test workout."""
    user = await test_user
    workout = Workout(
        name="Test Workout",
        description="Test workout description",
        user_id=user.id,
        created_at=datetime.now()
    )
    db.add(workout)
    db.commit()
    db.refresh(workout)
    return workout

@pytest.fixture(scope="function")
async def test_exercise(db, test_workout) -> Exercise:
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
    db.add(exercise)
    db.commit()
    db.refresh(exercise)
    return exercise

@pytest.fixture(scope="function")
async def test_workout_plan(db, test_user) -> WorkoutPlan:
    """Create a test workout plan."""
    user = await test_user
    plan = WorkoutPlan(
        name="Test Plan",
        description="Test plan description",
        user_id=user.id,
        created_at=datetime.now()
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan

@pytest.fixture(scope="function")
async def setup_test_db():
    """Create all tables for testing."""
    # Create all tables
    async with test_async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    # Run the test
    yield
    
    # Drop all tables
    async with test_async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture(scope="function")
async def async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async session for tests."""
    async with test_async_session_factory() as session:
        yield session

@pytest.fixture(scope="function")
async def async_client(setup_test_db, async_session) -> Generator[TestClient, None, None]:
    """Get test client with overridden session."""
    # Override dependencies
    async def override_get_db():
        try:
            yield async_session
        finally:
            await async_session.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_async_db] = override_get_db
    
    # Set test engine as app state
    app.state.engine = test_async_engine
    
    # Return test client
    with TestClient(app) as client:
        yield client
    
    # Clear overrides
    app.dependency_overrides.clear()

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "e2e: mark test as end-to-end test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "security: mark test as security test")
    config.addinivalue_line("markers", "performance: mark test as performance test") 