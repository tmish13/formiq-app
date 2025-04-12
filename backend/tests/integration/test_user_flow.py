import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.services.user_service import UserService
from app.services.auth_service import AuthService
from app.services.video_service import VideoService
from app.schemas.user import UserCreate
from app.schemas.video import VideoCreate

@pytest.fixture
def test_client():
    return TestClient(app)

@pytest.fixture
async def test_user(db_session):
    """Create a test user for integration tests."""
    user_service = UserService(db_session)
    user_data = UserCreate(
        email="integration@example.com",
        password="TestPass123!",
        full_name="Integration Test User"
    )
    return await user_service.create_user(user_data)

@pytest.mark.asyncio
async def test_complete_user_flow(test_client, db_session, test_user):
    """Test complete user flow from registration to form analysis."""
    
    # 1. User Registration
    register_response = test_client.post(
        "/api/auth/register",
        json={
            "email": "flow@example.com",
            "password": "FlowTest123!",
            "full_name": "Flow Test User"
        }
    )
    assert register_response.status_code == 201
    user_data = register_response.json()
    assert "id" in user_data
    
    # 2. User Login
    login_response = test_client.post(
        "/api/auth/login",
        data={
            "username": "flow@example.com",
            "password": "FlowTest123!"
        }
    )
    assert login_response.status_code == 200
    tokens = login_response.json()
    assert "access_token" in tokens
    
    # Set up authenticated client
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    
    # 3. Upload Video
    with open("tests/fixtures/test_video.mp4", "rb") as video_file:
        files = {"file": ("test_video.mp4", video_file, "video/mp4")}
        data = {
            "exercise_type": "squat",
            "user_id": user_data["id"]
        }
        upload_response = test_client.post(
            "/api/videos/upload",
            headers=headers,
            files=files,
            data=data
        )
    assert upload_response.status_code == 200
    video_data = upload_response.json()
    assert "id" in video_data
    
    # 4. Get Video Analysis
    analysis_response = test_client.get(
        f"/api/videos/{video_data['id']}/analysis",
        headers=headers
    )
    assert analysis_response.status_code == 200
    analysis = analysis_response.json()
    assert "feedback" in analysis
    assert "score" in analysis
    
    # 5. Get User History
    history_response = test_client.get(
        "/api/users/me/history",
        headers=headers
    )
    assert history_response.status_code == 200
    history = history_response.json()
    assert len(history) > 0
    assert history[0]["exercise_type"] == "squat"

@pytest.mark.asyncio
async def test_error_scenarios(test_client, db_session):
    """Test various error scenarios in the user flow."""
    
    # 1. Registration with existing email
    register_response = test_client.post(
        "/api/auth/register",
        json={
            "email": "error@example.com",
            "password": "ErrorTest123!",
            "full_name": "Error Test User"
        }
    )
    assert register_response.status_code == 201
    
    # Try registering again with same email
    duplicate_response = test_client.post(
        "/api/auth/register",
        json={
            "email": "error@example.com",
            "password": "ErrorTest123!",
            "full_name": "Error Test User"
        }
    )
    assert duplicate_response.status_code == 400
    
    # 2. Login with wrong password
    wrong_login_response = test_client.post(
        "/api/auth/login",
        data={
            "username": "error@example.com",
            "password": "WrongPass123!"
        }
    )
    assert wrong_login_response.status_code == 401
    
    # 3. Access protected route without token
    no_auth_response = test_client.get("/api/users/me")
    assert no_auth_response.status_code == 401
    
    # 4. Access with invalid token
    invalid_headers = {"Authorization": "Bearer invalid_token"}
    invalid_auth_response = test_client.get(
        "/api/users/me",
        headers=invalid_headers
    )
    assert invalid_auth_response.status_code == 401

@pytest.mark.asyncio
async def test_video_processing_flow(test_client, db_session, test_user):
    """Test video processing and analysis flow."""
    
    # 1. Login
    login_response = test_client.post(
        "/api/auth/login",
        data={
            "username": "integration@example.com",
            "password": "TestPass123!"
        }
    )
    assert login_response.status_code == 200
    tokens = login_response.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    
    # 2. Upload multiple videos
    video_files = [
        ("squat_test.mp4", "squat"),
        ("deadlift_test.mp4", "deadlift"),
        ("bench_test.mp4", "bench_press")
    ]
    
    video_ids = []
    for filename, exercise_type in video_files:
        with open(f"tests/fixtures/{filename}", "rb") as video_file:
            files = {"file": (filename, video_file, "video/mp4")}
            data = {
                "exercise_type": exercise_type,
                "user_id": test_user.id
            }
            response = test_client.post(
                "/api/videos/upload",
                headers=headers,
                files=files,
                data=data
            )
            assert response.status_code == 200
            video_ids.append(response.json()["id"])
    
    # 3. Check processing status
    for video_id in video_ids:
        status_response = test_client.get(
            f"/api/videos/{video_id}/status",
            headers=headers
        )
        assert status_response.status_code == 200
        status = status_response.json()
        assert status["status"] in ["pending", "processing", "completed", "failed"]
    
    # 4. Get analysis results
    for video_id in video_ids:
        analysis_response = test_client.get(
            f"/api/videos/{video_id}/analysis",
            headers=headers
        )
        if analysis_response.status_code == 200:
            analysis = analysis_response.json()
            assert "feedback" in analysis
            assert "score" in analysis
            assert isinstance(analysis["score"], (int, float))
            assert 0 <= analysis["score"] <= 100

@pytest.mark.asyncio
async def test_user_settings_flow(test_client, db_session, test_user):
    """Test user settings and preferences flow."""
    
    # 1. Login
    login_response = test_client.post(
        "/api/auth/login",
        data={
            "username": "integration@example.com",
            "password": "TestPass123!"
        }
    )
    assert login_response.status_code == 200
    tokens = login_response.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    
    # 2. Update user settings
    settings_response = test_client.put(
        "/api/users/me/settings",
        headers=headers,
        json={
            "notification_preferences": {
                "email": True,
                "push": False
            },
            "exercise_preferences": ["squat", "deadlift"],
            "difficulty_level": "intermediate"
        }
    )
    assert settings_response.status_code == 200
    updated_settings = settings_response.json()
    assert updated_settings["notification_preferences"]["email"] is True
    assert updated_settings["notification_preferences"]["push"] is False
    
    # 3. Get user settings
    get_settings_response = test_client.get(
        "/api/users/me/settings",
        headers=headers
    )
    assert get_settings_response.status_code == 200
    settings = get_settings_response.json()
    assert settings["exercise_preferences"] == ["squat", "deadlift"]
    
    # 4. Update user profile
    profile_response = test_client.put(
        "/api/users/me",
        headers=headers,
        json={
            "full_name": "Updated Test User",
            "bio": "Integration test user"
        }
    )
    assert profile_response.status_code == 200
    updated_profile = profile_response.json()
    assert updated_profile["full_name"] == "Updated Test User" 