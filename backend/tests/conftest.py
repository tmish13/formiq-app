import os
os.environ["ENVIRONMENT"] = "test"

import pytest
from typing import Dict, Generator
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient
from dotenv import load_dotenv
from pathlib import Path
from unittest.mock import MagicMock, patch
from app.core.config import settings
from app.core.database import Base, get_db
from app.core.security import create_access_token, get_password_hash
from app.core.constants import Roles
from app.models.user import User
from app.core.logging import logger
import logging
from app.main import app, create_application
from app.core.cache import cache_service
from app.models.workout import Workout, Exercise, WorkoutPlan
from datetime import datetime, timedelta

# Load test environment variables
test_env_path = Path(__file__).parent / ".env.test"
load_dotenv(test_env_path)

# Test database URL
TEST_DATABASE_URL = "sqlite:///./test.db"

# Create test database engine
engine = create_engine(TEST_DATABASE_URL)

# Create test session factory
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Mock Redis client
class MockRedis:
    def __init__(self):
        self.data = {}
        
    def ping(self):
        return True
        
    def get(self, key):
        return self.data.get(key)
        
    def setex(self, key, expire, value):
        self.data[key] = value
        return True
        
    def delete(self, key):
        if key in self.data:
            del self.data[key]
            return 1
        return 0
        
    def keys(self, pattern):
        return [k for k in self.data.keys() if k.startswith(pattern)]
        
    def exists(self, key):
        return key in self.data
        
    def incr(self, key, amount=1):
        if key not in self.data:
            self.data[key] = "0"
        self.data[key] = str(int(self.data[key]) + amount)
        return int(self.data[key])
        
    def mget(self, keys):
        return [self.data.get(k) for k in keys]
        
    def pipeline(self):
        return self

    def setex(self, key, expire, value):
        self.data[key] = value
        return self

    def execute(self):
        return True

@pytest.fixture(scope="session")
def test_db_engine():
    """Create a test database engine."""
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def test_db(test_db_engine):
    """Create a fresh database session for each test."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()

@pytest.fixture(scope="function")
def client(test_db):
    """Create a test client with a test database session."""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    app = create_application()
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)

@pytest.fixture(scope="session")
def redis_client():
    """Create a test Redis client."""
    return cache_service.redis_client

@pytest.fixture(scope="function")
def mock_redis(redis_client):
    """Mock Redis for testing."""
    # Clear Redis before each test
    redis_client.flushall()
    yield redis_client
    # Clear Redis after each test
    redis_client.flushall()

@pytest.fixture(scope="function")
def test_user():
    """Create a test user."""
    return {
        "email": "test@example.com",
        "password": "testpassword123",
        "full_name": "Test User",
        "is_active": True,
        "is_superuser": False
    }

@pytest.fixture(scope="function")
def test_superuser():
    """Create a test superuser."""
    return {
        "email": "admin@example.com",
        "password": "adminpassword123",
        "full_name": "Admin User",
        "is_active": True,
        "is_superuser": True
    }

@pytest.fixture(scope="function")
def test_token(test_user):
    """Create a test JWT token."""
    return create_access_token(data={"sub": test_user["email"]})

@pytest.fixture(scope="function")
def authorized_client(client, test_token):
    """Create an authorized test client."""
    client.headers = {
        **client.headers,
        "Authorization": f"Bearer {test_token}"
    }
    return client

@pytest.fixture(scope="function")
def test_user(test_db) -> User:
    """Create a test user"""
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
    test_db.commit()
    test_db.refresh(user)
    return user

@pytest.fixture(scope="function")
def test_admin(test_db) -> User:
    """Create a test admin user"""
    admin = User(
        email="admin@example.com",
        username="admin",
        hashed_password=get_password_hash("adminpassword"),
        is_active=True,
        is_verified=True,
        subscription_tier="PRO",
        is_admin=True,
        created_at=datetime.now()
    )
    test_db.add(admin)
    test_db.commit()
    test_db.refresh(admin)
    return admin

@pytest.fixture(scope="function")
def test_workout(test_db, test_user) -> Workout:
    """Create a test workout"""
    workout = Workout(
        user_id=test_user.id,
        name="Test Workout",
        description="Test workout description",
        duration=timedelta(minutes=60),
        difficulty="intermediate",
        created_at=datetime.now()
    )
    test_db.add(workout)
    test_db.commit()
    test_db.refresh(workout)
    return workout

@pytest.fixture(scope="function")
def test_exercise(test_db, test_workout) -> Exercise:
    """Create a test exercise"""
    exercise = Exercise(
        workout_id=test_workout.id,
        name="Squat",
        description="Basic squat exercise",
        sets=3,
        reps=12,
        weight=100,
        muscle_groups=["legs", "core"],
        equipment_needed=["barbell", "squat rack"],
        difficulty="intermediate"
    )
    test_db.add(exercise)
    test_db.commit()
    test_db.refresh(exercise)
    return exercise

@pytest.fixture(scope="function")
def test_workout_plan(test_db, test_user) -> WorkoutPlan:
    """Create a test workout plan"""
    plan = WorkoutPlan(
        user_id=test_user.id,
        name="Test Plan",
        description="Test plan description",
        duration_weeks=4,
        created_at=datetime.now()
    )
    test_db.add(plan)
    test_db.commit()
    test_db.refresh(plan)
    return plan

@pytest.fixture(scope="function")
def test_admin_token(test_admin) -> str:
    """Create a test admin access token"""
    return create_access_token(data={"sub": test_admin.email})

@pytest.fixture(scope="function")
def auth_headers(test_token) -> dict:
    """Create authentication headers"""
    return {"Authorization": f"Bearer {test_token}"}

@pytest.fixture(scope="function")
def admin_auth_headers(test_admin_token) -> dict:
    """Create admin authentication headers"""
    return {"Authorization": f"Bearer {test_admin_token}"}

@pytest.fixture(scope="session", autouse=True)
def setup_test_logging():
    """Configure logging for tests."""
    logging.basicConfig(level=logging.DEBUG)
    yield
    logging.basicConfig(level=logging.INFO)

@pytest.fixture(scope="function")
def superuser_token_headers(client: TestClient) -> Dict[str, str]:
    """Fixture for creating a superuser token."""
    access_token = create_access_token(subject=1)
    return {"Authorization": f"Bearer {access_token}"}

@pytest.fixture(scope="function")
def normal_user_token_headers(client: TestClient, db: Session) -> Dict[str, str]:
    """Fixture for creating a normal user token."""
    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("password"),
        full_name="Test User",
        is_active=True,
        role=Roles.USER
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    access_token = create_access_token(subject=user.id)
    return {"Authorization": f"Bearer {access_token}"}

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "e2e: mark test as end-to-end test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "security: mark test as security test")
    config.addinivalue_line("markers", "performance: mark test as performance test") 