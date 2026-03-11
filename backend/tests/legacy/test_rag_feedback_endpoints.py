"""Tests for RAG feedback API endpoints."""

import pytest
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient

from app.main import app
from app.services.rag_feedback_service import FeedbackContext


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_authenticated_user():
    """Mock authenticated user for endpoint testing."""
    user_mock = Mock()
    user_mock.id = "test-user-id"
    user_mock.email = "test@example.com"
    return user_mock


class TestRAGFeedbackEndpoints:
    """Test suite for RAG feedback API endpoints."""
    
    @patch('app.api.v1.endpoints.feedback.rag_feedback_service')
    @patch('app.api.deps.get_current_active_user')
    def test_generate_rag_feedback_success(self, mock_get_user, mock_rag_service, client, mock_authenticated_user):
        """Test successful RAG feedback generation endpoint."""
        # Mock authentication
        mock_get_user.return_value = mock_authenticated_user
        
        # Mock RAG service
        mock_rag_service.generate_feedback.return_value = "Excellent squat form! Focus on knee alignment for better stability."
        mock_rag_service.is_available.return_value = True
        
        # Test request
        request_data = {
            "exercise_name": "Barbell Squat",
            "exercise_type": "squat",
            "posture_score": 85.0,
            "stability_score": 70.0,
            "depth_score": 90.0,
            "identified_faults": ["knee_valgus"],
            "user_level": "intermediate",
            "additional_context": "User improving over last 3 sessions"
        }
        
        response = client.post("/api/v1/feedback/rag/generate", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["feedback_text"] == "Excellent squat form! Focus on knee alignment for better stability."
        assert data["rag_enabled"] is True
        assert data["exercise_name"] == "Barbell Squat"
        assert data["exercise_type"] == "squat"
        
        # Verify service was called with correct context
        mock_rag_service.generate_feedback.assert_called_once()
        call_args = mock_rag_service.generate_feedback.call_args[0][0]
        assert isinstance(call_args, FeedbackContext)
        assert call_args.exercise_name == "Barbell Squat"
        assert call_args.form_scores["posture_score"] == 85.0
        assert call_args.identified_faults == ["knee_valgus"]
    
    @patch('app.api.v1.endpoints.feedback.rag_feedback_service')
    @patch('app.api.deps.get_current_active_user')
    def test_generate_rag_feedback_minimal_request(self, mock_get_user, mock_rag_service, client, mock_authenticated_user):
        """Test RAG feedback with minimal required fields."""
        mock_get_user.return_value = mock_authenticated_user
        mock_rag_service.generate_feedback.return_value = "Good squat technique!"
        mock_rag_service.is_available.return_value = False  # RAG disabled
        
        # Minimal request data
        request_data = {
            "exercise_name": "Squat",
            "exercise_type": "squat",
            "posture_score": 80.0,
            "stability_score": 75.0,
            "depth_score": 85.0
        }
        
        response = client.post("/api/v1/feedback/rag/generate", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["feedback_text"] == "Good squat technique!"
        assert data["rag_enabled"] is False
        assert data["exercise_name"] == "Squat"
        
        # Check default values were used
        call_args = mock_rag_service.generate_feedback.call_args[0][0]
        assert call_args.user_level == "intermediate"  # default
        assert call_args.identified_faults == []  # default
        assert call_args.additional_context is None  # default
    
    @patch('app.api.deps.get_current_active_user')
    def test_generate_rag_feedback_unauthenticated(self, mock_get_user, client):
        """Test RAG feedback endpoint without authentication."""
        mock_get_user.side_effect = Exception("Unauthorized")
        
        request_data = {
            "exercise_name": "Squat",
            "exercise_type": "squat",
            "posture_score": 80.0,
            "stability_score": 75.0,
            "depth_score": 85.0
        }
        
        with pytest.raises(Exception):
            client.post("/api/v1/feedback/rag/generate", json=request_data)
    
    @patch('app.api.v1.endpoints.feedback.rag_feedback_service')
    @patch('app.api.deps.get_current_active_user')
    def test_generate_rag_feedback_service_error(self, mock_get_user, mock_rag_service, client, mock_authenticated_user):
        """Test RAG feedback endpoint when service throws error."""
        mock_get_user.return_value = mock_authenticated_user
        mock_rag_service.generate_feedback.side_effect = Exception("RAG service error")
        
        request_data = {
            "exercise_name": "Squat",
            "exercise_type": "squat",
            "posture_score": 80.0,
            "stability_score": 75.0,
            "depth_score": 85.0
        }
        
        response = client.post("/api/v1/feedback/rag/generate", json=request_data)
        
        assert response.status_code == 500
        assert "error occurred while generating feedback" in response.json()["detail"]
    
    @patch('app.api.deps.get_current_active_user')
    def test_generate_rag_feedback_invalid_data(self, mock_get_user, client, mock_authenticated_user):
        """Test RAG feedback endpoint with invalid request data."""
        mock_get_user.return_value = mock_authenticated_user
        
        # Missing required fields
        request_data = {
            "exercise_name": "Squat",
            # Missing exercise_type, posture_score, etc.
        }
        
        response = client.post("/api/v1/feedback/rag/generate", json=request_data)
        
        assert response.status_code == 422  # Validation error
    
    @patch('app.api.v1.endpoints.feedback.rag_feedback_service')
    @patch('app.api.deps.get_current_active_user')
    def test_generate_rag_feedback_edge_case_scores(self, mock_get_user, mock_rag_service, client, mock_authenticated_user):
        """Test RAG feedback with edge case score values."""
        mock_get_user.return_value = mock_authenticated_user
        mock_rag_service.generate_feedback.return_value = "Keep working on your form!"
        mock_rag_service.is_available.return_value = True
        
        # Edge case: very low scores
        request_data = {
            "exercise_name": "Beginner Squat",
            "exercise_type": "squat",
            "posture_score": 0.0,
            "stability_score": 25.0,
            "depth_score": 100.0,
            "identified_faults": ["knee_valgus", "forward_lean", "heel_rise"],
            "user_level": "beginner"
        }
        
        response = client.post("/api/v1/feedback/rag/generate", json=request_data)
        
        assert response.status_code == 200
        
        # Verify context passed to service
        call_args = mock_rag_service.generate_feedback.call_args[0][0]
        assert call_args.form_scores["posture_score"] == 0.0
        assert len(call_args.identified_faults) == 3
        assert call_args.user_level == "beginner"
    
    @patch('app.api.v1.endpoints.feedback.rag_feedback_service')
    @patch('app.api.deps.get_current_active_user')  
    def test_generate_rag_feedback_different_exercise_types(self, mock_get_user, mock_rag_service, client, mock_authenticated_user):
        """Test RAG feedback with different exercise types."""
        mock_get_user.return_value = mock_authenticated_user
        mock_rag_service.generate_feedback.return_value = "Great deadlift form!"
        mock_rag_service.is_available.return_value = True
        
        request_data = {
            "exercise_name": "Romanian Deadlift",
            "exercise_type": "deadlift",
            "posture_score": 88.0,
            "stability_score": 92.0,
            "depth_score": 85.0,
            "identified_faults": [],
            "user_level": "advanced"
        }
        
        response = client.post("/api/v1/feedback/rag/generate", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["exercise_type"] == "deadlift"
        assert data["exercise_name"] == "Romanian Deadlift"
        
        # Verify correct exercise type passed to service
        call_args = mock_rag_service.generate_feedback.call_args[0][0]
        assert call_args.exercise_type == "deadlift"