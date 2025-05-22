import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock, call
import numpy as np
import cv2
from app.services.ai_service import AIService
from app.models.enums import ExerciseType
import torch
import json
from app.core.config import Settings
from app.core.config import settings as app_settings

# This is a placeholder for the actual AIService.
# We will need to import the actual service.
# For example:
# from backend.app.services.ai_service import AIService

# Placeholder class to allow tests to be structured
class AIServicePlaceholder:
    def process_frames_for_pose(self, frame_paths):
        # This method will be mocked in tests
        pass

    def smooth_and_interpolate_poses(self, poses, max_gap_to_interpolate=5, smoothing_window_size=5):
        # This method will be mocked or tested individually
        pass

    def _interpolate_landmark(self, prev_landmark_data, next_landmark_data, prev_frame_idx, next_frame_idx, current_frame_idx):
        # This method will be mocked or tested individually
        pass

class TestAIService:
    @pytest.fixture
    def mock_ai_service(self):
        """Fixture to create a MagicMock instance of AIService."""
        service_mock = MagicMock(spec=AIServicePlaceholder)
        return service_mock

    @pytest.fixture
    def ai_service_instance(self):
        """Fixture to create a real instance of AIService for testing its methods."""
        # Replace AIServicePlaceholder with the actual class when available
        return AIServicePlaceholder()

    def test_initial_setup_passing(self):
        """A simple test to confirm the test file and pytest are working."""
        assert True

# We will now begin adding tests for AIService as per the plan.
# First, tests for `process_frames_for_pose` method.

@pytest.fixture
def mock_model():
    """Mock PyTorch model"""
    model = Mock()
    model.eval = Mock(return_value=model)
    model.to = Mock(return_value=model)
    model.forward = Mock(return_value=torch.tensor([0.8, 0.9, 0.7]))
    return model

@pytest.fixture
def mock_pose_estimator():
    """Mock pose estimation model"""
    estimator = Mock()
    estimator.process = Mock(return_value={
        "pose_landmarks": [
            {"x": 0.5, "y": 0.5, "z": 0.0, "visibility": 0.9}
            for _ in range(33)  # MediaPipe uses 33 landmarks
        ]
    })
    return estimator

@pytest.fixture
def mock_settings() -> MagicMock:
    """Provides a mock Settings object for AIService tests."""
    settings = MagicMock(spec=Settings)
    # Add any specific setting attributes AIService might use, e.g.:
    # settings.AI_MODEL_CONFIDENCE_THRESHOLD = 0.7
    # settings.MAX_FRAMES_FOR_POSE_ESTIMATION = 500
    return settings

@pytest.fixture
def mock_settings_for_ai_service(monkeypatch) -> MagicMock:
    """Patches the global app_settings AIService uses."""
    monkeypatch.setattr(app_settings, 'AI_MODEL_COMPLEXITY', 1)
    monkeypatch.setattr(app_settings, 'AI_MIN_DETECTION_CONFIDENCE', 0.5)
    monkeypatch.setattr(app_settings, 'AI_MIN_TRACKING_CONFIDENCE', 0.5)
    monkeypatch.setattr(app_settings, 'AI_MODEL_PATH', './mock_models') 
    monkeypatch.setattr(app_settings, 'AI_POSE_SMOOTHING_WINDOW_SIZE', 5) 
    monkeypatch.setattr(app_settings, 'AI_POSE_MAX_INTERPOLATION_GAP', 3) 
    return app_settings

@pytest.fixture
def ai_service(mock_settings_for_ai_service, monkeypatch) -> AIService:
    """Provides an instance of AIService with MediaPipe and model loading mocked.
    AIService.__init__ takes no arguments and uses global app_settings.
    """
    # mock_settings_for_ai_service fixture ensures global app_settings are patched.
    
    mock_mp_pose_instance = MagicMock()
    mock_mediapipe_results_object = MagicMock()
    mock_mediapipe_results_object.pose_landmarks = None 
    mock_mp_pose_instance.process.return_value = mock_mediapipe_results_object
    # Patch where AIService looks for mp.solutions.pose.Pose
    monkeypatch.setattr('app.services.ai_service.mp.solutions.pose.Pose', lambda *args, **kwargs: mock_mp_pose_instance)

    mock_loaded_torch_model = MagicMock()
    mock_loaded_torch_model.eval.return_value = mock_loaded_torch_model 
    monkeypatch.setattr(AIService, '_load_form_analysis_model', lambda self: mock_loaded_torch_model)
    
    service = AIService() # AIService uses patched global settings
    return service

@pytest.fixture
def test_video():
    """Create a mock video for testing"""
    video = np.zeros((300, 300, 3), dtype=np.uint8)  # Create blank frame
    return [video for _ in range(30)]  # 30 frames

@pytest.fixture
def sample_frame_paths() -> list[str]:
    return ["/mock/path/frame1.jpg", "/mock/path/frame2.jpg"]

@pytest.fixture
def sample_image_data() -> list[np.ndarray]:
    frame1 = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    frame2 = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    return [frame1, frame2]

def test_initialize_models(ai_service):
    """Test model initialization"""
    assert ai_service.models is not None
    assert all(model is not None for model in ai_service.models.values())
    assert ai_service.pose_estimator is not None

def test_analyze_form_squat(ai_service, test_video):
    """Test form analysis for squat exercise"""
    result = ai_service.analyze_form(
        video=test_video,
        exercise_type=ExerciseType.SQUAT
    )
    
    assert isinstance(result, dict)
    assert "score" in result
    assert "overall_feedback" in result
    assert "issues" in result
    assert isinstance(result["issues"], list)

def test_analyze_form_deadlift(ai_service, test_video):
    """Test form analysis for deadlift exercise"""
    result = ai_service.analyze_form(
        video=test_video,
        exercise_type=ExerciseType.DEADLIFT
    )
    
    assert isinstance(result, dict)
    assert "score" in result
    assert 0 <= result["score"] <= 10

def test_analyze_form_invalid_exercise(ai_service, test_video):
    """Test form analysis with invalid exercise type"""
    with pytest.raises(AIServiceError):
        ai_service.analyze_form(
            video=test_video,
            exercise_type="INVALID_EXERCISE"
        )

def test_extract_frames(ai_service, test_video):
    """Test video frame extraction"""
    frames = ai_service._extract_frames(test_video)
    
    assert isinstance(frames, list)
    assert len(frames) > 0
    assert all(isinstance(frame, np.ndarray) for frame in frames)

def test_preprocess_video(ai_service, test_video):
    """Test video preprocessing"""
    processed_frames = ai_service._preprocess_video(test_video)
    
    assert isinstance(processed_frames, torch.Tensor)
    assert processed_frames.dim() == 4  # [batch, channels, height, width]
    assert processed_frames.dtype == torch.float32

def test_extract_pose_landmarks(ai_service, test_video):
    """Test pose landmark extraction"""
    landmarks = ai_service._extract_pose_landmarks(test_video[0])
    
    assert isinstance(landmarks, list)
    assert len(landmarks) == 33  # MediaPipe uses 33 landmarks
    assert all("x" in point and "y" in point for point in landmarks)

def test_analyze_pose_sequence(ai_service, test_video):
    """Test pose sequence analysis"""
    landmarks_sequence = [
        ai_service._extract_pose_landmarks(frame)
        for frame in test_video[:10]
    ]
    
    analysis = ai_service._analyze_pose_sequence(
        landmarks_sequence,
        ExerciseType.SQUAT
    )
    
    assert isinstance(analysis, dict)
    assert "score" in analysis
    assert "issues" in analysis

def test_generate_feedback(ai_service):
    """Test feedback generation"""
    mock_analysis = {
        "score": 8.5,
        "issues": [
            {"frame": 10, "type": "knee_valgus", "severity": 0.7},
            {"frame": 20, "type": "back_rounding", "severity": 0.8}
        ]
    }
    
    feedback = ai_service._generate_feedback(
        mock_analysis,
        ExerciseType.SQUAT
    )
    
    assert isinstance(feedback, str)
    assert len(feedback) > 0

def test_detect_exercise_phases(ai_service, test_video):
    """Test exercise phase detection"""
    landmarks_sequence = [
        ai_service._extract_pose_landmarks(frame)
        for frame in test_video
    ]
    
    phases = ai_service._detect_exercise_phases(
        landmarks_sequence,
        ExerciseType.SQUAT
    )
    
    assert isinstance(phases, list)
    assert all(isinstance(phase, dict) for phase in phases)
    assert all("start_frame" in phase and "end_frame" in phase for phase in phases)

def test_calculate_joint_angles(ai_service):
    """Test joint angle calculation"""
    landmarks = [
        {"x": 0, "y": 0, "z": 0},
        {"x": 0, "y": 1, "z": 0},
        {"x": 1, "y": 1, "z": 0}
    ]
    
    angle = ai_service._calculate_joint_angles(landmarks, 0, 1, 2)
    assert isinstance(angle, float)
    assert 0 <= angle <= 180

def test_analyze_form_with_low_confidence(ai_service, test_video):
    """Test form analysis with low confidence pose detection"""
    # Mock pose estimator to return low confidence
    ai_service.pose_estimator.process.return_value = {
        "pose_landmarks": [
            {"x": 0.5, "y": 0.5, "z": 0.0, "visibility": 0.1}  # Low confidence
            for _ in range(33)
        ]
    }
    
    with pytest.raises(AIServiceError):
        ai_service.analyze_form(test_video, ExerciseType.SQUAT)

def test_handle_model_error(ai_service, test_video):
    """Test handling of model inference errors"""
    # Mock model to raise an error
    ai_service.models[ExerciseType.SQUAT].forward.side_effect = RuntimeError("CUDA out of memory")
    
    with pytest.raises(AIServiceError):
        ai_service.analyze_form(test_video, ExerciseType.SQUAT)

def test_validate_video_duration(ai_service):
    """Test video duration validation"""
    # Test with valid duration
    valid_video = [np.zeros((300, 300, 3)) for _ in range(300)]  # 10 seconds at 30 fps
    ai_service._validate_video_duration(valid_video)
    
    # Test with invalid duration
    invalid_video = [np.zeros((300, 300, 3)) for _ in range(3000)]  # 100 seconds
    with pytest.raises(AIServiceError):
        ai_service._validate_video_duration(invalid_video)

def test_get_exercise_specific_thresholds(ai_service):
    """Test exercise-specific threshold retrieval"""
    thresholds = ai_service._get_exercise_specific_thresholds(ExerciseType.SQUAT)
    
    assert isinstance(thresholds, dict)
    assert "knee_angle" in thresholds
    assert "hip_angle" in thresholds
    assert "back_angle" in thresholds

def test_save_analysis_debug_info(ai_service, test_video, tmp_path):
    """Test saving debug information"""
    debug_path = tmp_path / "debug_info.json"
    
    analysis_result = ai_service.analyze_form(
        test_video,
        ExerciseType.SQUAT,
        save_debug_info=True,
        debug_path=str(debug_path)
    )
    
    assert debug_path.exists()
    with open(debug_path) as f:
        debug_info = json.load(f)
    
    assert "landmarks_sequence" in debug_info
    assert "phase_detection" in debug_info
    assert "model_confidence" in debug_info 

@pytest.mark.asyncio
@patch('app.services.ai_service.cv2.imread')
async def test_process_frames_for_pose_ideal_frames(
    mock_cv2_imread: MagicMock,
    ai_service: AIService, 
    sample_frame_paths: list[str],
    sample_image_data: list[np.ndarray]
):
    """Test process_frames_for_pose with ideal frame data."""
    min_conf_threshold = 0.7
    mock_cv2_imread.side_effect = sample_image_data
    mock_landmarks_frame1 = [{'x': 0.1, 'y': 0.2, 'z': 0.3, 'visibility': 0.99}]
    mock_confidence_frame1 = 0.99
    mock_landmarks_frame2 = [{'x': 0.4, 'y': 0.5, 'z': 0.6, 'visibility': 0.98}]
    mock_confidence_frame2 = 0.98

    def mock_detect_pose_side_effect(frame_np_array):
        if np.array_equal(frame_np_array, sample_image_data[0]):
            return (mock_landmarks_frame1, mock_confidence_frame1)
        elif np.array_equal(frame_np_array, sample_image_data[1]):
            return (mock_landmarks_frame2, mock_confidence_frame2)
        return ([], 0.0) 

    with patch.object(ai_service, 'detect_pose', new_callable=MagicMock) as mock_detect_pose:
        mock_detect_pose.side_effect = mock_detect_pose_side_effect
        results = await ai_service.process_frames_for_pose(
            frame_paths=sample_frame_paths, 
            min_pose_confidence_threshold=min_conf_threshold
        )
        assert mock_cv2_imread.call_count == len(sample_frame_paths)
        mock_cv2_imread.assert_has_calls([call(path) for path in sample_frame_paths])
        assert mock_detect_pose.call_count == len(sample_frame_paths)
        assert len(results) == len(sample_frame_paths)
        assert results[0] == mock_landmarks_frame1
        assert results[1] == mock_landmarks_frame2
        
@pytest.mark.asyncio
@patch('app.services.ai_service.cv2.imread')
async def test_process_frames_for_pose_low_confidence(
    mock_cv2_imread: MagicMock,
    ai_service: AIService,
    sample_frame_paths: list[str],
    sample_image_data: list[np.ndarray]
):
    """Test process_frames_for_pose where one frame has low confidence."""
    min_conf_threshold = 0.7
    mock_cv2_imread.side_effect = sample_image_data
    mock_landmarks_frame1 = [{'x': 0.1, 'y': 0.2, 'z': 0.3, 'visibility': 0.99}]
    mock_confidence_frame1 = 0.99
    mock_landmarks_frame2_low_conf = [{'x': 0.4, 'y': 0.5, 'z': 0.6, 'visibility': 0.45}]
    mock_confidence_frame2_low = 0.4

    def mock_detect_pose_side_effect(frame_np_array):
        if np.array_equal(frame_np_array, sample_image_data[0]):
            return (mock_landmarks_frame1, mock_confidence_frame1)
        elif np.array_equal(frame_np_array, sample_image_data[1]):
            return (mock_landmarks_frame2_low_conf, mock_confidence_frame2_low)
        return ([], 0.0)

    with patch.object(ai_service, 'detect_pose', new_callable=MagicMock) as mock_detect_pose:
        mock_detect_pose.side_effect = mock_detect_pose_side_effect
        results = await ai_service.process_frames_for_pose(
            frame_paths=sample_frame_paths,
            min_pose_confidence_threshold=min_conf_threshold
        )
        assert mock_cv2_imread.call_count == len(sample_frame_paths)
        mock_cv2_imread.assert_has_calls([call(path) for path in sample_frame_paths])
        assert mock_detect_pose.call_count == len(sample_frame_paths)
        assert len(results) == len(sample_frame_paths)
        assert results[0] == mock_landmarks_frame1
        assert results[1] is None

@pytest.mark.asyncio
async def test_process_frames_for_pose_empty_input(
    ai_service: AIService 
):
    """Test process_frames_for_pose with an empty list of frame_paths."""
    empty_frame_paths = []
    min_conf_threshold = 0.7
    with patch('app.services.ai_service.cv2.imread') as mock_cv2_imread_local, patch.object(ai_service, 'detect_pose') as mock_detect_pose_local:
        results = await ai_service.process_frames_for_pose(
            frame_paths=empty_frame_paths,
            min_pose_confidence_threshold=min_conf_threshold
        )
        assert results == []
        mock_cv2_imread_local.assert_not_called()
        mock_detect_pose_local.assert_not_called()

@pytest.mark.asyncio
@patch('app.services.ai_service.cv2.imread')
@patch('app.services.ai_service.logger.warning') 
async def test_process_frames_for_pose_imread_fails(
    mock_logger_warning: MagicMock,
    mock_cv2_imread: MagicMock,
    ai_service: AIService,
    sample_frame_paths: list[str], 
    sample_image_data: list[np.ndarray] 
):
    """Test process_frames_for_pose when cv2.imread fails for one frame."""
    min_conf_threshold = 0.7
    mock_cv2_imread.side_effect = [sample_image_data[0], None]
    mock_landmarks_frame1 = [{'x': 0.1, 'y': 0.2, 'z': 0.3, 'visibility': 0.99}]
    mock_confidence_frame1 = 0.99

    def mock_detect_pose_side_effect(frame_np_array):
        if np.array_equal(frame_np_array, sample_image_data[0]):
            return (mock_landmarks_frame1, mock_confidence_frame1)
        pytest.fail("detect_pose called with unexpected frame data")
        return ([], 0.0) 

    with patch.object(ai_service, 'detect_pose', new_callable=MagicMock) as mock_detect_pose:
        mock_detect_pose.side_effect = mock_detect_pose_side_effect
        results = await ai_service.process_frames_for_pose(
            frame_paths=sample_frame_paths, 
            min_pose_confidence_threshold=min_conf_threshold
        )
        assert mock_cv2_imread.call_count == len(sample_frame_paths)
        mock_cv2_imread.assert_has_calls([
            call(sample_frame_paths[0]),
            call(sample_frame_paths[1])
        ])
        mock_detect_pose.assert_called_once_with(sample_image_data[0])
        assert len(results) == len(sample_frame_paths)
        assert results[0] == mock_landmarks_frame1
        assert results[1] is None
        mock_logger_warning.assert_called_once()
        logged_message = mock_logger_warning.call_args[0][0]
        assert f"Could not read frame 2/{len(sample_frame_paths)}: {sample_frame_paths[1]}" in logged_message

@pytest.mark.asyncio
@patch('app.services.ai_service.cv2.imread')
@patch('app.services.ai_service.logger.debug') 
async def test_process_frames_for_pose_detect_pose_empty_landmarks_high_confidence(
    mock_logger_debug: MagicMock,
    mock_cv2_imread: MagicMock,
    ai_service: AIService,
    sample_frame_paths: list[str],
    sample_image_data: list[np.ndarray]
):
    """Test PFP when detect_pose returns empty landmarks but high confidence."""
    # ARRANGE
    min_conf_threshold = 0.7
    mock_cv2_imread.side_effect = sample_image_data

    mock_landmarks_frame1 = [{'x': 0.1, 'y': 0.2, 'z': 0.3, 'visibility': 0.99}]
    mock_confidence_frame1 = 0.99
    
    mock_empty_landmarks_frame2: list = []
    mock_confidence_frame2_high = 0.95 # Above min_conf_threshold

    def mock_detect_pose_side_effect(frame_np_array):
        if np.array_equal(frame_np_array, sample_image_data[0]):
            return (mock_landmarks_frame1, mock_confidence_frame1)
        elif np.array_equal(frame_np_array, sample_image_data[1]):
            return (mock_empty_landmarks_frame2, mock_confidence_frame2_high)
        pytest.fail("detect_pose called with unexpected frame data")
        return ([], 0.0) 

    with patch.object(ai_service, 'detect_pose', new_callable=MagicMock) as mock_detect_pose:
        mock_detect_pose.side_effect = mock_detect_pose_side_effect

        # ACT
        results = await ai_service.process_frames_for_pose(
            frame_paths=sample_frame_paths, 
            min_pose_confidence_threshold=min_conf_threshold
        )

        # ASSERT
        assert mock_cv2_imread.call_count == len(sample_frame_paths)
        mock_cv2_imread.assert_has_calls([
            call(sample_frame_paths[0]),
            call(sample_frame_paths[1])
        ])

        assert mock_detect_pose.call_count == len(sample_frame_paths)
        mock_detect_pose.assert_any_call(sample_image_data[0])
        mock_detect_pose.assert_any_call(sample_image_data[1])
        
        assert len(results) == len(sample_frame_paths)
        assert results[0] == mock_landmarks_frame1 
        assert results[1] is None # Because `not raw_landmarks_from_mp` (not []) is True

        mock_logger_debug.assert_called()
        frame2_log_found = False
        for log_call_args in mock_logger_debug.call_args_list:
            logged_message = log_call_args[0][0]
            if f"Frame 2/{len(sample_frame_paths)}" in logged_message and "No landmarks detected by MediaPipe" in logged_message:
                frame2_log_found = True
                break
        assert frame2_log_found, "Debug log for frame 2 (empty landmarks) not found or incorrect."

@pytest.mark.asyncio
@patch('app.services.ai_service.cv2.imread')
async def test_process_frames_for_pose_detect_pose_raises_exception(
    mock_cv2_imread: MagicMock,
    ai_service: AIService,
    sample_frame_paths: list[str], # Expects 2 paths
    sample_image_data: list[np.ndarray] # Expects 2 image data
):
    """Test PFP when detect_pose raises an exception for a frame."""
    # ARRANGE
    min_conf_threshold = 0.7
    mock_cv2_imread.side_effect = sample_image_data # imread succeeds for both

    mock_landmarks_frame1 = [{'x': 0.1, 'y': 0.2, 'z': 0.3, 'visibility': 0.99}]
    mock_confidence_frame1 = 0.99
    simulated_error = RuntimeError("Simulated MediaPipe processing error")

    def mock_detect_pose_side_effect(frame_np_array):
        if np.array_equal(frame_np_array, sample_image_data[0]):
            return (mock_landmarks_frame1, mock_confidence_frame1)
        elif np.array_equal(frame_np_array, sample_image_data[1]):
            raise simulated_error
        pytest.fail("detect_pose called with unexpected frame data")
        return ([], 0.0) # Should not be reached

    with patch.object(ai_service, 'detect_pose', new_callable=MagicMock) as mock_detect_pose:
        mock_detect_pose.side_effect = mock_detect_pose_side_effect

        # ACT & ASSERT
        with pytest.raises(RuntimeError, match="Simulated MediaPipe processing error"):
            await ai_service.process_frames_for_pose(
                frame_paths=sample_frame_paths, 
                min_pose_confidence_threshold=min_conf_threshold
            )

        # Verify calls up to the point of failure
        assert mock_cv2_imread.call_count == 2 # imread for both frames attempted
        mock_cv2_imread.assert_has_calls([
            call(sample_frame_paths[0]),
            call(sample_frame_paths[1])
        ])

        # detect_pose called for frame1 (ok) and frame2 (raises error)
        assert mock_detect_pose.call_count == 2 
        mock_detect_pose.assert_any_call(sample_image_data[0])
        mock_detect_pose.assert_any_call(sample_image_data[1])

# Tests for detect_pose method
@patch('app.services.ai_service.cv2.cvtColor')
def test_detect_pose_successful_detection(
    mock_cv2_cvtColor: MagicMock,
    ai_service: AIService
):
    """Test detect_pose when MediaPipe successfully detects landmarks."""
    # ARRANGE
    sample_bgr_frame = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    sample_rgb_frame = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8) # Mocked output of cvtColor
    mock_cv2_cvtColor.return_value = sample_rgb_frame

    # Mock MediaPipe Landmark objects
    mock_mp_landmark1 = MagicMock()
    mock_mp_landmark1.x = 0.1
    mock_mp_landmark1.y = 0.2
    mock_mp_landmark1.z = 0.3
    mock_mp_landmark1.visibility = 0.99

    mock_mp_landmark2 = MagicMock()
    mock_mp_landmark2.x = 0.4
    mock_mp_landmark2.y = 0.5
    mock_mp_landmark2.z = 0.6
    mock_mp_landmark2.visibility = 0.95

    mock_mediapipe_results = MagicMock() # Simulates MediaPipe Results object
    mock_mediapipe_results.pose_landmarks = [mock_mp_landmark1, mock_mp_landmark2]

    # Configure the pose.process mock on the ai_service instance
    ai_service.pose.process = MagicMock(return_value=mock_mediapipe_results)

    expected_landmarks = [
        {'x': 0.1, 'y': 0.2, 'z': 0.3, 'visibility': 0.99},
        {'x': 0.4, 'y': 0.5, 'z': 0.6, 'visibility': 0.95},
    ]
    expected_confidence = (0.99 + 0.95) / 2

    # ACT
    landmarks, confidence = ai_service.detect_pose(sample_bgr_frame)

    # ASSERT
    mock_cv2_cvtColor.assert_called_once_with(sample_bgr_frame, cv2.COLOR_BGR2RGB)
    ai_service.pose.process.assert_called_once_with(sample_rgb_frame)
    assert landmarks == expected_landmarks
    assert confidence == expected_confidence

@patch('app.services.ai_service.cv2.cvtColor')
def test_detect_pose_no_landmarks_detected(
    mock_cv2_cvtColor: MagicMock,
    ai_service: AIService
):
    """Test detect_pose when MediaPipe returns no landmarks (results.pose_landmarks is None)."""
    # ARRANGE
    sample_bgr_frame = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    sample_rgb_frame = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    mock_cv2_cvtColor.return_value = sample_rgb_frame

    mock_mediapipe_results = MagicMock() # Simulates MediaPipe Results object
    mock_mediapipe_results.pose_landmarks = None # Key difference: no landmarks

    ai_service.pose.process = MagicMock(return_value=mock_mediapipe_results)

    expected_landmarks = []
    expected_confidence = 0.0

    # ACT
    landmarks, confidence = ai_service.detect_pose(sample_bgr_frame)

    # ASSERT
    mock_cv2_cvtColor.assert_called_once_with(sample_bgr_frame, cv2.COLOR_BGR2RGB)
    ai_service.pose.process.assert_called_once_with(sample_rgb_frame)
    assert landmarks == expected_landmarks
    assert confidence == expected_confidence

@patch('app.services.ai_service.cv2.cvtColor')
@patch('app.services.ai_service.logger.error') # Patch the logger to check error logging
def test_detect_pose_mediapipe_process_raises_exception(
    mock_logger_error: MagicMock,
    mock_cv2_cvtColor: MagicMock,
    ai_service: AIService
):
    """Test detect_pose when MediaPipe's process() method raises an exception."""
    # ARRANGE
    sample_bgr_frame = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    sample_rgb_frame = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    mock_cv2_cvtColor.return_value = sample_rgb_frame

    simulated_exception = RuntimeError("Simulated MediaPipe processing error")
    ai_service.pose.process = MagicMock(side_effect=simulated_exception)

    expected_landmarks = []
    expected_confidence = 0.0

    # ACT
    landmarks, confidence = ai_service.detect_pose(sample_bgr_frame)

    # ASSERT
    mock_cv2_cvtColor.assert_called_once_with(sample_bgr_frame, cv2.COLOR_BGR2RGB)
    ai_service.pose.process.assert_called_once_with(sample_rgb_frame)
    assert landmarks == expected_landmarks
    assert confidence == expected_confidence
    mock_logger_error.assert_called_once()
    # Check that the log message contains info about the exception
    log_message = mock_logger_error.call_args[0][0]
    assert "Error processing frame with MediaPipe" in log_message
    assert str(simulated_exception) in log_message

@patch('app.services.ai_service.cv2.cvtColor')
def test_detect_pose_low_individual_landmark_visibility(
    mock_cv2_cvtColor: MagicMock,
    ai_service: AIService, # Uses mock_settings_for_ai_service for settings
    mock_settings_for_ai_service: MagicMock # To potentially add a new setting for visibility
):
    """Test detect_pose when MediaPipe returns landmarks with low individual visibility."""
    # ARRANGE
    sample_bgr_frame = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    sample_rgb_frame = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    mock_cv2_cvtColor.return_value = sample_rgb_frame

    # This test currently assumes no specific filtering based on individual landmark visibility
    # happens within detect_pose itself, beyond what MediaPipe provides.
    # If such a feature (e.g., using a settings.AI_MIN_LANDMARK_VISIBILITY) were added to detect_pose,
    # this test would need to be updated to assert that filtering.

    mock_mp_landmark_high_vis = MagicMock()
    mock_mp_landmark_high_vis.x = 0.1
    mock_mp_landmark_high_vis.y = 0.2
    mock_mp_landmark_high_vis.z = 0.3
    mock_mp_landmark_high_vis.visibility = 0.9 # High visibility

    mock_mp_landmark_low_vis = MagicMock()
    mock_mp_landmark_low_vis.x = 0.4
    mock_mp_landmark_low_vis.y = 0.5
    mock_mp_landmark_low_vis.z = 0.6
    mock_mp_landmark_low_vis.visibility = 0.4 # Low visibility (but still positive)

    mock_mediapipe_results = MagicMock()
    mock_mediapipe_results.pose_landmarks = [mock_mp_landmark_high_vis, mock_mp_landmark_low_vis]

    ai_service.pose.process = MagicMock(return_value=mock_mediapipe_results)

    # Expected behavior (current assumption): all landmarks are converted and returned as is.
    expected_landmarks = [
        {'x': 0.1, 'y': 0.2, 'z': 0.3, 'visibility': 0.9},
        {'x': 0.4, 'y': 0.5, 'z': 0.6, 'visibility': 0.4},
    ]
    # Overall confidence calculation is based on the average visibility of landmarks returned by MediaPipe.
    expected_confidence = (0.9 + 0.4) / 2 

    # ACT
    landmarks, confidence = ai_service.detect_pose(sample_bgr_frame)

    # ASSERT
    mock_cv2_cvtColor.assert_called_once_with(sample_bgr_frame, cv2.COLOR_BGR2RGB)
    ai_service.pose.process.assert_called_once_with(sample_rgb_frame)
    assert landmarks == expected_landmarks
    assert pytest.approx(confidence) == expected_confidence

# Tests for smooth_and_interpolate_poses
@pytest.mark.asyncio
@patch('app.services.ai_service.AIService._apply_smoothing_to_landmarks')
async def test_smooth_and_interpolate_basic_interpolation(
    mock_apply_smoothing: MagicMock,
    ai_service: AIService,
    mock_settings_for_ai_service: MagicMock # To access AI_POSE_MAX_INTERPOLATION_GAP etc.
):
    """Test basic interpolation of a single None frame between two valid frames."""
    # ARRANGE
    # Let _apply_smoothing just return the landmarks it receives to isolate interpolation testing
    mock_apply_smoothing.side_effect = lambda x, y: x # (landmarks, window_size) -> landmarks

    # Ensure MAX_INTERPOLATION_GAP allows for a 1-frame gap
    # The fixture mock_settings_for_ai_service sets AI_POSE_MAX_INTERPOLATION_GAP = 3
    assert mock_settings_for_ai_service.AI_POSE_MAX_INTERPOLATION_GAP >= 1

    # Simplified landmarks: just one landmark (e.g., 'nose') for clarity
    # Frame 0: Nose at (10, 20, 30), vis 1.0
    landmarks_frame0 = [
        {'name': 'nose', 'x': 10.0, 'y': 20.0, 'z': 30.0, 'visibility': 1.0}
    ]
    # Frame 1: None (to be interpolated)
    # Frame 2: Nose at (30, 40, 50), vis 0.8
    landmarks_frame2 = [
        {'name': 'nose', 'x': 30.0, 'y': 40.0, 'z': 50.0, 'visibility': 0.8}
    ]

    all_pose_landmarks_input = [landmarks_frame0, None, landmarks_frame2]
    exercise_type = ExerciseType.SQUAT # Example exercise type

    # Expected interpolated values for 'nose' in Frame 1 (midpoint for simplicity)
    # x: (10+30)/2 = 20, y: (20+40)/2 = 30, z: (30+50)/2 = 40, vis: (1.0+0.8)/2 = 0.9
    expected_interpolated_nose = {
        'name': 'nose', 'x': 20.0, 'y': 30.0, 'z': 40.0, 'visibility': 0.9
    }

    # ACT
    result_landmarks = await ai_service.smooth_and_interpolate_poses(
        all_pose_landmarks_input, exercise_type
    )

    # ASSERT
    assert len(result_landmarks) == len(all_pose_landmarks_input)
    
    # Frame 0 should be unchanged (since smoothing is mocked to pass through)
    assert result_landmarks[0] == landmarks_frame0
    
    # Frame 1 (interpolated)
    assert result_landmarks[1] is not None
    assert len(result_landmarks[1]) == 1
    # Comparing floats requires close assertion
    assert result_landmarks[1][0]['name'] == expected_interpolated_nose['name']
    assert pytest.approx(result_landmarks[1][0]['x']) == expected_interpolated_nose['x']
    assert pytest.approx(result_landmarks[1][0]['y']) == expected_interpolated_nose['y']
    assert pytest.approx(result_landmarks[1][0]['z']) == expected_interpolated_nose['z']
    assert pytest.approx(result_landmarks[1][0]['visibility']) == expected_interpolated_nose['visibility']
    
    # Frame 2 should be unchanged
    assert result_landmarks[2] == landmarks_frame2

    # Verify smoothing was called (even if its effect is bypassed by the mock's side_effect)
    # It should be called once with the (potentially) interpolated data.
    # The first argument to _apply_smoothing_to_landmarks will be the list *after* interpolation.
    assert mock_apply_smoothing.call_count == 1
    # Further assertions could be made on mock_apply_smoothing.call_args if needed

@pytest.mark.asyncio
@patch('app.services.ai_service.AIService._apply_smoothing_to_landmarks')
async def test_smooth_and_interpolate_no_interpolation_for_large_gap(
    mock_apply_smoothing: MagicMock,
    ai_service: AIService,
    mock_settings_for_ai_service: MagicMock 
):
    """Test that no interpolation occurs if the gap of None frames is too large."""
    # ARRANGE
    mock_apply_smoothing.side_effect = lambda x, y: x # Pass-through smoothing

    max_gap = mock_settings_for_ai_service.AI_POSE_MAX_INTERPOLATION_GAP # Default is 3
    gap_too_large = max_gap + 1 # e.g., 4 None frames

    landmarks_frame_start = [
        {'name': 'nose', 'x': 10.0, 'y': 20.0, 'z': 30.0, 'visibility': 1.0}
    ]
    landmarks_frame_end = [
        {'name': 'nose', 'x': 50.0, 'y': 60.0, 'z': 70.0, 'visibility': 1.0}
    ]

    all_pose_landmarks_input = [landmarks_frame_start] + ([None] * gap_too_large) + [landmarks_frame_end]
    # Example: [frame_start, None, None, None, None, frame_end] if max_gap is 3
    
    exercise_type = ExerciseType.SQUAT

    # ACT
    result_landmarks = await ai_service.smooth_and_interpolate_poses(
        all_pose_landmarks_input, exercise_type
    )

    # ASSERT
    assert len(result_landmarks) == len(all_pose_landmarks_input)
    assert result_landmarks[0] == landmarks_frame_start
    
    # Check that all frames within the large gap remain None
    for i in range(1, gap_too_large + 1):
        assert result_landmarks[i] is None, f"Frame at index {i} should be None due to large gap"
        
    assert result_landmarks[gap_too_large + 1] == landmarks_frame_end

    assert mock_apply_smoothing.call_count == 1
    # The input to smoothing should still contain the Nones for the large gap
    arg_to_smoothing = mock_apply_smoothing.call_args[0][0]
    assert arg_to_smoothing[0] == landmarks_frame_start
    for i in range(1, gap_too_large + 1):
        assert arg_to_smoothing[i] is None, f"Frame {i} passed to smoothing should be None"
    assert arg_to_smoothing[gap_too_large + 1] == landmarks_frame_end

@pytest.mark.asyncio
@patch('app.services.ai_service.AIService._apply_smoothing_to_landmarks')
async def test_smooth_and_interpolate_multiple_landmarks_interpolation(
    mock_apply_smoothing: MagicMock,
    ai_service: AIService,
    mock_settings_for_ai_service: MagicMock
):
    """Test interpolation of multiple distinct landmarks across a single None frame."""
    # ARRANGE
    mock_apply_smoothing.side_effect = lambda x, y: x # Pass-through smoothing
    assert mock_settings_for_ai_service.AI_POSE_MAX_INTERPOLATION_GAP >= 1

    landmarks_frame0 = [
        {'name': 'nose',       'x': 10.0, 'y': 20.0, 'z': 30.0, 'visibility': 1.0},
        {'name': 'left_elbow', 'x': 100.0, 'y': 110.0, 'z': 120.0, 'visibility': 0.98},
        {'name': 'right_knee', 'x': 200.0, 'y': 210.0, 'z': 220.0, 'visibility': 0.96}
    ]
    # Frame 1 is None
    landmarks_frame2 = [
        {'name': 'nose',       'x': 30.0, 'y': 40.0, 'z': 50.0, 'visibility': 0.8},
        # left_elbow is intentionally missing in frame2 to test robustness / how it handles this
        # The current interpolation logic in AIService iterates over landmarks_to_interpolate_names
        # which are keys from the *first valid frame* before the gap.
        # If a landmark is missing in the *second valid frame* after the gap, its interpolation might be tricky
        # or might use the last known value. For this test, let's assume it interpolates towards (0,0,0,0) or similar if missing.
        # OR, more likely, the _interpolate_landmark function should handle a missing next_landmark gracefully.
        # For now, let's provide it to ensure clear interpolation targets.
        {'name': 'left_elbow', 'x': 140.0, 'y': 150.0, 'z': 160.0, 'visibility': 0.78},
        {'name': 'right_knee', 'x': 240.0, 'y': 250.0, 'z': 260.0, 'visibility': 0.76}
    ]

    all_pose_landmarks_input = [landmarks_frame0, None, landmarks_frame2]
    exercise_type = ExerciseType.SQUAT

    expected_interpolated_frame1 = [
        {'name': 'nose',       'x': 20.0, 'y': 30.0, 'z': 40.0, 'visibility': 0.9},
        {'name': 'left_elbow', 'x': 120.0, 'y': 130.0, 'z': 140.0, 'visibility': (0.98 + 0.78)/2 },
        {'name': 'right_knee', 'x': 220.0, 'y': 230.0, 'z': 240.0, 'visibility': (0.96 + 0.76)/2 }
    ]

    # ACT
    result_landmarks = await ai_service.smooth_and_interpolate_poses(
        all_pose_landmarks_input, exercise_type
    )

    # ASSERT
    assert len(result_landmarks) == len(all_pose_landmarks_input)
    assert result_landmarks[0] == landmarks_frame0

    interpolated_frame = result_landmarks[1]
    assert interpolated_frame is not None
    assert len(interpolated_frame) == len(expected_interpolated_frame1)

    # Sort by name to ensure consistent order for comparison
    interpolated_frame.sort(key=lambda lm: lm['name'])
    expected_interpolated_frame1.sort(key=lambda lm: lm['name'])

    for i in range(len(interpolated_frame)):
        assert interpolated_frame[i]['name'] == expected_interpolated_frame1[i]['name']
        assert pytest.approx(interpolated_frame[i]['x']) == expected_interpolated_frame1[i]['x']
        assert pytest.approx(interpolated_frame[i]['y']) == expected_interpolated_frame1[i]['y']
        assert pytest.approx(interpolated_frame[i]['z']) == expected_interpolated_frame1[i]['z']
        assert pytest.approx(interpolated_frame[i]['visibility']) == expected_interpolated_frame1[i]['visibility']

    assert result_landmarks[2] == landmarks_frame2
    assert mock_apply_smoothing.call_count == 1

@pytest.mark.asyncio
@patch('app.services.ai_service.AIService._apply_smoothing_to_landmarks')
async def test_smooth_and_interpolate_landmark_missing_post_gap(
    mock_apply_smoothing: MagicMock,
    ai_service: AIService,
    mock_settings_for_ai_service: MagicMock
):
    """Test interpolation when a specific landmark is missing in the frame after the gap."""
    # ARRANGE
    mock_apply_smoothing.side_effect = lambda x, y: x # Pass-through smoothing
    assert mock_settings_for_ai_service.AI_POSE_MAX_INTERPOLATION_GAP >= 1

    landmarks_frame0 = [
        {'name': 'nose',       'x': 10.0, 'y': 20.0, 'z': 30.0, 'visibility': 1.0},
        {'name': 'left_wrist', 'x': 50.0, 'y': 55.0, 'z': 60.0, 'visibility': 0.9}
    ]
    # Frame 1 is None
    landmarks_frame2 = [
        {'name': 'nose', 'x': 30.0, 'y': 40.0, 'z': 50.0, 'visibility': 0.8}
        # 'left_wrist' is intentionally missing in landmarks_frame2
    ]

    all_pose_landmarks_input = [landmarks_frame0, None, landmarks_frame2]
    exercise_type = ExerciseType.SQUAT

    # Expected: 'nose' is interpolated. 'left_wrist' is not, so it won't appear in the interpolated frame.
    expected_interpolated_frame1 = [
        {'name': 'nose', 'x': 20.0, 'y': 30.0, 'z': 40.0, 'visibility': 0.9}
    ]

    # ACT
    result_landmarks = await ai_service.smooth_and_interpolate_poses(
        all_pose_landmarks_input, exercise_type
    )

    # ASSERT
    assert len(result_landmarks) == len(all_pose_landmarks_input)
    assert result_landmarks[0] == landmarks_frame0 # Unchanged

    interpolated_frame = result_landmarks[1]
    assert interpolated_frame is not None
    # Based on Hypothesis 1: 'left_wrist' is not interpolated and thus not included.
    assert len(interpolated_frame) == len(expected_interpolated_frame1)
    
    assert interpolated_frame[0]['name'] == 'nose'
    assert pytest.approx(interpolated_frame[0]['x']) == expected_interpolated_frame1[0]['x']
    assert pytest.approx(interpolated_frame[0]['y']) == expected_interpolated_frame1[0]['y']
    assert pytest.approx(interpolated_frame[0]['z']) == expected_interpolated_frame1[0]['z']
    assert pytest.approx(interpolated_frame[0]['visibility']) == expected_interpolated_frame1[0]['visibility']

    assert result_landmarks[2] == landmarks_frame2 # Unchanged
    assert mock_apply_smoothing.call_count == 1

@pytest.mark.asyncio
@patch('app.services.ai_service.AIService._apply_smoothing_to_landmarks')
async def test_smooth_and_interpolate_empty_input_list(
    mock_apply_smoothing: MagicMock,
    ai_service: AIService
):
    """Test smooth_and_interpolate_poses with an empty input list."""
    # ARRANGE
    all_pose_landmarks_input = []
    exercise_type = ExerciseType.SQUAT
    mock_apply_smoothing.side_effect = lambda x, y: x # Pass-through

    # ACT
    result_landmarks = await ai_service.smooth_and_interpolate_poses(
        all_pose_landmarks_input, exercise_type
    )

    # ASSERT
    assert result_landmarks == []
    # Depending on implementation, smoothing might not be called for an empty list.
    # If it is, it should handle it. If not, call_count would be 0.
    # For now, let's assume the main loop won't run, so smoothing isn't called.
    # This depends on how AIService.smooth_and_interpolate_poses is structured internally.
    # If it calls smoothing with an empty list, the mock will handle it.
    # Let's be flexible: if it is called, it must be with an empty list.
    if mock_apply_smoothing.called:
        assert mock_apply_smoothing.call_args[0][0] == []
    # else: # Not called, which is also fine for an empty input. 
    #    pass

@pytest.mark.asyncio
@patch('app.services.ai_service.AIService._apply_smoothing_to_landmarks')
async def test_smooth_and_interpolate_all_none_input_list(
    mock_apply_smoothing: MagicMock,
    ai_service: AIService
):
    """Test smooth_and_interpolate_poses with a list containing only None values."""
    # ARRANGE
    all_pose_landmarks_input = [None, None, None]
    exercise_type = ExerciseType.SQUAT
    mock_apply_smoothing.side_effect = lambda x, y: x # Pass-through

    # ACT
    result_landmarks = await ai_service.smooth_and_interpolate_poses(
        all_pose_landmarks_input, exercise_type
    )

    # ASSERT
    assert result_landmarks == [None, None, None]
    # Smoothing should be called with the list of Nones and should return it as is (due to mock)
    mock_apply_smoothing.assert_called_once_with([None, None, None], ai_service.settings.AI_POSE_SMOOTHING_WINDOW_SIZE)

@pytest.mark.asyncio
# No mock for _apply_smoothing_to_landmarks this time, we test its behavior with short lists.
async def test_smooth_and_interpolate_list_too_short_for_smoothing(
    ai_service: AIService,
    mock_settings_for_ai_service: MagicMock # To access AI_POSE_SMOOTHING_WINDOW_SIZE
):
    """Test behavior when the landmark list is too short for the smoothing window."""
    # ARRANGE
    window_size = mock_settings_for_ai_service.AI_POSE_SMOOTHING_WINDOW_SIZE # Default is 5
    # Create a list shorter than the window size, e.g., window_size - 2
    # Ensure it has at least one frame for the internal loops to run if needed.
    num_frames = max(1, window_size - 2) 

    # Create some consistent valid landmark data for these frames
    sample_landmark_data = [
        {'name': 'nose', 'x': 10.0, 'y': 20.0, 'z': 30.0, 'visibility': 1.0},
        {'name': 'left_eye', 'x': 12.0, 'y': 22.0, 'z': 32.0, 'visibility': 0.98}
    ]
    all_pose_landmarks_input = [list(sample_landmark_data) for _ in range(num_frames)]
    exercise_type = ExerciseType.SQUAT

    # We expect the data to be returned as-is because it's too short to smooth.
    # The _apply_smoothing_to_landmarks method should handle this gracefully.

    # ACT
    result_landmarks = await ai_service.smooth_and_interpolate_poses(
        all_pose_landmarks_input, exercise_type
    )

    # ASSERT
    # The result should be identical to the input if smoothing was (correctly) skipped.
    assert len(result_landmarks) == num_frames
    for i in range(num_frames):
        assert result_landmarks[i] is not None
        assert len(result_landmarks[i]) == len(sample_landmark_data)
        # Sort by name for consistent comparison if the order might change
        # For this setup, order should be preserved by list comprehension.
        for j in range(len(sample_landmark_data)):
            assert result_landmarks[i][j]['name'] == sample_landmark_data[j]['name']
            assert pytest.approx(result_landmarks[i][j]['x']) == sample_landmark_data[j]['x']
            assert pytest.approx(result_landmarks[i][j]['y']) == sample_landmark_data[j]['y']
            assert pytest.approx(result_landmarks[i][j]['z']) == sample_landmark_data[j]['z']
            assert pytest.approx(result_landmarks[i][j]['visibility']) == sample_landmark_data[j]['visibility']

@pytest.mark.asyncio
@patch('app.services.ai_service.savgol_filter') # Assuming 'from scipy.signal import savgol_filter' in ai_service.py
async def test_smooth_and_interpolate_calls_savgol_filter(
    mock_savgol_filter: MagicMock,
    ai_service: AIService,
    mock_settings_for_ai_service: MagicMock
):
    """Test that savgol_filter is called when data is sufficient for smoothing."""
    # ARRANGE
    window_size = mock_settings_for_ai_service.AI_POSE_SMOOTHING_WINDOW_SIZE # Default is 5
    polyorder = 2 # Common polyorder, assuming AIService might use this or similar
    num_frames = window_size + 5 # Ensure it's longer than window_size

    # Side effect for savgol_filter: just return the input data slice to avoid complex output assertion
    # and to ensure the main function can complete.
    mock_savgol_filter.side_effect = lambda data, window, order: data 

    # Create consistent valid landmark data for these frames
    # Using two distinct landmarks to ensure iteration over landmarks works
    landmarks_template = [
        {'name': 'nose', 'x': 0.0, 'y': 0.0, 'z': 0.0, 'visibility': 0.0},
        {'name': 'left_shoulder', 'x': 0.0, 'y': 0.0, 'z': 0.0, 'visibility': 0.0}
    ]
    
    all_pose_landmarks_input = []
    for i in range(num_frames):
        frame_landmarks = []
        for lm_template in landmarks_template:
            frame_landmarks.append({
                'name': lm_template['name'],
                'x': float(i * 10 + 1), # Varying data
                'y': float(i * 10 + 2),
                'z': float(i * 10 + 3),
                'visibility': (i % 2) * 0.1 + 0.8 # Varying visibility between 0.8 and 0.9
            })
        all_pose_landmarks_input.append(frame_landmarks)
        
    exercise_type = ExerciseType.SQUAT

    # ACT
    await ai_service.smooth_and_interpolate_poses(
        all_pose_landmarks_input, exercise_type
    )

    # ASSERT
    assert mock_savgol_filter.called
    
    # Expected number of calls: num_landmarks * num_coordinates_per_landmark (x,y,z,visibility = 4)
    num_landmark_types = len(landmarks_template)
    num_coords = 4 
    expected_call_count = num_landmark_types * num_coords
    assert mock_savgol_filter.call_count == expected_call_count

    # Check arguments for at least one call (e.g., the first call)
    # The first argument to savgol_filter is the data series (a numpy array)
    # The second is window_length, the third is polyorder.
    first_call_args = mock_savgol_filter.call_args_list[0][0]
    # first_call_args[0] is the ndarray of x-coordinates for the first landmark type ('nose')
    assert isinstance(first_call_args[0], np.ndarray)
    assert len(first_call_args[0]) == num_frames
    assert first_call_args[1] == window_size
    # Assuming a polyorder is used by the implementation, e.g., 2 or 3.
    # If AIService._apply_smoothing_to_landmarks has a hardcoded polyorder, match it here.
    # For this test, we assume it passes a polyorder (e.g. 2).
    # If the actual implementation doesn't pass polyorder and uses default, this assert needs adjustment.
    assert first_call_args[2] == polyorder # AIService._apply_smoothing_to_landmarks needs to pass this
                                          # If it only passes data and window, then this assert changes.
                                          # For now, assuming it passes polyorder too.
                                          # If actual code is savgol_filter(series, window_size), this test needs update for polyorder.

@pytest.mark.asyncio
@patch('app.services.ai_service.savgol_filter')
async def test_smooth_and_interpolate_effect_on_jittery_data(
    mock_savgol_filter: MagicMock,
    ai_service: AIService,
    mock_settings_for_ai_service: MagicMock # Provides AI_POSE_SMOOTHING_WINDOW_SIZE
):
    """Test the smoothing effect of smooth_and_interpolate_poses on jittery data."""
    # ARRANGE
    window_size = mock_settings_for_ai_service.AI_POSE_SMOOTHING_WINDOW_SIZE
    polyorder = 2 # Assuming a polyorder used by the service
    num_frames = window_size + 10 # Ensure enough frames for smoothing

    # Create jittery landmark data for one landmark type, e.g., 'nose'
    # True underlying smooth path (e.g., linear)
    smooth_x = np.linspace(10, 100, num_frames)
    smooth_y = np.linspace(20, 50, num_frames)
    smooth_z = np.linspace(5, 15, num_frames)
    smooth_vis = np.linspace(0.9, 0.95, num_frames)

    # Add jitter
    jitter_amplitude = 2.0
    jittery_x = smooth_x + np.random.uniform(-jitter_amplitude, jitter_amplitude, num_frames)
    jittery_y = smooth_y + np.random.uniform(-jitter_amplitude, jitter_amplitude, num_frames)
    jittery_z = smooth_z + np.random.uniform(-jitter_amplitude, jitter_amplitude, num_frames)
    # Visibility usually doesn't need smoothing or is less jittery, but can be included
    jittery_vis = np.clip(smooth_vis + np.random.uniform(-0.05, 0.05, num_frames), 0, 1)

    all_pose_landmarks_input = []
    for i in range(num_frames):
        all_pose_landmarks_input.append([
            {'name': 'nose', 'x': jittery_x[i], 'y': jittery_y[i], 'z': jittery_z[i], 'visibility': jittery_vis[i]}
        ])
    
    exercise_type = ExerciseType.SQUAT

    # Mock savgol_filter to return the *actual* smooth path (or a less jittery version)
    # This simulates the filter successfully removing jitter.
    def mock_savgol_side_effect(data_series, window, order):
        # Determine which coordinate is being smoothed based on its values
        # This is a bit heuristic for a mock; a real test might compare variance.
        if np.allclose(data_series, jittery_x, atol=jitter_amplitude*2):
            return smooth_x
        elif np.allclose(data_series, jittery_y, atol=jitter_amplitude*2):
            return smooth_y
        elif np.allclose(data_series, jittery_z, atol=jitter_amplitude*2):
            return smooth_z
        elif np.allclose(data_series, jittery_vis, atol=0.1):
            return smooth_vis
        return data_series # Fallback, should not happen if all coords are handled
    mock_savgol_filter.side_effect = mock_savgol_side_effect

    # ACT
    result_landmarks = await ai_service.smooth_and_interpolate_poses(
        all_pose_landmarks_input, exercise_type
    )

    # ASSERT
    assert len(result_landmarks) == num_frames
    assert mock_savgol_filter.call_count == 4 # nose_x, nose_y, nose_z, nose_visibility

    # Verify that the output landmarks match the smooth path
    for i in range(num_frames):
        assert result_landmarks[i] is not None
        assert len(result_landmarks[i]) == 1
        lm = result_landmarks[i][0]
        assert lm['name'] == 'nose'
        assert pytest.approx(lm['x']) == smooth_x[i]
        assert pytest.approx(lm['y']) == smooth_y[i]
        assert pytest.approx(lm['z']) == smooth_z[i]
        assert pytest.approx(lm['visibility']) == smooth_vis[i]

# TODO: Revisit polyorder assertion above once AIService._apply_smoothing_to_landmarks implementation detail for polyorder is confirmed.

def test_interpolate_landmark_helper_direct(ai_service_instance: AIService): # Using AIServicePlaceholder instance for direct method call
    """Test the _interpolate_landmark helper method directly with various scenarios."""
    # SCENARIO 1: Basic linear interpolation for x, y, z, and visibility
    prev_lm = {'x': 10.0, 'y': 20.0, 'z': 30.0, 'visibility': 1.0}
    next_lm = {'x': 30.0, 'y': 40.0, 'z': 50.0, 'visibility': 0.8}
    prev_idx, current_idx, next_idx = 0, 1, 2

    interpolated = ai_service_instance._interpolate_landmark(
        prev_lm, next_lm, prev_idx, next_idx, current_idx
    )
    assert interpolated is not None
    assert pytest.approx(interpolated['x']) == 20.0 # Midpoint
    assert pytest.approx(interpolated['y']) == 30.0 # Midpoint
    assert pytest.approx(interpolated['z']) == 40.0 # Midpoint
    assert pytest.approx(interpolated['visibility']) == 0.9 # Midpoint

    # SCENARIO 2: Interpolation closer to prev_lm
    prev_idx, current_idx, next_idx = 0, 1, 4 # Gap of 3 frames (0, [1,2,3], 4), interpolating for frame 1
    interpolated_closer_to_prev = ai_service_instance._interpolate_landmark(
        prev_lm, next_lm, prev_idx, next_idx, current_idx
    )
    # Expected: prev_lm_val + (next_lm_val - prev_lm_val) * ( (current_idx - prev_idx) / (next_idx - prev_idx) )
    # Ratio = (1-0)/(4-0) = 1/4 = 0.25
    expected_x_closer = 10.0 + (30.0 - 10.0) * 0.25 # 10 + 20 * 0.25 = 10 + 5 = 15.0
    expected_y_closer = 20.0 + (40.0 - 20.0) * 0.25 # 20 + 20 * 0.25 = 20 + 5 = 25.0
    expected_z_closer = 30.0 + (50.0 - 30.0) * 0.25 # 30 + 20 * 0.25 = 30 + 5 = 35.0
    expected_vis_closer = 1.0 + (0.8 - 1.0) * 0.25   # 1.0 + (-0.2) * 0.25 = 1.0 - 0.05 = 0.95
    
    assert interpolated_closer_to_prev is not None
    assert pytest.approx(interpolated_closer_to_prev['x']) == expected_x_closer
    assert pytest.approx(interpolated_closer_to_prev['y']) == expected_y_closer
    assert pytest.approx(interpolated_closer_to_prev['z']) == expected_z_closer
    assert pytest.approx(interpolated_closer_to_prev['visibility']) == expected_vis_closer

    # SCENARIO 3: current_idx is the same as prev_idx (should ideally return prev_lm or handle gracefully)
    # Based on typical interpolation formula, (current-prev)/(next-prev) would be 0.
    # So, output should be prev_lm values.
    interpolated_at_prev = ai_service_instance._interpolate_landmark(
        prev_lm, next_lm, 0, 2, 0 # current_idx = prev_idx
    )
    assert interpolated_at_prev is not None
    assert pytest.approx(interpolated_at_prev['x']) == prev_lm['x']
    assert pytest.approx(interpolated_at_prev['y']) == prev_lm['y']
    assert pytest.approx(interpolated_at_prev['z']) == prev_lm['z']
    assert pytest.approx(interpolated_at_prev['visibility']) == prev_lm['visibility']

    # SCENARIO 4: current_idx is the same as next_idx (should return next_lm)
    # (current-prev)/(next-prev) would be 1.
    interpolated_at_next = ai_service_instance._interpolate_landmark(
        prev_lm, next_lm, 0, 2, 2 # current_idx = next_idx
    )
    assert interpolated_at_next is not None
    assert pytest.approx(interpolated_at_next['x']) == next_lm['x']
    assert pytest.approx(interpolated_at_next['y']) == next_lm['y']
    assert pytest.approx(interpolated_at_next['z']) == next_lm['z']
    assert pytest.approx(interpolated_at_next['visibility']) == next_lm['visibility']

    # SCENARIO 5: prev_idx is the same as next_idx (division by zero in ratio if not handled)
    # The _interpolate_landmark should handle this gracefully, e.g., by returning prev_lm or None.
    # Let's assume it returns prev_lm in such a case.
    # This case should ideally not occur if called correctly by smooth_and_interpolate_poses.
    with pytest.raises(ZeroDivisionError): # Or specific custom error, or check for None/prev_lm
        # Depending on implementation, it might raise ZeroDivisionError or return a default.
        # For the purpose of this test, let's assume current placeholder AIService._interpolate_landmark
        # might raise ZeroDivisionError or we are testing for it.
        # If it returns prev_lm: result = ai_service_instance._interpolate_landmark(prev_lm, next_lm, 0, 0, 0)
        # assert result == prev_lm
        # For now, let's assume it should be robust and not raise an unhandled error.
        # The placeholder doesn't have implementation, so this test would fail if called as is.
        # Let's refine this after seeing AIService._interpolate_landmark implementation.
        # For now, we can assume the caller `smooth_and_interpolate_poses` prevents next_idx == prev_idx.
        # So this scenario is more about robustness if called directly with bad args.
        # If the actual method returns e.g. prev_lm: 
        # result = ai_service_instance._interpolate_landmark(prev_lm, next_lm, 0, 0, 0)
        # assert result['x'] == prev_lm['x']
        pass # Placeholder for ZeroDivisionError or specific handling test

    # SCENARIO 6: Missing keys in landmark dicts (should handle gracefully or raise error)
    prev_lm_missing_z = {'x': 10.0, 'y': 20.0, 'visibility': 1.0} # Missing 'z'
    # Assuming it might raise KeyError or return None for 'z' or skip 'z' field.
    # This also depends on AIService._interpolate_landmark implementation.
    # Let's assume it would attempt to access 'z' and raise KeyError if not robust.
    with pytest.raises(KeyError):
        ai_service_instance._interpolate_landmark(
            prev_lm_missing_z, next_lm, 0, 2, 1
        )
    
    next_lm_missing_vis = {'x': 30.0, 'y': 40.0, 'z': 50.0} # Missing 'visibility'
    with pytest.raises(KeyError):
        ai_service_instance._interpolate_landmark(
            prev_lm, next_lm_missing_vis, 0, 2, 1
        )

# TODO: Add more tests for smooth_and_interpolate_poses
# TODO: Add tests for _interpolate_landmark (if it's a distinct, testable helper)
# TODO: Add tests for detect_pose method itself
#   - Mock self.pose.process to return results with landmarks
#   - Mock self.pose.process to return results with NO landmarks
#   - Mock self.pose.process to raise an exception

# TODO: Add tests for smooth_and_interpolate_poses
# TODO: Add tests for _interpolate_landmark (if it's a distinct, testable helper) 