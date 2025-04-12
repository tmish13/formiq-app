"""Tests for video processing service."""
import pytest
from unittest.mock import Mock, patch, AsyncMock
import os
import tempfile
from app.services.video_processing import VideoProcessingService
from tests.base import BaseTest
from app.models.video import VideoStatus
from app.exceptions import VideoProcessingError

class TestVideoProcessingService(BaseTest):
    """Test suite for VideoProcessingService."""
    
    @pytest.fixture
    def video_processing_service(self):
        """Create a VideoProcessingService instance."""
        return VideoProcessingService()
    
    @pytest.fixture
    def sample_video_file(self):
        """Create a sample video file for testing."""
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_file:
            # Write some dummy data to simulate a video file
            temp_file.write(b"dummy video data")
            return temp_file.name
    
    @pytest.fixture
    def mock_s3_client(self):
        with patch('app.services.video_processing.boto3.client') as mock:
            yield mock
    
    @pytest.fixture
    def mock_pose_detector(self):
        with patch('app.services.video_processing.PoseDetector') as mock:
            yield mock
    
    @pytest.mark.asyncio
    async def test_process_video_success(self, video_processing_service, mock_s3_client, mock_pose_detector):
        """Test successful video processing."""
        # Setup
        video_id = "test-video-123"
        video_url = "https://s3.example.com/videos/test.mp4"
        mock_s3_client.return_value.get_object.return_value = {
            'Body': Mock(read=lambda: b'fake video data')
        }
        mock_pose_detector.return_value.detect_poses.return_value = [
            {'keypoints': [{'x': 100, 'y': 100}]}
        ]

        # Execute
        result = await video_processing_service.process_video(video_id, video_url)

        # Assert
        assert result['status'] == VideoStatus.COMPLETED
        assert 'poses' in result
        assert len(result['poses']) == 1
        mock_s3_client.return_value.get_object.assert_called_once()
        mock_pose_detector.return_value.detect_poses.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_video_invalid_format(self, video_processing_service, mock_s3_client):
        """Test video processing with invalid video format."""
        # Setup
        video_id = "test-video-123"
        video_url = "https://s3.example.com/videos/test.txt"
        
        # Execute & Assert
        with pytest.raises(VideoProcessingError) as exc_info:
            await video_processing_service.process_video(video_id, video_url)
        assert "Invalid video format" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_process_video_s3_error(self, video_processing_service, mock_s3_client):
        """Test video processing with S3 error."""
        # Setup
        video_id = "test-video-123"
        video_url = "https://s3.example.com/videos/test.mp4"
        mock_s3_client.return_value.get_object.side_effect = Exception("S3 Error")

        # Execute & Assert
        with pytest.raises(VideoProcessingError) as exc_info:
            await video_processing_service.process_video(video_id, video_url)
        assert "Failed to fetch video" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_process_video_pose_detection_error(self, video_processing_service, mock_s3_client, mock_pose_detector):
        """Test video processing with pose detection error."""
        # Setup
        video_id = "test-video-123"
        video_url = "https://s3.example.com/videos/test.mp4"
        mock_s3_client.return_value.get_object.return_value = {
            'Body': Mock(read=lambda: b'fake video data')
        }
        mock_pose_detector.return_value.detect_poses.side_effect = Exception("Pose detection failed")

        # Execute & Assert
        with pytest.raises(VideoProcessingError) as exc_info:
            await video_processing_service.process_video(video_id, video_url)
        assert "Pose detection failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_process_video_empty_result(self, video_processing_service, mock_s3_client, mock_pose_detector):
        """Test video processing with empty result."""
        # Setup
        video_id = "test-video-123"
        video_url = "https://s3.example.com/videos/test.mp4"
        mock_s3_client.return_value.get_object.return_value = {
            'Body': Mock(read=lambda: b'fake video data')
        }
        mock_pose_detector.return_value.detect_poses.return_value = []

        # Execute
        result = await video_processing_service.process_video(video_id, video_url)

        # Assert
        assert result['status'] == VideoStatus.COMPLETED
        assert 'poses' in result
        assert len(result['poses']) == 0
    
    @pytest.mark.asyncio
    async def test_process_video_invalid_video(self, video_processing_service):
        """Test video processing with invalid video ID."""
        # Try to process non-existent video
        with pytest.raises(ValueError, match="Video not found"):
            await video_processing_service.process_video(999)
    
    @pytest.mark.asyncio
    async def test_process_video_processing_error(self, video_processing_service, sample_video_file):
        """Test video processing with processing error."""
        # Create test user and video
        user = await self.create_test_user()
        video = await self.create_test_video(
            user_id=user["id"],
            filename=os.path.basename(sample_video_file)
        )
        
        # Mock the pose detection model to raise an exception
        with patch("app.services.video_processing.PoseDetector") as mock_detector:
            mock_detector.return_value.detect_poses.side_effect = Exception("Processing failed")
            
            # Process video
            result = await video_processing_service.process_video(video["id"])
            
            # Verify results
            assert result is not None
            assert result["status"] == "failed"
            assert "error" in result
    
    @pytest.mark.asyncio
    async def test_get_video_status(self, video_processing_service):
        """Test getting video processing status."""
        # Create test user and video
        user = await self.create_test_user()
        video = await self.create_test_video(
            user_id=user["id"],
            status="processing"
        )
        
        # Get status
        status = await video_processing_service.get_video_status(video["id"])
        
        # Verify results
        assert status == "processing"
    
    @pytest.mark.asyncio
    async def test_get_video_status_not_found(self, video_processing_service):
        """Test getting status for non-existent video."""
        # Try to get status for non-existent video
        with pytest.raises(ValueError, match="Video not found"):
            await video_processing_service.get_video_status(999)
    
    @pytest.mark.asyncio
    async def test_cancel_video_processing(self, video_processing_service):
        """Test canceling video processing."""
        # Create test user and video
        user = await self.create_test_user()
        video = await self.create_test_video(
            user_id=user["id"],
            status="processing"
        )
        
        # Cancel processing
        await video_processing_service.cancel_video_processing(video["id"])
        
        # Verify video status was updated
        updated_video = await self.db.execute(
            "SELECT * FROM videos WHERE id = :id",
            {"id": video["id"]}
        )
        updated_video = updated_video.first()
        
        assert updated_video["status"] == "canceled"
    
    @pytest.mark.asyncio
    async def test_cancel_video_processing_not_found(self, video_processing_service):
        """Test canceling processing for non-existent video."""
        # Try to cancel processing for non-existent video
        with pytest.raises(ValueError, match="Video not found"):
            await video_processing_service.cancel_video_processing(999)
    
    @pytest.mark.asyncio
    async def test_get_user_videos(self, video_processing_service):
        """Test getting user's videos."""
        # Create test user and videos
        user = await self.create_test_user()
        video1 = await self.create_test_video(user_id=user["id"])
        video2 = await self.create_test_video(user_id=user["id"])
        
        # Get user's videos
        videos = await video_processing_service.get_user_videos(user["id"])
        
        # Verify results
        assert len(videos) == 2
        assert videos[0]["id"] == video1["id"]
        assert videos[1]["id"] == video2["id"]
    
    @pytest.mark.asyncio
    async def test_get_user_videos_empty(self, video_processing_service):
        """Test getting videos for user with no videos."""
        # Create test user without videos
        user = await self.create_test_user()
        
        # Get user's videos
        videos = await video_processing_service.get_user_videos(user["id"])
        
        # Verify results
        assert len(videos) == 0 