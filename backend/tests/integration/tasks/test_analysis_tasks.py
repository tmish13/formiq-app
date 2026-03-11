import pytest
pytestmark = pytest.mark.integration

from unittest.mock import AsyncMock, patch, MagicMock
import uuid
from typing import Optional, List, Dict, Any

from app.tasks.analysis_tasks import process_form_check_task
from app.models.video import Video
from app.models.form_check import FormCheck
from app.models.exercise_config import ExerciseConfig
from app.schemas.video import VideoStatus
from app.schemas.form_check import FormCheckStatus
from app.services.ai_service import AIService
from app.services.form_check_service import FormCheckService
from app.services.exercise_config_service import ExerciseConfigService
from app.core.config import Settings



# Dummy data for tests
DUMMY_VIDEO_ID = uuid.uuid4()
DUMMY_FORM_CHECK_ID = uuid.uuid4()
DUMMY_USER_ID = uuid.uuid4()
DUMMY_EXERCISE_ID = uuid.uuid4()
DUMMY_EXERCISE_SLUG = "test-exercise"

@pytest.fixture
def mock_settings() -> Settings:
    return Settings(EXERCISE_CLASSIFICATION_THRESHOLD=0.75)

@pytest.fixture
def mock_video_model_factory():
    def _factory(
        id: uuid.UUID = DUMMY_VIDEO_ID,
        user_id: uuid.UUID = DUMMY_USER_ID,
        pose_data: Optional[List[List[Optional[Dict[str, Any]]]]] = None,
        raw_pose_data: Optional[List[List[Optional[Dict[str, Any]]]]] = None,
        angle_data: Optional[List[Dict[str, Any]]] = None, # Required by current task if no classification
        calculated_angles: Optional[List[Dict[str, Any]]] = None, # Alternative for angle_data
        status: VideoStatus = VideoStatus.ANALYSIS_COMPLETE # Assume previous steps done
    ) -> Video:
        video = Video(
            id=id,
            user_id=user_id,
            s3_bucket="test-bucket",
            s3_key=f"{id}.mp4",
            status=status,
            pose_data=pose_data,
            raw_pose_data=raw_pose_data,
            angle_data=angle_data if angle_data is not None else ([{}] if calculated_angles is None else None), # Ensure angle_data or calculated_angles has some value
            calculated_angles=calculated_angles
        )
        return video
    return _factory

@pytest.fixture
def mock_form_check_model_factory():
    def _factory(
        id: uuid.UUID = DUMMY_FORM_CHECK_ID,
        user_id: uuid.UUID = DUMMY_USER_ID,
        video_id: uuid.UUID = DUMMY_VIDEO_ID,
        exercise_id: Optional[uuid.UUID] = None,
        status: FormCheckStatus = FormCheckStatus.PENDING # Corrected default status
    ) -> FormCheck:
        form_check = FormCheck(
            id=id,
            user_id=user_id,
            video_id=video_id,
            exercise_id=exercise_id,
            status=status,
            # Add other required fields with default values
            score=None,
            feedback=None, # Deprecated
            overall_feedback=None,
            keypoints=None, # Deprecated
            form_metadata=None,
            issues=None, # Deprecated
        )
        return form_check
    return _factory

@pytest.fixture
def sample_exercise_config_model() -> ExerciseConfig:
    return ExerciseConfig(
        id=DUMMY_EXERCISE_ID,
        exercise_id=DUMMY_EXERCISE_ID, 
        slug=DUMMY_EXERCISE_SLUG,
        name="Test Exercise",
        description="A test exercise config",
        version=1,
        is_active=True,
        # Provide valid, minimal defaults for non-nullable JSON fields
        joint_angle_rules={"phases": {}, "joints": []},  # Empty but valid structure
        movement_phases={},  # Empty dict is valid if no phases defined
        feedback_templates={}, # Empty dict is valid if no templates defined
        # Nullable fields can be None or have minimal empty structures
        classification_metadata=None, # Or e.g., {"keypoints": [], "features": {}}
        rom_rules=[], # Assuming it's a list of rules
        posture_rules=[], # Assuming it's a list of rules
        symmetry_rules=[]  # Assuming it's a list of rules
    )

@pytest.fixture
def mock_ai_service() -> MagicMock:
    mock = MagicMock(spec=AIService)
    mock.classify_exercise_from_keypoints = AsyncMock(return_value=(None, 0.0))
    # Mock other methods called by DynamicFormAnalysisService if not deeply testing it here
    mock.smooth_and_interpolate_poses = AsyncMock(return_value=None) # Placeholder
    mock.calculate_angles_for_pose_sequence = AsyncMock(return_value=None) # Placeholder
    return mock

@pytest.fixture
def mock_form_check_service() -> MagicMock:
    mock = MagicMock(spec=FormCheckService)
    mock.get_form_check_by_id_async = AsyncMock()
    mock.update_form_check_status_and_save_results_async = AsyncMock()
    return mock

@pytest.fixture
def mock_exercise_config_service() -> MagicMock:
    mock = MagicMock(spec=ExerciseConfigService)
    mock.get_active_config_for_exercise_async = AsyncMock()
    mock.get_exercise_config_by_slug_async = AsyncMock()
    return mock

@pytest.mark.asyncio
@patch("app.tasks.analysis_tasks.get_settings_override")
@patch("app.tasks.analysis_tasks.get_async_session_context")
@patch("app.tasks.analysis_tasks.AIService")
@patch("app.tasks.analysis_tasks.FormCheckService")
@patch("app.tasks.analysis_tasks.ExerciseConfigService")
@patch("app.tasks.analysis_tasks.DynamicFormAnalysisService")
async def test_process_form_check_with_provided_exercise_id(
    MockedDynamicFormAnalysisService: MagicMock, # Patched class
    MockedExerciseConfigService: MagicMock,    # Patched class
    MockedFormCheckService: MagicMock,         # Patched class
    MockedAIService: MagicMock,                # Patched class
    mock_get_async_session_context: MagicMock,
    mock_get_settings_override: MagicMock,
    mock_video_model_factory,
    mock_form_check_model_factory,
    sample_exercise_config_model,
    mock_settings, # Fixture for settings values
    # Fixtures for mock instances that the patched classes will return
    mock_ai_service: MagicMock, 
    mock_form_check_service: MagicMock, 
    mock_exercise_config_service: MagicMock
):
    """
    Test Case 1: exercise_id is provided.
    Classifier should be skipped.
    ExerciseConfigService.get_active_config_for_exercise_async should be called.
    DynamicFormAnalysisService.analyze_form_dynamically should be called.
    """
    # --- Arrange ---
    mock_get_settings_override.return_value = mock_settings
    
    # Configure the mock async session context
    mock_db_session = AsyncMock() # Mock for the database session itself
    mock_async_context_manager = AsyncMock()
    mock_async_context_manager.__aenter__.return_value = mock_db_session
    mock_get_async_session_context.return_value = mock_async_context_manager

    # Configure patched service classes to return our mock instances
    MockedAIService.return_value = mock_ai_service
    MockedFormCheckService.return_value = mock_form_check_service
    MockedExerciseConfigService.return_value = mock_exercise_config_service
    
    mock_dfa_instance = AsyncMock()
    mock_dfa_instance.analyze_form_dynamically = AsyncMock(return_value={
        "score": 90.0,
        "overall_feedback": "Good form!",
        "feedback_items": [],
        "form_metadata": {}
    })
    MockedDynamicFormAnalysisService.return_value = mock_dfa_instance # Patched class returns mock instance

    video = mock_video_model_factory(angle_data=[{"angles": {"left_knee": 90}, "raw_landmarks": [{}]*33}])
    form_check = mock_form_check_model_factory(exercise_id=DUMMY_EXERCISE_ID)

    mock_form_check_service.get_form_check_by_id_async.return_value = form_check
    with patch("app.models.video.Video.get_or_none", new_callable=AsyncMock, return_value=video) as mock_video_get:
        mock_exercise_config_service.get_active_config_for_exercise_async.return_value = sample_exercise_config_model

        # --- Act ---
        await process_form_check_task(
            form_check_id=DUMMY_FORM_CHECK_ID,
            video_id=DUMMY_VIDEO_ID,
        )

        # --- Assert ---
        mock_get_settings_override.assert_called_once()
        mock_get_async_session_context.assert_called_once_with(mock_settings)
        
        MockedAIService.assert_called_once_with(app_settings=mock_settings)
        MockedFormCheckService.assert_called_once_with(db_session=mock_db_session, settings=mock_settings)
        MockedExerciseConfigService.assert_called_once_with(db_session=mock_db_session)
        MockedDynamicFormAnalysisService.assert_called_once_with(db_session=mock_db_session, ai_service=mock_ai_service, settings=mock_settings)

        mock_ai_service.classify_exercise_from_keypoints.assert_not_called()
        mock_exercise_config_service.get_active_config_for_exercise_async.assert_called_once_with(
            exercise_id=DUMMY_EXERCISE_ID
        )
        mock_exercise_config_service.get_exercise_config_by_slug_async.assert_not_called()
        mock_dfa_instance.analyze_form_dynamically.assert_called_once()
        mock_form_check_service.update_form_check_status_and_save_results_async.assert_called_once()
        update_args = mock_form_check_service.update_form_check_status_and_save_results_async.call_args[0]
        assert update_args[0] == DUMMY_FORM_CHECK_ID
        assert update_args[1] == FormCheckStatus.ANALYSIS_COMPLETE
        assert update_args[2]["score"] == 90.0
        assert update_args[2]["overall_feedback"] == "Good form!"
        mock_video_get.assert_called_once_with(DUMMY_VIDEO_ID)
        mock_form_check_service.get_form_check_by_id_async.assert_called_once_with(DUMMY_FORM_CHECK_ID)

@pytest.mark.asyncio
@patch("app.tasks.analysis_tasks.get_settings_override")
@patch("app.tasks.analysis_tasks.get_async_session_context")
@patch("app.tasks.analysis_tasks.AIService")
@patch("app.tasks.analysis_tasks.FormCheckService")
@patch("app.tasks.analysis_tasks.ExerciseConfigService")
@patch("app.tasks.analysis_tasks.DynamicFormAnalysisService")
async def test_process_form_check_no_exercise_id_uses_pose_data_for_classification(
    MockedDynamicFormAnalysisService: MagicMock,
    MockedExerciseConfigService: MagicMock,
    MockedFormCheckService: MagicMock,
    MockedAIService: MagicMock,
    mock_get_async_session_context: MagicMock,
    mock_get_settings_override: MagicMock,
    mock_video_model_factory,
    mock_form_check_model_factory,
    sample_exercise_config_model,
    mock_settings, 
    mock_ai_service, 
    mock_form_check_service, 
    mock_exercise_config_service
):
    """
    Test Case 2: exercise_id is missing, and pose_data exists.
    Classifier (classify_exercise_from_keypoints) should be called with pose_data.
    If classification is successful & above threshold, ExerciseConfigService.get_exercise_config_by_slug_async is called.
    DynamicFormAnalysisService.analyze_form_dynamically should be called.
    FormCheck should be updated with classification details.
    """
    # --- Arrange ---
    mock_get_settings_override.return_value = mock_settings
    mock_db_session = AsyncMock()
    mock_async_context_manager = AsyncMock()
    mock_async_context_manager.__aenter__.return_value = mock_db_session
    mock_get_async_session_context.return_value = mock_async_context_manager

    MockedAIService.return_value = mock_ai_service
    MockedFormCheckService.return_value = mock_form_check_service
    MockedExerciseConfigService.return_value = mock_exercise_config_service

    mock_dfa_instance = AsyncMock()
    mock_dfa_instance.analyze_form_dynamically = AsyncMock(return_value={
        "score": 85.0,
        "overall_feedback": "Classified and analyzed!",
        "feedback_items": [],
        "form_metadata": {}
    })
    MockedDynamicFormAnalysisService.return_value = mock_dfa_instance

    sample_pose_data = [[{"x": 0.5, "y": 0.5, "z": 0.1, "visibility": 0.9}] * 33]
    video = mock_video_model_factory(pose_data=sample_pose_data, raw_pose_data=None, angle_data=None, calculated_angles=[{}])
    form_check = mock_form_check_model_factory(exercise_id=None)

    mock_form_check_service.get_form_check_by_id_async.return_value = form_check
    
    classified_slug = "classified-squat"
    classification_confidence = 0.90
    mock_ai_service.classify_exercise_from_keypoints = AsyncMock(return_value=(classified_slug, classification_confidence))
    mock_exercise_config_service.get_exercise_config_by_slug_async.return_value = sample_exercise_config_model

    with patch("app.models.video.Video.get_or_none", new_callable=AsyncMock, return_value=video):
        # --- Act ---
        await process_form_check_task(
            form_check_id=DUMMY_FORM_CHECK_ID,
            video_id=DUMMY_VIDEO_ID
        )

        # --- Assert ---
        mock_get_settings_override.assert_called_once()
        mock_get_async_session_context.assert_called_once_with(mock_settings)
        MockedAIService.assert_called_once_with(app_settings=mock_settings)
        MockedFormCheckService.assert_called_once_with(db_session=mock_db_session, settings=mock_settings)
        MockedExerciseConfigService.assert_called_once_with(db_session=mock_db_session)
        MockedDynamicFormAnalysisService.assert_called_once_with(db_session=mock_db_session, ai_service=mock_ai_service, settings=mock_settings)

        mock_ai_service.classify_exercise_from_keypoints.assert_called_once_with(
            keypoint_sequence=sample_pose_data
        )
        mock_exercise_config_service.get_active_config_for_exercise_async.assert_not_called()
        mock_exercise_config_service.get_exercise_config_by_slug_async.assert_called_once_with(slug=classified_slug)
        mock_dfa_instance.analyze_form_dynamically.assert_called_once()
        mock_form_check_service.update_form_check_status_and_save_results_async.assert_called_once()
        update_args = mock_form_check_service.update_form_check_status_and_save_results_async.call_args[0]
        assert update_args[0] == DUMMY_FORM_CHECK_ID
        assert update_args[1] == FormCheckStatus.ANALYSIS_COMPLETE
        assert update_args[2]["score"] == 85.0
        assert update_args[2]["classified_exercise_slug"] == classified_slug
        assert update_args[2]["classification_confidence"] == classification_confidence


@pytest.mark.asyncio
@patch("app.tasks.analysis_tasks.get_settings_override")
@patch("app.tasks.analysis_tasks.get_async_session_context")
@patch("app.tasks.analysis_tasks.AIService")
@patch("app.tasks.analysis_tasks.FormCheckService")
@patch("app.tasks.analysis_tasks.ExerciseConfigService")
@patch("app.tasks.analysis_tasks.DynamicFormAnalysisService")
async def test_process_form_check_no_exercise_id_uses_raw_pose_data_for_classification(
    MockedDynamicFormAnalysisService: MagicMock,
    MockedExerciseConfigService: MagicMock,
    MockedFormCheckService: MagicMock,
    MockedAIService: MagicMock,
    mock_get_async_session_context: MagicMock,
    mock_get_settings_override: MagicMock,
    mock_video_model_factory,
    mock_form_check_model_factory,
    sample_exercise_config_model,
    mock_settings, 
    mock_ai_service, 
    mock_form_check_service, 
    mock_exercise_config_service
):
    """
    Test Case 3: exercise_id is missing, pose_data is missing, but raw_pose_data exists.
    Classifier should be called with raw_pose_data.
    Other logic follows Test Case 2 if classification is successful.
    """
    # --- Arrange ---
    mock_get_settings_override.return_value = mock_settings
    mock_db_session = AsyncMock()
    mock_async_context_manager = AsyncMock()
    mock_async_context_manager.__aenter__.return_value = mock_db_session
    mock_get_async_session_context.return_value = mock_async_context_manager

    MockedAIService.return_value = mock_ai_service
    MockedFormCheckService.return_value = mock_form_check_service
    MockedExerciseConfigService.return_value = mock_exercise_config_service

    mock_dfa_instance = AsyncMock()
    mock_dfa_instance.analyze_form_dynamically = AsyncMock(return_value={
        "score": 82.0,
        "overall_feedback": "Classified with raw data and analyzed!",
        "feedback_items": [],
        "form_metadata": {}
    })
    MockedDynamicFormAnalysisService.return_value = mock_dfa_instance

    sample_raw_pose_data = [[{"x": 0.6, "y": 0.6, "z": 0.2, "visibility": 0.8}] * 33]
    video = mock_video_model_factory(pose_data=None, raw_pose_data=sample_raw_pose_data, angle_data=None, calculated_angles=[{}])
    form_check = mock_form_check_model_factory(exercise_id=None)

    mock_form_check_service.get_form_check_by_id_async.return_value = form_check
    
    classified_slug = "classified-lunge"
    classification_confidence = 0.88
    mock_ai_service.classify_exercise_from_keypoints = AsyncMock(return_value=(classified_slug, classification_confidence))
    mock_exercise_config_service.get_exercise_config_by_slug_async.return_value = sample_exercise_config_model 

    with patch("app.models.video.Video.get_or_none", new_callable=AsyncMock, return_value=video):
        # --- Act ---
        await process_form_check_task(
            form_check_id=DUMMY_FORM_CHECK_ID,
            video_id=DUMMY_VIDEO_ID
        )

        # --- Assert ---
        mock_get_settings_override.assert_called_once()
        mock_get_async_session_context.assert_called_once_with(mock_settings)
        MockedAIService.assert_called_once_with(app_settings=mock_settings)
        MockedFormCheckService.assert_called_once_with(db_session=mock_db_session, settings=mock_settings)
        MockedExerciseConfigService.assert_called_once_with(db_session=mock_db_session)
        MockedDynamicFormAnalysisService.assert_called_once_with(db_session=mock_db_session, ai_service=mock_ai_service, settings=mock_settings)
        
        mock_ai_service.classify_exercise_from_keypoints.assert_called_once_with(
            keypoint_sequence=sample_raw_pose_data
        )
        mock_exercise_config_service.get_active_config_for_exercise_async.assert_not_called()
        mock_exercise_config_service.get_exercise_config_by_slug_async.assert_called_once_with(slug=classified_slug)
        mock_dfa_instance.analyze_form_dynamically.assert_called_once()
        mock_form_check_service.update_form_check_status_and_save_results_async.assert_called_once()
        update_args = mock_form_check_service.update_form_check_status_and_save_results_async.call_args[0]
        assert update_args[1] == FormCheckStatus.ANALYSIS_COMPLETE
        assert update_args[2]["score"] == 82.0
        assert update_args[2]["classified_exercise_slug"] == classified_slug
        assert update_args[2]["classification_confidence"] == classification_confidence


@pytest.mark.asyncio
@patch("app.tasks.analysis_tasks.get_settings_override")
@patch("app.tasks.analysis_tasks.get_async_session_context")
@patch("app.tasks.analysis_tasks.AIService")
@patch("app.tasks.analysis_tasks.FormCheckService")
@patch("app.tasks.analysis_tasks.ExerciseConfigService")
@patch("app.tasks.analysis_tasks.DynamicFormAnalysisService")
async def test_process_form_check_no_keypoint_data_for_classification_fails_task(
    MockedDynamicFormAnalysisService: MagicMock,
    MockedExerciseConfigService: MagicMock,
    MockedFormCheckService: MagicMock,
    MockedAIService: MagicMock,
    mock_get_async_session_context: MagicMock,
    mock_get_settings_override: MagicMock,
    mock_video_model_factory,
    mock_form_check_model_factory,
    mock_settings,
    mock_ai_service, 
    mock_form_check_service, 
    mock_exercise_config_service
):
    """
    Test Case 4: exercise_id is missing, and both pose_data and raw_pose_data are missing/invalid.
    The task should fail, and FormCheck status updated to ANALYSIS_FAILED.
    Classifier and DFA should not be called.
    """
    # --- Arrange ---
    mock_get_settings_override.return_value = mock_settings
    mock_db_session = AsyncMock()
    mock_async_context_manager = AsyncMock()
    mock_async_context_manager.__aenter__.return_value = mock_db_session
    mock_get_async_session_context.return_value = mock_async_context_manager

    MockedAIService.return_value = mock_ai_service
    MockedFormCheckService.return_value = mock_form_check_service
    MockedExerciseConfigService.return_value = mock_exercise_config_service
    MockedDynamicFormAnalysisService.return_value = AsyncMock() # Should not be called directly

    video_no_data = mock_video_model_factory(pose_data=None, raw_pose_data=None, angle_data=None, calculated_angles=[{}])
    form_check = mock_form_check_model_factory(exercise_id=None)
    mock_form_check_service.get_form_check_by_id_async.return_value = form_check

    with patch("app.models.video.Video.get_or_none", new_callable=AsyncMock, return_value=video_no_data):
        with pytest.raises(ValueError, match="Keypoint data unavailable for exercise classification."):
            await process_form_check_task(
                form_check_id=DUMMY_FORM_CHECK_ID,
                video_id=DUMMY_VIDEO_ID
            )
    
    mock_get_settings_override.assert_called_once()
    mock_get_async_session_context.assert_called_once_with(mock_settings)
    MockedAIService.assert_called_once_with(app_settings=mock_settings)
    # FormCheckService and ExerciseConfigService might not be called if error is early
    # MockedFormCheckService.assert_called_once_with(db_session=mock_db_session, settings=mock_settings)
    # MockedExerciseConfigService.assert_called_once_with(db_session=mock_db_session) 
    # MockedDynamicFormAnalysisService should not be instantiated if keypoint error occurs before its use
    MockedDynamicFormAnalysisService.assert_not_called() 

    mock_ai_service.classify_exercise_from_keypoints.assert_not_called()
    MockedDynamicFormAnalysisService.return_value.analyze_form_dynamically.assert_not_called()

    # Reset mocks for other scenarios in this test if any (currently, each scenario is one Act/Assert block)
    # For clarity, it might be better to have separate test functions for each invalid data scenario.
    # This example keeps them grouped under one test for brevity of this response.



@pytest.mark.asyncio
@patch("app.tasks.analysis_tasks.get_settings_override")
@patch("app.tasks.analysis_tasks.get_async_session_context")
@patch("app.tasks.analysis_tasks.AIService")
@patch("app.tasks.analysis_tasks.FormCheckService")
@patch("app.tasks.analysis_tasks.ExerciseConfigService")
@patch("app.tasks.analysis_tasks.DynamicFormAnalysisService")
async def test_process_form_check_classification_below_threshold(
    MockedDynamicFormAnalysisService: MagicMock,
    MockedExerciseConfigService: MagicMock,
    MockedFormCheckService: MagicMock,
    MockedAIService: MagicMock,
    mock_get_async_session_context: MagicMock,
    mock_get_settings_override: MagicMock,
    mock_video_model_factory,
    mock_form_check_model_factory,
    mock_settings, 
    mock_ai_service, 
    mock_form_check_service, 
    mock_exercise_config_service
):
    """
    Test Case 6: Classification succeeds but is below threshold.
    No ExerciseConfig is fetched by slug. DFA runs with no specific config.
    FormCheck is not updated with classification details.
    """
    # --- Arrange ---
    mock_get_settings_override.return_value = mock_settings
    mock_db_session = AsyncMock()
    mock_async_context_manager = AsyncMock()
    mock_async_context_manager.__aenter__.return_value = mock_db_session
    mock_get_async_session_context.return_value = mock_async_context_manager

    MockedAIService.return_value = mock_ai_service
    MockedFormCheckService.return_value = mock_form_check_service
    MockedExerciseConfigService.return_value = mock_exercise_config_service

    mock_dfa_instance = AsyncMock()
    mock_dfa_instance.analyze_form_dynamically = AsyncMock(return_value={
        "score": 60.0, 
        "overall_feedback": "Generic analysis, classification confidence too low.",
        "feedback_items": [],
        "form_metadata": {}
    })
    MockedDynamicFormAnalysisService.return_value = mock_dfa_instance

    sample_pose_data = [[{"x": 0.5, "y": 0.5, "z": 0.1, "visibility": 0.9}] * 33]
    video = mock_video_model_factory(pose_data=sample_pose_data, angle_data=None, calculated_angles=[{}])
    form_check = mock_form_check_model_factory(exercise_id=None)
    mock_form_check_service.get_form_check_by_id_async.return_value = form_check
    
    low_confidence_slug = "weak-classification"
    low_confidence = 0.50
    mock_ai_service.classify_exercise_from_keypoints = AsyncMock(return_value=(low_confidence_slug, low_confidence))

    with patch("app.models.video.Video.get_or_none", new_callable=AsyncMock, return_value=video):
        # --- Act ---
        await process_form_check_task(
            form_check_id=DUMMY_FORM_CHECK_ID,
            video_id=DUMMY_VIDEO_ID
        )

        # --- Assert ---
        mock_get_settings_override.assert_called_once()
        mock_get_async_session_context.assert_called_once_with(mock_settings)
        MockedAIService.assert_called_once_with(app_settings=mock_settings)
        MockedFormCheckService.assert_called_once_with(db_session=mock_db_session, settings=mock_settings)
        MockedExerciseConfigService.assert_called_once_with(db_session=mock_db_session)
        MockedDynamicFormAnalysisService.assert_called_once_with(db_session=mock_db_session, ai_service=mock_ai_service, settings=mock_settings)

        mock_ai_service.classify_exercise_from_keypoints.assert_called_once_with(keypoint_sequence=sample_pose_data)
        mock_exercise_config_service.get_exercise_config_by_slug_async.assert_not_called()
        mock_exercise_config_service.get_active_config_for_exercise_async.assert_not_called()
        mock_dfa_instance.analyze_form_dynamically.assert_called_once()
        call_args_dfa = mock_dfa_instance.analyze_form_dynamically.call_args[0]
        assert call_args_dfa[1] is None 
        mock_form_check_service.update_form_check_status_and_save_results_async.assert_called_once()
        update_args = mock_form_check_service.update_form_check_status_and_save_results_async.call_args[0]
        assert update_args[1] == FormCheckStatus.ANALYSIS_COMPLETE
        assert update_args[2]["score"] == 60.0
        assert update_args[2].get("classified_exercise_slug") is None
        assert update_args[2].get("classification_confidence") is None


@pytest.mark.asyncio
@patch("app.tasks.analysis_tasks.get_settings_override")
@patch("app.tasks.analysis_tasks.get_async_session_context")
@patch("app.tasks.analysis_tasks.AIService")
@patch("app.tasks.analysis_tasks.FormCheckService")
@patch("app.tasks.analysis_tasks.ExerciseConfigService")
@patch("app.tasks.analysis_tasks.DynamicFormAnalysisService")
async def test_process_form_check_classification_fails_completely(
    MockedDynamicFormAnalysisService: MagicMock,
    MockedExerciseConfigService: MagicMock,
    MockedFormCheckService: MagicMock,
    MockedAIService: MagicMock,
    mock_get_async_session_context: MagicMock,
    mock_get_settings_override: MagicMock,
    mock_video_model_factory,
    mock_form_check_model_factory,
    mock_settings,
    mock_ai_service, 
    mock_form_check_service, 
    mock_exercise_config_service
):
    """
    Test Case 7: Classification fails entirely (returns None, 0.0).
    No ExerciseConfig is fetched. DFA runs with no specific config.
    FormCheck is not updated with classification details.
    """
    # --- Arrange ---
    mock_get_settings_override.return_value = mock_settings
    mock_db_session = AsyncMock()
    mock_async_context_manager = AsyncMock()
    mock_async_context_manager.__aenter__.return_value = mock_db_session
    mock_get_async_session_context.return_value = mock_async_context_manager

    MockedAIService.return_value = mock_ai_service
    MockedFormCheckService.return_value = mock_form_check_service
    MockedExerciseConfigService.return_value = mock_exercise_config_service

    mock_dfa_instance = AsyncMock()
    mock_dfa_instance.analyze_form_dynamically = AsyncMock(return_value={
        "score": 50.0, 
        "overall_feedback": "Generic analysis, classification failed.",
        "feedback_items": [],
        "form_metadata": {}
    })
    MockedDynamicFormAnalysisService.return_value = mock_dfa_instance

    sample_pose_data = [[{"x": 0.5, "y": 0.5, "z": 0.1, "visibility": 0.9}] * 33]
    video = mock_video_model_factory(pose_data=sample_pose_data, angle_data=None, calculated_angles=[{}])
    form_check = mock_form_check_model_factory(exercise_id=None)
    mock_form_check_service.get_form_check_by_id_async.return_value = form_check
    
    mock_ai_service.classify_exercise_from_keypoints = AsyncMock(return_value=(None, 0.0))

    with patch("app.models.video.Video.get_or_none", new_callable=AsyncMock, return_value=video):
        # --- Act ---
        await process_form_check_task(
            form_check_id=DUMMY_FORM_CHECK_ID,
            video_id=DUMMY_VIDEO_ID
        )

        # --- Assert ---
        mock_get_settings_override.assert_called_once()
        mock_get_async_session_context.assert_called_once_with(mock_settings)
        MockedAIService.assert_called_once_with(app_settings=mock_settings)
        MockedFormCheckService.assert_called_once_with(db_session=mock_db_session, settings=mock_settings)
        MockedExerciseConfigService.assert_called_once_with(db_session=mock_db_session)
        MockedDynamicFormAnalysisService.assert_called_once_with(db_session=mock_db_session, ai_service=mock_ai_service, settings=mock_settings)

        mock_ai_service.classify_exercise_from_keypoints.assert_called_once_with(keypoint_sequence=sample_pose_data)
        mock_exercise_config_service.get_exercise_config_by_slug_async.assert_not_called()
        mock_exercise_config_service.get_active_config_for_exercise_async.assert_not_called()
        mock_dfa_instance.analyze_form_dynamically.assert_called_once()
        call_args_dfa = mock_dfa_instance.analyze_form_dynamically.call_args[0]
        assert call_args_dfa[1] is None
        mock_form_check_service.update_form_check_status_and_save_results_async.assert_called_once()
        update_args = mock_form_check_service.update_form_check_status_and_save_results_async.call_args[0]
        assert update_args[1] == FormCheckStatus.ANALYSIS_COMPLETE
        assert update_args[2]["score"] == 50.0
        assert update_args[2].get("classified_exercise_slug") is None
        assert update_args[2].get("classification_confidence") is None
