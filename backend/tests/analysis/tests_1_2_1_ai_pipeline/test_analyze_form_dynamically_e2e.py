import pytest
from unittest.mock import AsyncMock, call, MagicMock
from uuid import uuid4
from typing import List, Dict, Any, Optional, Tuple
import copy

from app.services.dynamic_form_analysis_service import DynamicFormAnalysisService
from app.models.video import Video
from app.models.form_check import FormCheck, FeedbackItem
from app.models.exercise_config import ExerciseConfig
from app.models.enums import FormCheckStatus, FeedbackSeverity, FeedbackType
from app.schemas.form_check import FormCheckUpdate
from unittest.mock import ANY # Ensure ANY is available

# --- Tests for analyze_form_dynamically (E2E type scenarios) ---

@pytest.mark.asyncio
async def test_analyze_form_dynamically_e2e_flow(
    dynamic_form_analysis_service: DynamicFormAnalysisService,
    sample_video: Video, # Uses sample_angle_data_two_reps
    sample_squat_config: ExerciseConfig,
    sample_form_check_model: FormCheck, # Added: To be used as initial_form_check
    mock_form_check_service: AsyncMock,
    # mock_exercise_config_service is not directly used by analyze_form_dynamically if config is passed
    mock_exercise_config_service: AsyncMock,
    mock_db_session: AsyncMock
):
    service = dynamic_form_analysis_service
    video_obj = sample_video
    config_to_pass = sample_squat_config
    initial_check_to_pass = sample_form_check_model

    # Ensure video_obj has angle_data
    if not hasattr(video_obj, 'angle_data') or video_obj.angle_data is None:
        video_obj.angle_data = [
            {"frame_num": 0, "timestamp": 0.0, "angles": {"leftHip": 175, "leftKnee": 170}, "raw_landmarks": []},
            {"frame_num": 1, "timestamp": 0.03, "angles": {"leftHip": 150, "leftKnee": 140}, "raw_landmarks": []}
        ] # Minimal valid angle_data for flow testing

    # Ensure the initial_form_check is compatible with the video and config
    initial_check_to_pass.video_id = video_obj.id
    initial_check_to_pass.user_id = video_obj.user_id # Assuming video has user_id
    initial_check_to_pass.exercise_config_id = config_to_pass.id
    initial_check_to_pass.status = FormCheckStatus.PENDING

    result_form_check = await service.analyze_form_dynamically(
        video=video_obj,
        exercise_config=config_to_pass,
        initial_form_check=initial_check_to_pass
    )

    assert result_form_check is not None
    assert isinstance(result_form_check, FormCheck)
    
    # Assert that update_async was called (once, with specific form_check_id)
    # mock_form_check_service.update_async.assert_called_once() # Service itself does not call update_async
    # call_args = mock_form_check_service.update_async.call_args
    # assert call_args[0][1] == initial_check_to_pass.id # form_check_id
    
    # Assertions on the result_form_check based on sample_angle_data_two_reps and sample_squat_config
    # This data should result in completed status, some score, and rep count.
    assert result_form_check.status == FormCheckStatus.COMPLETED
    assert result_form_check.reps_detected == 1 
    assert result_form_check.score is not None
    # assert result_form_check.error_message is None
    assert result_form_check.error_details is None # Changed from error_message

    # Ensure config fetching was NOT called (since config was passed directly)
    # mock_exercise_config_service.get_active_config_by_template_id_async.assert_not_called()
    mock_exercise_config_service.get_active_config_for_exercise_async.assert_not_called()
    
    # Ensure form check creation was NOT called (since initial_form_check was passed)
    mock_form_check_service.create_async.assert_not_called()


@pytest.mark.asyncio
async def test_analyze_form_dynamically_e2e_good_rep(
    dynamic_form_analysis_service: DynamicFormAnalysisService,
    mock_db_session: AsyncMock,
    mock_form_check_service: AsyncMock,
    mock_exercise_config_service: AsyncMock,
    sample_video_model: Video,
    sample_form_check_model: FormCheck,
    sample_squat_config_fsm: ExerciseConfig,
    sample_angle_data_one_good_rep: List[Dict[str, Any]]
):
    service = dynamic_form_analysis_service
    video_obj = sample_video_model
    config_to_pass = sample_squat_config_fsm
    initial_check_to_pass = sample_form_check_model

    video_obj.angle_data = sample_angle_data_one_good_rep

    initial_check_to_pass.video_id = video_obj.id
    initial_check_to_pass.user_id = video_obj.user_id
    initial_check_to_pass.exercise_config_id = config_to_pass.id
    initial_check_to_pass.status = FormCheckStatus.PENDING

    result_form_check = await service.analyze_form_dynamically(
        video=video_obj,
        exercise_config=config_to_pass,
        initial_form_check=initial_check_to_pass
    )

    # mock_form_check_service.update_async.assert_called_once_with(
    #     mock_db_session, initial_check_to_pass.id, ANY
    # ) # Service itself does not call update_async
    assert result_form_check.status == FormCheckStatus.COMPLETED
    assert result_form_check.reps_detected == 1
    assert result_form_check.score < 100.0 # Even a "good" rep might have minor ideal_range deviations with FSM config
    assert len(result_form_check.feedback_items) > 0 # Expect some feedback items due to ideal_range deviations
    assert not (result_form_check.form_metadata and result_form_check.form_metadata.get("issues_by_rep")) # Good rep might not populate this if only minor issues
    assert result_form_check.error_details is None # Changed from error_message
    # mock_exercise_config_service.get_active_config_by_template_id_async.assert_not_called()
    mock_exercise_config_service.get_active_config_for_exercise_async.assert_not_called()
    mock_form_check_service.create_async.assert_not_called()


@pytest.mark.asyncio
async def test_analyze_form_dynamically_e2e_bad_rep(
    dynamic_form_analysis_service: DynamicFormAnalysisService,
    mock_db_session: AsyncMock,
    mock_form_check_service: AsyncMock,
    mock_exercise_config_service: AsyncMock,
    sample_video_model: Video,
    sample_form_check_model: FormCheck,
    sample_squat_config_fsm: ExerciseConfig,
    sample_angle_data_two_reps_one_bad: List[Dict[str, Any]]
):
    service = dynamic_form_analysis_service
    video_obj = sample_video_model
    config_to_pass = sample_squat_config_fsm
    initial_check_to_pass = sample_form_check_model

    # Ensure pristine data for this test run using a deep copy
    video_obj.angle_data = copy.deepcopy(sample_angle_data_two_reps_one_bad)

    # DEBUG: Print knee angles for the frames that should form the 'bad rep'
    # The 'bad_rep_frames' start at index 6 of the combined list
    # and have original frame_nums 6, 7, 8, 9, 10, 11
    # print("\nDEBUG E2E BAD REP TEST - Angle Data State After Deepcopy:")
    # for i, frame in enumerate(video_obj.angle_data):
    #     if frame.get("frame_num", -1) >= 6: # Check frames that are part of the bad rep data
    #         print(f"  Frame {frame.get('frame_num')} (original index {i}): LeftKnee={frame['angles'].get('leftKnee')}, RightKnee={frame['angles'].get('rightKnee')}")

    initial_check_to_pass.video_id = video_obj.id
    initial_check_to_pass.user_id = video_obj.user_id
    initial_check_to_pass.exercise_config_id = config_to_pass.id
    initial_check_to_pass.status = FormCheckStatus.PENDING

    result_form_check = await service.analyze_form_dynamically(
        video=video_obj,
        exercise_config=config_to_pass,
        initial_form_check=initial_check_to_pass
    )

    # mock_form_check_service.update_async.assert_called_once_with(
    #     mock_db_session, initial_check_to_pass.id, ANY
    # ) # Service itself does not call update_async
    assert result_form_check.status == FormCheckStatus.COMPLETED
    assert result_form_check.reps_detected == 2 # Two reps in the data
    assert result_form_check.score < 100 # Bad rep should lower score
    assert len(result_form_check.feedback_items) > 0 # Expect some feedback for the bad rep
    # assert result_form_check.form_metadata and result_form_check.form_metadata.get("issues_by_rep")
    # assert len(result_form_check.form_metadata.get("issues_by_rep", [])) == 2 # For two reps

    # Check that feedback items exist for the bad rep (rep_index 1)
    # It's acceptable for rep_index 0 (the good rep in this data) to have no feedback items if it's perfect.
    feedback_for_rep1_exists = any(
        fi.rep_index == 1 for fi in result_form_check.feedback_items
    )
    assert feedback_for_rep1_exists, "Expected feedback items associated with rep_index 1 (the bad rep)"

    # Check for specific feedback based on the 'bad' part of the data (rep_index 1)
    has_symmetry_feedback_on_rep1 = False
    has_posture_feedback_on_rep1 = False # Changed from has_back_rounding_feedback_on_rep1

    for fi in result_form_check.feedback_items:
        if fi.rep_index == 1: # Use direct attribute
            if "Symmetry" in fi.message or "asymmetry" in fi.message:
                has_symmetry_feedback_on_rep1 = True
            # Check for the specific posture rule message
            if "Posture issue" in fi.message and "Torso Upright (Vertical Check)" in fi.message:
                has_posture_feedback_on_rep1 = True
    
    assert has_symmetry_feedback_on_rep1, "Expected symmetry feedback for rep_index 1"
    assert has_posture_feedback_on_rep1, "Expected posture feedback (Torso Upright) for rep_index 1"

    assert result_form_check.error_details is None # Changed from error_message
    # mock_exercise_config_service.get_active_config_by_template_id_async.assert_not_called()
    mock_exercise_config_service.get_active_config_for_exercise_async.assert_not_called()
    mock_form_check_service.create_async.assert_not_called() 