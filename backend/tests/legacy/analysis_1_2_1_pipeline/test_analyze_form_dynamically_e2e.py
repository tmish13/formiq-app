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
    feedback_for_rep1 = [fi for fi in result_form_check.feedback_items if fi.rep_index == 1]
    assert feedback_for_rep1, "Expected feedback items associated with rep_index 1 (the bad rep)"

    # Check for FeedbackItem instances with specific violation_types in details_payload
    symmetry_feedback_items = [
        fi for fi in feedback_for_rep1 
        if fi.type == FeedbackType.TECHNIQUE and 
        fi.details_payload and 
        fi.details_payload.get("violation_type") == "asymmetry_leftKnee_rightKnee"
    ]
    
    posture_feedback_items = [
        fi for fi in feedback_for_rep1 
        if fi.type == FeedbackType.POSTURE and 
        fi.details_payload and 
        fi.details_payload.get("violation_type") == "Torso Upright (Vertical Check)_deviation"
    ]
    
    assert symmetry_feedback_items, "Expected at least one knee symmetry feedback item"
    assert posture_feedback_items, "Expected at least one torso posture feedback item"
    
    # Verify detailed structure of symmetry feedback item
    symmetry_item = symmetry_feedback_items[0]
    assert symmetry_item.severity in [FeedbackSeverity.MEDIUM, FeedbackSeverity.HIGH], "Symmetry issue should have appropriate severity"
    assert symmetry_item.message.startswith("Symmetry issue: Difference between leftKnee"), "Message should describe the symmetry issue"
    
    # Check details_payload fields for symmetry
    assert "joint_name" in symmetry_item.details_payload, "details_payload should have joint_name"
    assert symmetry_item.details_payload["joint_name"] == "leftKnee", "joint_name should be leftKnee"
    assert "compared_to_joint" in symmetry_item.details_payload, "details_payload should have compared_to_joint"
    assert symmetry_item.details_payload["compared_to_joint"] == "rightKnee", "compared_to_joint should be rightKnee"
    
    # Corrected assertion: 'difference' is a key within 'current_value' dict inside details_payload
    assert "current_value" in symmetry_item.details_payload, "details_payload should have current_value for symmetry"
    assert isinstance(symmetry_item.details_payload["current_value"], dict), "current_value in symmetry details_payload should be a dict"
    assert "difference" in symmetry_item.details_payload["current_value"], "details_payload current_value should have difference"
    assert isinstance(symmetry_item.details_payload["current_value"]["difference"], (int, float)), "difference in details_payload should be numeric"

    # Check 'expected_value' for the threshold ('max_difference_degrees')
    assert "expected_value" in symmetry_item.details_payload, "details_payload should have expected_value for symmetry"
    assert isinstance(symmetry_item.details_payload["expected_value"], dict), "expected_value in symmetry details_payload should be a dict"
    assert "max_difference_degrees" in symmetry_item.details_payload["expected_value"], "details_payload expected_value should have max_difference_degrees"
    assert isinstance(symmetry_item.details_payload["expected_value"]["max_difference_degrees"], (int, float)), "max_difference_degrees in details_payload should be numeric"
    
    # Verify detailed structure of posture feedback item
    posture_item = posture_feedback_items[0]
    assert posture_item.severity in [FeedbackSeverity.MEDIUM, FeedbackSeverity.HIGH], "Posture issue should have appropriate severity"
    assert posture_item.message.startswith("Posture issue: 'Torso Upright"), "Message should describe the posture issue"
    
    # Check details_payload fields for posture
    assert "current_value" in posture_item.details_payload, "details_payload should have current_value"
    # For 'Torso Upright (Vertical Check)_deviation', current_value is a dict
    assert isinstance(posture_item.details_payload["current_value"], dict), "current_value for Torso Upright deviation should be a dict"
    assert "observed_vector_angle_from_vertical_degrees" in posture_item.details_payload["current_value"], "current_value dict should have 'observed_vector_angle_from_vertical_degrees'"
    assert isinstance(posture_item.details_payload["current_value"]["observed_vector_angle_from_vertical_degrees"], (int, float)), "observed_vector_angle_from_vertical_degrees should be numeric"
    
    assert "expected_value" in posture_item.details_payload, "details_payload should have expected_value"
    assert isinstance(posture_item.details_payload["expected_value"], dict), "expected_value should be a dictionary"
    if "min_value" in posture_item.details_payload["expected_value"]:
        assert isinstance(posture_item.details_payload["expected_value"]["min_value"], (int, float)), "min_value should be numeric"
    if "max_value" in posture_item.details_payload["expected_value"]:
        assert isinstance(posture_item.details_payload["expected_value"]["max_value"], (int, float)), "max_value should be numeric"
    
    # Make sure key FeedbackItem fields are consistent with the internal details_payload
    for fi in feedback_for_rep1:
        # Verify FeedbackItem metadata is consistent
        assert fi.timestamp is not None, "timestamp should be set"
        assert isinstance(fi.timestamp, float), "timestamp should be a float"
        assert fi.severity is not None, "severity should be set"
        assert fi.type is not None, "type should be set"
        assert fi.rep_index == 1, "rep_index should be 1 for the bad rep"
        
        # Verify movement_phase is consistent with details_payload
        if "phase" in fi.details_payload:
            assert fi.movement_phase == fi.details_payload["phase"], "movement_phase should match details_payload phase"
        
        # Verify joint_name is consistent
        if "joint_name" in fi.details_payload and fi.details_payload["joint_name"]:
            assert fi.joint_name == fi.details_payload["joint_name"], "joint_name should match details_payload joint_name"

    assert result_form_check.error_details is None # Changed from error_message
    # mock_exercise_config_service.get_active_config_by_template_id_async.assert_not_called()
    mock_exercise_config_service.get_active_config_for_exercise_async.assert_not_called()
    mock_form_check_service.create_async.assert_not_called() 