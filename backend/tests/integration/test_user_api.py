"""Integration tests for user API endpoints."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.main import app
from app.models.user import User
from app.core.security import get_password_hash, create_access_token
from app.core.database import get_async_db

@pytest.fixture
async def client() -> AsyncClient:
    """Create test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
async def auth_headers(test_token: str) -> dict:
    """Create authorization headers."""
    token = await test_token
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
async def test_user(test_db: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        email="test@example.com",
        hashed_password="hashed_password",
        full_name="Test User",
        is_active=True,
        is_superuser=False,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user

@pytest.mark.asyncio
async def test_create_user(client: AsyncClient, test_headers: dict):
    """Test creating a new user."""
    response = await client.post(
        "/api/v1/users/",
        headers=test_headers,
        json={
            "email": "newuser@example.com",
            "password": "strongpassword123",
            "full_name": "New User",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["full_name"] == "New User"
    assert "id" in data
    assert "hashed_password" not in data

@pytest.mark.asyncio
async def test_get_user(client: AsyncClient, test_user: User, test_headers: dict):
    """Test getting a user by ID."""
    response = await client.get(f"/api/v1/users/{test_user.id}", headers=test_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user.email
    assert data["full_name"] == test_user.full_name
    assert data["id"] == str(test_user.id)

@pytest.mark.asyncio
async def test_get_user_not_found(client: AsyncClient, test_headers: dict):
    """Test getting a non-existent user."""
    response = await client.get("/api/v1/users/999", headers=test_headers)
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_update_user(client: AsyncClient, test_user: User, test_headers: dict):
    """Test updating a user."""
    response = await client.put(
        f"/api/v1/users/{test_user.id}",
        headers=test_headers,
        json={"full_name": "Updated Name"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Updated Name"
    assert data["email"] == test_user.email

@pytest.mark.asyncio
async def test_delete_user(client: AsyncClient, test_user: User, test_headers: dict):
    """Test deleting a user."""
    response = await client.delete(f"/api/v1/users/{test_user.id}", headers=test_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "User deleted successfully"

@pytest.mark.asyncio
async def test_get_current_user(client: AsyncClient, test_headers: dict):
    """Test getting the current user."""
    response = await client.get("/api/v1/users/me", headers=test_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["full_name"] == "Test User"

@pytest.mark.asyncio
async def test_update_current_user(client: AsyncClient, test_headers: dict):
    """Test updating the current user."""
    response = await client.put(
        "/api/v1/users/me",
        headers=test_headers,
        json={"full_name": "Updated Current User"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Updated Current User"
    assert data["email"] == "test@example.com"

@pytest.mark.asyncio
async def test_create_user_duplicate_email(client: AsyncClient, test_user: User, test_headers: dict):
    """Test creating a user with a duplicate email."""
    response = await client.post(
        "/api/v1/users/",
        headers=test_headers,
        json={
            "email": test_user.email,
            "password": "strongpassword123",
            "full_name": "Duplicate User",
        },
    )
    assert response.status_code == 400
    data = response.json()
    assert "email already registered" in data["detail"]

@pytest.mark.asyncio
async def test_create_user_invalid_email(client: AsyncClient, test_headers: dict):
    """Test creating a user with an invalid email."""
    response = await client.post(
        "/api/v1/users/",
        headers=test_headers,
        json={
            "email": "invalid-email",
            "password": "strongpassword123",
            "full_name": "Invalid Email User",
        },
    )
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_create_user_weak_password(client: AsyncClient, test_headers: dict):
    """Test creating a user with a weak password."""
    response = await client.post(
        "/api/v1/users/",
        headers=test_headers,
        json={
            "email": "weakpass@example.com",
            "password": "weak",
            "full_name": "Weak Password User",
        },
    )
    assert response.status_code == 422 