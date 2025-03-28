import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
import jwt
from ..main import app
from ..config import settings
from ..models import User, FormCheck

client = TestClient(app)

@pytest.fixture
def test_user():
    return {
        "id": 1,
        "email": "test@example.com",
        "username": "testuser",
        "password": "testpassword",
        "subscription_tier": "basic",
        "subscription_end_date": (datetime.now() + timedelta(days=30)).isoformat(),
        "is_email_verified": True
    }

@pytest.fixture
def auth_token(test_user):
    return jwt.encode(
        {
            "sub": str(test_user["id"]),
            "email": test_user["email"],
            "exp": datetime.now() + timedelta(days=1)
        },
        settings.jwt_secret,
        algorithm="HS256"
    )

@pytest.fixture
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_register_user():
    user_data = {
        "email": "newuser@example.com",
        "username": "newuser",
        "password": "newpassword"
    }
    response = client.post("/api/auth/register", json=user_data)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == user_data["email"]
    assert data["username"] == user_data["username"]
    assert "password" not in data

def test_login_user(test_user):
    response = client.post("/api/auth/login", json={
        "email": test_user["email"],
        "password": test_user["password"]
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == test_user["email"]

def test_get_current_user(auth_headers):
    response = client.get("/api/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"

def test_unauthorized_access():
    response = client.get("/api/auth/me")
    assert response.status_code == 401

def test_create_form_check(auth_headers):
    form_check_data = {
        "exercise_type": "squat",
        "video_url": "https://example.com/video.mp4"
    }
    response = client.post("/api/form-checks", json=form_check_data, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["exercise_type"] == form_check_data["exercise_type"]
    assert data["video_url"] == form_check_data["video_url"]
    assert "score" in data
    assert "overall_feedback" in data
    assert "issues" in data

def test_get_form_checks(auth_headers):
    response = client.get("/api/form-checks", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert "exercise_type" in data[0]
        assert "video_url" in data[0]
        assert "score" in data[0]

def test_get_form_check_by_id(auth_headers):
    # First create a form check
    form_check_data = {
        "exercise_type": "squat",
        "video_url": "https://example.com/video.mp4"
    }
    create_response = client.post("/api/form-checks", json=form_check_data, headers=auth_headers)
    form_check_id = create_response.json()["id"]

    # Then retrieve it
    response = client.get(f"/api/form-checks/{form_check_id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == form_check_id
    assert data["exercise_type"] == form_check_data["exercise_type"]

def test_get_nonexistent_form_check(auth_headers):
    response = client.get("/api/form-checks/999999", headers=auth_headers)
    assert response.status_code == 404

def test_upload_video(auth_headers):
    with open("tests/test_video.mp4", "rb") as f:
        response = client.post(
            "/api/upload",
            files={"file": ("test_video.mp4", f, "video/mp4")},
            headers=auth_headers
        )
    assert response.status_code == 200
    data = response.json()
    assert "url" in data
    assert data["url"].endswith(".mp4")

def test_upload_invalid_file_type(auth_headers):
    with open("tests/test_file.txt", "rb") as f:
        response = client.post(
            "/api/upload",
            files={"file": ("test_file.txt", f, "text/plain")},
            headers=auth_headers
        )
    assert response.status_code == 400
    assert "Invalid file type" in response.json()["detail"]

def test_subscription_required():
    # Create a user with expired subscription
    user_data = {
        "email": "expired@example.com",
        "username": "expired",
        "password": "password",
        "subscription_tier": "free",
        "subscription_end_date": (datetime.now() - timedelta(days=1)).isoformat()
    }
    
    # Generate token for expired user
    token = jwt.encode(
        {
            "sub": "2",
            "email": user_data["email"],
            "exp": datetime.now() + timedelta(days=1)
        },
        settings.jwt_secret,
        algorithm="HS256"
    )
    headers = {"Authorization": f"Bearer {token}"}

    # Try to create a form check
    form_check_data = {
        "exercise_type": "squat",
        "video_url": "https://example.com/video.mp4"
    }
    response = client.post("/api/form-checks", json=form_check_data, headers=headers)
    assert response.status_code == 403
    assert "subscription required" in response.json()["detail"].lower()

def test_rate_limiting():
    # Make multiple requests in quick succession
    responses = []
    for _ in range(70):  # More than the rate limit
        response = client.get("/api/health")
        responses.append(response.status_code)

    # At least one request should be rate limited
    assert 429 in responses

def test_error_handling():
    # Test invalid JSON
    response = client.post("/api/auth/register", data="invalid json")
    assert response.status_code == 422

    # Test validation error
    response = client.post("/api/auth/register", json={})
    assert response.status_code == 422

    # Test database error (try to register same user twice)
    user_data = {
        "email": "duplicate@example.com",
        "username": "duplicate",
        "password": "password"
    }
    client.post("/api/auth/register", json=user_data)
    response = client.post("/api/auth/register", json=user_data)
    assert response.status_code == 400 