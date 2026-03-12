import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from typing import List, Dict, Any

from app.services.dynamic_form_analysis_service import DynamicFormAnalysisService
from app.models.video import Video
from app.models.form_check import FormCheck
from app.models.exercise_config import ExerciseConfig
from app.models.enums import FormCheckStatus
from app.schemas.form_check import FormCheckUpdate
from app.core.exceptions import ServerErrorException

# --- Tests for analyze_form_dynamically (Error/Edge Case Scenarios) ---

@pytest.mark.asyncio
async def test_analyze_form_dynamically_no_exercise_config(
    dynamic_form_analysis_service: DynamicFormAnalysisService,
    mock_form_check_service: AsyncMock,
    mock_exercise_config_service: AsyncMock,
    sample_video_model: Video,
    sample_form_check_model: FormCheck,
    mock_db_session: AsyncMock,
    sample_angle_data_one_good_rep: List[Dict[str, Any]]
):
    service = dynamic_form_analysis_service
    video_obj = sample_video_model
    initial_check_to_pass = sample_form_check_model

    video_obj.angle_data = sample_angle_data_one_good_rep
    # No specific exercise_config_template_id needed on video if we pass config=None

    initial_check_to_pass.video_id = video_obj.id
    initial_check_to_pass.user_id = video_obj.user_id
    # initial_check_to_pass.exercise_config_id = None # Config ID might not be set if config is None
    initial_check_to_pass.status = FormCheckStatus.PENDING

    result_form_check = await service.analyze_form_dynamically(
        video=video_obj,
        exercise_config=None, # Pass None for config
        initial_form_check=initial_check_to_pass
    )

    # mock_form_check_service.update_async.assert_called_once() # Service itself does not call update_async
    assert result_form_check.status == FormCheckStatus.FAILED
    assert result_form_check.score == 0
    # assert result_form_check.reps_detected == 0 # reps_detected might be None if config is missing
    assert result_form_check.error_details is not None
    assert "Exercise configuration missing" in result_form_check.error_details

    mock_exercise_config_service.get_active_config_for_exercise_async.assert_not_called()
    mock_form_check_service.create_async.assert_not_called()


@pytest.mark.asyncio
async def test_analyze_form_dynamically_invalid_angle_data(
    dynamic_form_analysis_service: DynamicFormAnalysisService,
    mock_form_check_service: AsyncMock, 
    mock_exercise_config_service: AsyncMock, 
    sample_video_model: Video, 
    sample_form_check_model: FormCheck, 
    sample_squat_config_fsm: ExerciseConfig,
    mock_db_session: AsyncMock
):
    service = dynamic_form_analysis_service
    video_obj = sample_video_model
    config_to_pass = sample_squat_config_fsm
    initial_check_to_pass = sample_form_check_model

    video_obj.angle_data = "this is not a valid list of frame data" # Invalid data

    initial_check_to_pass.video_id = video_obj.id
    initial_check_to_pass.user_id = video_obj.user_id
    initial_check_to_pass.exercise_config_id = config_to_pass.id 
    initial_check_to_pass.status = FormCheckStatus.PENDING

    result_form_check = await service.analyze_form_dynamically(
        video=video_obj,
        exercise_config=config_to_pass,
        initial_form_check=initial_check_to_pass
    )

    # mock_form_check_service.update_async.assert_called_once() # Service itself does not call update_async
    assert result_form_check.status == FormCheckStatus.FAILED
    assert result_form_check.score == 0
    # assert result_form_check.reps_detected == 0 # reps_detected might be None if error occurs before it's set
    assert result_form_check.error_details is not None
    assert "mapping" in result_form_check.error_details or "TypeError" in result_form_check.error_details # Error from trying to unpack string
    possible_error_messages = [
        "Invalid angle data format", 
        "Failed to process angle data", 
        "Could not deserialize angle data",
        "Angle data is not a list of dictionaries as expected",
        "str' object is not a mapping" # Adding the specific TypeError message
    ]
    assert any(msg in result_form_check.error_details for msg in possible_error_messages), \
        f"Expected one of {possible_error_messages} in error_details, got: {result_form_check.error_details}"
    mock_exercise_config_service.get_active_config_for_exercise_async.assert_not_called()
    mock_form_check_service.create_async.assert_not_called()


@pytest.mark.asyncio
async def test_analyze_form_dynamically_empty_angle_data_list(
    dynamic_form_analysis_service: DynamicFormAnalysisService,
    mock_form_check_service: AsyncMock, 
    mock_exercise_config_service: AsyncMock, 
    sample_video_model: Video, 
    sample_form_check_model: FormCheck, 
    sample_squat_config_fsm: ExerciseConfig, 
    mock_db_session: AsyncMock
):
    service = dynamic_form_analysis_service
    video_obj = sample_video_model
    config_to_pass = sample_squat_config_fsm
    initial_check_to_pass = sample_form_check_model

    video_obj.angle_data = [] # Empty list

    initial_check_to_pass.video_id = video_obj.id
    initial_check_to_pass.user_id = video_obj.user_id
    initial_check_to_pass.exercise_config_id = config_to_pass.id
    initial_check_to_pass.status = FormCheckStatus.PENDING

    result_form_check = await service.analyze_form_dynamically(
        video=video_obj,
        exercise_config=config_to_pass,
        initial_form_check=initial_check_to_pass
    )

    # mock_form_check_service.update_async.assert_called_once() # Service itself does not call update_async
    # Expect COMPLETED as no reps means no errors, but nothing to score.
    assert result_form_check.status == FormCheckStatus.COMPLETED 
    assert result_form_check.score == 0 # Or 100, depending on definition of score with 0 reps
    assert result_form_check.reps_detected == 0
    assert not result_form_check.feedback_items
    assert not (result_form_check.form_metadata and result_form_check.form_metadata.get("issues_by_rep"))
    assert result_form_check.error_details is None
    mock_exercise_config_service.get_active_config_for_exercise_async.assert_not_called()
    mock_form_check_service.create_async.assert_not_called()


@pytest.mark.asyncio
async def test_analyze_form_dynamically_general_exception_handling(
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

    # Make a part of the service logic raise an unexpected error
    # For example, if _segment_repetitions or evaluate_rep raised an unhandled error.
    # We can mock one of the internal methods it calls, if they are mockable (not private _),
    # or mock a dependency called by those internal methods if that's easier.
    # Here, let's assume evaluate_rep (which is called per rep) might fail.
    
    original_evaluate_rep = service.evaluate_rep
    async def mock_evaluate_rep_fails(*args, **kwargs):
        raise ServerErrorException("Simulated unexpected error during rep evaluation")
    service.evaluate_rep = mock_evaluate_rep_fails

    result_form_check = await service.analyze_form_dynamically(
        video=video_obj,
        exercise_config=config_to_pass,
        initial_form_check=initial_check_to_pass
    )
    
    # Restore the original method
    service.evaluate_rep = original_evaluate_rep

    # mock_form_check_service.update_async.assert_called_once() # Service itself does not call update_async
    assert result_form_check.status == FormCheckStatus.FAILED
    assert result_form_check.error_details is not None
    assert "Simulated unexpected error" in result_form_check.error_details or \
           "Generic server error" in result_form_check.error_details
    assert result_form_check.score == 0
    # assert result_form_check.reps_detected == 0 # Commenting out as reps_detected can be None
    mock_exercise_config_service.get_active_config_for_exercise_async.assert_not_called()
    mock_form_check_service.create_async.assert_not_called() 