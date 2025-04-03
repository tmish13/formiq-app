"""Integration tests for auth endpoints."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.main import app
from app.models.user import User


@pytest.fixture(scope="module")
def client():
    """Create test client for the app."""
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="function")
def db_session(request):
    """Create a fresh database session for each test."""
    # Use a clean database for tests
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    # Use in-memory SQLite for tests
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def override_get_db(db_session):
    """Override get_db dependency."""
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides = {}


class TestAuthEndpoints:
    """Tests for auth endpoints."""
    
    @pytest.mark.asyncio
    async def test_register_endpoint(self, async_client: TestClient, async_session: AsyncSession):
        """Test register endpoint."""
        # Test data
        user_data = {
            "email": "test@example.com",
            "password": "Password123!",
            "full_name": "Test User",
        }
        
        # Register user
        response = async_client.post(
            f"{settings.API_V1_STR}/auth/register",
            json=user_data,
        )
        
        # Check response
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["full_name"] == user_data["full_name"]
        assert "id" in data
        assert "password" not in data
        
        # Check user was saved to database
        result = await async_session.get(User, int(data["id"]))
        assert result is not None
        assert result.email == user_data["email"]
        
    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, async_client: TestClient, async_session: AsyncSession):
        """Test register with duplicate email."""
        # Create test user
        user_data = {
            "email": "test@example.com",
            "password": "Password123!",
            "full_name": "Test User",
        }
        
        # Register first user
        response = async_client.post(
            f"{settings.API_V1_STR}/auth/register",
            json=user_data,
        )
        assert response.status_code == 201
        
        # Try to register with same email
        response = async_client.post(
            f"{settings.API_V1_STR}/auth/register",
            json=user_data,
        )
        
        # Check response
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]
        
    @pytest.mark.asyncio
    async def test_login_endpoint(self, async_client: TestClient):
        """Test login endpoint."""
        # Create test user
        user_data = {
            "email": "test@example.com",
            "password": "Password123!",
            "full_name": "Test User",
        }
        
        # Register user
        async_client.post(
            f"{settings.API_V1_STR}/auth/register",
            json=user_data,
        )
        
        # Login with correct credentials
        response = async_client.post(
            f"{settings.API_V1_STR}/auth/login",
            data={"username": user_data["email"], "password": user_data["password"]},
        )
        
        # Check response
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        
    @pytest.mark.asyncio
    async def test_login_wrong_password(self, async_client: TestClient):
        """Test login with wrong password."""
        # Create test user
        user_data = {
            "email": "test@example.com",
            "password": "Password123!",
            "full_name": "Test User",
        }
        
        # Register user
        async_client.post(
            f"{settings.API_V1_STR}/auth/register",
            json=user_data,
        )
        
        # Login with wrong password
        response = async_client.post(
            f"{settings.API_V1_STR}/auth/login",
            data={"username": user_data["email"], "password": "WrongPassword123!"},
        )
        
        # Check response
        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]
        
    @pytest.mark.asyncio
    async def test_me_endpoint(self, async_client: TestClient):
        """Test me endpoint."""
        # Create test user
        user_data = {
            "email": "test@example.com",
            "password": "Password123!",
            "full_name": "Test User",
        }
        
        # Register user
        async_client.post(
            f"{settings.API_V1_STR}/auth/register",
            json=user_data,
        )
        
        # Login to get token
        login_response = async_client.post(
            f"{settings.API_V1_STR}/auth/login",
            data={"username": user_data["email"], "password": user_data["password"]},
        )
        token = login_response.json()["access_token"]
        
        # Access me endpoint with token
        response = async_client.get(
            f"{settings.API_V1_STR}/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        
        # Check response
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["full_name"] == user_data["full_name"] 