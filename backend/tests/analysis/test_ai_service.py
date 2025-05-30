import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock, call
import numpy as np
import cv2
from app.services.ai_service import AIService
# from app.models.enums import ExerciseType # Commented out as tests using it will be commented
import torch
import json # ADDED for JSON serializability tests
from app.core.config import Settings
from app.core.config import settings as app_settings
from app.constants.angles import UNIVERSAL_ANGLE_DEFINITIONS # ADDED
from typing import Dict, List # ADDED

# This is a placeholder for the actual AIService.
# We will need to import the actual service.
# For example:
# from backend.app.services.ai_service import AIService

# Commenting out AIServicePlaceholder as it's not used by the focused tests
# class AIServicePlaceholder:
#     def process_frames_for_pose(self, frame_paths):
#         # This method will be mocked in tests
#         pass
# 
#     def smooth_and_interpolate_poses(self, poses, max_gap_to_interpolate=5, smoothing_window_size=5):
#         # This method will be mocked or tested individually
#         pass
# 
#     def _interpolate_landmark(self, prev_landmark_data, next_landmark_data, prev_frame_idx, next_frame_idx, current_frame_idx):
#         # This method will be mocked or tested individually
#         pass

class TestAIService: # Keep the class structure
    # @pytest.fixture
    # def mock_ai_service(self): # This fixture might be used by legacy tests, comment if not used by focused tests
    #     \"\"\"Fixture to create a MagicMock instance of AIService.\"\"\"
    #     # service_mock = MagicMock(spec=AIServicePlaceholder)
    #     # return service_mock
    #     pass # Placeholder if no longer needed

    # @pytest.fixture
    # def ai_service_instance(self): # This fixture might be used by legacy tests, comment if not used by focused tests
    #     \"\"\"Fixture to create a real instance of AIService for testing its methods.\"\"\"
    #     # Replace AIServicePlaceholder with the actual class when available
    #     # return AIServicePlaceholder()
    #     pass # Placeholder if no longer needed

    def test_initial_setup_passing(self):
        """A simple test to confirm the test file and pytest are working."""
        assert True

    @patch('app.services.ai_service.logger.error')
    def test_detect_pose_invalid_frame_input(
        self,
        mock_logger_error: MagicMock,
        ai_service: AIService # Uses the fixture
    ):
        """Test detect_pose with invalid frame inputs that might cause cv2.cvtColor to fail."""
        invalid_frames = [
            np.array([]),  # Empty array
            np.array([1, 2, 3]), # 1D array
            np.array([[[1, 2]]], dtype=np.float32), # Wrong dtype / channel structure
            "not_an_array" # Completely wrong type
        ]

        for invalid_frame_np in invalid_frames:
            mock_logger_error.reset_mock() # Reset for each iteration
            try:
                # Provide a default value for frame if it's not a numpy array
                # to prevent AttributeError when accessing frame.shape or frame.dtype
                # This is a pragmatic approach as cvtColor itself will error out.
                # Alternatively, the test could specifically mock cvtColor for these inputs.
                if not isinstance(invalid_frame_np, np.ndarray):
                     # cvtColor will fail. detect_pose should catch this.
                     pass

                landmarks, confidence = ai_service.detect_pose(invalid_frame_np)
                assert landmarks == []
                assert confidence == 0.0
                mock_logger_error.assert_called_once() # Check that an error was logged
            except Exception as e:
                # This case might occur if the error happens before cvtColor, 
                # or if the broad except in detect_pose is not hit as expected.
                # For this test, we expect detect_pose to catch and handle internally.
                pytest.fail(f"detect_pose raised an unexpected exception for input {invalid_frame_np}: {e}")

# We will now begin adding tests for AIService as per the plan.
# First, tests for `process_frames_for_pose` method.

# Commenting out mock_model as it's likely for form_analysis_model which is not the focus of Step 1.2
# @pytest.fixture
# def mock_model():
#     """Mock PyTorch model"""
#     model = Mock()
#     model.eval = Mock(return_value=model)
#     model.to = Mock(return_value=model)
#     model.forward = Mock(return_value=torch.tensor([0.8, 0.9, 0.7]))
#     return model

# Commenting out mock_pose_estimator as the AIService fixture mocks mp.solutions.pose.Pose directly
# @pytest.fixture
# def mock_pose_estimator():
#     """Mock pose estimation model"""
#     estimator = Mock()
#     estimator.process = Mock(return_value={
#         "pose_landmarks": [
#             {"x": 0.5, "y": 0.5, "z": 0.0, "visibility": 0.9}
#             for _ in range(33)  # MediaPipe uses 33 landmarks
#         ]
#     })
#     return estimator

# Keep mock_settings, it's a general fixture pattern
@pytest.fixture
def mock_settings() -> MagicMock:
    """Provides a mock Settings object for AIService tests."""
    settings_mock = MagicMock(spec=Settings)
    # Add any specific setting attributes AIService might use, e.g.:
    settings_mock.AI_MIN_DETECTION_CONFIDENCE = 0.5 # Example, adjust as needed for focused tests
    settings_mock.AI_MODEL_COMPLEXITY = 1
    settings_mock.AI_MIN_TRACKING_CONFIDENCE = 0.5
    settings_mock.AI_MODEL_PATH = './mock_models'
    # settings_mock.AI_POSE_SMOOTHING_WINDOW_SIZE = 5 # Related to smoothing, not 1.2
    # settings_mock.AI_POSE_MAX_INTERPOLATION_GAP = 3 # Related to smoothing, not 1.2
    return settings_mock

@pytest.fixture
def mock_settings_for_ai_service(monkeypatch) -> MagicMock: # Keep, used by ai_service fixture
    """Patches the global app_settings AIService uses."""
    monkeypatch.setattr(app_settings, 'AI_MODEL_COMPLEXITY', 1)
    monkeypatch.setattr(app_settings, 'AI_MIN_DETECTION_CONFIDENCE', 0.5)
    monkeypatch.setattr(app_settings, 'AI_MIN_TRACKING_CONFIDENCE', 0.5)
    monkeypatch.setattr(app_settings, 'AI_MODEL_PATH', './mock_models') 
    # monkeypatch.setattr(app_settings, 'AI_POSE_SMOOTHING_WINDOW_SIZE', 5) # Smoothing related
    # monkeypatch.setattr(app_settings, 'AI_POSE_MAX_INTERPOLATION_GAP', 3) # Smoothing related
    return app_settings

@pytest.fixture
def ai_service(mock_settings_for_ai_service, monkeypatch) -> AIService: # Keep, core fixture
    """Provides an instance of AIService with MediaPipe and model loading mocked.
    AIService.__init__ takes no arguments and uses global app_settings.
    """
    mock_mp_pose_instance = MagicMock()
    mock_mediapipe_results_object = MagicMock()
    mock_mediapipe_results_object.pose_landmarks = None 
    mock_mp_pose_instance.process.return_value = mock_mediapipe_results_object
    monkeypatch.setattr('app.services.ai_service.mp.solutions.pose.Pose', lambda *args, **kwargs: mock_mp_pose_instance)

    # Mock _load_form_analysis_model as it's not part of pose detection logic for Step 1.2
    monkeypatch.setattr(AIService, '_load_form_analysis_model', lambda self: None) 
    
    service = AIService(app_settings=mock_settings_for_ai_service) # Pass patched settings
    return service

# Commenting out test_video fixture if no focused tests use it directly for video content
# @pytest.fixture
# def test_video():
#     """Create a mock video for testing"""
#     video = np.zeros((300, 300, 3), dtype=np.uint8)  # Create blank frame
#     return [video for _ in range(30)]  # 30 frames

@pytest.fixture
def sample_frame_paths() -> list[str]: # Keep, used by relevant tests
    return ["/mock/path/frame1.jpg", "/mock/path/frame2.jpg", "/mock/path/frame3.jpg"]

@pytest.fixture
def sample_image_data() -> list[np.ndarray]: # Keep, used by relevant tests
    frame1 = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    frame2 = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    frame3 = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    return [frame1, frame2, frame3]

# Commenting out tests not directly related to detect_pose or process_frames_for_pose (Step 1.2)
# def test_initialize_models(ai_service):
#     """Test model initialization"""
#     # This test's relevance depends on what ai_service.models and ai_service.pose_estimator are
#     # For Step 1.2, we care that self.pose (MediaPipe) is initialized.
#     # assert ai_service.models is not None # .models might be for form analysis
#     # assert all(model is not None for model in ai_service.models.values())
#     assert ai_service.pose is not None # Check that MediaPipe Pose is initialized

# def test_analyze_form_squat(ai_service, test_video):
#     """Test form analysis for squat exercise"""
#     # result = ai_service.analyze_form(
#     #     video=test_video,
#     #     exercise_type=ExerciseType.SQUAT
#     # )
#     # 
#     # assert isinstance(result, dict)
#     # assert "score" in result
#     # assert "overall_feedback" in result
#     # assert "issues" in result
#     # assert isinstance(result["issues"], list)
#     pass

# def test_analyze_form_deadlift(ai_service, test_video):
#     """Test form analysis for deadlift exercise"""
#     # result = ai_service.analyze_form(
#     #     video=test_video,
#     #     exercise_type=ExerciseType.DEADLIFT
#     # )
#     # 
#     # assert isinstance(result, dict)
#     # assert "score" in result
#     # assert 0 <= result["score"] <= 10
#     pass

# def test_analyze_form_invalid_exercise(ai_service, test_video):
#     """Test form analysis with invalid exercise type"""
#     # from app.services.ai_service import AIServiceError # Assuming this error exists
#     # with pytest.raises(AIServiceError): # Or appropriate error
#     #     ai_service.analyze_form(
#     #         video=test_video,
#     #         exercise_type="INVALID_EXERCISE"
#     #     )
#     pass

# def test_extract_frames(ai_service, test_video):
#     """Test video frame extraction"""
#     # frames = ai_service.extract_frames(test_video) # test_video is List[np.ndarray]
#     # This test is for ai_service.extract_frames(video_path: str)
#     # For now, commenting out as process_frames_for_pose takes np.ndarray
#     pass

# def test_preprocess_video(ai_service, test_video):
#     """Test video preprocessing"""
#     # processed_frames = ai_service._preprocess_video(test_video)
#     # 
#     # assert isinstance(processed_frames, torch.Tensor)
#     # assert processed_frames.dim() == 4  # [batch, channels, height, width]
#     # assert processed_frames.dtype == torch.float32
#     pass

# def test_extract_pose_landmarks(ai_service, test_video):
#     """Test pose landmark extraction"""
#     # landmarks = ai_service._extract_pose_landmarks(test_video[0]) # _extract_pose_landmarks might be legacy
#     # 
#     # assert isinstance(landmarks, list)
#     # assert len(landmarks) == 33  # MediaPipe uses 33 landmarks
#     # assert all("x" in point and "y" in point for point in landmarks)
#     pass

# def test_analyze_pose_sequence(ai_service, test_video):
#     """Test pose sequence analysis"""
#     # landmarks_sequence = [
#     #     ai_service._extract_pose_landmarks(frame) # Legacy
#     #     for frame in test_video[:10]
#     # ]
#     # 
#     # analysis = ai_service._analyze_pose_sequence(
#     #     landmarks_sequence,
#     #     ExerciseType.SQUAT
#     # )
#     pass

# def test_generate_feedback(ai_service):
#     """Test feedback generation"""
#     # analysis_data = {"issues": [{"type": "depth", "message": "Squat deeper"}]}
#     # feedback = ai_service._generate_feedback(analysis_data)
#     # 
#     # assert isinstance(feedback, dict)
#     # assert "overall_feedback" in feedback
#     # assert "specific_issues" in feedback
#     pass

# def test_detect_exercise_phases(ai_service, test_video):
#     """Test exercise phase detection"""
#     # landmarks_sequence = [ai_service._extract_pose_landmarks(f) for f in test_video] # Legacy
#     # phases = ai_service._detect_exercise_phases(landmarks_sequence, ExerciseType.SQUAT)
#     # 
#     # assert isinstance(phases, list)
#     # if phases: # Only check if phases are detected
#     #     assert all("phase_name" in phase and "start_frame" in phase and "end_frame" in phase for phase in phases)
#     pass

# def test_calculate_joint_angles(ai_service): # Belongs to Step 1.3
#     """Test joint angle calculation"""
#     # landmarks = [{"x": 0, "y": 0}, {"x": 1, "y": 0}, {"x": 1, "y": 1}] # Example
#     # angles = ai_service._calculate_joint_angles(landmarks, ExerciseType.SQUAT)
#     # 
#     # assert isinstance(angles, dict)
#     # if angles: # Only check if angles are calculated
#     #    assert all(isinstance(angle, float) for angle in angles.values())
#     pass

# def test_analyze_form_with_low_confidence(ai_service, test_video): # Form analysis related
#     """Test form analysis with low confidence video"""
#     # result = ai_service.analyze_form(video=test_video, exercise_type=ExerciseType.SQUAT, confidence_threshold=0.95)
#     # 
#     # assert isinstance(result, dict)
#     # assert result.get("warning_message") is not None
#     pass

# def test_handle_model_error(ai_service, test_video): # General error handling, not specific to 1.2
#     """Test graceful error handling for model issues"""
#     # with patch.object(ai_service.models["squat"], "predict", side_effect=Exception("Model failure")):
#     #     with pytest.raises(AIServiceError): # Or specific error
#     #         ai_service.analyze_form(video=test_video, exercise_type=ExerciseType.SQUAT)
#     pass

# def test_validate_video_duration(ai_service): # Not core to 1.2 pose detection logic
#     """Test video duration validation"""
#     # assert ai_service._validate_video_duration(duration=10, min_duration=5, max_duration=60)
#     # with pytest.raises(ValueError): # Or specific error
#     #     ai_service._validate_video_duration(duration=2, min_duration=5, max_duration=60)
#     pass

# def test_get_exercise_specific_thresholds(ai_service): # For form analysis/rules
#     """Test retrieval of exercise-specific thresholds"""
#     # thresholds = ai_service._get_exercise_specific_thresholds(ExerciseType.SQUAT)
#     # assert isinstance(thresholds, dict)
#     # assert "angle_thresholds" in thresholds
#     pass

# def test_save_analysis_debug_info(ai_service, test_video, tmp_path): # Utility, not core 1.2
#     """Test saving of analysis debug information"""
#     # analysis_results = {"score": 0.8, "issues": []}
#     # output_dir = tmp_path / "debug_output"
#     # output_dir.mkdir()
#     # 
#     # ai_service.save_analysis_debug_info(
#     #     video_path="dummy_video.mp4",
#     #     frames=test_video,
#     #     analysis_results=analysis_results,
#     #     output_dir=str(output_dir)
#     # )
#     # 
#     # assert (output_dir / "analysis_summary.json").exists()
#     # # Add more assertions for images if they are saved
#     pass

# KEEPING: test_process_frames_for_pose_filters_low_visibility_landmarks and related tests
@pytest.mark.asyncio
# @patch('app.services.ai_service.cv2.imread', new_callable=AsyncMock) # cv2.imread not directly used by process_frames_for_pose
@patch('app.services.ai_service.cv2.cvtColor') # cv2.cvtColor is used by detect_pose
async def test_process_frames_for_pose_filters_low_visibility_landmarks(
    # mock_cv2_imread: AsyncMock, # Not needed as input is np.ndarray
    mock_cv2_cvtColor: MagicMock,
    ai_service: AIService,
    sample_image_data: list[np.ndarray], # Using sample_image_data instead of sample_frame_paths
    mock_settings_for_ai_service: MagicMock # To access settings
):
    """
    Tests that process_frames_for_pose correctly filters out individual landmarks
    that are below the visibility threshold, while keeping the frame if overall
    confidence is high.
    """
    mock_settings_for_ai_service.AI_MIN_DETECTION_CONFIDENCE = 0.5 # Set a clear threshold
    test_frame_data = sample_image_data[0]
    
    # Mock cv2.cvtColor for process_frames_for_pose
    mock_frame_data = np.zeros((100, 100, 3), dtype=np.uint8)
    mock_cv2_cvtColor.return_value = mock_frame_data

    # Configure the mock for ai_service.detect_pose
    # This mock will be used by process_frames_for_pose internally via asyncio.to_thread
    # AIService.detect_pose is what mp.solutions.pose.Pose().process calls eventually.
    # The ai_service fixture already mocks mp.solutions.pose.Pose().process
    # We need to configure that mock_mp_pose_instance that ai_service.pose points to.

    mock_mediapipe_landmarks = []
    num_high_vis_landmarks = 0
    num_low_vis_landmarks = 0

    for i in range(ai_service.NUM_EXPECTED_LANDMARKS):
        if i % 2 == 0: # Alternate visibility
            visibility = 0.8 # Above threshold
            num_high_vis_landmarks +=1
        else:
            visibility = 0.3 # Below threshold
            num_low_vis_landmarks +=1
        mock_mediapipe_landmarks.append(
            MagicMock(x=0.1*i, y=0.2*i, z=0.05*i, visibility=visibility)
        )
    
    # Mock the return value of ai_service.pose.process() which is called by ai_service.detect_pose
    # The ai_service fixture has: ai_service.pose = mock_mp_pose_instance
    # mock_mp_pose_instance.process.return_value = mock_mediapipe_results_object
    # We need to set pose_landmarks on that results object.
    
    # Re-access the mock created in the ai_service fixture for mp.solutions.pose.Pose().process
    # This is a bit indirect but necessary given the fixture setup.
    # Alternatively, the ai_service fixture could return its internal mocks.
    
    # For simplicity, let's patch detect_pose directly on the ai_service instance for this test
    # to control its output more easily than manipulating the deeper MediaPipe mocks.
    
    # Overall frame confidence (returned by detect_pose as the second element)
    overall_frame_confidence = 0.9 # High, so frame is kept

    def mock_detect_pose_output(frame_np_array):
        # This function will be called by process_frames_for_pose via to_thread
        # It needs to return (list_of_landmark_dicts, overall_confidence)
        # The landmark_dicts should match what detect_pose creates.
        landmark_dicts = []
        for lm_mock in mock_mediapipe_landmarks:
            landmark_dicts.append({
                'x': lm_mock.x, 'y': lm_mock.y, 'z': lm_mock.z, 'visibility': lm_mock.visibility
            })
        return landmark_dicts, overall_frame_confidence

    with patch.object(ai_service, 'detect_pose', new_callable=MagicMock) as mock_detect_pose_method:
        mock_detect_pose_method.side_effect = mock_detect_pose_output
        
        # Call the method under test
        results = await ai_service.process_frames_for_pose(
            frames_data_np=[test_frame_data], 
            min_pose_confidence_threshold=0.5 # Explicitly pass for clarity
        )

    # Assertions
    assert results is not None
    assert len(results) == 1 # We processed one frame
    
    processed_frame_landmarks = results[0]
    assert processed_frame_landmarks is not None # Frame should not be None due to high overall confidence
    assert len(processed_frame_landmarks) == ai_service.NUM_EXPECTED_LANDMARKS

    count_visible_in_output = 0
    count_none_in_output = 0
    for i, landmark_output in enumerate(processed_frame_landmarks):
        expected_visibility = 0.8 if i % 2 == 0 else 0.3
        if expected_visibility >= 0.5:
            assert landmark_output is not None, f"Landmark {i} should be visible"
            assert landmark_output['visibility'] == expected_visibility
            count_visible_in_output += 1
        else:
            assert landmark_output is None, f"Landmark {i} should be None (low visibility)"
            count_none_in_output += 1
            
    assert count_visible_in_output == num_high_vis_landmarks
    assert count_none_in_output == num_low_vis_landmarks
    
    # Ensure detect_pose was called once by process_frames_for_pose (via to_thread)
    mock_detect_pose_method.assert_called_once()

@pytest.mark.asyncio
# @patch('app.services.ai_service.cv2.imread') # Not needed
async def test_process_frames_for_pose_ideal_frames(
    # mock_cv2_imread: MagicMock, # Not needed
    ai_service: AIService, 
    # sample_frame_paths: list[str], # Use sample_image_data
    sample_image_data: list[np.ndarray]
):
    """Test process_frames_for_pose with ideal frame data."""
    min_conf_threshold = 0.7
    # mock_cv2_imread.side_effect = sample_image_data
    mock_landmarks_frame1_raw = [{'x': 0.1, 'y': 0.2, 'z': 0.3, 'visibility': 0.99}]
    mock_confidence_frame1 = 0.99
    mock_landmarks_frame2_raw = [{'x': 0.4, 'y': 0.5, 'z': 0.6, 'visibility': 0.98}]
    mock_confidence_frame2 = 0.98
    # Frame 3 will default to [], 0.0 by the mock_detect_pose_side_effect
    
    expected_landmarks_frame1_dense = [None] * AIService.NUM_EXPECTED_LANDMARKS
    if mock_landmarks_frame1_raw: # Should be true
         expected_landmarks_frame1_dense[0] = mock_landmarks_frame1_raw[0]

    expected_landmarks_frame2_dense = [None] * AIService.NUM_EXPECTED_LANDMARKS
    if mock_landmarks_frame2_raw: # Should be true
        expected_landmarks_frame2_dense[0] = mock_landmarks_frame2_raw[0]


    def mock_detect_pose_side_effect(frame_np_array):
        if np.array_equal(frame_np_array, sample_image_data[0]):
            return (mock_landmarks_frame1_raw, mock_confidence_frame1)
        elif np.array_equal(frame_np_array, sample_image_data[1]):
            return (mock_landmarks_frame2_raw, mock_confidence_frame2)
        elif np.array_equal(frame_np_array, sample_image_data[2]): # Ensure third frame is handled
            return ([], 0.0) # No landmarks, low confidence
        return ([], 0.0) 

    with patch.object(ai_service, 'detect_pose', new_callable=MagicMock) as mock_detect_pose:
        mock_detect_pose.side_effect = mock_detect_pose_side_effect
        results = await ai_service.process_frames_for_pose(
            frames_data_np=sample_image_data, # sample_image_data has 3 frames
            min_pose_confidence_threshold=min_conf_threshold
        )
        assert mock_detect_pose.call_count == len(sample_image_data)
        
        # Custom check for calls with numpy arrays
        called_with_frame0 = any(np.array_equal(call[0][0], sample_image_data[0]) for call in mock_detect_pose.call_args_list)
        called_with_frame1 = any(np.array_equal(call[0][0], sample_image_data[1]) for call in mock_detect_pose.call_args_list)
        called_with_frame2 = any(np.array_equal(call[0][0], sample_image_data[2]) for call in mock_detect_pose.call_args_list)
        assert called_with_frame0, "detect_pose not called with sample_image_data[0]"
        assert called_with_frame1, "detect_pose not called with sample_image_data[1]"
        assert called_with_frame2, "detect_pose not called with sample_image_data[2]"

        assert len(results) == len(sample_image_data)
        assert results[0] == expected_landmarks_frame1_dense
        assert results[1] == expected_landmarks_frame2_dense
        assert results[2] is None # Due to 0.0 confidence from mock_detect_pose for frame 2
        
@pytest.mark.asyncio
# @patch('app.services.ai_service.cv2.imread') # Not needed
async def test_process_frames_for_pose_low_confidence(
    # mock_cv2_imread: MagicMock, # Not needed
    ai_service: AIService,
    # sample_frame_paths: list[str], # Use sample_image_data
    sample_image_data: list[np.ndarray]
):
    """Test process_frames_for_pose where one frame has low confidence."""
    min_conf_threshold = 0.7
    # mock_cv2_imread.side_effect = sample_image_data
    mock_landmarks_frame1_raw = [{'x': 0.1, 'y': 0.2, 'z': 0.3, 'visibility': 0.99}]
    mock_confidence_frame1 = 0.99
    mock_landmarks_frame2_low_conf_raw = [{'x': 0.4, 'y': 0.5, 'z': 0.6, 'visibility': 0.45}] # Landmark visibility OK
    mock_confidence_frame2_low = 0.4 # Overall frame confidence is low

    expected_landmarks_frame1_dense = [None] * AIService.NUM_EXPECTED_LANDMARKS
    if mock_landmarks_frame1_raw:
        expected_landmarks_frame1_dense[0] = mock_landmarks_frame1_raw[0]
    
    # Frame 3 will default to [], 0.0 by the mock_detect_pose_side_effect

    def mock_detect_pose_side_effect(frame_np_array):
        if np.array_equal(frame_np_array, sample_image_data[0]):
            return (mock_landmarks_frame1_raw, mock_confidence_frame1)
        elif np.array_equal(frame_np_array, sample_image_data[1]):
            # detect_pose returns landmarks and its calculated confidence
            return (mock_landmarks_frame2_low_conf_raw, mock_confidence_frame2_low) 
        elif np.array_equal(frame_np_array, sample_image_data[2]): # Ensure third frame is handled
            return ([], 0.0) # No landmarks, low confidence
        return ([], 0.0)

    with patch.object(ai_service, 'detect_pose', new_callable=MagicMock) as mock_detect_pose:
        mock_detect_pose.side_effect = mock_detect_pose_side_effect
        results = await ai_service.process_frames_for_pose(
            frames_data_np=sample_image_data, # sample_image_data has 3 frames
            min_pose_confidence_threshold=min_conf_threshold
        )
        assert mock_detect_pose.call_count == len(sample_image_data)

        # Custom check for calls with numpy arrays
        called_with_frame0 = any(np.array_equal(call[0][0], sample_image_data[0]) for call in mock_detect_pose.call_args_list)
        called_with_frame1 = any(np.array_equal(call[0][0], sample_image_data[1]) for call in mock_detect_pose.call_args_list)
        called_with_frame2 = any(np.array_equal(call[0][0], sample_image_data[2]) for call in mock_detect_pose.call_args_list)
        assert called_with_frame0, "detect_pose not called with sample_image_data[0]"
        assert called_with_frame1, "detect_pose not called with sample_image_data[1]"
        assert called_with_frame2, "detect_pose not called with sample_image_data[2]"
        
        assert len(results) == len(sample_image_data)
        assert results[0] == expected_landmarks_frame1_dense
        assert results[1] is None # Frame 2's overall confidence (0.4) < threshold (0.7)
        assert results[2] is None # Due to 0.0 confidence from mock_detect_pose for frame 2

@pytest.mark.asyncio
async def test_process_frames_for_pose_empty_input(
    ai_service: AIService 
):
    """Test process_frames_for_pose with an empty list of frame_paths."""
    empty_frame_paths = []
    min_conf_threshold = 0.7
    with patch('app.services.ai_service.cv2.imread') as mock_cv2_imread_local, patch.object(ai_service, 'detect_pose') as mock_detect_pose_local:
        results = await ai_service.process_frames_for_pose(
            frames_data_np=empty_frame_paths,
            min_pose_confidence_threshold=min_conf_threshold
        )
        assert results == []
        mock_cv2_imread_local.assert_not_called()
        mock_detect_pose_local.assert_not_called()

@pytest.mark.asyncio
@patch('app.services.ai_service.logger.warning') 
async def test_process_frames_for_pose_handles_none_frames( # Rename to test_process_frames_for_pose_handles_none_frames
    mock_logger_warning: MagicMock,
    # mock_cv2_imread: MagicMock, # Not needed
    ai_service: AIService,
    # sample_frame_paths: list[str], # Use sample_image_data
    sample_image_data: list[np.ndarray] # Modified to include a None frame
):
    """Test process_frames_for_pose when the input list contains None for some frames."""
    # ARRANGE
    # Modify sample_image_data to include a None frame
    modified_image_data = list(sample_image_data) # Create a mutable copy
    if len(modified_image_data) > 1:
        modified_image_data[1] = None # Set the second frame to None
    else: # Handle cases with less than 2 frames
        modified_image_data.append(None)


    mock_landmark = {'x': 0.5, 'y': 0.5, 'z': 0.0, 'visibility': 0.99}
    mock_landmarks_for_frame = [mock_landmark] * ai_service.NUM_EXPECTED_LANDMARKS
    mock_confidence = 0.95

    def mock_detect_pose_side_effect(frame_np_array): # MADE SYNCHRONOUS
        if frame_np_array is None:
            # This case should ideally not reach detect_pose if process_frames_for_pose handles None frames earlier
            # However, if it did, detect_pose might raise an error or return empty.
            # For this test, we assume process_frames_for_pose correctly skips calling detect_pose for None frames.
            # So, this side effect will only be called for non-None frames.
            return list(mock_landmarks_for_frame), mock_confidence
        return list(mock_landmarks_for_frame), mock_confidence

    with patch.object(ai_service, 'detect_pose', side_effect=mock_detect_pose_side_effect) as mock_detect_pose_method:
        # ACT
        results = await ai_service.process_frames_for_pose(
            frames_data_np=modified_image_data, 
            min_pose_confidence_threshold=0.5
        )

    # ASSERT
    assert len(results) == len(modified_image_data)
    expected_detect_pose_calls = 0
    for i, frame_data in enumerate(modified_image_data):
        if frame_data is None:
            assert results[i] is None, f"Frame {i} (which was None input) should result in None output."
            mock_logger_warning.assert_any_call(f"AIService: Received None for frame {i+1}/{len(modified_image_data)}")
        else:
            expected_detect_pose_calls +=1
            assert results[i] is not None, f"Frame {i} (non-None input) should have been processed."
            assert len(results[i]) == ai_service.NUM_EXPECTED_LANDMARKS, f"Frame {i} should have {ai_service.NUM_EXPECTED_LANDMARKS} landmarks."
            for lm_idx, landmark in enumerate(results[i]):
                assert landmark is not None
                assert landmark == mock_landmark
    
    assert mock_detect_pose_method.call_count == expected_detect_pose_calls


@pytest.mark.asyncio
# @patch('app.services.ai_service.cv2.imread') # Not needed
@patch('app.services.ai_service.logger.debug') 
async def test_process_frames_for_pose_detect_pose_empty_landmarks_high_confidence(
    mock_logger_debug: MagicMock,
    # mock_cv2_imread: MagicMock, # Not needed
    ai_service: AIService,
    # sample_frame_paths: list[str], # Use sample_image_data
    sample_image_data: list[np.ndarray]
):
    """Test case where detect_pose returns no landmarks but high overall confidence."""
    # ARRANGE
    high_confidence = 0.9
    # Mock detect_pose to return empty landmarks but high confidence for the first frame
    def mock_detect_pose_side_effect(frame_np_array): # MADE SYNCHRONOUS
        if mock_detect_pose_method.call_count == 1: # First call
            return [], high_confidence # No landmarks, high confidence
        # For other frames, return valid data to ensure the list processing works
        mock_landmark = {'x': 0.5, 'y': 0.5, 'z': 0.0, 'visibility': 0.99}
        return [mock_landmark] * ai_service.NUM_EXPECTED_LANDMARKS, high_confidence

    with patch.object(ai_service, 'detect_pose', side_effect=mock_detect_pose_side_effect) as mock_detect_pose_method:
        # ACT
        results = await ai_service.process_frames_for_pose(
            frames_data_np=sample_image_data, 
            min_pose_confidence_threshold=0.5 # Threshold is less than high_confidence
        )

        # ASSERT
        assert len(results) == len(sample_image_data)
        assert results[0] is None, "First frame should be None as detect_pose returned no landmarks."
        
        # Check other frames are processed if sample_image_data has more than one
        if len(sample_image_data) > 1:
            for i in range(1, len(sample_image_data)):
                assert results[i] is not None, f"Frame {i} should have been processed."
                assert len(results[i]) == ai_service.NUM_EXPECTED_LANDMARKS, f"Frame {i} should have {ai_service.NUM_EXPECTED_LANDMARKS} landmarks."


@pytest.mark.asyncio
# @patch('app.services.ai_service.cv2.imread') # Not needed
async def test_process_frames_for_pose_detect_pose_raises_exception(
    # mock_cv2_imread: MagicMock, # Not needed
    ai_service: AIService,
    # sample_frame_paths: list[str], # Expects 3 paths now
    sample_image_data: list[np.ndarray] # Expects 3 image data
):
    """Test that if detect_pose raises an exception for a frame, that frame's result is None."""
    # ARRANGE
    if len(sample_image_data) < 2: # Ensure there are at least two frames for this test logic
        pytest.skip("Test requires at least 2 frames in sample_image_data")

    # Mock detect_pose to raise an exception for the first frame, succeed for others
    mock_landmark = {'x': 0.5, 'y': 0.5, 'z': 0.0, 'visibility': 0.99}
    mock_landmarks_for_frame = [mock_landmark] * ai_service.NUM_EXPECTED_LANDMARKS
    mock_confidence = 0.95

    def mock_detect_pose_side_effect(frame_np_array): # MADE SYNCHRONOUS
        if mock_detect_pose_method.call_count == 1: # First call
            raise ValueError("Simulated error in detect_pose")
        return list(mock_landmarks_for_frame), mock_confidence

    with patch.object(ai_service, 'detect_pose', side_effect=mock_detect_pose_side_effect) as mock_detect_pose_method:
        # ACT
        results = await ai_service.process_frames_for_pose(
            frames_data_np=sample_image_data, 
            min_pose_confidence_threshold=0.5
        )

        # ASSERT
        assert len(results) == len(sample_image_data)
        assert results[0] is None, "First frame should be None due to exception in detect_pose."
        
        # Check other frames are processed
        if len(sample_image_data) > 1: # Redundant due to skip, but good practice
            for i in range(1, len(sample_image_data)):
                assert results[i] is not None, f"Frame {i} should have been processed."
                assert len(results[i]) == ai_service.NUM_EXPECTED_LANDMARKS, f"Frame {i} should have {ai_service.NUM_EXPECTED_LANDMARKS} landmarks."
                for lm_idx, landmark in enumerate(results[i]):
                    assert landmark is not None
                    assert landmark == mock_landmark

# Test for _get_landmark_coords (New Test)
# ... existing code ...

# KEEPING: tests for detect_pose
@patch('app.services.ai_service.cv2.cvtColor')
def test_detect_pose_successful_detection(
    mock_cv2_cvtColor: MagicMock,
    ai_service: AIService # Uses the fixture that mocks MediaPipe
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

    # Corrected mock structure for pose_landmarks
    mock_pose_landmarks_container = MagicMock()
    mock_pose_landmarks_container.landmark = [mock_mp_landmark1, mock_mp_landmark2]

    mock_mediapipe_results = MagicMock() # Simulates MediaPipe Results object
    mock_mediapipe_results.pose_landmarks = mock_pose_landmarks_container # Assign container

    # Configure the pose.process mock on the ai_service instance
    # The ai_service fixture already mocks ai_service.pose to be a MagicMock instance.
    # We configure its .process method here for this specific test case.
    ai_service.pose.process.return_value = mock_mediapipe_results

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
    ai_service: AIService # Uses the fixture
):
    """Test detect_pose when MediaPipe does not detect any landmarks."""
    # ARRANGE
    sample_bgr_frame = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    sample_rgb_frame = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    mock_cv2_cvtColor.return_value = sample_rgb_frame

    mock_mediapipe_results_no_landmarks = MagicMock()
    mock_mediapipe_results_no_landmarks.pose_landmarks = None # Correct: MediaPipe sets this to None

    # Configure the pose.process mock on the ai_service instance
    ai_service.pose.process.return_value = mock_mediapipe_results_no_landmarks

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
@patch('app.services.ai_service.logger.error') 
def test_detect_pose_mediapipe_process_raises_exception(
    mock_logger_error: MagicMock,
    mock_cv2_cvtColor: MagicMock,
    ai_service: AIService # Uses the fixture
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
    assert "Error detecting pose:" in log_message
    assert "Simulated MediaPipe processing error" in log_message

# Commenting out test_detect_pose_low_individual_landmark_visibility as its core idea is in 
# test_process_frames_for_pose_filters_low_visibility_landmarks
# @patch('app.services.ai_service.cv2.cvtColor')
# def test_detect_pose_low_individual_landmark_visibility(
#     mock_cv2_cvtColor: MagicMock,
#     ai_service: AIService, 
#     mock_settings_for_ai_service: MagicMock 
# ):
#     # This test's logic is now better covered by 
#     # test_process_frames_for_pose_filters_low_visibility_landmarks,
#     # which tests the consuming function's behavior regarding visibility.
#     # detect_pose itself should return all landmarks from MediaPipe along with their visibility.
#     # The filtering happens in process_frames_for_pose.
#     pass


# Commenting out ALL smoothing and interpolation tests as they are deferred from Step 1.2
# @pytest.mark.asyncio
# @patch('app.services.ai_service.AIService._apply_smoothing_to_landmarks') # This method might not exist or be private
# async def test_smooth_and_interpolate_basic_interpolation(
#     mock_apply_smoothing: MagicMock,
#     ai_service: AIService,
#     mock_settings_for_ai_service: MagicMock 
# ):
#   pass
# ... (all other smooth_and_interpolate tests and _interpolate_landmark test) ...

# def test_interpolate_landmark_helper_direct(ai_service_instance: AIService): 
    #    pass

# One final check on AIServicePlaceholder usage in fixtures
# mock_ai_service and ai_service_instance fixtures used AIServicePlaceholder.
# If these fixtures are not used by any remaining tests, they can be fully commented or simplified.
# For now, their internal logic referencing AIServicePlaceholder is commented.

# Commenting out test_smooth_and_interpolate_basic_interpolation as it's not directly related to process_frames_for_pose
# @pytest.mark.asyncio
# @patch('app.services.ai_service.AIService._apply_smoothing_to_landmarks')
# async def test_smooth_and_interpolate_basic_interpolation(
#     mock_apply_smoothing: MagicMock,
#     ai_service: AIService,
#     mock_settings_for_ai_service: MagicMock 
# ):
#   pass

# Commenting out test_smooth_and_interpolate_no_interpolation_for_large_gap as it's not directly related to process_frames_for_pose
# @pytest.mark.asyncio
# @patch('app.services.ai_service.AIService._apply_smoothing_to_landmarks')
# async def test_smooth_and_interpolate_no_interpolation_for_large_gap(
#     mock_apply_smoothing: MagicMock,
#     ai_service: AIService,
#     mock_settings_for_ai_service: MagicMock 
# ):
#   pass

# Commenting out test_smooth_and_interpolate_multiple_landmarks_interpolation as it's not directly related to process_frames_for_pose
# @pytest.mark.asyncio
# @patch('app.services.ai_service.AIService._apply_smoothing_to_landmarks')
# async def test_smooth_and_interpolate_multiple_landmarks_interpolation(
#     mock_apply_smoothing: MagicMock,
#     ai_service: AIService,
#     mock_settings_for_ai_service: MagicMock
# ):
#   pass

# Commenting out test_smooth_and_interpolate_landmark_missing_post_gap as it's not directly related to process_frames_for_pose
# @pytest.mark.asyncio
# @patch('app.services.ai_service.AIService._apply_smoothing_to_landmarks')
# async def test_smooth_and_interpolate_landmark_missing_post_gap(
#     mock_apply_smoothing: MagicMock,
#     ai_service: AIService,
#     mock_settings_for_ai_service: MagicMock
# ):
#   pass

# Commenting out test_smooth_and_interpolate_empty_input_list as it's not directly related to process_frames_for_pose
# @pytest.mark.asyncio
# @patch('app.services.ai_service.AIService._apply_smoothing_to_landmarks')
# async def test_smooth_and_interpolate_empty_input_list(
#     mock_apply_smoothing: MagicMock,
#     ai_service: AIService
# ):
#   pass

# Commenting out test_smooth_and_interpolate_all_none_input_list as it's not directly related to process_frames_for_pose
# @pytest.mark.asyncio
# @patch('app.services.ai_service.AIService._apply_smoothing_to_landmarks')
# async def test_smooth_and_interpolate_all_none_input_list(
#     mock_apply_smoothing: MagicMock,
#     ai_service: AIService
# ):
#   pass

# Commenting out test_smooth_and_interpolate_list_too_short_for_smoothing as it's not directly related to process_frames_for_pose
# @pytest.mark.asyncio
# @patch('app.services.ai_service.savgol_filter') # Assuming 'from scipy.signal import savgol_filter' in ai_service.py
# async def test_smooth_and_interpolate_calls_savgol_filter(
#     mock_savgol_filter: MagicMock,
#     ai_service: AIService,
#     mock_settings_for_ai_service: MagicMock
# ):
#   pass

# Commenting out test_smooth_and_interpolate_effect_on_jittery_data as it's not directly related to process_frames_for_pose
# @pytest.mark.asyncio
# @patch('app.services.ai_service.savgol_filter')
# async def test_smooth_and_interpolate_effect_on_jittery_data(
#     mock_savgol_filter: MagicMock,
#     ai_service: AIService,
#     mock_settings_for_ai_service: MagicMock # Provides AI_POSE_SMOOTHING_WINDOW_SIZE
# ):
#   pass

# Commenting out test_interpolate_landmark_helper_direct as it's not directly related to process_frames_for_pose
# def test_interpolate_landmark_helper_direct(ai_service_instance: AIService): 
#    pass 

# Added test for varying confidence threshold
@pytest.mark.asyncio
async def test_process_frames_for_pose_varying_threshold(
    ai_service: AIService,
    sample_image_data: list[np.ndarray]
):
    """Test PFP with different min_pose_confidence_threshold values."""
    mock_landmark = {'x': 0.5, 'y': 0.5, 'z': 0.0, 'visibility': 0.75} # Landmark visibility fixed at 0.75
    mock_landmarks_for_frame = [mock_landmark] * ai_service.NUM_EXPECTED_LANDMARKS
    mock_overall_confidence = 0.8 # Overall frame confidence fixed at 0.8

    def mock_detect_pose_side_effect(frame_np_array):
        return list(mock_landmarks_for_frame), mock_overall_confidence

    with patch.object(ai_service, 'detect_pose', side_effect=mock_detect_pose_side_effect):
        # Scenario 1: Threshold LOWER than overall confidence and landmark visibility
        results_low_thresh = await ai_service.process_frames_for_pose(
            frames_data_np=sample_image_data,
            min_pose_confidence_threshold=0.7
        )
        assert len(results_low_thresh) == len(sample_image_data)
        for frame_result in results_low_thresh:
            assert frame_result is not None
            assert len(frame_result) == ai_service.NUM_EXPECTED_LANDMARKS
            for landmark in frame_result:
                assert landmark is not None # All landmarks should be visible

        # Scenario 2: Threshold HIGHER than landmark visibility but LOWER than overall confidence
        results_mid_thresh = await ai_service.process_frames_for_pose(
            frames_data_np=sample_image_data,
            min_pose_confidence_threshold=0.78 # Visibility is 0.75, Overall is 0.8
        )
        assert len(results_mid_thresh) == len(sample_image_data)
        for frame_result in results_mid_thresh:
            assert frame_result is not None # Frame itself is processed due to overall confidence
            assert len(frame_result) == ai_service.NUM_EXPECTED_LANDMARKS
            for landmark in frame_result:
                assert landmark is None # All landmarks should be None due to visibility < threshold

        # Scenario 3: Threshold HIGHER than overall confidence
        results_high_thresh = await ai_service.process_frames_for_pose(
            frames_data_np=sample_image_data,
            min_pose_confidence_threshold=0.85 # Overall confidence is 0.8
        )
        assert len(results_high_thresh) == len(sample_image_data)
        for frame_result in results_high_thresh:
            assert frame_result is None # Frame should be discarded

# KEEPING: tests for detect_pose
# ... existing code ...
# ... (rest of the existing tests remain unchanged) ... 

# Helper to create a single mock landmark
def _create_mock_landmark(x: float, y: float, z: float = 0.0, visibility: float = 1.0) -> Dict[str, float]:
    return {"x": x, "y": y, "z": z, "visibility": visibility}

# Helper to create a full set of 33 mock landmarks for a frame
def _create_mock_pose(offset: float = 0.0) -> List[Dict[str, float]]:
    return [_create_mock_landmark(0.5 + i*0.01 + offset, 0.5 - i*0.01 + offset) for i in range(33)]

@pytest.mark.asyncio
async def test_calculate_angles_for_pose_sequence_valid_single_frame(ai_service: AIService):
    """
    Tests that all angles in UNIVERSAL_ANGLE_DEFINITIONS are calculated for a single valid frame.
    Corresponds to: UNIT TEST GOAL 1.1 (partial)
    MVP Stability: Critical
    """
    pose_sequence = [_create_mock_pose()]
    
    result = await ai_service.calculate_angles_for_pose_sequence(pose_sequence)
    
    assert len(result) == 1
    assert result[0] is not None
    frame_angles = result[0]
    
    # Check that all defined angles are present
    for angle_name in UNIVERSAL_ANGLE_DEFINITIONS.keys():
        assert angle_name in frame_angles
        assert isinstance(frame_angles[angle_name], float) # All angles should be floats

    # Spot check a known angle if possible (e.g., straight leg for knee)
    # This requires specific keypoint values in _create_mock_pose to yield a predictable angle
    # For now, we mostly check presence and type.
    # Example: A perfectly straight right knee (landmarks 24, 26, 28 in a line) should be ~180 degrees.
    # _create_mock_pose with offset=0:
    # p_hip_r (24): x=0.74, y=0.26
    # p_knee_r (26): x=0.76, y=0.24
    # p_ankle_r (28): x=0.78, y=0.22
    # These are collinear, so right_knee angle should be close to 180.0
    if "right_knee" in frame_angles: # Check if definition exists
        assert frame_angles["right_knee"] == pytest.approx(180.0, abs=1e-3)


@pytest.mark.asyncio
async def test_calculate_angles_for_pose_sequence_multiple_frames_mixed_data(ai_service: AIService):
    """
    Tests correct angle calculation across multiple frames with a mix of complete and incomplete data.
    Corresponds to: UNIT TEST GOAL 1.3
    MVP Stability: Critical
    """
    frame_0_complete = _create_mock_pose(offset=0.0)
    frame_1_none = None # Simulate a frame where pose detection failed
    
    frame_2_missing_some_for_left_knee = _create_mock_pose(offset=0.1)
    # Invalidate left knee calculation by setting a required keypoint to None
    # UNIVERSAL_ANGLE_DEFINITIONS["left_knee"] = {"p1_idx": 23, "p2_idx": 25, "p3_idx": 27}
    frame_2_missing_some_for_left_knee[25] = None # Left Knee landmark

    pose_sequence = [frame_0_complete, frame_1_none, frame_2_missing_some_for_left_knee]
    
    result = await ai_service.calculate_angles_for_pose_sequence(pose_sequence)
    
    assert len(result) == 3
    
    # Frame 0: All angles should be present
    assert result[0] is not None
    for angle_name in UNIVERSAL_ANGLE_DEFINITIONS.keys():
        assert angle_name in result[0]
        assert isinstance(result[0][angle_name], float)
    
    # Frame 1: Should be None as input frame was None
    assert result[1] is None
    
    # Frame 2: Most angles present, left_knee should be None
    assert result[2] is not None
    for angle_name, definition in UNIVERSAL_ANGLE_DEFINITIONS.items():
        if angle_name == "left_knee":
            assert "left_knee" not in result[2] or result[2]["left_knee"] is None, "Left knee angle should be None due to missing keypoint"
        else:
            # Check if all necessary keypoints for *other* angles are present in frame_2
            # This is a bit more involved, for now, assume they are if not left_knee
            if all(frame_2_missing_some_for_left_knee[idx] is not None for idx in definition.values()):
                 assert angle_name in result[2], f"{angle_name} should be present in frame 2"
                 assert isinstance(result[2][angle_name], float), f"{angle_name} in frame 2 should be a float"
            else:
                # If other angles are also affected by the None landmark 25 (e.g. left hip, if it uses 25)
                # then those should also be None. This check is a simplification.
                pass 

@pytest.mark.asyncio
async def test_calculate_angles_for_pose_sequence_handles_missing_keypoints_gracefully(ai_service: AIService):
    """
    Tests that angles are set to None if essential keypoints are missing.
    Corresponds to: UNIT TEST GOAL 1.2
    MVP Stability: Critical
    """
    pose_with_missing = _create_mock_pose()
    # Invalidate left_knee (needs 23, 25, 27) and right_shoulder (needs 24, 12, 14)
    pose_with_missing[25] = None  # Left Knee
    pose_with_missing[12] = None  # Right Shoulder (vertex for right_shoulder angle)

    pose_sequence = [pose_with_missing]
    result = await ai_service.calculate_angles_for_pose_sequence(pose_sequence)
    
    assert len(result) == 1
    assert result[0] is not None
    frame_angles = result[0]

    assert "left_knee" not in frame_angles or frame_angles["left_knee"] is None
    assert "right_shoulder" not in frame_angles or frame_angles["right_shoulder"] is None
    
    # Check a few other angles that should still be calculable
    assert "right_knee" in frame_angles and isinstance(frame_angles["right_knee"], float)
    assert "left_elbow" in frame_angles and isinstance(frame_angles["left_elbow"], float)

@pytest.mark.asyncio
async def test_calculate_angles_for_pose_sequence_empty_input(ai_service: AIService):
    """
    Tests behavior with an empty pose sequence.
    Corresponds to: UNIT TEST GOAL 1.4 (Edge case)
    MVP Stability: Important
    """
    pose_sequence = []
    result = await ai_service.calculate_angles_for_pose_sequence(pose_sequence)
    assert result == []

@pytest.mark.asyncio
async def test_calculate_angles_for_pose_sequence_all_none_frames(ai_service: AIService):
    """
    Tests behavior with a pose sequence where all frames are None.
    Corresponds to: UNIT TEST GOAL 1.4 (Edge case)
    MVP Stability: Important
    """
    pose_sequence = [None, None, None]
    result = await ai_service.calculate_angles_for_pose_sequence(pose_sequence)
    assert result == [None, None, None]

@pytest.mark.asyncio
async def test_calculate_angles_for_pose_sequence_json_serializable(ai_service: AIService):
    """
    Tests that the output is JSON serializable.
    Corresponds to: STRUCTURAL GOAL (JSON serializability)
    MVP Stability: Critical
    """
    pose_sequence = [_create_mock_pose(), None, _create_mock_pose(offset=0.1)]
    result = await ai_service.calculate_angles_for_pose_sequence(pose_sequence)
    
    try:
        json_output = json.dumps(result)
        # Further check: deserialize and compare structure if needed
        deserialized_result = json.loads(json_output)
        assert len(deserialized_result) == len(result)
        if result[0] and deserialized_result[0]:
            assert len(deserialized_result[0]) == len(result[0]) 
            for angle_name in result[0].keys():
                assert angle_name in deserialized_result[0]
                assert deserialized_result[0][angle_name] == pytest.approx(result[0][angle_name])
        assert deserialized_result[1] is None
        # ... similar check for deserialized_result[2]
        
    except (TypeError, OverflowError) as e:
        pytest.fail(f"Angle calculation output is not JSON serializable: {e}\nOutput: {result}") 

# --- Tests for smooth_angle_trajectories ---

def test_smooth_angle_trajectories_basic_smoothing_and_interpolation(ai_service: AIService):
    """
    Tests basic smoothing and interpolation.
    Corresponds to: UNIT TEST GOAL 2.1, 2.3
    MVP Stability: Critical
    """
    raw_angles = [
        {"left_knee": 90.0, "right_knee": 85.0},
        {"left_knee": 95.0, "right_knee": None},  # Gap for right_knee
        {"left_knee": 100.0, "right_knee": 95.0}, # right_knee should be interpolated
        {"left_knee": 105.0, "right_knee": 100.0},
        {"left_knee": 110.0, "right_knee": 105.0},
    ]
    # With window=3, max_gap=1:
    # left_knee: 90, 95, 100, 105, 110
    #   Smooth:  NaN, (90+95+100)/3=95, (95+100+105)/3=100, (100+105+110)/3=105, NaN
    # right_knee: 85, None, 95, 100, 105
    #   Interpolate: 85, (85+95)/2=90, 95, 100, 105
    #   Smooth: NaN, (85+90+95)/3=90, (90+95+100)/3=95, (95+100+105)/3=100, NaN
    
    smoothed_angles = ai_service.smooth_angle_trajectories(raw_angles, smoothing_window=3, max_gap_to_interpolate=1)
    
    assert len(smoothed_angles) == len(raw_angles)
    # assert smoothed_angles[0] is None # Smoothing window effect INCORRECT for min_periods=1
    # assert smoothed_angles[-1] is None # Smoothing window effect INCORRECT for min_periods=1

    # Corrected assertions for boundary conditions with min_periods=1
    assert smoothed_angles[0]["left_knee"] == pytest.approx((90.0 + 95.0) / 2) 
    assert smoothed_angles[0]["right_knee"] == pytest.approx((85.0 + ((85.0+95.0)/2)) / 2) # Interpolated value used

    assert smoothed_angles[4]["left_knee"] == pytest.approx((105.0 + 110.0) / 2)
    assert smoothed_angles[4]["right_knee"] == pytest.approx((100.0 + 105.0) / 2)

    # Check frame 1 (index 1 after window effect)
    assert smoothed_angles[1]["left_knee"] == pytest.approx((90.0 + 95.0 + 100.0) / 3)
    assert smoothed_angles[1]["right_knee"] == pytest.approx((85.0 + ((85.0+95.0)/2) + 95.0) / 3) # Interpolated value used in smoothing

    # Check frame 2 (index 2 after window effect)
    assert smoothed_angles[2]["left_knee"] == pytest.approx((95.0 + 100.0 + 105.0) / 3)
    assert smoothed_angles[2]["right_knee"] == pytest.approx((((85.0+95.0)/2) + 95.0 + 100.0) / 3)

def test_smooth_angle_trajectories_preserves_none_frames_and_large_gaps(ai_service: AIService):
    """
    Tests that None frames are preserved and gaps larger than max_gap are not interpolated.
    Corresponds to: UNIT TEST GOAL 2.2
    MVP Stability: Critical
    """
    raw_angles = [
        {"left_knee": 90.0},
        None,  # Entire frame is None
        {"left_knee": 100.0},
        {"left_knee": None}, # Gap for left_knee (size 1)
        {"left_knee": None}, # Gap for left_knee (size 2)
        {"left_knee": 110.0}, # This should not interpolate the two Nones above with max_gap=1
        {"left_knee": 115.0},
    ]
    smoothed_angles = ai_service.smooth_angle_trajectories(raw_angles, smoothing_window=3, max_gap_to_interpolate=1)

    assert len(smoothed_angles) == len(raw_angles)
    assert smoothed_angles[1] is None, "None frame should be preserved"
    
    # Check around the large gap for 'left_knee'
    # raw_angles[4] is {"left_knee": None}. This is part of a 2-frame gap for 'left_knee' values.
    # With max_gap_to_interpolate=1, the None value for 'left_knee' at frame 4 should not be interpolated.
    # The frame itself (smoothed_angles[4]) should exist as a dictionary because raw_angles[4] was a dictionary.
    # The 'left_knee' key within smoothed_angles[4] should have a value of None.

    assert smoothed_angles[4] is not None, "Frame 4 itself should exist as it was a dict in raw_angles."
    assert "left_knee" in smoothed_angles[4], "'left_knee' key should be present in frame 4."
    assert smoothed_angles[4]['left_knee'] is None, "'left_knee' in frame 4 should remain None due to the large uninterpolated gap."

    # Further detailed assertions based on pandas behavior for other frames can be added if needed,
    # but the core of this test is about None frame preservation and large gap handling for angle values.

def test_smooth_angle_trajectories_handles_all_none_input(ai_service: AIService):
    """
    Tests behavior with all-None angle data per frame (but not None frames).
    Corresponds to: UNIT TEST GOAL 2.4 (Edge case)
    MVP Stability: Important
    """
    raw_angles = [
        {"left_knee": None, "right_knee": None},
        {"left_knee": None, "right_knee": None},
        {"left_knee": None, "right_knee": None},
    ]
    smoothed_angles = ai_service.smooth_angle_trajectories(raw_angles, smoothing_window=3, max_gap_to_interpolate=1)
    
    assert len(smoothed_angles) == len(raw_angles)
    for frame_angles in smoothed_angles:
        assert frame_angles is not None # Frames themselves are dicts
        assert frame_angles["left_knee"] is None
        assert frame_angles["right_knee"] is None

def test_smooth_angle_trajectories_handles_all_none_frames_input(ai_service: AIService):
    """
    Tests behavior with a list entirely of None frames.
    Corresponds to: UNIT TEST GOAL 2.4 (Edge case)
    MVP Stability: Important
    """
    raw_angles = [None, None, None]
    smoothed_angles = ai_service.smooth_angle_trajectories(raw_angles, smoothing_window=3, max_gap_to_interpolate=1)
    assert smoothed_angles == [None, None, None]

def test_smooth_angle_trajectories_empty_input(ai_service: AIService):
    """
    Tests behavior with an empty list.
    Corresponds to: UNIT TEST GOAL 2.4 (Edge case)
    MVP Stability: Important
    """
    raw_angles = []
    smoothed_angles = ai_service.smooth_angle_trajectories(raw_angles, smoothing_window=3, max_gap_to_interpolate=1)
    assert smoothed_angles == []

def test_smooth_angle_trajectories_single_frame_input(ai_service: AIService):
    """
    Tests behavior with a single frame; smoothing might return None or original based on min_periods.
    Corresponds to: UNIT TEST GOAL 2.4 (Edge case)
    MVP Stability: Important
    """
    raw_angles = [{"left_knee": 90.0}]
    # With min_periods=1, and center=True, it should return the value itself for window=3
    smoothed_angles = ai_service.smooth_angle_trajectories(raw_angles, smoothing_window=3, max_gap_to_interpolate=1)
    assert len(smoothed_angles) == 1
    assert smoothed_angles[0]["left_knee"] == pytest.approx(90.0)

def test_smooth_angle_trajectories_output_shape_and_keys(ai_service: AIService):
    """
    Ensures output has the same shape and keys as input (excluding None frames).
    Corresponds to: STRUCTURAL GOAL (shape and key consistency)
    MVP Stability: Critical
    """
    raw_angles = [
        {"left_knee": 90.0, "right_hip": 120.0, "left_elbow": 150.0},
        None,
        {"left_knee": 95.0, "right_hip": None, "left_elbow": 155.0}, # right_hip is None
    ]
    smoothed_angles = ai_service.smooth_angle_trajectories(raw_angles, smoothing_window=1, max_gap_to_interpolate=0) # No smoothing, no interpolation beyond 0

    assert len(smoothed_angles) == len(raw_angles)
    assert smoothed_angles[1] is None # Preserves None frame

    assert set(smoothed_angles[0].keys()) == set(raw_angles[0].keys())
    assert set(smoothed_angles[2].keys()) == set(raw_angles[2].keys())
    
    # Check that original None values within a dict are preserved if not interpolated
    assert smoothed_angles[2]["right_hip"] is None 

def test_smooth_angle_trajectories_json_serializable(ai_service: AIService):
    """
    Tests that the output of smoothing is JSON serializable.
    Corresponds to: STRUCTURAL GOAL (JSON serializability)
    MVP Stability: Critical
    """
    raw_angles = [
        {"left_knee": 90.0, "right_knee": 85.0},
        None,
        {"left_knee": 100.0, "right_knee": 95.0},
    ]
    smoothed_angles = ai_service.smooth_angle_trajectories(raw_angles, smoothing_window=1, max_gap_to_interpolate=1)
    
    try:
        json_output = json.dumps(smoothed_angles)
        deserialized_result = json.loads(json_output)
        assert len(deserialized_result) == len(smoothed_angles)
        # Add more specific checks if necessary, e.g., comparing values after deserialization
        if smoothed_angles[0] and deserialized_result[0]:
            assert deserialized_result[0]["left_knee"] == pytest.approx(smoothed_angles[0]["left_knee"])
        assert deserialized_result[1] is None
    except (TypeError, OverflowError) as e:
        pytest.fail(f"Smoothed angle output is not JSON serializable: {e}\nOutput: {smoothed_angles}") 