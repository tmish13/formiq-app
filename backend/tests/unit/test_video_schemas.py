"""Video schema tests."""
import pytest
from fastapi import UploadFile
from pydantic import ValidationError
from datetime import datetime
from app.schemas.video import (
    VideoUploadBase,
    VideoCreate,
    VideoAnalysis,
    VideoUploadRequest,
    VideoUploadResponse
)

def test_video_upload_base_validation():
    """Test VideoUploadBase schema validation."""
    # Valid data
    data = {
        "title": "Test Video",
        "description": "Test description",
        "exercise_type": "squat"
    }
    video = VideoUploadBase(**data)
    assert video.title == "Test Video"
    assert video.description == "Test description"
    assert video.exercise_type == "squat"

    # Test title validation
    with pytest.raises(ValidationError):
        VideoUploadBase(title="", description="Test", exercise_type="squat")
    
    with pytest.raises(ValidationError):
        VideoUploadBase(title="  ", description="Test", exercise_type="squat")
    
    # Test description length
    with pytest.raises(ValidationError):
        VideoUploadBase(
            title="Test",
            description="x" * 501,  # Exceeds max length
            exercise_type="squat"
        )

def test_video_create_validation():
    """Test VideoCreate schema validation."""
    data = {
        "title": "Test Video",
        "description": "Test description",
        "exercise_type": "squat",
        "user_id": "123e4567-e89b-12d3-a456-426614174000",
        "url": "http://example.com/video.mp4",
        "filename": "video.mp4"
    }
    video = VideoCreate(**data)
    assert video.user_id == data["user_id"]
    assert video.url == data["url"]
    assert video.filename == data["filename"]

def test_video_analysis_validation():
    """Test VideoAnalysis schema validation."""
    data = {
        "video_id": "123e4567-e89b-12d3-a456-426614174000",
        "score": 85.5,
        "feedback": ["Good form", "Keep chest up"],
        "joint_angles": {"hip": 90.0, "knee": 85.5},
        "spine_alignment": 0.95,
        "created_at": datetime.utcnow(),
        "metadata": {"duration": 30}
    }
    analysis = VideoAnalysis(**data)
    assert analysis.score == 85.5
    assert len(analysis.feedback) == 2
    assert analysis.joint_angles["hip"] == 90.0
    assert analysis.spine_alignment == 0.95

    # Test score validation
    with pytest.raises(ValidationError):
        VideoAnalysis(
            video_id=data["video_id"],
            score=101,  # Exceeds maximum
            spine_alignment=0.5
        )
    
    with pytest.raises(ValidationError):
        VideoAnalysis(
            video_id=data["video_id"],
            score=-1,  # Below minimum
            spine_alignment=0.5
        )

def test_video_upload_request_validation(tmp_path):
    """Test VideoUploadRequest schema validation."""
    # Create a test file
    test_file = tmp_path / "test.mp4"
    test_file.write_bytes(b"test content")
    
    # Create UploadFile instance
    upload_file = UploadFile(
        filename="test.mp4",
        file=test_file.open("rb"),
        content_type="video/mp4"
    )
    
    data = {
        "title": "Test Video",
        "description": "Test description",
        "exercise_type": "squat",
        "file": upload_file
    }
    
    request = VideoUploadRequest(**data)
    assert request.title == "Test Video"
    assert request.file.filename == "test.mp4"
    assert request.file.content_type == "video/mp4"

    # Test invalid file type
    invalid_file = UploadFile(
        filename="test.txt",
        file=test_file.open("rb"),
        content_type="text/plain"
    )
    with pytest.raises(ValidationError):
        VideoUploadRequest(
            title="Test",
            exercise_type="squat",
            file=invalid_file
        )

def test_video_upload_response_validation():
    """Test VideoUploadResponse schema validation."""
    data = {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "title": "Test Video",
        "description": "Test description",
        "exercise_type": "squat",
        "url": "http://example.com/video.mp4",
        "status": "processing",
        "created_at": datetime.utcnow().isoformat()
    }
    response = VideoUploadResponse(**data)
    assert response.id == data["id"]
    assert response.url == data["url"]
    assert response.status == "processing" 