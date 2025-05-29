import pytest
from unittest.mock import MagicMock, patch, mock_open, call, AsyncMock
import numpy as np
import cv2
import tempfile
import os
import asyncio # For running async methods if needed in tests, or mocking their sync counterparts
import subprocess

from app.services.video_processing_service import VideoProcessingService
from app.models.enums import ExerciseType
from app.core.config import Settings
from app.core.exceptions import VideoProcessingError, VideoValidationError, VideoReadError

@pytest.fixture
def mock_settings() -> MagicMock:
    settings = MagicMock(spec=Settings)
    settings.VIDEO_FRAME_RATE = 10
    settings.MAX_VIDEO_FRAMES = 50 # Example: Max 50 frames to be extracted by _extract_frames_sync
    settings.AI_TARGET_FRAME_WIDTH = 128
    settings.AI_TARGET_FRAME_HEIGHT = 128
    settings.FFMPEG_PATH = "ffmpeg" # Added FFMPEG_PATH
    settings.FFMPEG_TIMEOUT = 30 # Added FFMPEG_TIMEOUT
    settings.MAX_VIDEO_DURATION = 60 # Added MAX_VIDEO_DURATION (e.g., 60 seconds)
    # Mock exercise-specific frame selection if needed directly by a tested method
    # or assume the service initializes its own self.frame_selection_configs
    # For _select_key_frames, the service uses its internal config.
    return settings

@pytest.fixture
def video_processing_service(mock_settings: MagicMock) -> VideoProcessingService:
    service = VideoProcessingService(app_settings=mock_settings)
    return service

# Helper to create a dummy video file for testing purposes
def create_dummy_video_file(temp_dir_path: str, filename: str = "dummy.mp4", frame_count: int = 30, fps: int = 10, width: int = 200, height: int = 200) -> str:
    video_path = os.path.join(temp_dir_path, filename)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(video_path, fourcc, fps, (width, height))
    for _ in range(frame_count):
        frame = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
        out.write(frame)
    out.release()
    return video_path

@pytest.fixture
def mock_video_capture(self, monkeypatch):
    # This single mock instance will be configured by the returned function
    mock_cap_instance = MagicMock(spec=cv2.VideoCapture)
    
    # The actual VideoCapture constructor will return our single mock_cap_instance
    monkeypatch.setattr(cv2, "VideoCapture", lambda path_or_index: mock_cap_instance)

    def configure_mock(is_opened_val, frame_data_list, gets_map=None):
        mock_cap_instance.isOpened.return_value = is_opened_val
        
        read_outputs = []
        if frame_data_list: 
             for frame_np in frame_data_list:
                read_outputs.append((True, frame_np))
        read_outputs.append((False, None)) # End of video or error signal
        # Reset and set side_effect each time configure_mock is called
        mock_cap_instance.read.side_effect = read_outputs
        mock_cap_instance.read.reset_mock() # Ensure previous call counts don't interfere
        
        # Configure .get() carefully
        def get_side_effect(prop_id):
            if gets_map and prop_id in gets_map:
                return gets_map[prop_id]
            # It's crucial to define behavior for all CAP_PROP_ IDs used by the service
            # or ensure tests provide them. Returning 0 for unspecified might be problematic.
            # For now, let's make it explicit that tests should provide all needed props.
            if prop_id == cv2.CAP_PROP_FRAME_COUNT: return len(frame_data_list) # Default if not in gets_map
            if prop_id == cv2.CAP_PROP_FPS: return 0 # A common default that might indicate issues
            if prop_id == cv2.CAP_PROP_FRAME_WIDTH: return 0
            if prop_id == cv2.CAP_PROP_FRAME_HEIGHT: return 0
            return 0 # Default for other props
        
        mock_cap_instance.get.side_effect = get_side_effect
        mock_cap_instance.release = MagicMock()
        return mock_cap_instance # Return the instance for potential direct manipulation if needed, though not typical

    return configure_mock # Return the configurator function

class TestVideoProcessingService:
    def test_initialization(self, video_processing_service: VideoProcessingService, mock_settings: MagicMock):
        assert video_processing_service.settings == mock_settings
        assert video_processing_service.logger is not None
        assert video_processing_service.frame_rate == mock_settings.VIDEO_FRAME_RATE
        assert video_processing_service.max_frames == mock_settings.MAX_VIDEO_FRAMES
        assert video_processing_service.target_size == (mock_settings.AI_TARGET_FRAME_WIDTH, mock_settings.AI_TARGET_FRAME_HEIGHT)
        assert ExerciseType.SQUAT in video_processing_service.frame_selection_configs

    # Tests for _validate_video
    def test_validate_video_valid_file(self, video_processing_service: VideoProcessingService, mock_video_capture, tmp_path, mock_settings):
        """Test _validate_video with a mock valid video file."""
        num_dummy_frames = 300 # 30s video at 10fps, less than MAX_VIDEO_DURATION
        fps_val = 10
        width_val = 640
        height_val = 480
        dummy_frames = [np.random.randint(0, 255, (height_val, width_val, 3), dtype=np.uint8) for _ in range(num_dummy_frames)]
        mock_cv_props = {
            cv2.CAP_PROP_FRAME_COUNT: num_dummy_frames,
            cv2.CAP_PROP_FPS: fps_val,
            cv2.CAP_PROP_FRAME_WIDTH: width_val,
            cv2.CAP_PROP_FRAME_HEIGHT: height_val,
        }
        mock_video_capture(True, dummy_frames, mock_cv_props) 
        
        video_path = str(tmp_path / "valid.mp4") 
        is_valid, message, metadata = video_processing_service._validate_video(video_path)

        assert is_valid is True
        assert message is None
        assert metadata["actual_frame_count"] == num_dummy_frames
        assert metadata["fps"] == fps_val
        assert metadata["width"] == width_val
        assert metadata["height"] == height_val
        assert metadata["duration"] == num_dummy_frames / fps_val

    def test_validate_video_cannot_open(self, video_processing_service: VideoProcessingService, mock_video_capture, tmp_path):
        """Test _validate_video when VideoCapture cannot open the file."""
        # gets_map is not strictly needed here as isOpened=False is the primary check
        mock_video_capture(False, [], {}) 
        
        video_path = str(tmp_path / "cannot_open.mp4")
        is_valid, message, metadata = video_processing_service._validate_video(video_path)

        assert is_valid is False
        assert "Could not open video file (validation step)" in message 
        assert metadata is None

    def test_validate_video_zero_frames(self, video_processing_service: VideoProcessingService, mock_video_capture, tmp_path):
        """Test _validate_video with a video that has zero frames."""
        mock_cv_props = {cv2.CAP_PROP_FRAME_COUNT: 0, cv2.CAP_PROP_FPS: 10, cv2.CAP_PROP_FRAME_WIDTH: 640, cv2.CAP_PROP_FRAME_HEIGHT: 480}
        mock_video_capture(True, [], mock_cv_props) 

        video_path = str(tmp_path / "zero_frames.mp4")
        is_valid, message, metadata = video_processing_service._validate_video(video_path)

        assert is_valid is False
        assert "Video has zero FPS or zero frames" in message 
        assert metadata is None # Service code returns None for metadata in this case

    def test_validate_video_zero_fps(self, video_processing_service: VideoProcessingService, mock_video_capture, tmp_path):
        """Test _validate_video with a video that has zero FPS."""
        dummy_frames = [np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)]
        mock_cv_props = {cv2.CAP_PROP_FRAME_COUNT: 1, cv2.CAP_PROP_FPS: 0, cv2.CAP_PROP_FRAME_WIDTH: 640, cv2.CAP_PROP_FRAME_HEIGHT: 480}
        mock_video_capture(True, dummy_frames, mock_cv_props)

        video_path = str(tmp_path / "zero_fps.mp4")
        is_valid, message, metadata = video_processing_service._validate_video(video_path)

        assert is_valid is False
        assert "Video has zero FPS or zero frames" in message 
        assert metadata is None # Service code returns None for metadata here too

    def test_validate_video_resolution_too_low_width(self, video_processing_service: VideoProcessingService, mock_video_capture, tmp_path):
        mock_cv_props = {cv2.CAP_PROP_FRAME_COUNT: 100, cv2.CAP_PROP_FPS: 30, cv2.CAP_PROP_FRAME_WIDTH: 319, cv2.CAP_PROP_FRAME_HEIGHT: 240}
        mock_video_capture(True, [np.zeros((240,319,3), dtype=np.uint8)], mock_cv_props)
        video_path = str(tmp_path / "low_res_w.mp4")
        is_valid, message, metadata = video_processing_service._validate_video(video_path)
        assert is_valid is False
        assert message == "Video resolution too low"
        assert metadata is not None

    def test_validate_video_resolution_too_low_height(self, video_processing_service: VideoProcessingService, mock_video_capture, tmp_path):
        mock_cv_props = {cv2.CAP_PROP_FRAME_COUNT: 100, cv2.CAP_PROP_FPS: 30, cv2.CAP_PROP_FRAME_WIDTH: 320, cv2.CAP_PROP_FRAME_HEIGHT: 239}
        mock_video_capture(True, [np.zeros((239,320,3), dtype=np.uint8)], mock_cv_props)
        video_path = str(tmp_path / "low_res_h.mp4")
        is_valid, message, metadata = video_processing_service._validate_video(video_path)
        assert is_valid is False
        assert message == "Video resolution too low"
        assert metadata is not None

    def test_validate_video_fps_too_low(self, video_processing_service: VideoProcessingService, mock_video_capture, tmp_path):
        mock_cv_props = {cv2.CAP_PROP_FRAME_COUNT: 100, cv2.CAP_PROP_FPS: 9, cv2.CAP_PROP_FRAME_WIDTH: 640, cv2.CAP_PROP_FRAME_HEIGHT: 480}
        mock_video_capture(True, [np.zeros((480,640,3), dtype=np.uint8)], mock_cv_props)
        video_path = str(tmp_path / "low_fps.mp4")
        is_valid, message, metadata = video_processing_service._validate_video(video_path)
        assert is_valid is False
        assert message == "Frame rate too low (less than 10 FPS)"
        assert metadata is not None

    def test_validate_video_duration_too_long(self, video_processing_service: VideoProcessingService, mock_settings: MagicMock, mock_video_capture, tmp_path):
        fps_val = 30
        # Duration = (MAX_VIDEO_DURATION + 1) seconds
        num_frames = fps_val * (mock_settings.MAX_VIDEO_DURATION + 1)
        mock_cv_props = {cv2.CAP_PROP_FRAME_COUNT: num_frames, cv2.CAP_PROP_FPS: fps_val, cv2.CAP_PROP_FRAME_WIDTH: 640, cv2.CAP_PROP_FRAME_HEIGHT: 480}
        mock_video_capture(True, [np.zeros((480,640,3), dtype=np.uint8)], mock_cv_props)
        video_path = str(tmp_path / "long_vid.mp4")
        is_valid, message, metadata = video_processing_service._validate_video(video_path)
        assert is_valid is False
        assert message == f"Video duration exceeds {mock_settings.MAX_VIDEO_DURATION} seconds"
        assert metadata is not None

    def test_validate_video_metadata_collection(self, video_processing_service: VideoProcessingService, mock_video_capture, tmp_path):
        """Test _validate_video primarily for metadata collection even if validation passes."""
        num_dummy_frames = 50 # 5s @ 10fps
        fps_val = 10
        width_val = 320
        height_val = 240
        dummy_frames = [np.random.randint(0, 255, (height_val, width_val, 3), dtype=np.uint8) for _ in range(num_dummy_frames)] 
        mock_cv_props = {
            cv2.CAP_PROP_FRAME_COUNT: num_dummy_frames,
            cv2.CAP_PROP_FPS: fps_val,
            cv2.CAP_PROP_FRAME_WIDTH: width_val,
            cv2.CAP_PROP_FRAME_HEIGHT: height_val,
        }
        mock_video_capture(True, dummy_frames, mock_cv_props)
        video_path = str(tmp_path / "short_valid.mp4")

        is_valid, message, metadata = video_processing_service._validate_video(video_path)

        assert is_valid is True # Assumes no min_duration validation in _validate_video itself
        assert message is None
        assert metadata["actual_frame_count"] == num_dummy_frames
        assert metadata["fps"] == fps_val
        assert metadata["width"] == width_val
        assert metadata["height"] == height_val
        assert metadata["duration"] == num_dummy_frames / fps_val

    # Tests for _normalize_video_with_ffmpeg
    @patch("subprocess.run")
    def test_normalize_video_with_ffmpeg_success(self, mock_subprocess_run: MagicMock, video_processing_service: VideoProcessingService, tmp_path):
        mock_subprocess_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        input_path = str(tmp_path / "input.mp4")
        output_path = str(tmp_path / "output.mp4")
        target_fps = video_processing_service.settings.VIDEO_FRAME_RATE

        # Create a dummy input file, as FFmpeg might check for its existence depending on flags
        # For a pure unit test focused on command generation, this might not be strictly necessary
        # if FFmpeg itself isn't actually run. However, good for robustness.
        open(input_path, 'w').close() 

        result = video_processing_service._normalize_video_with_ffmpeg(input_path, output_path, target_fps)

        assert result is True
        # The vf_filter is a single string argument after "-vf"
        # Check if the actual command used by subprocess.run contains expected elements
        args, kwargs = mock_subprocess_run.call_args
        called_command_list = args[0]

        # Ensure -vf is present, then check the content of the filter string itself
        assert "-vf" in called_command_list
        vf_filter_index = called_command_list.index("-vf") + 1
        assert vf_filter_index < len(called_command_list) # Ensure there's an argument after -vf
        actual_vf_filter_string = called_command_list[vf_filter_index]

        assert f"fps={target_fps}" in actual_vf_filter_string
        assert f"scale={video_processing_service.settings.AI_TARGET_FRAME_WIDTH}:{video_processing_service.settings.AI_TARGET_FRAME_HEIGHT}" in actual_vf_filter_string
        assert "pad=" in actual_vf_filter_string # Basic check for padding

        # Check other essential parts that should be separate arguments
        expected_separate_parts = [
            video_processing_service.settings.FFMPEG_PATH,
            "-y", 
            "-i", input_path,
            "-an", 
            output_path 
        ]
        for part in expected_separate_parts:
            assert part in called_command_list

        mock_subprocess_run.assert_called_once()

    @patch("subprocess.run")
    def test_normalize_video_with_ffmpeg_failure(self, mock_subprocess_run: MagicMock, video_processing_service: VideoProcessingService, tmp_path, caplog):
        # Simulate FFmpeg command failure
        simulated_error = subprocess.CalledProcessError(returncode=1, cmd="ffmpeg ...", stderr="ffmpeg error")
        mock_subprocess_run.side_effect = simulated_error
        input_path = str(tmp_path / "input.mp4")
        output_path = str(tmp_path / "output.mp4")
        open(input_path, 'w').close()

        with pytest.raises(VideoProcessingError) as exc_info:
            video_processing_service._normalize_video_with_ffmpeg(input_path, output_path, 10)
        
        assert f"Subprocess error during FFmpeg execution: {simulated_error}" in str(exc_info.value)
        assert exc_info.value.__cause__ is simulated_error

        assert mock_subprocess_run.called # Ensure subprocess.run was actually called
        # Verify logs (optional, as exception is the primary check)
        # Example: assert "FFmpeg failed for" in caplog.text or "Subprocess error during FFmpeg" in caplog.text
        # Depending on which log you want to confirm specifically, given the service logs before raising.
        assert "Subprocess error during FFmpeg execution" in caplog.text # Check for the specific log before raising

    @patch("subprocess.run")
    def test_normalize_video_with_ffmpeg_command_construction(self, mock_subprocess_run: MagicMock, video_processing_service: VideoProcessingService, tmp_path):
        mock_subprocess_run.return_value = MagicMock(returncode=0)
        
        input_p = str(tmp_path / "in.mp4")
        output_p = str(tmp_path / "out.mp4")
        fps = 15
        open(input_p, 'w').close()

        video_processing_service._normalize_video_with_ffmpeg(input_p, output_p, fps)

        # Verify subprocess.run was called with a command list containing expected elements
        args, kwargs = mock_subprocess_run.call_args
        called_command_list = args[0]
        
        assert "-vf" in called_command_list
        vf_filter_index = called_command_list.index("-vf") + 1
        assert vf_filter_index < len(called_command_list)
        actual_vf_filter_string = called_command_list[vf_filter_index]

        assert f"fps={fps}" in actual_vf_filter_string # fps is part of the vf filter string
        # Check other essential parts
        expected_parts_in_list = [
            video_processing_service.settings.FFMPEG_PATH, 
            "-i", input_p, 
            output_p
        ]
        for part in expected_parts_in_list:
            assert part in called_command_list
        assert mock_subprocess_run.called_once()

    # Tests for _extract_frames_sync
    def test_extract_frames_sync_success(self, video_processing_service: VideoProcessingService, mock_video_capture, tmp_path):
        num_frames_to_simulate = 30
        simulated_frames = [np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8) for _ in range(num_frames_to_simulate)]
        
        # Configure the VideoCapture mock
        mock_video_capture(True, list(simulated_frames)) # Pass a copy for side_effect
        
        video_path = str(tmp_path / "extractable.mp4") # Path doesn't need to exist due to mock
        # ExerciseType.SQUAT is arbitrary here, _extract_frames_sync doesn't use it directly
        # but process_video does, so it's good practice to pass it.
        extracted_frames = video_processing_service._extract_frames_sync(video_path, ExerciseType.SQUAT)

        assert len(extracted_frames) == num_frames_to_simulate
        for i in range(num_frames_to_simulate):
            assert np.array_equal(extracted_frames[i], simulated_frames[i])

    def test_extract_frames_sync_max_frames_capping(self, video_processing_service: VideoProcessingService, mock_settings: MagicMock, mock_video_capture, tmp_path):
        num_frames_to_simulate = mock_settings.MAX_VIDEO_FRAMES + 20 # More frames than max_frames setting
        simulated_frames = [np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8) for _ in range(num_frames_to_simulate)]
        
        mock_video_capture(True, list(simulated_frames))
        video_path = str(tmp_path / "long_video.mp4")
        extracted_frames = video_processing_service._extract_frames_sync(video_path, ExerciseType.SQUAT)

        assert len(extracted_frames) == mock_settings.MAX_VIDEO_FRAMES

    def test_extract_frames_sync_cannot_open(self, video_processing_service: VideoProcessingService, mock_video_capture, tmp_path, caplog):
        # Pass gets_map even if not strictly needed by _extract_frames_sync, for consistency with fixture
        mock_video_capture(False, [], {cv2.CAP_PROP_FRAME_COUNT: 0}) 
        video_path = str(tmp_path / "unopenable.mp4")
        
        with pytest.raises(VideoReadError) as exc_info:
            video_processing_service._extract_frames_sync(video_path, ExerciseType.SQUAT)
        
        assert f"Could not open video file for frame extraction: {video_path}" in str(exc_info.value)
        # Ensure no frames were added to any internal list if it were to be checked.
        # Log message is not asserted here as the exception is the primary outcome.

    def test_extract_frames_sync_read_failure_midway(self, video_processing_service: VideoProcessingService, mock_video_capture, tmp_path, caplog):
        """Test when cap.read() returns False unexpectedly after some frames."""
        simulated_frames_part1 = [np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8) for _ in range(5)]
        # Configure read to return 5 good frames, then (False, None)
        read_outputs = [(True, frame) for frame in simulated_frames_part1] + [(False, None)]
        
        # We need to get the actual mock_cap instance to set its side_effect for read directly
        # The mock_video_capture fixture returns a configurator function.
        # So, we'll patch cv2.VideoCapture for this specific test differently.
        with patch("cv2.VideoCapture") as mock_vc_constructor:
            mock_cap_instance = MagicMock()
            mock_cap_instance.isOpened.return_value = True
            mock_cap_instance.read.side_effect = read_outputs
            mock_cap_instance.get.return_value = 0 # Default for any other .get calls
            mock_cap_instance.release = MagicMock()
            mock_vc_constructor.return_value = mock_cap_instance

            video_path = str(tmp_path / "read_fail.mp4")
            extracted_frames = video_processing_service._extract_frames_sync(video_path, ExerciseType.SQUAT)

            assert len(extracted_frames) == 5
            # No specific error log in _extract_frames_sync for cap.read() returning False, it just stops.
            # The method is expected to simply return the frames successfully read up to that point.

    # Tests for _select_key_frames
    def test_select_key_frames_squat_sufficient_frames(self, video_processing_service: VideoProcessingService):
        input_frames = [np.random.rand(10,10,3) for _ in range(100)] # 100 frames
        # SQUAT expects 5 key frames from frame_selection_configs
        selected = video_processing_service._select_key_frames(input_frames, ExerciseType.SQUAT)
        assert len(selected) == 5
        # Check if indices are somewhat distributed (exact indices depend on np.linspace)
        # This is a basic check; more precise index checking might be too brittle if np.linspace behavior changes subtly.
        assert np.array_equal(selected[0], input_frames[0]) # First frame
        assert np.array_equal(selected[4], input_frames[99]) # Last frame

    def test_select_key_frames_plank_sufficient_frames(self, video_processing_service: VideoProcessingService):
        input_frames = [np.random.rand(10,10,3) for _ in range(50)] # 50 frames
        # PLANK expects 3 key frames
        selected = video_processing_service._select_key_frames(input_frames, ExerciseType.PLANK)
        assert len(selected) == 3
        assert np.array_equal(selected[0], input_frames[0])
        assert np.array_equal(selected[2], input_frames[49])

    def test_select_key_frames_fewer_frames_than_desired(self, video_processing_service: VideoProcessingService):
        input_frames = [np.random.rand(10,10,3) for _ in range(3)] # 3 frames
        # SQUAT normally wants 5, but should return all 3
        selected = video_processing_service._select_key_frames(input_frames, ExerciseType.SQUAT)
        assert len(selected) == 3
        assert np.array_equal(selected[0], input_frames[0])
        assert np.array_equal(selected[1], input_frames[1])
        assert np.array_equal(selected[2], input_frames[2])

    def test_select_key_frames_exact_frames_as_desired(self, video_processing_service: VideoProcessingService):
        input_frames = [np.random.rand(10,10,3) for _ in range(5)] # 5 frames
        selected = video_processing_service._select_key_frames(input_frames, ExerciseType.SQUAT)
        assert len(selected) == 5
        for i in range(5):
            assert np.array_equal(selected[i], input_frames[i])

    def test_select_key_frames_empty_input(self, video_processing_service: VideoProcessingService):
        input_frames = []
        selected = video_processing_service._select_key_frames(input_frames, ExerciseType.SQUAT)
        assert len(selected) == 0

    def test_select_key_frames_unknown_exercise_type(self, video_processing_service: VideoProcessingService, caplog):
        input_frames = [np.random.rand(10,10,3) for _ in range(10)]
        
        # To robustly test the default path when an exercise_type is not in frame_selection_configs,
        # we mock the .get() method of that dictionary for this specific test.
        # The default config used by the service is {"frame_count": 1}
        default_config_val = {"frame_count": 1} # This is what the service code uses as default
        unknown_exercise_type_key = "THIS_IS_A_TOTALLY_UNKNOWN_KEY"

        with patch.dict(video_processing_service.frame_selection_configs, {}, clear=True): # Temporarily empty the dict
            # Or, more targeted, mock the get method if the dict is complex / shared state
            # For this case, an empty dict + ensuring the key isn't there is simpler.
            # The service uses .get(exercise_type, {"frame_count": 1}), so if key not present, it uses the default.
            
            # Re-populate with a config that does NOT include our unknown_exercise_type_key
            video_processing_service.frame_selection_configs[ExerciseType.SQUAT] = {"frame_count": 5} # Example

            selected = video_processing_service._select_key_frames(input_frames, unknown_exercise_type_key) # Pass the string key
            # If config is not found (service uses .get(key) without a default in current version for the primary lookup),
            # it logs "No frame selection config for..." and returns all original frames.
            assert f"No frame selection config for {unknown_exercise_type_key}, returning all frames." in caplog.text
            assert len(selected) == len(input_frames) # Should return all input frames
            if input_frames: # Ensure content check only if there are frames
                 assert np.array_equal(selected[0], input_frames[0]) # First frame as a basic check
                 assert np.array_equal(selected[-1], input_frames[-1]) # Last frame as a basic check

    # Tests for _preprocess_frames
    @patch("cv2.resize")
    @patch("cv2.cvtColor")
    def test_preprocess_frames_success(self, mock_cv2_cvtColor: MagicMock, mock_cv2_resize: MagicMock, video_processing_service: VideoProcessingService, mock_settings: MagicMock):
        # Create a list of mock frames (np.ndarray)
        input_frames_data = [
            np.random.randint(0, 255, (200, 300, 3), dtype=np.uint8),
            np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
        ]
        
        target_w, target_h = mock_settings.AI_TARGET_FRAME_WIDTH, mock_settings.AI_TARGET_FRAME_HEIGHT
        resized_frame_template = np.random.randint(0, 255, (target_h, target_w, 3), dtype=np.uint8)
        
        # Configure mocks
        mock_cv2_resize.side_effect = [resized_frame_template.copy() for _ in input_frames_data]
        # cvtColor should return an ndarray that .astype can be called on.
        # For this test, the exact color conversion isn't critical, just the type and shape flow.
        mock_cv2_cvtColor.side_effect = lambda frame, code: frame.copy() # Pass through for simplicity

        processed_frames = video_processing_service._preprocess_frames(input_frames_data)

        assert len(processed_frames) == len(input_frames_data)
        assert mock_cv2_resize.call_count == len(input_frames_data)
        assert mock_cv2_cvtColor.call_count == len(input_frames_data) # cvtColor is called for each frame

        for i, original_frame in enumerate(input_frames_data):
            # Check resize was called correctly for this frame
            resize_call = mock_cv2_resize.call_args_list[i]
            resize_call_args = resize_call.args # Access positional args via .args
            resize_call_kwargs = resize_call.kwargs # Access keyword args via .kwargs

            assert np.array_equal(resize_call_args[0], original_frame) 
            assert resize_call_args[1] == (target_w, target_h)     

            # Check the output frame properties
            processed_frame = processed_frames[i]
            assert processed_frame.shape == (target_h, target_w, 3)
            assert processed_frame.dtype == np.float32
            assert np.all(processed_frame >= 0) and np.all(processed_frame <= 1.0) # Normalized
            
            # Check that the output frame came from the mocked resize output (after normalization)
            # This means the mocked resized_frame_template (0-255) divided by 255.0 should match processed_frame
            expected_normalized_frame = (resized_frame_template / 255.0).astype(np.float32)
            assert np.allclose(processed_frame, expected_normalized_frame) 

    def test_preprocess_frames_empty_input(self, video_processing_service: VideoProcessingService):
        processed_frames = video_processing_service._preprocess_frames([])
        assert len(processed_frames) == 0

    # Tests for process_video (orchestration)
    @pytest.mark.asyncio
    @patch.object(VideoProcessingService, "_normalize_video_with_ffmpeg", new_callable=MagicMock)
    @patch.object(VideoProcessingService, "_validate_video", new_callable=MagicMock)
    @patch.object(VideoProcessingService, "_extract_frames_sync", new_callable=MagicMock)
    @patch.object(VideoProcessingService, "_select_key_frames", new_callable=MagicMock)
    @patch.object(VideoProcessingService, "_preprocess_frames", new_callable=MagicMock)
    @patch("cv2.imwrite")
    @patch("app.services.video_processing_service.tempfile.TemporaryDirectory")
    @patch("app.services.video_processing_service.open", new_callable=mock_open)
    @patch("app.services.video_processing_service.os.path.exists")
    @patch("app.services.video_processing_service.os.makedirs")
    async def test_process_video_success_no_save(
        self, 
        mock_os_makedirs: MagicMock, # Corresponds to os.makedirs
        mock_os_path_exists: MagicMock, # Corresponds to os.path.exists
        mock_builtin_open: MagicMock, # Corresponds to open
        mock_temp_dir: MagicMock, # Corresponds to tempfile.TemporaryDirectory
        mock_cv2_imwrite: MagicMock, # Corresponds to cv2.imwrite
        mock_preprocess_frames: MagicMock, # Corresponds to _preprocess_frames
        mock_select_keyframes: MagicMock, # Corresponds to _select_key_frames
        mock_extract_frames: MagicMock, # Corresponds to _extract_frames_sync
        mock_validate_video: MagicMock, # Corresponds to _validate_video
        mock_normalize_ffmpeg: MagicMock, # Corresponds to _normalize_video_with_ffmpeg
        video_processing_service: VideoProcessingService, 
        mock_settings: MagicMock
    ):
        mock_temp_dir.return_value.__enter__.return_value = "/mock/temp/dir"
        video_data = b"dummy video data"
        exercise_type = ExerciseType.SQUAT
    
        mock_normalize_ffmpeg.return_value = True 
        mock_validate_video.return_value = (True, None, {"fps": 10, "actual_frame_count": 30, "width": 640, "height": 480, "duration": 3.0})
        mock_extracted_np_frames = [np.random.rand(10,10,3) for _ in range(10)]
        mock_extract_frames.return_value = mock_extracted_np_frames
        mock_selected_np_frames = [np.random.rand(10,10,3) for _ in range(5)]
        mock_select_keyframes.return_value = mock_selected_np_frames
        mock_processed_np_frames = [(np.random.rand(mock_settings.AI_TARGET_FRAME_HEIGHT, mock_settings.AI_TARGET_FRAME_WIDTH, 3)).astype(np.float32) for _ in range(5)]
        mock_preprocess_frames.return_value = mock_processed_np_frames
    
        result = await video_processing_service.process_video(video_data, exercise_type, save_processed_frames=False)
    
        assert result["frame_paths"] is not None
        assert len(result["frame_paths"]) == len(mock_processed_np_frames)
        for i, frame_res in enumerate(result["frame_paths"]):
            assert np.array_equal(frame_res, mock_processed_np_frames[i])
        assert result["frame_count"] == len(mock_processed_np_frames)
        
        mock_builtin_open.assert_called_once_with("/mock/temp/dir/input_video.mp4", 'wb')
        mock_normalize_ffmpeg.assert_called_once()
        mock_validate_video.assert_called_once()
        mock_extract_frames.assert_called_once()
        mock_select_keyframes.assert_called_once()
        mock_preprocess_frames.assert_called_once()
        mock_cv2_imwrite.assert_not_called() # Not called when save_processed_frames=False
        mock_os_makedirs.assert_not_called()
        mock_os_path_exists.assert_not_called() # Not called when save_processed_frames=False or base_output_path is None

    @pytest.mark.asyncio
    @patch.object(VideoProcessingService, "_normalize_video_with_ffmpeg", new_callable=MagicMock)
    @patch.object(VideoProcessingService, "_validate_video", new_callable=MagicMock)
    @patch.object(VideoProcessingService, "_extract_frames_sync", new_callable=MagicMock)
    @patch.object(VideoProcessingService, "_select_key_frames", new_callable=MagicMock)
    @patch.object(VideoProcessingService, "_preprocess_frames", new_callable=MagicMock)
    @patch("cv2.imwrite") 
    @patch("app.services.video_processing_service.tempfile.TemporaryDirectory")
    @patch("app.services.video_processing_service.open", new_callable=mock_open)
    @patch("app.services.video_processing_service.os.path.exists")
    @patch("app.services.video_processing_service.os.makedirs")
    async def test_process_video_success_with_save(
        self, 
        mock_os_makedirs: MagicMock, 
        mock_os_path_exists: MagicMock, 
        mock_builtin_open: MagicMock, 
        mock_temp_dir: MagicMock, 
        mock_cv2_imwrite: MagicMock, 
        mock_preprocess_frames: MagicMock, 
        mock_select_keyframes: MagicMock, 
        mock_extract_frames: MagicMock, 
        mock_validate_video: MagicMock, 
        mock_normalize_ffmpeg: MagicMock, 
        video_processing_service: VideoProcessingService,
        mock_settings: MagicMock # Added mock_settings here
    ):
        mock_temp_dir.return_value.__enter__.return_value = "/mock/temp/dir"
        video_data = b"dummy video data"
        exercise_type = ExerciseType.PUSH_UP
        base_output_path = "/mock/output/frames_dir"

        mock_normalize_ffmpeg.return_value = True
        mock_validate_video.return_value = (True, None, {"fps": 10, "actual_frame_count": 20, "width": 640, "height": 480, "duration": 2.0})
        mock_extracted_frames_val = [np.random.rand(10,10,3)] * 5 
        mock_extract_frames.return_value = mock_extracted_frames_val
        mock_selected_frames_val = [np.random.rand(10,10,3)] * 3
        mock_select_keyframes.return_value = mock_selected_frames_val
        
        # Simulate what _preprocess_frames would output (float32 RGB 0-1)
        # And what would be passed to cv2.imwrite (uint8 BGR 0-255)
        preprocessed_float_frames = [(np.random.rand(mock_settings.AI_TARGET_FRAME_HEIGHT, mock_settings.AI_TARGET_FRAME_WIDTH, 3)).astype(np.float32) for _ in range(3)]
        mock_preprocess_frames.return_value = preprocessed_float_frames
        
        expected_saved_frame_paths = [os.path.join(base_output_path, f"frame_{i:04d}.png") for i in range(len(preprocessed_float_frames))]
        
        mock_os_path_exists.return_value = False 

        result = await video_processing_service.process_video(video_data, exercise_type, save_processed_frames=True, base_output_path=base_output_path)

        mock_os_path_exists.assert_called_once_with(base_output_path)
        mock_os_makedirs.assert_called_once_with(base_output_path, exist_ok=True)
        
        assert mock_cv2_imwrite.call_count == len(preprocessed_float_frames)
        for i, call_args in enumerate(mock_cv2_imwrite.call_args_list):
            saved_path_arg = call_args[0][0]
            saved_img_arg = call_args[0][1]
            assert saved_path_arg == expected_saved_frame_paths[i]
            
            # Reconstruct what would be passed to cv2.imwrite from preprocessed_float_frames
            frame_array_rgb_float = preprocessed_float_frames[i]
            img_to_save_uint8_rgb = (frame_array_rgb_float * 255).astype(np.uint8)
            # We cannot easily mock the internal cv2.cvtColor to BGR, 
            # so we check shape and dtype of the saved image.
            assert saved_img_arg.shape == img_to_save_uint8_rgb.shape 
            assert saved_img_arg.dtype == np.uint8

        assert result["frame_paths"] == expected_saved_frame_paths
        assert result["frame_count"] == len(expected_saved_frame_paths)
        assert result.get("frames_data") is None # No data in memory when saving

    @pytest.mark.asyncio
    async def test_process_video_empty_data(self, video_processing_service: VideoProcessingService):
        with pytest.raises(VideoReadError, match="Input video data is empty."):
            await video_processing_service.process_video(b"", ExerciseType.SQUAT)

    @pytest.mark.asyncio
    @patch("app.services.video_processing_service.tempfile.TemporaryDirectory")
    @patch("app.services.video_processing_service.open", new_callable=mock_open)
    async def test_process_video_temp_file_write_error(self, mock_file_open: MagicMock, mock_temp_dir: MagicMock, video_processing_service: VideoProcessingService):
        mock_temp_dir.return_value.__enter__.return_value = "/mock/temp/dir"
        mock_file_open.return_value.write.side_effect = IOError("Disk full")
        video_data = b"some data"

        with pytest.raises(VideoProcessingError, match="Could not write temporary video file: Disk full"):
            await video_processing_service.process_video(video_data, ExerciseType.SQUAT)

    @pytest.mark.asyncio
    @patch.object(VideoProcessingService, "_normalize_video_with_ffmpeg", new_callable=MagicMock)
    @patch("app.services.video_processing_service.tempfile.TemporaryDirectory")
    @patch("app.services.video_processing_service.open", new_callable=mock_open)
    async def test_process_video_ffmpeg_failure(
        self, 
        mock_builtin_open: MagicMock, 
        mock_temp_dir: MagicMock, 
        mock_normalize_ffmpeg: MagicMock, 
        video_processing_service: VideoProcessingService, 
        mock_settings # mock_settings is from the class fixture, not a patch for this test
    ):
        mock_temp_dir.return_value.__enter__.return_value = "/mock/temp/dir"
        video_data = b"good data"
        mock_normalize_ffmpeg.return_value = False # Simulate FFmpeg failure

        with pytest.raises(VideoProcessingError, match="FFmpeg normalization failed"):
            await video_processing_service.process_video(video_data, ExerciseType.SQUAT)
        
        mock_builtin_open.assert_called_once()
        mock_normalize_ffmpeg.assert_called_once()

    @pytest.mark.asyncio
    @patch.object(VideoProcessingService, "_normalize_video_with_ffmpeg", new_callable=MagicMock)
    @patch.object(VideoProcessingService, "_validate_video", new_callable=MagicMock)
    @patch("app.services.video_processing_service.tempfile.TemporaryDirectory")
    @patch("app.services.video_processing_service.open", new_callable=mock_open)
    async def test_process_video_validation_failure(
        self, 
        mock_builtin_open: MagicMock, 
        mock_temp_dir: MagicMock, 
        mock_validate_video: MagicMock, 
        mock_normalize_ffmpeg: MagicMock, 
        video_processing_service: VideoProcessingService
    ):
        mock_temp_dir.return_value.__enter__.return_value = "/mock/temp/dir"
        video_data = b"good data"
        mock_normalize_ffmpeg.return_value = True # Normalization succeeds
        mock_validate_video.return_value = (False, "Validation failed message", None) # Validation fails

        with pytest.raises(VideoValidationError, match="Validation failed message"):
            await video_processing_service.process_video(video_data, ExerciseType.BENCH_PRESS)
        
        mock_normalize_ffmpeg.assert_called_once()
        mock_validate_video.assert_called_once()

    @pytest.mark.asyncio
    @patch.object(VideoProcessingService, "_normalize_video_with_ffmpeg", new_callable=MagicMock)
    @patch.object(VideoProcessingService, "_validate_video", new_callable=MagicMock)
    @patch.object(VideoProcessingService, "_extract_frames_sync", new_callable=MagicMock)
    @patch("app.services.video_processing_service.tempfile.TemporaryDirectory")
    @patch("app.services.video_processing_service.open", new_callable=mock_open)
    async def test_process_video_no_frames_extracted(
        self, 
        mock_builtin_open: MagicMock, 
        mock_temp_dir: MagicMock, 
        mock_extract_frames: MagicMock, 
        mock_validate_video: MagicMock, 
        mock_normalize_ffmpeg: MagicMock, 
        video_processing_service: VideoProcessingService
    ):
        mock_temp_dir.return_value.__enter__.return_value = "/mock/temp/dir"
        video_data = b"good data"
        mock_normalize_ffmpeg.return_value = True
        mock_validate_video.return_value = (True, None, {"fps": 10, "actual_frame_count": 30})
        mock_extract_frames.return_value = [] # No frames extracted

        # Match the wrapped message from the general exception handler in process_video
        expected_message_regex = r"An unexpected error occurred during video processing: No frames could be extracted from the video\."
        with pytest.raises(VideoProcessingError, match=expected_message_regex):
            await video_processing_service.process_video(video_data, ExerciseType.DEADLIFT)
        
        mock_extract_frames.assert_called_once()

    @pytest.mark.asyncio
    @patch.object(VideoProcessingService, "_normalize_video_with_ffmpeg", new_callable=MagicMock)
    @patch.object(VideoProcessingService, "_validate_video", new_callable=MagicMock)
    @patch.object(VideoProcessingService, "_extract_frames_sync", new_callable=MagicMock)
    @patch.object(VideoProcessingService, "_select_key_frames", new_callable=MagicMock)
    @patch("app.services.video_processing_service.tempfile.TemporaryDirectory")
    @patch("app.services.video_processing_service.open", new_callable=mock_open)
    async def test_process_video_no_keyframes_selected(
        self, 
        mock_builtin_open: MagicMock, 
        mock_temp_dir: MagicMock, 
        mock_select_keyframes: MagicMock, 
        mock_extract_frames: MagicMock, 
        mock_validate_video: MagicMock, 
        mock_normalize_ffmpeg: MagicMock, 
        video_processing_service: VideoProcessingService
    ):
        mock_temp_dir.return_value.__enter__.return_value = "/mock/temp/dir"
        video_data = b"good data"
        mock_normalize_ffmpeg.return_value = True
        mock_validate_video.return_value = (True, None, {"fps": 10, "actual_frame_count": 30})
        mock_extract_frames.return_value = [np.random.rand(10,10,3)] # Some frames extracted
        mock_select_keyframes.return_value = [] # No keyframes selected

        # Match the wrapped message from the general exception handler in process_video
        expected_message_regex = r"An unexpected error occurred during video processing: No key frames could be selected from the extracted frames\."
        with pytest.raises(VideoProcessingError, match=expected_message_regex):
            await video_processing_service.process_video(video_data, ExerciseType.OVERHEAD_PRESS)
        
        mock_select_keyframes.assert_called_once()

    @pytest.mark.asyncio
    @patch.object(VideoProcessingService, "_normalize_video_with_ffmpeg", new_callable=MagicMock)
    @patch.object(VideoProcessingService, "_validate_video", new_callable=MagicMock)
    @patch.object(VideoProcessingService, "_extract_frames_sync", new_callable=MagicMock)
    @patch.object(VideoProcessingService, "_select_key_frames", new_callable=MagicMock)
    @patch.object(VideoProcessingService, "_preprocess_frames", new_callable=MagicMock)
    @patch("app.services.video_processing_service.tempfile.TemporaryDirectory")
    @patch("app.services.video_processing_service.open", new_callable=mock_open)
    async def test_process_video_normalization_skipped(
        self, 
        mock_builtin_open: MagicMock, 
        mock_temp_dir: MagicMock, 
        mock_preprocess_frames: MagicMock, 
        mock_select_keyframes: MagicMock, 
        mock_extract_frames: MagicMock, 
        mock_validate_video: MagicMock, 
        mock_normalize_ffmpeg: MagicMock, 
        video_processing_service: VideoProcessingService, 
        mock_settings: MagicMock
    ):
        mock_temp_dir.return_value.__enter__.return_value = "/mock/temp/dir" 
        video_data = b"dummy video data"
        exercise_type = ExerciseType.SQUAT

        original_frame_rate = video_processing_service.frame_rate
        video_processing_service.frame_rate = 0 # Explicitly skip normalization
        mock_settings.VIDEO_FRAME_RATE = 0 # Also update mock_settings if service re-reads it, though service init is usually once

        mock_validate_video.return_value = (True, None, {"fps": 30, "actual_frame_count": 300}) 
        mock_extracted_frames_val = [np.random.rand(10,10,3)] * 10
        mock_extract_frames.return_value = mock_extracted_frames_val
        mock_selected_frames_val = [np.random.rand(10,10,3)] * 5
        mock_select_keyframes.return_value = mock_selected_frames_val
        mock_processed_frames_val = [(np.random.rand(10,10,3)).astype(np.float32)] * 5
        mock_preprocess_frames.return_value = mock_processed_frames_val

        result = await video_processing_service.process_video(video_data, exercise_type, save_processed_frames=False)

        mock_normalize_ffmpeg.assert_not_called() # Crucial check
        mock_validate_video.assert_called_once() # Should use temp_video_path for validation
        assert len(result["frame_paths"]) == len(mock_processed_frames_val)

        video_processing_service.frame_rate = original_frame_rate # Restore

    # Example of a more complex fixture if needed later
    @pytest.fixture
    def mock_video_capture(self, monkeypatch):
        # This single mock instance will be configured by the returned function
        mock_cap_instance = MagicMock(spec=cv2.VideoCapture)
        
        # The actual VideoCapture constructor will return our single mock_cap_instance
        monkeypatch.setattr(cv2, "VideoCapture", lambda path_or_index: mock_cap_instance)

        def configure_mock(is_opened_val, frame_data_list, gets_map=None):
            mock_cap_instance.isOpened.return_value = is_opened_val
            
            read_outputs = []
            if frame_data_list: 
                 for frame_np in frame_data_list:
                    read_outputs.append((True, frame_np))
            read_outputs.append((False, None)) # End of video or error signal
            # Reset and set side_effect each time configure_mock is called
            mock_cap_instance.read.side_effect = read_outputs
            mock_cap_instance.read.reset_mock() # Ensure previous call counts don't interfere
            
            # Configure .get() carefully
            def get_side_effect(prop_id):
                if gets_map and prop_id in gets_map:
                    return gets_map[prop_id]
                # It's crucial to define behavior for all CAP_PROP_ IDs used by the service
                # or ensure tests provide them. Returning 0 for unspecified might be problematic.
                # For now, let's make it explicit that tests should provide all needed props.
                if prop_id == cv2.CAP_PROP_FRAME_COUNT: return len(frame_data_list) # Default if not in gets_map
                if prop_id == cv2.CAP_PROP_FPS: return 0 # A common default that might indicate issues
                if prop_id == cv2.CAP_PROP_FRAME_WIDTH: return 0
                if prop_id == cv2.CAP_PROP_FRAME_HEIGHT: return 0
                return 0 # Default for other props
            
            mock_cap_instance.get.side_effect = get_side_effect
            mock_cap_instance.release = MagicMock()
            return mock_cap_instance # Return the instance for potential direct manipulation if needed, though not typical

        return configure_mock # Return the configurator function 