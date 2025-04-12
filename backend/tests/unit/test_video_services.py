import pytest
from pathlib import Path
import numpy as np
from fastapi import UploadFile
from app.services.video_service import VideoService
from app.services.form_analysis_service import FormAnalysisService
from app.schemas.video import VideoCreate, VideoAnalysis
from app.core.exceptions import ValidationError, ProcessingError
from app.models.video import Video
from app.models.form_check import FormCheck

class MockVideoFile:
    def __init__(self, content: bytes, filename: str):
        self.file = content
        self.filename = filename
        self._size = len(content)

    async def read(self):
        return self.file

    def seek(self, offset: int):
        pass

    @property
    def size(self):
        return self._size

@pytest.fixture
def mock_video_file():
    """Create a mock video file for testing."""
    content = b"mock video content"
    return MockVideoFile(content, "test_video.mp4")

@pytest.fixture
def mock_video_service(db_session):
    """Create a mock video service instance."""
    return VideoService(db_session)

@pytest.fixture
def mock_form_analysis_service(db_session):
    """Create a mock form analysis service instance."""
    return FormAnalysisService(db_session)

@pytest.mark.asyncio
async def test_video_upload(db_session, mock_video_file, mock_video_service):
    """Test video upload functionality."""
    # Test successful upload
    video_data = VideoCreate(
        exercise_type="squat",
        user_id=1,
        filename="test_video.mp4"
    )
    
    video = await mock_video_service.upload_video(
        file=mock_video_file,
        video_data=video_data
    )
    
    assert isinstance(video, Video)
    assert video.filename == "test_video.mp4"
    assert video.exercise_type == "squat"
    
    # Test invalid file type
    invalid_file = MockVideoFile(b"invalid", "test.txt")
    with pytest.raises(ValidationError):
        await mock_video_service.upload_video(
            file=invalid_file,
            video_data=video_data
        )

@pytest.mark.asyncio
async def test_video_processing(db_session, mock_video_file, mock_video_service):
    """Test video processing pipeline."""
    video_data = VideoCreate(
        exercise_type="squat",
        user_id=1,
        filename="test_video.mp4"
    )
    
    video = await mock_video_service.upload_video(
        file=mock_video_file,
        video_data=video_data
    )
    
    # Test processing status updates
    assert video.status == "pending"
    
    processed_video = await mock_video_service.process_video(video.id)
    assert processed_video.status == "processed"
    
    # Test processing error handling
    with pytest.raises(ProcessingError):
        await mock_video_service.process_video(999)  # Non-existent video

@pytest.mark.asyncio
async def test_form_analysis(db_session, mock_form_analysis_service, mock_video_service):
    """Test form analysis functionality."""
    # Create test video
    video_data = VideoCreate(
        exercise_type="squat",
        user_id=1,
        filename="test_video.mp4"
    )
    
    video = await mock_video_service.upload_video(
        file=MockVideoFile(b"content", "test_video.mp4"),
        video_data=video_data
    )
    
    # Test form analysis
    analysis = await mock_form_analysis_service.analyze_form(video.id)
    assert isinstance(analysis, VideoAnalysis)
    assert "feedback" in analysis.dict()
    assert "score" in analysis.dict()
    
    # Test analysis with invalid video
    with pytest.raises(ValidationError):
        await mock_form_analysis_service.analyze_form(999)

@pytest.mark.asyncio
async def test_video_retrieval(db_session, mock_video_service):
    """Test video retrieval operations."""
    # Create test videos
    video_data1 = VideoCreate(
        exercise_type="squat",
        user_id=1,
        filename="squat1.mp4"
    )
    video_data2 = VideoCreate(
        exercise_type="deadlift",
        user_id=1,
        filename="deadlift1.mp4"
    )
    
    video1 = await mock_video_service.upload_video(
        file=MockVideoFile(b"content1", "squat1.mp4"),
        video_data=video_data1
    )
    video2 = await mock_video_service.upload_video(
        file=MockVideoFile(b"content2", "deadlift1.mp4"),
        video_data=video_data2
    )
    
    # Test get video by id
    retrieved_video = await mock_video_service.get_video(video1.id)
    assert retrieved_video.id == video1.id
    assert retrieved_video.exercise_type == "squat"
    
    # Test get videos by user
    user_videos = await mock_video_service.get_user_videos(1)
    assert len(user_videos) == 2
    assert any(v.filename == "squat1.mp4" for v in user_videos)
    assert any(v.filename == "deadlift1.mp4" for v in user_videos)

@pytest.mark.asyncio
async def test_form_feedback(db_session, mock_form_analysis_service):
    """Test form feedback generation."""
    # Test feedback for different exercises
    exercises = ["squat", "deadlift", "bench_press"]
    
    for exercise in exercises:
        feedback = await mock_form_analysis_service.generate_feedback(
            exercise_type=exercise,
            form_data={
                "joint_angles": {"hip": 90, "knee": 90},
                "spine_alignment": 0.95,
                "symmetry_score": 0.85
            }
        )
        
        assert isinstance(feedback, dict)
        assert "score" in feedback
        assert "feedback" in feedback
        assert isinstance(feedback["feedback"], list)
        assert 0 <= feedback["score"] <= 100

@pytest.mark.asyncio
async def test_error_handling(db_session, mock_video_service, mock_form_analysis_service):
    """Test error handling in video and form analysis services."""
    # Test file size limit
    large_file = MockVideoFile(b"x" * (100 * 1024 * 1024 + 1), "large.mp4")  # > 100MB
    with pytest.raises(ValidationError):
        await mock_video_service.validate_video_file(large_file)
    
    # Test corrupted video handling
    corrupted_file = MockVideoFile(b"corrupted data", "corrupted.mp4")
    with pytest.raises(ProcessingError):
        await mock_video_service.process_video_frames(corrupted_file)
    
    # Test invalid exercise type
    with pytest.raises(ValidationError):
        await mock_form_analysis_service.generate_feedback(
            exercise_type="invalid_exercise",
            form_data={}
        )

@pytest.mark.asyncio
async def test_video_cleanup(db_session, mock_video_service):
    """Test video cleanup operations."""
    # Create test video
    video_data = VideoCreate(
        exercise_type="squat",
        user_id=1,
        filename="cleanup_test.mp4"
    )
    
    video = await mock_video_service.upload_video(
        file=MockVideoFile(b"content", "cleanup_test.mp4"),
        video_data=video_data
    )
    
    # Test successful deletion
    await mock_video_service.delete_video(video.id)
    
    # Verify video is deleted
    with pytest.raises(ValidationError):
        await mock_video_service.get_video(video.id)
    
    # Test deletion of non-existent video
    with pytest.raises(ValidationError):
        await mock_video_service.delete_video(999) 