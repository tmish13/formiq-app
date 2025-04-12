import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.services.workout import WorkoutService
from app.services.user import UserService
from app.services.ai import AIService
from app.models.user import User
from app.models.workout import Workout, Exercise, WorkoutPlan
from app.models.subscription import Subscription
from sqlalchemy.orm import Session
from app.core.exceptions import NotFoundError, ValidationError, AuthenticationError
from app.core.security import get_password_hash, verify_password, create_access_token

@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)

@pytest.fixture
def mock_db_session():
    """Create a mock database session"""
    session = Mock(spec=Session)
    session.query.return_value.filter.return_value.first.return_value = None
    session.add = Mock()
    session.commit = Mock()
    session.refresh = Mock()
    return session

@pytest.fixture
def test_user():
    """Create a test user"""
    return User(
        id=1,
        email="test@example.com",
        username="testuser",
        hashed_password=get_password_hash("testpassword"),
        is_active=True,
        is_superuser=False,
        subscription_tier="PRO",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

@pytest.fixture
def test_token(test_user):
    """Create a test access token"""
    return create_access_token(data={"sub": test_user.email})

def test_user_registration_flow(client, mock_db_session):
    """Test the complete user registration flow"""
    # Register new user
    user_data = {
        "email": "new@example.com",
        "username": "newuser",
        "password": "newpassword123"
    }
    
    response = client.post("/api/v1/users/register", json=user_data)
    assert response.status_code == 201
    assert response.json()["email"] == user_data["email"]
    
    # Try to register with same email
    response = client.post("/api/v1/users/register", json=user_data)
    assert response.status_code == 400

def test_user_login_flow(client, test_user, test_token, mock_db_session):
    """Test the complete user login flow"""
    # Mock user service response
    mock_db_session.query.return_value.filter.return_value.first.return_value = test_user
    
    # Login with correct credentials
    login_data = {
        "username": "test@example.com",
        "password": "testpassword"
    }
    
    response = client.post("/api/v1/users/login", data=login_data)
    assert response.status_code == 200
    assert "access_token" in response.json()
    
    # Try to login with wrong password
    login_data["password"] = "wrongpassword"
    response = client.post("/api/v1/users/login", data=login_data)
    assert response.status_code == 401

def test_workout_creation_flow(client, test_user, test_token, mock_db_session):
    """Test the complete workout creation flow"""
    # Create new workout
    workout_data = {
        "name": "New Workout",
        "description": "New workout description",
        "duration": 45,
        "difficulty": "beginner"
    }
    
    response = client.post(
        "/api/v1/workouts",
        json=workout_data,
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert response.status_code == 201
    workout_id = response.json()["id"]
    
    # Add exercise to workout
    exercise_data = {
        "exercise_id": 1,
        "sets": 3,
        "reps": 12,
        "weight": 100
    }
    
    response = client.post(
        f"/api/v1/workouts/{workout_id}/exercises",
        json=exercise_data,
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert response.status_code == 200
    
    # Get workout details
    response = client.get(
        f"/api/v1/workouts/{workout_id}",
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert response.status_code == 200
    assert response.json()["name"] == workout_data["name"]

def test_workout_plan_flow(client, test_user, test_token, mock_db_session):
    """Test the complete workout plan flow"""
    # Create workout plan
    plan_data = {
        "name": "Weekly Plan",
        "description": "Weekly workout plan",
        "duration_weeks": 4,
        "difficulty": "intermediate"
    }
    
    response = client.post(
        "/api/v1/workout-plans",
        json=plan_data,
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert response.status_code == 201
    plan_id = response.json()["id"]
    
    # Add workout to plan
    workout_data = {
        "workout_id": 1,
        "day_of_week": 1
    }
    
    response = client.post(
        f"/api/v1/workout-plans/{plan_id}/workouts",
        json=workout_data,
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert response.status_code == 200
    
    # Get plan details
    response = client.get(
        f"/api/v1/workout-plans/{plan_id}",
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert response.status_code == 200
    assert response.json()["name"] == plan_data["name"]

def test_workout_analysis_flow(client, test_user, test_token, mock_db_session):
    """Test the complete workout analysis flow"""
    # Upload workout video
    with open("test_video.mp4", "rb") as f:
        response = client.post(
            "/api/v1/workouts/analyze",
            files={"video": ("test_video.mp4", f, "video/mp4")},
            headers={"Authorization": f"Bearer {test_token}"}
        )
    assert response.status_code == 200
    
    # Get analysis results
    analysis_id = response.json()["analysis_id"]
    response = client.get(
        f"/api/v1/workouts/analysis/{analysis_id}",
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert response.status_code == 200
    assert "feedback" in response.json()
    assert "form_analysis" in response.json()

def test_subscription_flow(client, test_user, test_token, mock_db_session):
    """Test the complete subscription flow"""
    # Create subscription
    subscription_data = {
        "tier": "PRO",
        "duration_days": 30
    }
    
    response = client.post(
        "/api/v1/subscriptions",
        json=subscription_data,
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert response.status_code == 201
    
    # Get subscription status
    response = client.get(
        "/api/v1/subscriptions/status",
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is True
    
    # Cancel subscription
    response = client.post(
        "/api/v1/subscriptions/cancel",
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert response.status_code == 200

def test_user_profile_flow(client, test_user, test_token, mock_db_session):
    """Test the complete user profile flow"""
    # Get user profile
    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == test_user.email
    
    # Update user profile
    update_data = {
        "username": "updateduser",
        "email": "updated@example.com"
    }
    
    response = client.put(
        "/api/v1/users/me",
        json=update_data,
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert response.status_code == 200
    assert response.json()["username"] == update_data["username"]
    
    # Update password
    password_data = {
        "current_password": "testpassword",
        "new_password": "newpassword123"
    }
    
    response = client.put(
        "/api/v1/users/me/password",
        json=password_data,
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert response.status_code == 200

def test_workout_progress_flow(client, test_user, test_token, mock_db_session):
    """Test the complete workout progress tracking flow"""
    # Create workout
    workout_data = {
        "name": "Progress Workout",
        "description": "Workout for progress tracking",
        "duration": 60,
        "difficulty": "intermediate"
    }
    
    response = client.post(
        "/api/v1/workouts",
        json=workout_data,
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert response.status_code == 201
    workout_id = response.json()["id"]
    
    # Upload progress video
    with open("progress_video.mp4", "rb") as f:
        response = client.post(
            f"/api/v1/workouts/{workout_id}/progress",
            files={"video": ("progress_video.mp4", f, "video/mp4")},
            headers={"Authorization": f"Bearer {test_token}"}
        )
    assert response.status_code == 200
    
    # Get progress report
    response = client.get(
        f"/api/v1/workouts/{workout_id}/progress",
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert response.status_code == 200
    assert "improvements" in response.json()
    assert "recommendations" in response.json()

def test_error_handling(client, test_token):
    """Test error handling in the API"""
    # Test unauthorized access
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401
    
    # Test invalid token
    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401
    
    # Test not found resource
    response = client.get(
        "/api/v1/workouts/999",
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert response.status_code == 404
    
    # Test validation error
    invalid_data = {
        "email": "invalid-email",
        "username": "a"  # Too short
    }
    response = client.post(
        "/api/v1/users/register",
        json=invalid_data
    )
    assert response.status_code == 422 