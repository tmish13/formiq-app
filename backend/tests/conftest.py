"""Test configuration module."""
import os
from pathlib import Path
from dotenv import load_dotenv
import pytest
import asyncio
from typing import AsyncGenerator, Generator, Dict
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from fastapi.testclient import TestClient

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
from app.models.video import Video

# Load test environment variables before importing other modules
test_env_path = Path(__file__).parent / ".env.test"
load_dotenv(test_env_path)

# Set test environment
os.environ["ENVIRONMENT"] = "test"

# Clear settings cache to reload with test environment
get_settings.cache_clear()

# Create test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# Create async engine for tests
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    poolclass=None
)

# Create async session factory for tests
TestingSessionLocal = sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_app() -> FastAPI:
    """Create a test instance of the application."""
    app = create_application()
    return app

@pytest.fixture(autouse=True)
async def setup_database():
    """Set up the test database."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for a test."""
    async with TestingSessionLocal() as session:
        yield session

@pytest.fixture
async def client(db_session: AsyncSession) -> Generator:
    """Create a test client with a fresh database session."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_async_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
async def test_user(db_session: AsyncSession):
    """Create a test user."""
    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("testpassword"),
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user

@pytest.fixture
async def test_superuser(db_session: AsyncSession):
    """Create a test superuser."""
    user = User(
        email="admin@example.com",
        hashed_password=get_password_hash("adminpassword"),
        is_active=True,
        is_superuser=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user

@pytest.fixture
def test_user_token_headers(client: TestClient, test_user):
    """Create test user token headers."""
    access_token = create_access_token(
        data={"sub": test_user.email}
    )
    return {"Authorization": f"Bearer {access_token}"}

@pytest.fixture
def test_superuser_token_headers(client: TestClient, test_superuser):
    """Create test superuser token headers."""
    access_token = create_access_token(
        data={"sub": test_superuser.email}
    )
    return {"Authorization": f"Bearer {access_token}"}

@pytest.fixture
async def test_video(db_session: AsyncSession, test_user: User) -> Video:
    """Create a test video."""
    video = Video(
        user_id=test_user.id,
        filename="test_video.mp4",
        status="pending",
        url="https://example.com/test_video.mp4"
    )
    db_session.add(video)
    await db_session.commit()
    await db_session.refresh(video)
    return video

@pytest.fixture
async def test_form_check(db_session: AsyncSession, test_video: Video) -> FormCheck:
    """Create a test form check."""
    form_check = FormCheck(
        video_id=test_video.id,
        score=85,
        feedback="Good form",
        joint_angles={"hip": 90, "knee": 90},
        spine_alignment=0.95,
        symmetry_score=0.85
    )
    db_session.add(form_check)
    await db_session.commit()
    await db_session.refresh(form_check)
    return form_check

@pytest.fixture
def test_video_file(tmp_path) -> str:
    """Create a test video file."""
    video_path = tmp_path / "test_video.mp4"
    video_path.write_bytes(b"fake video data")
    return str(video_path)

@pytest.fixture
def mock_video_processor():
    """Create a mock video processor."""
    class MockVideoProcessor:
        async def process_video(self, video_path: str) -> dict:
            return {
                "status": "completed",
                "poses": [{"keypoints": [{"x": 100, "y": 100, "score": 0.9}]}]
            }

        async def extract_frames(self, video_path: str) -> list:
            return ["frame1", "frame2"]

        async def analyze_form(self, frames: list) -> dict:
            return {
                "score": 85,
                "feedback": "Good form",
                "joint_angles": {"hip": 90, "knee": 90},
                "spine_alignment": 0.95,
                "symmetry_score": 0.85
            }

    return MockVideoProcessor()

@pytest.fixture
def mock_storage_service():
    """Create a mock storage service."""
    class MockStorageService:
        async def upload_file(self, file_path: str, destination: str) -> str:
            return f"https://example.com/{destination}"

        async def download_file(self, file_path: str, destination: str) -> str:
            return destination

        async def delete_file(self, file_path: str) -> None:
            pass

    return MockStorageService()

@pytest.fixture
def mock_email_service():
    """Create a mock email service."""
    class MockEmailService:
        async def send_email(self, to_email: str, subject: str, body: str) -> None:
            pass

        async def send_verification_email(self, to_email: str, token: str) -> None:
            pass

        async def send_password_reset_email(self, to_email: str, token: str) -> None:
            pass

    return MockEmailService()

@pytest.fixture
def mock_cache_service():
    """Create a mock cache service."""
    class MockCacheService:
        _cache = {}

        async def get(self, key: str) -> str:
            return self._cache.get(key)

        async def set(self, key: str, value: str, expire: int = 0) -> None:
            self._cache[key] = value

        async def delete(self, key: str) -> None:
            self._cache.pop(key, None)

        async def clear(self) -> None:
            self._cache.clear()

    return MockCacheService()

@pytest.fixture
def mock_form_analyzer():
    """Create a mock form analyzer."""
    class MockFormAnalyzer:
        async def analyze_exercise(self, exercise_type: str, form_data: dict) -> dict:
            return {
                "score": 85,
                "feedback": "Good form",
                "joint_angles": {"hip": 90, "knee": 90},
                "spine_alignment": 0.95,
                "symmetry_score": 0.85,
                "confidence_score": 0.9
            }

        async def get_exercise_metrics(self, exercise_type: str) -> dict:
            return {
                "joint_angles": {"hip": 90, "knee": 90},
                "spine_alignment": 0.95,
                "symmetry_score": 0.85
            }

    return MockFormAnalyzer()

@pytest.fixture(scope="session")
def mock_redis():
    """Create a mock Redis instance."""
    return MockRedis()

@pytest.fixture(scope="function")
async def test_admin(db_session: AsyncSession) -> User:
    """Create a test admin user."""
    admin = User(
        email="admin@example.com",
        hashed_password=get_password_hash("adminpassword"),
        is_active=True,
        is_superuser=True
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin

@pytest.fixture(scope="function")
async def test_admin_token(test_admin: User) -> str:
    """Create a token for the test admin user."""
    return create_access_token(data={"sub": test_admin.email})

@pytest.fixture(scope="function")
async def test_admin_headers(test_admin_token: str) -> Dict[str, str]:
    """Create authentication headers for the test admin user."""
    return {"Authorization": f"Bearer {test_admin_token}"}

@pytest.fixture(scope="function")
async def test_workout(db_session: AsyncSession, test_user: User) -> Workout:
    """Create a test workout."""
    workout = Workout(
        user_id=test_user.id,
        name="Test Workout",
        description="A test workout",
        duration_minutes=30
    )
    db_session.add(workout)
    await db_session.commit()
    await db_session.refresh(workout)
    return workout

@pytest.fixture(scope="function")
async def test_exercise(db_session: AsyncSession, test_workout: Workout) -> Exercise:
    """Create a test exercise."""
    exercise = Exercise(
        workout_id=test_workout.id,
        name="Test Exercise",
        description="A test exercise",
        sets=3,
        reps=10,
        weight_kg=20
    )
    db_session.add(exercise)
    await db_session.commit()
    await db_session.refresh(exercise)
    return exercise

@pytest.fixture(scope="function")
async def test_workout_plan(db_session: AsyncSession, test_user: User) -> WorkoutPlan:
    """Create a test workout plan."""
    workout_plan = WorkoutPlan(
        user_id=test_user.id,
        name="Test Plan",
        description="A test workout plan",
        duration_weeks=4
    )
    db_session.add(workout_plan)
    await db_session.commit()
    await db_session.refresh(workout_plan)
    return workout_plan

@pytest.fixture(scope="function")
async def setup_test_db():
    """Set up the test database."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture(scope="function")
async def async_session() -> AsyncGenerator[AsyncSession, None]:
    """Create an async session for testing."""
    async with TestingSessionLocal() as session:
        yield session

@pytest.fixture(scope="function")
async def async_client(setup_test_db, async_session) -> AsyncGenerator[AsyncClient, None]:
    """Create an async client for testing."""
    async def override_get_db():
        yield async_session

    app.dependency_overrides[get_async_db] = override_get_db
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
def db_session(test_engine) -> Generator[Session, None, None]:
    """Create a database session for testing."""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")
def client(db_session) -> Generator:
    """Create a test client."""
    def override_get_db():
        try:
            yield db_session
        finally:
            db_session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "e2e: mark test as end-to-end test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "security: mark test as security test")
    config.addinivalue_line("markers", "performance: mark test as performance test")

@pytest.fixture(scope="session")
def engine():
    """Create a test database engine."""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    os.remove("./test.db")

@pytest.fixture(scope="function")
def db_session(engine):
    """Create a new database session for a test."""
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.rollback()
        session.close()

@pytest.fixture(scope="function")
def client(db_session) -> Generator:
    """Create a test client with a clean database session."""
    app.dependency_overrides = {}

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture
def test_user(db_session) -> User:
    """Create a test user."""
    user = User(
        email="test@example.com",
        hashed_password="hashed_password",
        is_active=True,
        full_name="Test User"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def test_superuser(db_session) -> User:
    """Create a test superuser."""
    user = User(
        email="admin@example.com",
        hashed_password="hashed_password",
        is_active=True,
        full_name="Admin User",
        is_superuser=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def token_headers(test_user: User) -> Dict[str, str]:
    """Create authentication headers for the test user."""
    token = create_access_token(data={"sub": test_user.email})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def superuser_token_headers(test_superuser: User) -> Dict[str, str]:
    """Create authentication headers for the test superuser."""
    token = create_access_token(data={"sub": test_superuser.email})
    return {"Authorization": f"Bearer {token}"}

# New directory structure
# backend/tests/
# ├── unit/
# │   ├── services/
# │   ├── models/
# │   └── utils/
# ├── integration/
# │   ├── api/
# │   └── database/
# ├── e2e/
# └── performance/ 