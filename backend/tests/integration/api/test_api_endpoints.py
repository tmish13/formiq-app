"""Tests for API endpoints."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from tests.base import BaseTest

class TestAPIEndpoints(BaseTest):
    """Test suite for API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self, client):
        """Create authentication headers."""
        # Create test user
        user = self.create_test_user_sync()
        
        # Login to get token
        response = client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "testpass123"}
        )
        token = response.json()["access_token"]
        
        return {"Authorization": f"Bearer {token}"}
    
    def create_test_user_sync(self):
        """Create a test user synchronously."""
        import asyncio
        return asyncio.run(self.create_test_user())
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/api/health")
        
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
    
    def test_register_user(self, client):
        """Test user registration endpoint."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "newpass123",
                "full_name": "New User"
            }
        )
        
        assert response.status_code == 201
        assert "id" in response.json()
        assert response.json()["email"] == "newuser@example.com"
    
    def test_register_user_duplicate_email(self, client):
        """Test user registration with duplicate email."""
        # Create existing user
        self.create_test_user_sync()
        
        # Try to register with same email
        response = client.post(
            "/api/auth/register",
            json={
                "email": "test@example.com",
                "password": "newpass123",
                "full_name": "New User"
            }
        )
        
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]
    
    def test_login_success(self, client):
        """Test successful login."""
        # Create test user
        self.create_test_user_sync()
        
        # Login
        response = client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "testpass123"}
        )
        
        assert response.status_code == 200
        assert "access_token" in response.json()
        assert "token_type" in response.json()
        assert response.json()["token_type"] == "bearer"
    
    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials."""
        # Create test user
        self.create_test_user_sync()
        
        # Try to login with wrong password
        response = client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "wrongpassword"}
        )
        
        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]
    
    def test_get_user_profile(self, client, auth_headers):
        """Test getting user profile."""
        response = client.get("/api/users/me", headers=auth_headers)
        
        assert response.status_code == 200
        assert response.json()["email"] == "test@example.com"
    
    def test_get_user_profile_unauthorized(self, client):
        """Test getting user profile without authentication."""
        response = client.get("/api/users/me")
        
        assert response.status_code == 401
    
    def test_update_user_profile(self, client, auth_headers):
        """Test updating user profile."""
        response = client.put(
            "/api/users/me",
            headers=auth_headers,
            json={"full_name": "Updated Name"}
        )
        
        assert response.status_code == 200
        assert response.json()["full_name"] == "Updated Name"
    
    def test_upload_video(self, client, auth_headers):
        """Test video upload endpoint."""
        # Create a test video file
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".mp4") as temp_file:
            temp_file.write(b"dummy video data")
            temp_file.flush()
            
            # Upload video
            response = client.post(
                "/api/videos/upload",
                headers=auth_headers,
                files={"file": ("test_video.mp4", open(temp_file.name, "rb"), "video/mp4")},
                data={"exercise_type": "squat"}
            )
        
        assert response.status_code == 201
        assert "id" in response.json()
        assert response.json()["exercise_type"] == "squat"
    
    def test_get_user_videos(self, client, auth_headers):
        """Test getting user's videos."""
        # Create test user and video
        user = self.create_test_user_sync()
        self.create_test_video_sync(user_id=user["id"])
        
        response = client.get("/api/videos", headers=auth_headers)
        
        assert response.status_code == 200
        assert len(response.json()) == 1
    
    def create_test_video_sync(self, user_id):
        """Create a test video synchronously."""
        import asyncio
        return asyncio.run(self.create_test_video(user_id=user_id))
    
    def test_get_video_status(self, client, auth_headers):
        """Test getting video processing status."""
        # Create test user and video
        user = self.create_test_user_sync()
        video = self.create_test_video_sync(user_id=user["id"])
        
        response = client.get(f"/api/videos/{video['id']}/status", headers=auth_headers)
        
        assert response.status_code == 200
        assert "status" in response.json()
    
    def test_get_video_status_not_found(self, client, auth_headers):
        """Test getting status for non-existent video."""
        response = client.get("/api/videos/999/status", headers=auth_headers)
        
        assert response.status_code == 404
        assert "Video not found" in response.json()["detail"]
    
    def test_get_form_history(self, client, auth_headers):
        """Test getting form analysis history."""
        # Create test user, video, and form check
        user = self.create_test_user_sync()
        video = self.create_test_video_sync(user_id=user["id"])
        self.create_test_form_check_sync(video_id=video["id"])
        
        response = client.get("/api/form/history", headers=auth_headers)
        
        assert response.status_code == 200
        assert len(response.json()) == 1
    
    def create_test_form_check_sync(self, video_id):
        """Create a test form check synchronously."""
        import asyncio
        return asyncio.run(self.create_test_form_check(video_id=video_id))
    
    def test_rate_limiting(self, client):
        """Test rate limiting."""
        # Make multiple requests to a rate-limited endpoint
        for _ in range(10):
            response = client.get("/api/health")
            assert response.status_code == 200
        
        # Next request should be rate limited
        response = client.get("/api/health")
        assert response.status_code == 429
        assert "Too many requests" in response.json()["detail"] 