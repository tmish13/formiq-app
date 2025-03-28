import pytest
from datetime import datetime
from ..services.form_check import FormCheckService, FormCheckError, ExerciseType
from ..models.form_check import FormCheck
from ..models.user import User
from sqlalchemy.orm import Session
from unittest.mock import Mock, patch, ANY
import json
import boto3

@pytest.fixture
def mock_s3():
    """Mock S3 client"""
    with patch('boto3.client') as mock_client:
        s3 = mock_client.return_value
        s3.generate_presigned_url.return_value = "https://test-bucket.s3.amazonaws.com/test.mp4"
        s3.upload_fileobj = Mock()
        yield s3

@pytest.fixture
def mock_db_session():
    """Create a mock database session"""
    session = Mock(spec=Session)
    session.query.return_value.filter.return_value.first.return_value = None
    session.add = Mock()
    session.commit = Mock()
    return session

@pytest.fixture
def mock_ai_service():
    """Mock AI service for form analysis"""
    with patch('..services.ai.AIService') as mock_service:
        service = mock_service.return_value
        service.analyze_form.return_value = {
            "score": 8.5,
            "overall_feedback": "Good form overall",
            "issues": [
                {"timestamp": 1.5, "description": "Slight knee valgus"},
                {"timestamp": 3.0, "description": "Back not straight"}
            ]
        }
        yield service

@pytest.fixture
def form_check_service(mock_db_session, mock_s3, mock_ai_service):
    """Create a form check service instance"""
    return FormCheckService(
        db=mock_db_session,
        s3_client=mock_s3,
        ai_service=mock_ai_service
    )

@pytest.fixture
def test_user():
    """Create a test user"""
    return User(
        id=1,
        email="test@example.com",
        username="testuser",
        subscription_tier="PRO"
    )

@pytest.fixture
def test_video():
    """Create a test video file-like object"""
    class MockVideo:
        def read(self):
            return b"test video content"
    return MockVideo()

def test_create_form_check(form_check_service, test_user, test_video, mock_s3):
    """Test creating a new form check"""
    form_check = form_check_service.create_form_check(
        user=test_user,
        video=test_video,
        exercise_type=ExerciseType.SQUAT,
        filename="test.mp4"
    )
    
    assert isinstance(form_check, FormCheck)
    assert form_check.user_id == test_user.id
    assert form_check.exercise_type == ExerciseType.SQUAT
    mock_s3.upload_fileobj.assert_called_once()

def test_create_form_check_invalid_exercise(form_check_service, test_user, test_video):
    """Test creating a form check with invalid exercise type"""
    with pytest.raises(FormCheckError):
        form_check_service.create_form_check(
            user=test_user,
            video=test_video,
            exercise_type="INVALID_EXERCISE",
            filename="test.mp4"
        )

def test_analyze_form(form_check_service, test_user, mock_ai_service):
    """Test form analysis"""
    form_check = FormCheck(
        id=1,
        user_id=test_user.id,
        exercise_type=ExerciseType.SQUAT,
        video_url="https://test-bucket.s3.amazonaws.com/test.mp4"
    )
    
    analysis = form_check_service.analyze_form(form_check)
    
    assert analysis["score"] == 8.5
    assert "overall_feedback" in analysis
    assert "issues" in analysis
    mock_ai_service.analyze_form.assert_called_once()

def test_get_form_check(form_check_service, test_user, mock_db_session):
    """Test retrieving a form check"""
    mock_db_session.query.return_value.filter.return_value.first.return_value = FormCheck(
        id=1,
        user_id=test_user.id,
        exercise_type=ExerciseType.SQUAT,
        video_url="https://test-bucket.s3.amazonaws.com/test.mp4"
    )
    
    form_check = form_check_service.get_form_check(form_check_id=1, user=test_user)
    
    assert form_check.id == 1
    assert form_check.user_id == test_user.id

def test_get_form_check_not_found(form_check_service, test_user):
    """Test retrieving a non-existent form check"""
    with pytest.raises(FormCheckError):
        form_check_service.get_form_check(form_check_id=999, user=test_user)

def test_get_user_form_checks(form_check_service, test_user, mock_db_session):
    """Test retrieving all form checks for a user"""
    mock_form_checks = [
        FormCheck(id=1, user_id=test_user.id, exercise_type=ExerciseType.SQUAT),
        FormCheck(id=2, user_id=test_user.id, exercise_type=ExerciseType.DEADLIFT)
    ]
    mock_db_session.query.return_value.filter.return_value.all.return_value = mock_form_checks
    
    form_checks = form_check_service.get_user_form_checks(user=test_user)
    
    assert len(form_checks) == 2
    assert all(fc.user_id == test_user.id for fc in form_checks)

def test_delete_form_check(form_check_service, test_user, mock_s3, mock_db_session):
    """Test deleting a form check"""
    mock_form_check = FormCheck(
        id=1,
        user_id=test_user.id,
        exercise_type=ExerciseType.SQUAT,
        video_url="https://test-bucket.s3.amazonaws.com/test.mp4"
    )
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_form_check
    
    form_check_service.delete_form_check(form_check_id=1, user=test_user)
    
    mock_s3.delete_object.assert_called_once()
    mock_db_session.delete.assert_called_once_with(mock_form_check)

def test_generate_video_url(form_check_service, mock_s3):
    """Test generating a presigned URL for video access"""
    url = form_check_service.generate_video_url("test.mp4")
    
    assert url == "https://test-bucket.s3.amazonaws.com/test.mp4"
    mock_s3.generate_presigned_url.assert_called_once()

def test_validate_video_format(form_check_service, test_video):
    """Test video format validation"""
    # Test valid format
    form_check_service.validate_video_format(test_video, "test.mp4")
    
    # Test invalid format
    with pytest.raises(FormCheckError):
        form_check_service.validate_video_format(test_video, "test.txt")

def test_validate_video_size(form_check_service, test_video):
    """Test video size validation"""
    # Mock video size
    test_video.seek = Mock()
    test_video.tell = Mock(return_value=5 * 1024 * 1024)  # 5MB
    
    # Test valid size
    form_check_service.validate_video_size(test_video)
    
    # Test invalid size
    test_video.tell = Mock(return_value=1000 * 1024 * 1024)  # 1GB
    with pytest.raises(FormCheckError):
        form_check_service.validate_video_size(test_video)

def test_process_form_check_async(form_check_service, test_user, mock_ai_service, mock_db_session):
    """Test asynchronous form check processing"""
    form_check = FormCheck(
        id=1,
        user_id=test_user.id,
        exercise_type=ExerciseType.SQUAT,
        video_url="https://test-bucket.s3.amazonaws.com/test.mp4"
    )
    
    form_check_service.process_form_check_async(form_check)
    
    mock_ai_service.analyze_form.assert_called_once()
    mock_db_session.commit.assert_called()

def test_get_form_check_statistics(form_check_service, test_user, mock_db_session):
    """Test getting form check statistics"""
    mock_db_session.query.return_value.filter.return_value.all.return_value = [
        FormCheck(score=8.5, created_at=datetime.now()),
        FormCheck(score=9.0, created_at=datetime.now())
    ]
    
    stats = form_check_service.get_form_check_statistics(user=test_user)
    
    assert "average_score" in stats
    assert "total_checks" in stats
    assert "improvement_rate" in stats

def test_handle_processing_error(form_check_service, test_user, mock_db_session):
    """Test handling processing errors"""
    form_check = FormCheck(
        id=1,
        user_id=test_user.id,
        exercise_type=ExerciseType.SQUAT,
        video_url="https://test-bucket.s3.amazonaws.com/test.mp4"
    )
    
    mock_ai_service = Mock()
    mock_ai_service.analyze_form.side_effect = Exception("AI service error")
    form_check_service.ai_service = mock_ai_service
    
    form_check_service.handle_processing_error(form_check, "AI service error")
    
    assert form_check.status == "ERROR"
    assert form_check.error_message == "AI service error"
    mock_db_session.commit.assert_called_once() 