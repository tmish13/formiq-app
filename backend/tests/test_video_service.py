import pytest
from unittest.mock import Mock, patch
import cv2
import numpy as np
from ..services.video import VideoService, VideoError
import tempfile
import os
from PIL import Image
import io

@pytest.fixture
def mock_cv2():
    """Mock OpenCV functions"""
    with patch('cv2.VideoCapture') as mock_capture, \
         patch('cv2.VideoWriter') as mock_writer, \
         patch('cv2.imread') as mock_imread, \
         patch('cv2.imwrite') as mock_imwrite:
        
        mock_capture.return_value = Mock()
        mock_capture.return_value.read = Mock(return_value=(True, np.zeros((300, 300, 3))))
        mock_capture.return_value.get = Mock(return_value=30.0)  # fps
        mock_capture.return_value.get.return_value = 30.0
        
        mock_writer.return_value = Mock()
        mock_writer.return_value.write = Mock()
        mock_writer.return_value.release = Mock()
        
        mock_imread.return_value = np.zeros((300, 300, 3))
        mock_imwrite.return_value = True
        
        yield {
            "capture": mock_capture,
            "writer": mock_writer,
            "imread": mock_imread,
            "imwrite": mock_imwrite
        }

@pytest.fixture
def video_service(mock_cv2):
    """Create a video service instance"""
    return VideoService()

@pytest.fixture
def test_video():
    """Create a test video file"""
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
        f.write(b"test video content")
        return f.name

def test_compress_video(video_service, test_video, mock_cv2):
    """Test video compression"""
    output_path = video_service.compress_video(
        input_path=test_video,
        target_size_mb=5
    )
    
    assert os.path.exists(output_path)
    mock_cv2["capture"].assert_called_once()
    mock_cv2["writer"].assert_called_once()

def test_extract_frames(video_service, test_video, mock_cv2):
    """Test frame extraction"""
    frames = video_service.extract_frames(
        video_path=test_video,
        frame_interval=10
    )
    
    assert isinstance(frames, list)
    assert all(isinstance(frame, np.ndarray) for frame in frames)
    mock_cv2["capture"].assert_called_once()

def test_create_thumbnail(video_service, test_video, mock_cv2):
    """Test thumbnail creation"""
    thumbnail = video_service.create_thumbnail(
        video_path=test_video,
        timestamp=1.0
    )
    
    assert isinstance(thumbnail, np.ndarray)
    mock_cv2["capture"].assert_called_once()

def test_validate_video_format(video_service, test_video):
    """Test video format validation"""
    # Test valid format
    video_service.validate_video_format(test_video)
    
    # Test invalid format
    with pytest.raises(VideoError):
        video_service.validate_video_format("test.txt")

def test_get_video_metadata(video_service, test_video, mock_cv2):
    """Test video metadata extraction"""
    metadata = video_service.get_video_metadata(test_video)
    
    assert isinstance(metadata, dict)
    assert "duration" in metadata
    assert "fps" in metadata
    assert "frame_count" in metadata
    assert "resolution" in metadata

def test_resize_video(video_service, test_video, mock_cv2):
    """Test video resizing"""
    output_path = video_service.resize_video(
        input_path=test_video,
        target_width=640,
        target_height=480
    )
    
    assert os.path.exists(output_path)
    mock_cv2["capture"].assert_called_once()
    mock_cv2["writer"].assert_called_once()

def test_convert_video_format(video_service, test_video, mock_cv2):
    """Test video format conversion"""
    output_path = video_service.convert_video_format(
        input_path=test_video,
        target_format="avi"
    )
    
    assert os.path.exists(output_path)
    assert output_path.endswith(".avi")
    mock_cv2["capture"].assert_called_once()
    mock_cv2["writer"].assert_called_once()

def test_create_video_from_frames(video_service, mock_cv2):
    """Test video creation from frames"""
    frames = [np.zeros((300, 300, 3)) for _ in range(30)]
    output_path = video_service.create_video_from_frames(
        frames=frames,
        fps=30,
        output_path="output.mp4"
    )
    
    assert os.path.exists(output_path)
    mock_cv2["writer"].assert_called_once()

def test_trim_video(video_service, test_video, mock_cv2):
    """Test video trimming"""
    output_path = video_service.trim_video(
        input_path=test_video,
        start_time=1.0,
        end_time=5.0
    )
    
    assert os.path.exists(output_path)
    mock_cv2["capture"].assert_called_once()
    mock_cv2["writer"].assert_called_once()

def test_concatenate_videos(video_service, test_video, mock_cv2):
    """Test video concatenation"""
    video_paths = [test_video, test_video]
    output_path = video_service.concatenate_videos(
        video_paths=video_paths,
        output_path="concatenated.mp4"
    )
    
    assert os.path.exists(output_path)
    assert mock_cv2["capture"].call_count == 2
    mock_cv2["writer"].assert_called_once()

def test_add_watermark(video_service, test_video, mock_cv2):
    """Test adding watermark to video"""
    watermark = Image.new('RGBA', (100, 50), (255, 255, 255, 128))
    output_path = video_service.add_watermark(
        input_path=test_video,
        watermark=watermark,
        position=(10, 10)
    )
    
    assert os.path.exists(output_path)
    mock_cv2["capture"].assert_called_once()
    mock_cv2["writer"].assert_called_once()

def test_extract_audio(video_service, test_video, mock_cv2):
    """Test audio extraction from video"""
    output_path = video_service.extract_audio(
        video_path=test_video,
        output_path="audio.mp3"
    )
    
    assert os.path.exists(output_path)
    mock_cv2["capture"].assert_called_once()

def test_handle_corrupted_video(video_service, test_video, mock_cv2):
    """Test handling of corrupted video"""
    mock_cv2["capture"].return_value.read.return_value = (False, None)
    
    with pytest.raises(VideoError):
        video_service.get_video_metadata(test_video)

def test_handle_large_video(video_service, test_video, mock_cv2):
    """Test handling of large video files"""
    mock_cv2["capture"].return_value.get.return_value = 1000000  # Large frame count
    
    with pytest.raises(VideoError):
        video_service.process_video(test_video)

def test_optimize_video_for_web(video_service, test_video, mock_cv2):
    """Test video optimization for web delivery"""
    output_path = video_service.optimize_video_for_web(
        input_path=test_video,
        target_quality="medium"
    )
    
    assert os.path.exists(output_path)
    mock_cv2["capture"].assert_called_once()
    mock_cv2["writer"].assert_called_once()

def test_create_video_preview(video_service, test_video, mock_cv2):
    """Test creating video preview"""
    preview = video_service.create_video_preview(
        video_path=test_video,
        duration=5.0
    )
    
    assert isinstance(preview, np.ndarray)
    mock_cv2["capture"].assert_called_once() 