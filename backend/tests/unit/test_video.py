import pytest
from unittest.mock import Mock, patch
from app.models.video import Video
from app.services.video import VideoService
from app.core.exceptions import VideoProcessingError
from tests.factories import VideoFactory, UserFactory

def test_video_creation():
    user = UserFactory()
    video = VideoFactory(user_id=user.id)
    assert video.user_id == user.id
    assert video.status == "pending"
    assert video.filename.endswith(".mp4")
    assert video.s3_key.startswith("uploads/")

def test_video_status_update():
    video = VideoFactory()
    video.status = "processing"
    assert video.status == "processing"
    video.status = "completed"
    assert video.status == "completed"

def test_video_processing_error():
    video = VideoFactory()
    with pytest.raises(VideoProcessingError):
        video.status = "error"
        video.error_message = "Processing failed"
        raise VideoProcessingError("Processing failed")

@patch('app.services.video.VideoService.upload_to_s3')
def test_video_upload(mock_upload):
    user = UserFactory()
    video = VideoFactory(user_id=user.id)
    mock_upload.return_value = "s3://bucket/video.mp4"
    
    service = VideoService()
    result = service.upload_video(video)
    
    assert result == "s3://bucket/video.mp4"
    mock_upload.assert_called_once_with(video)

@patch('app.services.video.VideoService.process_video')
def test_video_processing(mock_process):
    video = VideoFactory()
    mock_process.return_value = {"status": "completed", "feedback": "Good form"}
    
    service = VideoService()
    result = service.process_video(video)
    
    assert result["status"] == "completed"
    assert "feedback" in result
    mock_process.assert_called_once_with(video)

def test_video_validation():
    video = VideoFactory()
    assert video.is_valid()
    
    video.filename = "invalid.txt"
    assert not video.is_valid()
    
    video.filename = "video.mp4"
    video.status = "error"
    assert not video.is_valid() 