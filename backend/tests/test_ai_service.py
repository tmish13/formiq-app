import pytest
from unittest.mock import Mock, patch
import numpy as np
import cv2
from ..services.ai import AIService, AIServiceError, ExerciseType
import torch
import json

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
def ai_service(mock_model, mock_pose_estimator):
    """Create an AI service instance with mocked components"""
    with patch('torch.load') as mock_load:
        mock_load.return_value = mock_model
        service = AIService()
        service.pose_estimator = mock_pose_estimator
        return service

@pytest.fixture
def test_video():
    """Create a mock video for testing"""
    video = np.zeros((300, 300, 3), dtype=np.uint8)  # Create blank frame
    return [video for _ in range(30)]  # 30 frames

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