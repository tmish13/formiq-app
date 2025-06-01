import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from typing import List, Dict, Any, Tuple

from app.services.dynamic_form_analysis_service import DynamicFormAnalysisService
from app.models.video import Video
from app.models.form_check import FormCheck, FeedbackItem
from app.models.exercise_config import ExerciseConfig
from app.models.enums import FormCheckStatus, FeedbackSeverity, FeedbackType
from app.schemas.form_check import FormCheckUpdate

# --- Tests for analyze_form_dynamically (Advanced/Specific Input Scenarios) ---

@pytest.mark.asyncio
async def test_analyze_form_with_advanced_positioning_data(
    dynamic_form_analysis_service: DynamicFormAnalysisService,
    mock_db_session: AsyncMock,
    mock_form_check_service: AsyncMock,
    mock_exercise_config_service: AsyncMock,
    sample_video_model: Video,
    sample_form_check_model: FormCheck,
    sample_squat_config_fsm: ExerciseConfig,
    sample_angle_data_two_reps_one_bad: List[Dict[str, Any]] # Using this as advanced data
):
    service = dynamic_form_analysis_service
    video_obj = sample_video_model
    config_to_pass = sample_squat_config_fsm
    initial_check_to_pass = sample_form_check_model

    # Simulate advanced positioning data being part of angle_data
    video_obj.angle_data = sample_angle_data_two_reps_one_bad 

    initial_check_to_pass.video_id = video_obj.id
    initial_check_to_pass.user_id = video_obj.user_id
    initial_check_to_pass.exercise_config_id = config_to_pass.id
    initial_check_to_pass.status = FormCheckStatus.PENDING

    result = await service.analyze_form_dynamically(
        video=video_obj, 
        exercise_config=config_to_pass, 
        initial_form_check=initial_check_to_pass
    )

    assert result is not None
    assert isinstance(result, FormCheck)
    assert result.status == FormCheckStatus.COMPLETED # Or ERROR, depending on data
    assert result.reps_detected > 0 # Expect some reps, using model attribute reps_detected
    assert result.score is not None

    # mock_form_check_service.update_async.assert_called_once() # Service itself does not call update_async
    # Ensure these are not called if config and initial_check are passed directly
    mock_exercise_config_service.get_active_config_for_exercise_async.assert_not_called()
    mock_form_check_service.create_async.assert_not_called()

@pytest.mark.asyncio
async def test_analyze_form_with_multiple_exercises(
    dynamic_form_analysis_service: DynamicFormAnalysisService,
    mock_db_session: AsyncMock,
    mock_form_check_service: AsyncMock,
    mock_exercise_config_service: AsyncMock,
    sample_video_model: Video,
    sample_form_check_model: FormCheck,
    sample_squat_config_fsm: ExerciseConfig, # Using squat config for this test
    sample_angle_data_two_reps: List[Dict[str, Any]] # Generic two rep data
):
    """ 
    This test name is a bit of a misnomer from the original test suite.
    The service processes one exercise_config at a time.
    This test, like others, passes a video, a specific config, and an initial_form_check.
    It's testing the standard flow with pre-defined config and initial check.
    """
    service = dynamic_form_analysis_service
    video_obj = sample_video_model
    config_to_pass = sample_squat_config_fsm
    initial_check_to_pass = sample_form_check_model

    video_obj.angle_data = sample_angle_data_two_reps

    initial_check_to_pass.video_id = video_obj.id
    initial_check_to_pass.user_id = video_obj.user_id
    initial_check_to_pass.exercise_config_id = config_to_pass.id
    initial_check_to_pass.status = FormCheckStatus.PENDING

    result = await service.analyze_form_dynamically(
        video=video_obj, 
        exercise_config=config_to_pass, 
        initial_form_check=initial_check_to_pass
    )

    assert result is not None
    assert isinstance(result, FormCheck)
    assert result.status == FormCheckStatus.COMPLETED
    assert result.reps_detected is not None # Check that reps_detected is populated
    # If sample_angle_data_two_reps is expected to have >0 reps:
    assert result.reps_detected > 0
    assert result.score is not None

    # mock_form_check_service.update_async.assert_called_once() # Service itself does not call update_async
    mock_exercise_config_service.get_active_config_for_exercise_async.assert_not_called()
    mock_form_check_service.create_async.assert_not_called()


@pytest.mark.asyncio
async def test_landmark_confidence_filtering(
    dynamic_form_analysis_service: DynamicFormAnalysisService,
    mock_db_session: AsyncMock,
    mock_form_check_service: AsyncMock,
    mock_exercise_config_service: AsyncMock,
    sample_video_model: Video,
    sample_form_check_model: FormCheck,
    sample_squat_config_fsm: ExerciseConfig
):
    """
    Test how the service handles landmark confidence.
    This might involve providing angle_data where raw_landmarks have low confidence.
    The service's internal _get_keypoint_coords_by_name (if still used) or similar logic 
    should handle this. For an E2E via analyze_form_dynamically, we'd need to ensure
    the angle_data reflects this. The current sample_angle_data fixtures don't explicitly 
    include landmark confidence in a way that analyze_form_dynamically would directly filter at its top level.
    This test will assume that if such filtering happens, it occurs during angle calculation or 
    within evaluate_rep if raw_landmarks are passed and processed there.
    For now, it tests the flow with a standard config and form check, assuming confidence issues
    are handled internally or by preceding services that generate angle_data.
    """
    service = dynamic_form_analysis_service
    video_obj = sample_video_model
    config_to_pass = sample_squat_config_fsm
    initial_check_to_pass = sample_form_check_model

    # Example: Provide angle data that might have been derived from low-confidence landmarks
    # For a true test of filtering, the `raw_landmarks` within angle_data items 
    # would need to have 'confidence' fields, and the service logic (e.g., _get_keypoint_coords_by_name)
    # would need to use it.
    # Using sample_angle_data_one_good_rep for now as a placeholder for valid angle data structure.
    # A more specific fixture might be needed if direct confidence filtering in this service is tested.
    
    # Let's use data that should process normally to ensure the flow itself works.
    # If confidence filtering leads to, e.g., fewer effective frames or issues, assertions would change.
    video_obj.angle_data = [
        {"frame_num": 0, "timestamp": 0.0, "angles": {"leftHip": 175, "leftKnee": 170}, "raw_landmarks": [{"name": "leftShoulder", "x": 0.5, "y": 0.2, "confidence": 0.9}, {"name": "leftHip", "x": 0.5, "y": 0.5, "confidence": 0.9}]},
        {"frame_num": 1, "timestamp": 0.03, "angles": {"leftHip": 150, "leftKnee": 140}, "raw_landmarks": [{"name": "leftShoulder", "x": 0.5, "y": 0.22, "confidence": 0.3}, {"name": "leftHip", "x": 0.5, "y": 0.5, "confidence": 0.4}]}, # Low confidence frame
        {"frame_num": 2, "timestamp": 0.06, "angles": {"leftHip": 100, "leftKnee": 85}, "raw_landmarks": [{"name": "leftShoulder", "x": 0.5, "y": 0.3, "confidence": 0.95}, {"name": "leftHip", "x": 0.5, "y": 0.5, "confidence": 0.95}]},
        {"frame_num": 3, "timestamp": 0.09, "angles": {"leftHip": 175, "leftKnee": 170}, "raw_landmarks": [{"name": "leftShoulder", "x": 0.5, "y": 0.2, "confidence": 0.85}, {"name": "leftHip", "x": 0.5, "y": 0.5, "confidence": 0.85}]}
    ]

    initial_check_to_pass.video_id = video_obj.id
    initial_check_to_pass.user_id = video_obj.user_id
    initial_check_to_pass.exercise_config_id = config_to_pass.id
    initial_check_to_pass.status = FormCheckStatus.PENDING

    result = await service.analyze_form_dynamically(
        video=video_obj, 
        exercise_config=config_to_pass, 
        initial_form_check=initial_check_to_pass
    )

    assert result is not None
    assert isinstance(result, FormCheck)
    # If confidence filtering impacts rep counting or scoring, these assertions would change.
    # For now, assume it completes; specific effects of filtering would need deeper inspection of service logic.
    assert result.status == FormCheckStatus.COMPLETED
    assert result.reps_detected is not None # Ensure reps_detected is populated
    # Add specific check for rep count if low confidence is expected to alter it, e.g.:
    # assert result.reps_detected == 1 # if low confidence frame is discarded, reducing rep count
    assert result.score is not None

    # mock_form_check_service.update_async.assert_called_once() # Service itself does not call update_async
    mock_exercise_config_service.get_active_config_for_exercise_async.assert_not_called()
    mock_form_check_service.create_async.assert_not_called() 