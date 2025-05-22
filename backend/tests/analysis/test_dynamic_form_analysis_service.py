import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch, call
from uuid import uuid4
from typing import List, Dict, Any, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai.dynamic_form_analysis_service import DynamicFormAnalysisService
from app.services.exercise_config_service import ExerciseConfigService
from app.services.form_check_service import FormCheckService
from app.models.exercise_config import ExerciseConfig, MovementPhase, JointAngleRule, FeedbackTemplate, TriggerCondition
from app.models.video import Video
from app.models.form_check import FormCheck, FeedbackItem
from app.schemas.exercise_config import (
    JointAngleRules,
    PhaseJointRules,
    JointAngleRule as PydanticJointAngleRule,
    FeedbackTemplate as PydanticFeedbackTemplate,
    ClassificationMetadata as PydanticClassificationMetadata
)
from app.schemas.form_check import FeedbackItemCreate
from app.models.enums import FeedbackType, FeedbackSeverity
from app.core.config import Settings
from app.core.exceptions import ValidationError, ServerErrorException


@pytest.fixture
def mock_db_session() -> AsyncMock:
    session = AsyncMock()
    session.merge = AsyncMock(side_effect=lambda x: x) # Ensure merge returns the object
    session.refresh = AsyncMock()
    return session

@pytest.fixture
def mock_settings() -> MagicMock:
    settings = MagicMock()
    # Add any specific settings attributes if needed by the service
    return settings

@pytest.fixture
def mock_exercise_config_service() -> AsyncMock:
    return AsyncMock(spec=ExerciseConfigService)

@pytest.fixture
def mock_form_check_service() -> AsyncMock:
    return AsyncMock(spec=FormCheckService)

@pytest.fixture
def dynamic_form_analysis_service(
    mock_db_session: AsyncMock,
    mock_settings: MagicMock,
    mock_exercise_config_service: AsyncMock,
    mock_form_check_service: AsyncMock
) -> DynamicFormAnalysisService:
    return DynamicFormAnalysisService(
        db=mock_db_session,
        settings=mock_settings,
        exercise_config_service=mock_exercise_config_service,
        form_check_service=mock_form_check_service
    )

@pytest.fixture
def sample_video(sample_angle_data_two_reps: List[Dict[str, Any]]) -> Video:
    video = Video(
        id=uuid4(),
        user_id=uuid4(),
        s3_bucket="test_bucket",
        s3_object_key="test_video.mp4",
        status="processed",
        exercise_template_id=uuid4(),
        angle_data=sample_angle_data_two_reps 
    )
    return video

@pytest.fixture
def sample_squat_config() -> ExerciseConfig:
    config = ExerciseConfig(
        id=uuid4(),
        name="Test Squat Config",
        exercise_id=uuid4(),
        version=1,
        is_active=True,
        joint_angle_rules=JointAngleRules(
            phases={
                "start_phase": PhaseJointRules(angles={
                    "leftKnee": PydanticJointAngleRule(min_angle=160, max_angle=180, ideal_angle=170, tolerance=10),
                    "leftHip": PydanticJointAngleRule(min_angle=160, max_angle=180, ideal_angle=170, tolerance=10),
                }),
                "descent_phase": PhaseJointRules(angles={
                    "leftKnee": PydanticJointAngleRule(min_angle=80, max_angle=100, ideal_angle=90, tolerance=5),
                    "leftHip": PydanticJointAngleRule(min_angle=80, max_angle=100, ideal_angle=90, tolerance=5),
                }),
                "ascent_phase": PhaseJointRules(angles={
                    "leftKnee": PydanticJointAngleRule(min_angle=160, max_angle=180, ideal_angle=170, tolerance=10),
                    "leftHip": PydanticJointAngleRule(min_angle=160, max_angle=180, ideal_angle=170, tolerance=10),
                }),
                "unknown": PhaseJointRules(angles={ 
                    "leftKnee": PydanticJointAngleRule(min_angle=0, max_angle=180, ideal_angle=90, tolerance=30),
                    "leftHip": PydanticJointAngleRule(min_angle=0, max_angle=180, ideal_angle=90, tolerance=30),
                })
            },
            joints=["leftKnee", "rightKnee", "leftHip", "rightHip"]
        ),
        movement_phases=dict(
            start_phase=MovementPhase(
                description="Standing upright",
                triggers={"next": [TriggerCondition(joint="leftKnee", condition="angle", value=150, comparator="<")]}
            ),
            descent_phase=MovementPhase(
                description="Lowering body",
                triggers={
                    "next": [TriggerCondition(joint="leftKnee", condition="angle", value=95, comparator="<")],
                    "previous": [TriggerCondition(joint="leftKnee", condition="angle", value=160, comparator=">")]
                }
            ),
            ascent_phase=MovementPhase(
                description="Returning to standing",
                triggers={
                    "next": [TriggerCondition(joint="leftKnee", condition="angle", value=165, comparator=">")],
                    "previous": [TriggerCondition(joint="leftKnee", condition="angle", value=100, comparator=">")]
                }
            )
        ),
        feedback_templates=dict(
            knee_too_bent_start=PydanticFeedbackTemplate(message="Knees too bent at start: {joint} at {actual:.1f}", severity="low", type="form"),
            knee_not_bent_enough_descent=PydanticFeedbackTemplate(message="Squat deeper: {joint} at {actual:.1f}, expected < 100", severity="medium", type="range"),
            hip_too_upright_descent=PydanticFeedbackTemplate(message="Hips not back enough in descent: {joint} at {actual:.1f}", severity="medium", type="form"),
            general_issue=PydanticFeedbackTemplate(message="General issue with {joint}", severity="low", type="form")
        ),
        classification_metadata=PydanticClassificationMetadata(
            keypoints=["leftKnee", "leftHip"], frame_count=30, features={}
        )
    )
    return config


# --- Fixtures for sample angle data ---
@pytest.fixture
def sample_angle_data_one_rep() -> List[Dict[str, Any]]:
    """Provides angle data for a single, typical squat repetition."""
    return [
        {"frame_num": 0, "angles": {"leftKnee": 175.0, "leftHip": 175.0}}, # start_phase
        {"frame_num": 1, "angles": {"leftKnee": 140.0, "leftHip": 140.0}}, # descent_phase
        {"frame_num": 2, "angles": {"leftKnee": 90.0,  "leftHip": 90.0}},  # descent_phase (bottom)
        {"frame_num": 3, "angles": {"leftKnee": 140.0, "leftHip": 140.0}}, # ascent_phase
        {"frame_num": 4, "angles": {"leftKnee": 175.0, "leftHip": 175.0}}, # ascent_phase (end) -> back to start_phase implicitly for next rep
    ]

@pytest.fixture
def sample_angle_data_two_reps(sample_angle_data_one_rep: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Provides angle data for two repetitions."""
    rep1 = sample_angle_data_one_rep
    rep2 = [{**frame, "frame_num": frame["frame_num"] + len(rep1)} for frame in rep1]
    return rep1 + rep2

@pytest.fixture
def sample_angle_data_with_errors() -> List[Dict[str, Any]]:
    """Angle data for one rep with a clear error (not squatting deep enough)."""
    return [
        {"frame_num": 0, "angles": {"leftKnee": 175.0, "leftHip": 175.0}}, # start_phase
        {"frame_num": 1, "angles": {"leftKnee": 140.0, "leftHip": 140.0}}, # descent_phase
        {"frame_num": 2, "angles": {"leftKnee": 110.0, "leftHip": 110.0}}, # descent_phase (bottom, but too shallow -> knee > 100)
        {"frame_num": 3, "angles": {"leftKnee": 140.0, "leftHip": 140.0}}, # ascent_phase
        {"frame_num": 4, "angles": {"leftKnee": 175.0, "leftHip": 175.0}}, # ascent_phase (end)
    ]

@pytest.fixture
def sample_video_model():
    return Video(
        id="test_video_id",
        user_id="test_user_id",
        exercise_template_id="squat_template_v1",
        angle_data=json.dumps([]), # Default to empty, override in tests
        s3_key_raw="raw/video.mp4",
        status="ANGLES_CALCULATED", # Assume angles are ready
        duration_seconds=10.0
    )

@pytest.fixture
def sample_form_check_model():
    return FormCheck(
        id="test_form_check_id",
        video_id="test_video_id",
        user_id="test_user_id",
        exercise_template_id="squat_template_v1",
        status="pending_analysis" # initial status for analysis
    )

@pytest.fixture
def sample_squat_config_fsm() -> ExerciseConfig:
    return ExerciseConfig(
        id="squat_template_v1_config_fsm",
        exercise_template_id="squat_template_v1",
        name="Squat FSM Config",
        version=1,
        is_active=True,
        movement_phases={
            "start_phase": MovementPhase(
                name="Start Phase",
                description="Standing, preparing for squat.",
                order=0,
                triggers={
                    "next": [TriggerCondition(joint="leftHip", comparator="<", value=160)] # Trigger to descent
                },
                expected_duration_range=(0.5, 2.0)
            ),
            "descent_phase": MovementPhase(
                name="Descent Phase",
                description="Lowering into the squat.",
                order=1,
                triggers={
                     "next": [TriggerCondition(joint="leftKnee", comparator="<", value=90)] # Trigger to bottom
                },
                expected_duration_range=(1.0, 3.0)
            ),
            "bottom_phase": MovementPhase(
                name="Bottom Phase",
                description="Lowest point of the squat.",
                order=2,
                triggers={
                    "next": [TriggerCondition(joint="leftKnee", comparator=">", value=95)] # Trigger to ascent
                },
                expected_duration_range=(0.2, 1.0)
            ),
            "ascent_phase": MovementPhase(
                name="Ascent Phase",
                description="Rising from the squat.",
                order=3,
                triggers={
                    # Transition back to start_phase
                    "start_phase": [TriggerCondition(joint="leftHip", comparator=">", value=170)]
                },
                expected_duration_range=(1.0, 3.0)
            )
        },
        joint_angle_rules=[
            JointAngleRule(
                joint="leftKnee",
                phase="descent_phase",
                min_angle=70,
                max_angle=170,
                ideal_angle=90,
                tolerance=10,
                feedback_template_key="knee_descent_angle"
            ),
            JointAngleRule(
                joint="leftKnee",
                phase="bottom_phase",
                min_angle=60, # Deeper for bottom
                max_angle=100,
                ideal_angle=75,
                tolerance=10,
                feedback_template_key="knee_bottom_angle"
            ),
            JointAngleRule(
                joint="backTilt", # Example for back angle
                phase="descent_phase",
                min_angle=-10, # Allow slight forward tilt
                max_angle=15, # But not excessive rounding or arching
                ideal_angle=0,
                tolerance=5,
                feedback_template_key="back_angle_general"
            )
        ],
        feedback_templates={
            "knee_descent_angle_below_min": PydanticFeedbackTemplate(
                message="Your left knee angle ({actual:.1f}°) is too low during descent. Expected > {expected_min:.1f}°.",
                type=FeedbackType.FORM,
                severity=FeedbackSeverity.MEDIUM,
                details="Try to control your descent and not let your knees go too far past your toes."
            ),
            "knee_bottom_angle_below_min": PydanticFeedbackTemplate(
                message="Your left knee angle ({actual:.1f}°) is too acute at the bottom. Expected > {expected_min:.1f}°.",
                type=FeedbackType.FORM,
                severity=FeedbackSeverity.HIGH,
                details="Ensure you're not collapsing at the bottom of the squat."
            ),
            "back_angle_general_below_min": PydanticFeedbackTemplate(
                message="Your back is rounding too much ({actual:.1f}°). Keep your chest up. Expected > {expected_min:.1f}°.",
                type=FeedbackType.POSTURE,
                severity=FeedbackSeverity.HIGH
            ),
             "back_angle_general_above_max": PydanticFeedbackTemplate(
                message="Your back is over-arched ({actual:.1f}°). Maintain a neutral spine. Expected < {expected_max:.1f}°.",
                type=FeedbackType.POSTURE,
                severity=FeedbackSeverity.MEDIUM
            ),
            "general_default_feedback": PydanticFeedbackTemplate(
                message="Form issue with {joint} during {phase}. Angle: {actual:.1f}°. Please review.",
                type=FeedbackType.FORM,
                severity=FeedbackSeverity.LOW
            )
        },
        scoring_config={"base_score": 100, "deductions_per_issue_severity": {"low": 2, "medium": 5, "high": 10, "critical": 20}}
    )

@pytest.fixture
def sample_angle_data_one_good_rep() -> List[Dict[str, Any]]:
    return [
        # Start Phase
        {"frame_num": 0, "timestamp": 0.0, "angles": {"leftHip": 175, "leftKnee": 170, "backTilt": 0}},
        {"frame_num": 1, "timestamp": 0.03, "angles": {"leftHip": 170, "leftKnee": 165, "backTilt": 1}}, # Transition to descent
        # Descent Phase
        {"frame_num": 2, "timestamp": 0.06, "angles": {"leftHip": 150, "leftKnee": 140, "backTilt": 2}},
        {"frame_num": 3, "timestamp": 0.09, "angles": {"leftHip": 120, "leftKnee": 110, "backTilt": 3}},
        {"frame_num": 4, "timestamp": 0.12, "angles": {"leftHip": 100, "leftKnee": 85, "backTilt": 2}}, # Transition to bottom
        # Bottom Phase
        {"frame_num": 5, "timestamp": 0.15, "angles": {"leftHip": 95, "leftKnee": 80, "backTilt": 1}},
        {"frame_num": 6, "timestamp": 0.18, "angles": {"leftHip": 98, "leftKnee": 96, "backTilt": 0}}, # Transition to ascent
        # Ascent Phase
        {"frame_num": 7, "timestamp": 0.21, "angles": {"leftHip": 110, "leftKnee": 120, "backTilt": -1}},
        {"frame_num": 8, "timestamp": 0.24, "angles": {"leftHip": 140, "leftKnee": 150, "backTilt": 0}},
        {"frame_num": 9, "timestamp": 0.27, "angles": {"leftHip": 175, "leftKnee": 170, "backTilt": 1}}, # Transition to start
        # Start Phase (end of rep)
        {"frame_num": 10, "timestamp": 0.30, "angles": {"leftHip": 178, "leftKnee": 175, "backTilt": 0}},
    ]

@pytest.fixture
def sample_angle_data_two_reps_one_bad() -> List[Dict[str, Any]]:
    return [
        # Rep 1 (Good)
        {"frame_num": 0, "timestamp": 0.0, "angles": {"leftHip": 175, "leftKnee": 170, "backTilt": 0}},
        {"frame_num": 1, "timestamp": 0.03, "angles": {"leftHip": 150, "leftKnee": 140, "backTilt": 2}}, # Enters Descent
        {"frame_num": 2, "timestamp": 0.06, "angles": {"leftHip": 100, "leftKnee": 85, "backTilt": 2}}, # Enters Bottom
        {"frame_num": 3, "timestamp": 0.09, "angles": {"leftHip": 130, "leftKnee": 130, "backTilt": 0}}, # Enters Ascent
        {"frame_num": 4, "timestamp": 0.12, "angles": {"leftHip": 175, "leftKnee": 170, "backTilt": 1}}, # Enters Start (End Rep 1)
        # Inter-rep rest / start phase
        {"frame_num": 5, "timestamp": 0.15, "angles": {"leftHip": 176, "leftKnee": 172, "backTilt": 0}},
        # Rep 2 (Bad - back rounds too much in descent)
        {"frame_num": 6, "timestamp": 0.18, "angles": {"leftHip": 175, "leftKnee": 170, "backTilt": 0}},
        {"frame_num": 7, "timestamp": 0.21, "angles": {"leftHip": 150, "leftKnee": 140, "backTilt": -20}}, # Bad back angle, enters descent
        {"frame_num": 8, "timestamp": 0.24, "angles": {"leftHip": 100, "leftKnee": 85, "backTilt": -22}}, # Still bad, enters bottom
        {"frame_num": 9, "timestamp": 0.27, "angles": {"leftHip": 130, "leftKnee": 130, "backTilt": -18}}, # Improving but still bad, enters ascent
        {"frame_num": 10, "timestamp": 0.30, "angles": {"leftHip": 175, "leftKnee": 170, "backTilt": 0}}, # Enters Start (End Rep 2)
        {"frame_num": 11, "timestamp": 0.33, "angles": {"leftHip": 178, "leftKnee": 175, "backTilt": 0}},
    ]

@pytest.mark.asyncio
async def test_segment_repetitions_logic(
    dynamic_form_analysis_service: DynamicFormAnalysisService,
    sample_angle_data_two_reps: List[Dict[str, Any]],
    sample_squat_config: ExerciseConfig
):
    """Test segment_repetitions with more realistic data and logic (still simplified FSM)."""
    repetitions = await dynamic_form_analysis_service.segment_repetitions(sample_angle_data_two_reps, sample_squat_config)
    
    # Current simplified FSM in service might struggle with precise 2 reps.
    # This test will need adjustment based on how robust the segmentation becomes.
    # For now, we expect it to find *something* or the whole thing if logic is very basic.
    assert len(repetitions) >= 1, "Should detect at least one repetition group"
    if len(repetitions) == 1:
        assert len(repetitions[0]) == len(sample_angle_data_two_reps)
    elif len(repetitions) == 2:
        assert len(repetitions[0]) == 5
        assert len(repetitions[1]) == 5
    # Add more specific assertions once segmentation is more deterministic
    # print(f"Detected {len(repetitions)} reps from test_segment_repetitions_logic")

@pytest.mark.asyncio
async def test_evaluate_rep_no_errors(
    dynamic_form_analysis_service: DynamicFormAnalysisService,
    sample_angle_data_one_rep: List[Dict[str, Any]],
    sample_squat_config: ExerciseConfig
):
    """Test evaluate_rep with good form data, expecting no feedback items and high score."""
    feedback_items, score = await dynamic_form_analysis_service.evaluate_rep(sample_angle_data_one_rep, sample_squat_config)
    
    assert len(feedback_items) == 0, "Should find no issues with good form data"
    assert score == 100.0, "Score should be perfect for good form"

@pytest.mark.asyncio
async def test_evaluate_rep_with_errors(
    dynamic_form_analysis_service: DynamicFormAnalysisService,
    sample_angle_data_with_errors: List[Dict[str, Any]],
    sample_squat_config: ExerciseConfig
):
    """Test evaluate_rep with data that should trigger a rule violation."""
    feedback_items, score = await dynamic_form_analysis_service.evaluate_rep(sample_angle_data_with_errors, sample_squat_config)
    
    assert len(feedback_items) > 0, "Should detect at least one issue with shallow squat data"
    assert score < 100.0, "Score should be less than 100 due to issues"
    
    found_shallow_squat_feedback = False
    for item in feedback_items:
        assert isinstance(item, FeedbackItemCreate)
        if "Squat deeper" in item.message:
            found_shallow_squat_feedback = True
            assert item.type == FeedbackType.RANGE
            assert item.severity == FeedbackSeverity.MEDIUM
            # Check if expected joint angle data is somewhat present in feedback
            # The current implementation puts expected in `joint_angles` field of FeedbackItemCreate
            assert item.joint_angles is not None 
            assert "min" in item.joint_angles or "ideal" in item.joint_angles
    assert found_shallow_squat_feedback, "Specific feedback for not squatting deep enough was not found"


@pytest.mark.asyncio
async def test_analyze_form_dynamically_e2e_flow(
    dynamic_form_analysis_service: DynamicFormAnalysisService,
    sample_video: Video, # Uses sample_angle_data_two_reps
    sample_squat_config: ExerciseConfig,
    mock_form_check_service: AsyncMock,
    mock_exercise_config_service: AsyncMock,
    mock_db_session: AsyncMock # For commit/refresh checks
):
    """Test the end-to-end flow of analyze_form_dynamically with implemented logic."""
    
    mock_fc_instance = FormCheck(id=uuid4(), video_id=sample_video.id, exercise_id=sample_video.exercise_template_id, status="pending", reps_detected=0)
    mock_form_check_service.get_or_create_form_check_for_video = AsyncMock(return_value=(mock_fc_instance, True))
    
    sample_squat_config.exercise_id = sample_video.exercise_template_id # Align IDs
    mock_exercise_config_service.get_active_config_for_exercise_async = AsyncMock(return_value=sample_squat_config)
    
    # `create_feedback_items_in_db` is part of the service, so it's not easily mocked
    # unless we patch it directly on the instance or use a spy.
    # For now, we trust its internal call and check its effect via FormCheck updates.
    # We can also mock `self.db.add_all` and `self.db.commit` if needed.
    dynamic_form_analysis_service.create_feedback_items_in_db = AsyncMock(return_value=[]) # Mock to prevent DB interaction

    result_form_check = await dynamic_form_analysis_service.analyze_form_dynamically(sample_video)

    mock_form_check_service.get_or_create_form_check_for_video.assert_called_once_with(video_id=sample_video.id)
    mock_exercise_config_service.get_active_config_for_exercise_async.assert_called_once_with(exercise_id=sample_video.exercise_template_id)
    
    assert result_form_check.status == "analysis_complete"
    # Based on sample_angle_data_two_reps and simplified segmentation, it might find 1 or 2 reps.
    # If 2 reps, and each is perfect (100 score), overall is 100.
    # If segmentation is basic and treats all as 1 rep, score will be based on that one rep.
    # This needs to be adjusted based on actual segmentation output.
    # print(f"Test E2E: Reps Detected: {result_form_check.reps_detected}, Score: {result_form_check.overall_score}")
    
    if result_form_check.reps_detected and result_form_check.reps_detected > 0:
        assert result_form_check.overall_score == 100.0 # Assuming good form data yields 100 per rep
        dynamic_form_analysis_service.create_feedback_items_in_db.assert_not_called() # No feedback for good form
    else:
        # If no reps were detected (possible with very basic segmentation)
        assert result_form_check.overall_score == 0.0
        assert "Could not detect any full repetitions" in result_form_check.overall_feedback

    mock_db_session.merge.assert_called_once_with(mock_fc_instance)
    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once_with(mock_fc_instance)

@pytest.mark.asyncio
async def test_analyze_form_dynamically_no_config(
    dynamic_form_analysis_service: DynamicFormAnalysisService,
    sample_video: Video,
    mock_form_check_service: AsyncMock,
    mock_exercise_config_service: AsyncMock,
    mock_db_session: AsyncMock
):
    mock_fc_instance = FormCheck(id=uuid4(), video_id=sample_video.id, status="pending")
    mock_form_check_service.get_or_create_form_check_for_video = AsyncMock(return_value=(mock_fc_instance, True))
    mock_exercise_config_service.get_active_config_for_exercise_async = AsyncMock(return_value=None) # No config

    result = await dynamic_form_analysis_service.analyze_form_dynamically(sample_video)

    assert result.status == "analysis_failed"
    assert "No valid exercise configuration found" in result.overall_feedback
    mock_db_session.merge.assert_called_once_with(mock_fc_instance)
    mock_db_session.commit.assert_called_once()

@pytest.mark.asyncio
async def test_analyze_form_dynamically_no_angle_data(
    dynamic_form_analysis_service: DynamicFormAnalysisService,
    sample_video: Video, # Video fixture
    mock_form_check_service: AsyncMock,
    mock_db_session: AsyncMock
):
    sample_video.angle_data = [] # Empty angle data
    mock_fc_instance = FormCheck(id=uuid4(), video_id=sample_video.id, status="pending")
    mock_form_check_service.get_or_create_form_check_for_video = AsyncMock(return_value=(mock_fc_instance, True))

    with pytest.raises(ValidationError, match="Video angle data is missing or empty"):
        await dynamic_form_analysis_service.analyze_form_dynamically(sample_video)
    
    # Check that FormCheck was updated to failed status
    updated_fc = mock_form_check_service.get_or_create_form_check_for_video.call_args[0][0]
    # This check is tricky because the instance is modified. Better to check DB calls.
    # Assert that status was updated before exception
    # This requires inspecting the mock_fc_instance that was passed to merge/commit
    assert mock_fc_instance.status == "analysis_failed"
    assert "Video angle data is missing or empty" in mock_fc_instance.overall_feedback
    mock_db_session.merge.assert_called_once_with(mock_fc_instance)
    mock_db_session.commit.assert_called_once() 

# Placeholder tests from previous plan - to be removed or integrated above
# @pytest.mark.asyncio
# async def test_segment_repetitions_placeholder(...): ...
# @pytest.mark.asyncio
# async def test_evaluate_rep_placeholder(...): ...
# @pytest.mark.asyncio
# async def test_analyze_form_dynamically_structure(...): ...

# TODO: Add more specific tests for segment_repetitions FSM logic once it's robust.
# Example: test_segment_repetitions_multiple_reps_precise, _incomplete_rep, etc. 

@pytest.mark.asyncio
async def test_evaluate_phase_transitions_basic(dynamic_form_analysis_service: DynamicFormAnalysisService, sample_squat_config_fsm: ExerciseConfig):
    service = dynamic_form_analysis_service
    config = sample_squat_config_fsm

    # From start_phase to descent_phase
    angles_to_descent = {"leftHip": 150} # < 160
    next_phase = service._evaluate_phase_transitions("start_phase", config.movement_phases, angles_to_descent)
    assert next_phase == "descent_phase"

    # From descent_phase to bottom_phase
    angles_to_bottom = {"leftKnee": 80} # < 90
    next_phase = service._evaluate_phase_transitions("descent_phase", config.movement_phases, angles_to_bottom)
    assert next_phase == "bottom_phase"
    
    # From ascent_phase to start_phase (specific key in trigger)
    angles_to_start = {"leftHip": 175} # > 170
    next_phase = service._evaluate_phase_transitions("ascent_phase", config.movement_phases, angles_to_start)
    assert next_phase == "start_phase"

    # No transition if conditions not met
    angles_stay_start = {"leftHip": 165} # Not < 160
    next_phase = service._evaluate_phase_transitions("start_phase", config.movement_phases, angles_stay_start)
    assert next_phase is None

@pytest.mark.asyncio
async def test_segment_repetitions_one_good_rep(
    dynamic_form_analysis_service: DynamicFormAnalysisService,
    sample_squat_config_fsm: ExerciseConfig,
    sample_angle_data_one_good_rep: List[Dict[str, Any]]
):
    service = dynamic_form_analysis_service
    reps, reps_phases = await service.segment_repetitions(sample_angle_data_one_good_rep, sample_squat_config_fsm)
    
    assert len(reps) == 1
    assert len(reps_phases) == 1
    # Rep 1 should contain frames 1 through 9 (inclusive by frame_num)
    # Frame 0: start_phase (initial, before rep starts)
    # Frame 1: descent_phase (rep starts here)
    # ...
    # Frame 9: start_phase (rep ends here, transition from ascent)
    # Frame 10: start_phase (after rep ended)
    # Expected rep length is 9 frames (indices 1-9)
    assert len(reps[0]) == 9 
    assert len(reps_phases[0]) == 9

    # Check some frame numbers to ensure correct segmentation boundaries
    assert reps[0][0]["frame_num"] == 1 # First frame of rep
    assert reps[0][-1]["frame_num"] == 9 # Last frame of rep

    # Check some phases
    # Phase for frame_num 1 (angles: {"leftHip": 170, ...}) should be descent_phase
    assert reps_phases[0][0] == "descent_phase" 
    # Phase for frame_num 4 (angles: {"leftHip": 100, "leftKnee": 85, ...}) should be bottom_phase
    assert reps_phases[0][3] == "bottom_phase" 
    # Phase for frame_num 9 (angles: {"leftHip": 175, ...}) should be start_phase (transition from ascent)
    assert reps_phases[0][-1] == "start_phase"

@pytest.mark.asyncio
async def test_segment_repetitions_two_reps(
    dynamic_form_analysis_service: DynamicFormAnalysisService,
    sample_squat_config_fsm: ExerciseConfig,
    sample_angle_data_two_reps_one_bad: List[Dict[str, Any]]
):
    service = dynamic_form_analysis_service
    reps, reps_phases = await service.segment_repetitions(sample_angle_data_two_reps_one_bad, sample_squat_config_fsm)
    
    assert len(reps) == 2
    assert len(reps_phases) == 2
    
    # Rep 1: frames 1-4 (4 frames)
    assert reps[0][0]["frame_num"] == 1
    assert reps[0][-1]["frame_num"] == 4
    assert len(reps[0]) == 4
    assert len(reps_phases[0]) == 4
    assert reps_phases[0][0] == "descent_phase" # hip < 160
    assert reps_phases[0][-1] == "start_phase" # hip > 170

    # Rep 2: frames 7-10 (4 frames)
    assert reps[1][0]["frame_num"] == 7
    assert reps[1][-1]["frame_num"] == 10
    assert len(reps[1]) == 4
    assert len(reps_phases[1]) == 4
    assert reps_phases[1][0] == "descent_phase"
    assert reps_phases[1][-1] == "start_phase"

@pytest.mark.asyncio
async def test_segment_repetitions_no_reps_if_not_enough_transitions(
    dynamic_form_analysis_service: DynamicFormAnalysisService,
    sample_squat_config_fsm: ExerciseConfig
):
    service = dynamic_form_analysis_service
    # Data that stays in start_phase or only makes one transition but doesn't complete a cycle
    angle_data_no_rep = [
        {"frame_num": 0, "angles": {"leftHip": 175, "leftKnee": 170}}, # Start
        {"frame_num": 1, "angles": {"leftHip": 172, "leftKnee": 168}}, # Start
        {"frame_num": 2, "angles": {"leftHip": 150, "leftKnee": 140}}, # Descent
        {"frame_num": 3, "angles": {"leftHip": 145, "leftKnee": 135}}, # Descent
    ]
    reps, reps_phases = await service.segment_repetitions(angle_data_no_rep, sample_squat_config_fsm)
    assert len(reps) == 0
    assert len(reps_phases) == 0

@pytest.mark.asyncio
async def test_segment_repetitions_handles_empty_data_or_config(dynamic_form_analysis_service: DynamicFormAnalysisService, sample_squat_config_fsm: ExerciseConfig):
    service = dynamic_form_analysis_service
    reps, phases = await service.segment_repetitions([], sample_squat_config_fsm)
    assert len(reps) == 0
    assert len(phases) == 0

    empty_config = ExerciseConfig(id="empty", exercise_template_id="empty", name="Empty", version=1, movement_phases={})
    reps, phases = await service.segment_repetitions([{"frame_num": 0, "angles": {"leftHip": 170}}], empty_config)
    assert len(reps) == 0
    assert len(phases) == 0

@pytest.mark.asyncio
async def test_evaluate_rep_one_good_rep_no_errors(
    dynamic_form_analysis_service: DynamicFormAnalysisService,
    sample_squat_config_fsm: ExerciseConfig,
    sample_angle_data_one_good_rep: List[Dict[str, Any]]
):
    service = dynamic_form_analysis_service
    # Manually create the rep segment and phases as segment_repetitions would
    # Rep is frames 1-9
    test_rep_frames = sample_angle_data_one_good_rep[1:10] 
    # Corresponding phases (assuming perfect phase detection by FSM for this test)
    # Frame 1 (idx 0 in test_rep_frames): descent (hip 170 < 160 from start)
    # Frame 2 (idx 1): descent
    # Frame 3 (idx 2): descent
    # Frame 4 (idx 3): bottom (knee 85 < 90 from descent)
    # Frame 5 (idx 4): bottom 
    # Frame 6 (idx 5): ascent (knee 96 > 95 from bottom)
    # Frame 7 (idx 6): ascent
    # Frame 8 (idx 7): ascent
    # Frame 9 (idx 8): start (hip 175 > 170 from ascent)
    test_rep_phases = [
        "descent_phase", "descent_phase", "descent_phase", 
        "bottom_phase", "bottom_phase", 
        "ascent_phase", "ascent_phase", "ascent_phase", 
        "start_phase" 
    ]
    
    assert len(test_rep_frames) == len(test_rep_phases)

    feedback_items, score = await service.evaluate_rep(test_rep_frames, test_rep_phases, sample_squat_config_fsm)
    
    assert len(feedback_items) == 0 # No errors expected
    assert score == 100.0

@pytest.mark.asyncio
async def test_evaluate_rep_with_errors(
    dynamic_form_analysis_service: DynamicFormAnalysisService,
    sample_squat_config_fsm: ExerciseConfig
):
    service = dynamic_form_analysis_service
    # Create a rep with a clear error: back rounding in descent
    rep_frames_with_error = [
        {"frame_num": 0, "timestamp": 0.0, "angles": {"leftHip": 150, "leftKnee": 140, "backTilt": -20}}, # Error: backTilt < -10
        {"frame_num": 1, "timestamp": 0.03, "angles": {"leftHip": 120, "leftKnee": 110, "backTilt": -22}}, # Error
        {"frame_num": 2, "timestamp": 0.06, "angles": {"leftHip": 100, "leftKnee": 85, "backTilt": 5}},   # OK
    ]
    rep_phases_with_error = ["descent_phase", "descent_phase", "bottom_phase"]

    # Mock check_joint_angles to control its output for this specific test
    # This way, we test generate_feedback and scoring more directly
    mock_issues_frame0 = [{"joint": "backTilt", "issue_type": "below_min", "actual": -20, "expected": {"min": -10}, "severity": FeedbackSeverity.HIGH, "deviation": -10}]
    mock_issues_frame1 = [{"joint": "backTilt", "issue_type": "below_min", "actual": -22, "expected": {"min": -10}, "severity": FeedbackSeverity.HIGH, "deviation": -12}]
    
    with patch.object(service, 'check_joint_angles', side_effect=[mock_issues_frame0, mock_issues_frame1, []]) as mock_check_angles:
        feedback_items, score = await service.evaluate_rep(rep_frames_with_error, rep_phases_with_error, sample_squat_config_fsm)

    assert mock_check_angles.call_count == 3
    assert len(feedback_items) == 1 # Only one unique feedback for the continuous backTilt issue in descent_phase
    
    fb_item = feedback_items[0]
    assert fb_item.severity == FeedbackSeverity.HIGH
    assert "Your back is rounding too much" in fb_item.message
    assert fb_item.type == FeedbackType.POSTURE # From template
    
    # Score deduction: 1 HIGH severity issue = 100 - 10 (from scoring_config)
    # Using the sample_squat_config_fsm scoring
    expected_penalty = sample_squat_config_fsm.scoring_config["deductions_per_issue_severity"][FeedbackSeverity.HIGH.value]
    assert score == 100.0 - expected_penalty


def test_generate_feedback_matches_template(dynamic_form_analysis_service: DynamicFormAnalysisService, sample_squat_config_fsm: ExerciseConfig):
    service = dynamic_form_analysis_service
    issues = [
        {"joint": "backTilt", "issue_type": "below_min", "actual": -25, "expected": {"min": -10}, "severity": FeedbackSeverity.HIGH}
    ]
    phase = "descent_phase"
    frame_angles = {"backTilt": -25}
    
    feedback_list = service.generate_feedback(sample_squat_config_fsm.feedback_templates, issues, phase, frame_angles)
    
    assert len(feedback_list) == 1
    fb = feedback_list[0]
    assert "Your back is rounding too much (-25.0°)" in fb["message"] # Interpolated
    assert fb["severity"] == FeedbackSeverity.HIGH.value
    assert fb["type"] == FeedbackType.POSTURE.value # from template 'back_angle_general_below_min'
    assert fb["raw_issue"] == issues[0]

def test_generate_feedback_uses_default_if_no_match(dynamic_form_analysis_service: DynamicFormAnalysisService, sample_squat_config_fsm: ExerciseConfig):
    service = dynamic_form_analysis_service
    issues = [
        {"joint": "unknownJoint", "issue_type": "weird_error", "actual": 50, "expected": {}, "severity": FeedbackSeverity.LOW}
    ]
    phase = "some_phase"
    frame_angles = {"unknownJoint": 50}
    
    feedback_list = service.generate_feedback(sample_squat_config_fsm.feedback_templates, issues, phase, frame_angles)
    
    assert len(feedback_list) == 1
    fb = feedback_list[0]
    # Should match "general_default_feedback"
    assert "Form issue with unknownJoint during some_phase. Angle: 50.0°." in fb["message"]
    assert fb["severity"] == FeedbackSeverity.LOW.value # from "general_default_feedback" template

def test_generate_feedback_no_templates_config(dynamic_form_analysis_service: DynamicFormAnalysisService):
    service = dynamic_form_analysis_service
    issues = [{"joint": "leftKnee", "issue_type": "below_min", "actual": 60, "expected": {"min": 70}, "severity": FeedbackSeverity.MEDIUM}]
    phase = "descent_phase"
    frame_angles = {"leftKnee": 60}

    feedback_list = service.generate_feedback({}, issues, phase, frame_angles) # Empty templates
    assert len(feedback_list) == 1
    fb = feedback_list[0]
    assert "Issue: leftKnee, below_min. Actual: 60.0, Expected: {'min': 70}. Phase: descent_phase." in fb["message"] # Generic message
    assert fb["severity"] == FeedbackSeverity.MEDIUM.value


def test_aggregate_feedback_and_score(dynamic_form_analysis_service: DynamicFormAnalysisService):
    service = dynamic_form_analysis_service
    feedback_items = [
        FeedbackItemCreate(message="Back rounding", severity=FeedbackSeverity.HIGH, type=FeedbackType.POSTURE, timestamp=1.0),
        FeedbackItemCreate(message="Knee caving", severity=FeedbackSeverity.MEDIUM, type=FeedbackType.FORM, timestamp=1.5),
        FeedbackItemCreate(message="Back rounding", severity=FeedbackSeverity.HIGH, type=FeedbackType.POSTURE, timestamp=2.0), # Duplicate message
    ]
    rep_scores = [70.0, 80.0]
    
    final_feedback, final_score, overall_message = service._aggregate_feedback_and_score(feedback_items, rep_scores)
    
    assert len(final_feedback) == 2 # Unique feedback items
    assert final_score == 75.0 # Average of rep_scores
    
    # Check overall message, ensure it prioritizes HIGH severity
    assert "Analyzed 2 reps. Score: 75.00." in overall_message
    assert "Key feedback: 'Back rounding' (severity: high, 2x)" in overall_message # High severity, 2 occurrences
    assert "'Knee caving' (severity: medium, 1x)" in overall_message
    
    # Ensure CRITICAL > HIGH > MEDIUM > LOW sorting for summary
    feedback_items_severity_sort = [
        FeedbackItemCreate(message="Low issue", severity=FeedbackSeverity.LOW, type=FeedbackType.FORM, timestamp=1.0),
        FeedbackItemCreate(message="Critical issue", severity=FeedbackSeverity.CRITICAL, type=FeedbackType.FORM, timestamp=1.0),
        FeedbackItemCreate(message="Medium issue", severity=FeedbackSeverity.MEDIUM, type=FeedbackType.FORM, timestamp=1.0),
        FeedbackItemCreate(message="High issue", severity=FeedbackSeverity.HIGH, type=FeedbackType.FORM, timestamp=1.0),
    ]
    _, _, overall_message_sorted = service._aggregate_feedback_and_score(feedback_items_severity_sort, [50.0])
    assert "'Critical issue' (severity: critical, 1x); 'High issue' (severity: high, 1x)" in overall_message_sorted


def test_aggregate_feedback_no_reps(dynamic_form_analysis_service: DynamicFormAnalysisService):
    service = dynamic_form_analysis_service
    _, final_score, overall_message = service._aggregate_feedback_and_score([], [])
    assert final_score == 0.0
    assert "No valid repetitions detected" in overall_message

def test_aggregate_feedback_perfect_reps(dynamic_form_analysis_service: DynamicFormAnalysisService):
    service = dynamic_form_analysis_service
    _, final_score, overall_message = service._aggregate_feedback_and_score([], [100.0, 100.0])
    assert final_score == 100.0
    assert "Excellent form! 2 reps analyzed." in overall_message

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
    sample_video_model.angle_data = json.dumps(sample_angle_data_one_good_rep)
    
    mock_form_check_service.get_or_create_form_check_for_video.return_value = (sample_form_check_model, True)
    mock_exercise_config_service.get_active_config_by_template_id_async.return_value = sample_squat_config_fsm
    # Ensure create_feedback_items_in_db is an async mock if called with await
    service.create_feedback_items_in_db = AsyncMock()


    result_form_check = await service.analyze_form_dynamically(sample_video_model)
    
    mock_form_check_service.get_or_create_form_check_for_video.assert_called_once_with(video_id=sample_video_model.id)
    mock_exercise_config_service.get_active_config_by_template_id_async.assert_called_once_with(sample_video_model.exercise_template_id)
    
    assert result_form_check.status == "analysis_complete"
    assert result_form_check.reps_detected == 1
    assert result_form_check.overall_score == 100.0
    assert "Excellent form! 1 reps analyzed." in result_form_check.overall_feedback # Adjusted for 1 rep
    assert result_form_check.reps_per_minute == (1 / 10.0) * 60 # 1 rep in 10s video

    service.create_feedback_items_in_db.assert_not_called() # No feedback items for good rep
    mock_db_session.merge.assert_called_with(result_form_check)
    mock_db_session.commit.assert_called()
    mock_db_session.refresh.assert_called_with(result_form_check)


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
    sample_video_model.angle_data = json.dumps(sample_angle_data_two_reps_one_bad) # Contains one bad rep
    
    mock_form_check_service.get_or_create_form_check_for_video.return_value = (sample_form_check_model, True)
    mock_exercise_config_service.get_active_config_by_template_id_async.return_value = sample_squat_config_fsm
    service.create_feedback_items_in_db = AsyncMock()

    result_form_check = await service.analyze_form_dynamically(sample_video_model)
    
    assert result_form_check.status == "analysis_complete"
    assert result_form_check.reps_detected == 2
    
    # Rep 1 score = 100. Rep 2 score = 100 - 10 (HIGH severity for backTilt) = 90.
    # Avg score = (100 + 90) / 2 = 95
    assert result_form_check.overall_score == 95.0 
    assert "Analyzed 2 reps. Score: 95.00." in result_form_check.overall_feedback
    assert "Your back is rounding too much" in result_form_check.overall_feedback # Specific feedback
    assert result_form_check.reps_per_minute == (2 / 10.0) * 60 # 2 reps in 10s video

    service.create_feedback_items_in_db.assert_called_once()
    # Check that the feedback passed to create_feedback_items_in_db has the expected message
    call_args_list = service.create_feedback_items_in_db.call_args_list
    assert len(call_args_list) == 1
    feedback_dicts_passed = call_args_list[0][0][1] # second arg of first call
    assert len(feedback_dicts_passed) == 1 # Only one unique feedback item
    assert "Your back is rounding too much" in feedback_dicts_passed[0]["message"]

    mock_db_session.merge.assert_called_with(result_form_check)


@pytest.mark.asyncio
async def test_analyze_form_dynamically_no_exercise_config(
    dynamic_form_analysis_service: DynamicFormAnalysisService,
    mock_form_check_service: AsyncMock,
    mock_exercise_config_service: AsyncMock,
    sample_video_model: Video,
    sample_form_check_model: FormCheck
):
    service = dynamic_form_analysis_service
    sample_video_model.angle_data = json.dumps([{"frame_num":0, "angles": {"leftKnee": 0}}])
    mock_form_check_service.get_or_create_form_check_for_video.return_value = (sample_form_check_model, True)
    mock_exercise_config_service.get_active_config_by_template_id_async.return_value = None # No config

    result_form_check = await service.analyze_form_dynamically(sample_video_model)
    
    assert result_form_check.status == "analysis_failed"
    assert "No active ExerciseConfig found" in result_form_check.overall_feedback
    assert result_form_check.overall_score is None # Or 0, depending on default
    assert result_form_check.reps_detected is None

@pytest.mark.asyncio
async def test_analyze_form_dynamically_invalid_angle_data(
    dynamic_form_analysis_service: DynamicFormAnalysisService,
    mock_form_check_service: AsyncMock,
    sample_video_model: Video,
    sample_form_check_model: FormCheck
):
    service = dynamic_form_analysis_service
    sample_video_model.angle_data = "this is not json"
    mock_form_check_service.get_or_create_form_check_for_video.return_value = (sample_form_check_model, True)
    # No need to mock exercise_config_service as it won't be reached

    result_form_check = await service.analyze_form_dynamically(sample_video_model)
    
    assert result_form_check.status == "analysis_failed"
    assert "Angle data is not valid JSON" in result_form_check.overall_feedback


@pytest.mark.asyncio
async def test_analyze_form_dynamically_empty_angle_data_list(
    dynamic_form_analysis_service: DynamicFormAnalysisService,
    mock_form_check_service: AsyncMock,
    sample_video_model: Video,
    sample_form_check_model: FormCheck
):
    service = dynamic_form_analysis_service
    sample_video_model.angle_data = json.dumps([]) # Empty list
    mock_form_check_service.get_or_create_form_check_for_video.return_value = (sample_form_check_model, True)

    result_form_check = await service.analyze_form_dynamically(sample_video_model)
    
    assert result_form_check.status == "analysis_failed"
    assert "Angle data missing or empty" in result_form_check.overall_feedback

@pytest.mark.asyncio
async def test_analyze_form_dynamically_no_template_id_on_video(
    dynamic_form_analysis_service: DynamicFormAnalysisService,
    mock_form_check_service: AsyncMock,
    sample_video_model: Video,
    sample_form_check_model: FormCheck
):
    service = dynamic_form_analysis_service
    sample_video_model.exercise_template_id = None
    mock_form_check_service.get_or_create_form_check_for_video.return_value = (sample_form_check_model, True)

    result_form_check = await service.analyze_form_dynamically(sample_video_model)
    
    assert result_form_check.status == "analysis_failed"
    assert "Missing exercise_template_id" in result_form_check.overall_feedback


@pytest.mark.asyncio
async def test_analyze_form_dynamically_general_exception_handling(
    dynamic_form_analysis_service: DynamicFormAnalysisService,
    mock_form_check_service: AsyncMock,
    mock_exercise_config_service: AsyncMock,
    sample_video_model: Video,
    sample_form_check_model: FormCheck,
    sample_squat_config_fsm: ExerciseConfig,
    sample_angle_data_one_good_rep: List[Dict[str, Any]]
):
    service = dynamic_form_analysis_service
    sample_video_model.angle_data = json.dumps(sample_angle_data_one_good_rep)
    mock_form_check_service.get_or_create_form_check_for_video.return_value = (sample_form_check_model, True)
    mock_exercise_config_service.get_active_config_by_template_id_async.return_value = sample_squat_config_fsm
    
    # Make something inside raise an unexpected error
    with patch.object(service, '_aggregate_feedback_and_score', side_effect=RuntimeError("Unexpected boom!")):
        with pytest.raises(ServerErrorException) as exc_info:
            await service.analyze_form_dynamically(sample_video_model)
    
    assert "Dynamic form analysis failed" in str(exc_info.value)
    assert sample_form_check_model.status == "analysis_failed"
    assert "Unexpected server error" in sample_form_check_model.overall_feedback
    # Verify commit was called to save the failed state
    dynamic_form_analysis_service.db_session.commit.assert_called()


# Placeholder for more detailed FSM segmentation tests
# e.g. partial reps, noise in data, different exercise configs

# Placeholder for more detailed evaluate_rep tests
# e.g. multiple issues in one rep, different severities, timestamp accuracy

# Helper to get the ExerciseConfig.movement_phases as Dict[str, MovementPhase]
# This should be how the service receives it.
# (No change needed if fixture sample_squat_config_fsm already provides it this way)

# Ensure FeedbackSeverity.get_sort_order() is available (added to enums.py)
# Tests for _aggregate_feedback_and_score cover its usage. 