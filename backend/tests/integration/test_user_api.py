import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.core.database import get_db
from app.models.user import User
from app.core.security import get_password_hash

@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)

@pytest.fixture
def db_session():
    """Create a test database session."""
    from app.core.database import SessionLocal
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture
def test_user(db_session: Session):
    """Create a test user."""
    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("testpassword123"),
        full_name="Test User",
        is_active=True,
        is_verified=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

def test_create_user(client: TestClient):
    """Test user creation endpoint."""
    response = client.post(
        "/api/v1/users/",
        json={
            "email": "newuser@example.com",
            "password": "newpassword123",
            "full_name": "New User"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["full_name"] == "New User"
    assert "id" in data
    assert "hashed_password" not in data

def test_get_user(client: TestClient, test_user: User):
    """Test user retrieval endpoint."""
    response = client.get(f"/api/v1/users/{test_user.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user.email
    assert data["full_name"] == test_user.full_name

def test_get_user_not_found(client: TestClient):
    """Test user retrieval when user doesn't exist."""
    response = client.get("/api/v1/users/999")
    assert response.status_code == 404

def test_update_user(client: TestClient, test_user: User):
    """Test user update endpoint."""
    response = client.put(
        f"/api/v1/users/{test_user.id}",
        json={"full_name": "Updated Name"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Updated Name"

def test_delete_user(client: TestClient, test_user: User):
    """Test user deletion endpoint."""
    response = client.delete(f"/api/v1/users/{test_user.id}")
    assert response.status_code == 204
    
    # Verify user is deleted
    response = client.get(f"/api/v1/users/{test_user.id}")
    assert response.status_code == 404 