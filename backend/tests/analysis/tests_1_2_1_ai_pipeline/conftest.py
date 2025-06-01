import pytest
import json
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from typing import List, Dict, Any
import math
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.dynamic_form_analysis_service import DynamicFormAnalysisService
from app.services.exercise_config_service import ExerciseConfigService
from app.services.form_check_service import FormCheckService
from app.models.exercise_config import (
    ExerciseConfig,
    MovementPhaseDefinition,
    # JointSpecificAngleRule, # Not directly used in fixtures, but part of the model
    FeedbackTemplateDefinition,
    Condition,
    MovementPhaseTrigger,
    # ROMRule, # Not directly used in fixtures, but part of the model
    # PostureRule, # Not directly used in fixtures, but part of the model
    # SymmetryRule, # Not directly used in fixtures, but part of the model
)
from app.models.video import Video
from app.models.form_check import FormCheck # FeedbackItem removed as not directly used by fixtures
from app.models.enums import (
    FeedbackSeverity as ModelFeedbackSeverity,
    FeedbackType as ModelFeedbackType,
    VideoStatus,
    FormCheckStatus,
)
from app.schemas.exercise_config import (
    JointAngleRules as PydanticJointAngleRules,
    PhaseJointRules as PydanticPhaseJointRules,
    JointAngleRule as PydanticJointAngleRuleSchema,
    FeedbackTemplate as PydanticFeedbackTemplateSchema,
    ClassificationMetadata as PydanticClassificationMetadata
)
from app.core.config import Settings


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
        filename="test_video.mp4",
        mime_type="video/mp4",
        object_key="test_video.mp4",
        status=VideoStatus.PROCESSED,
        angle_data=sample_angle_data_two_reps,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    return video

@pytest.fixture
def sample_video_with_no_template_id(sample_angle_data_two_reps: List[Dict[str, Any]]) -> Video:
    return Video(
        id=uuid4(),
        user_id=uuid4(),
        filename="test_video_no_template.mp4",
        mime_type="video/mp4",
        object_key="test_video_no_template.mp4",
        status=VideoStatus.PROCESSED,
        angle_data=sample_angle_data_two_reps,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

@pytest.fixture
def sample_squat_config() -> ExerciseConfig:
    config = ExerciseConfig(
        id=uuid4(),
        name="Test Squat Config",
        exercise_id=uuid4(),
        version=1,
        is_active=True,
        joint_angle_rules=PydanticJointAngleRules(
            phases={
                "start_phase": PydanticPhaseJointRules(angles={
                    "leftKnee": PydanticJointAngleRuleSchema(min_angle=160, max_angle=180, ideal_angle=170, tolerance=10),
                    "leftHip": PydanticJointAngleRuleSchema(min_angle=160, max_angle=180, ideal_angle=170, tolerance=10),
                }),
                "descent_phase": PydanticPhaseJointRules(angles={
                    "leftKnee": PydanticJointAngleRuleSchema(min_angle=80, max_angle=100, ideal_angle=90, tolerance=5),
                    "leftHip": PydanticJointAngleRuleSchema(min_angle=80, max_angle=100, ideal_angle=90, tolerance=5),
                }),
                "ascent_phase": PydanticPhaseJointRules(angles={
                    "leftKnee": PydanticJointAngleRuleSchema(min_angle=160, max_angle=180, ideal_angle=170, tolerance=10),
                    "leftHip": PydanticJointAngleRuleSchema(min_angle=160, max_angle=180, ideal_angle=170, tolerance=10),
                }),
                "unknown": PydanticPhaseJointRules(angles={
                    "leftKnee": PydanticJointAngleRuleSchema(min_angle=0, max_angle=180, ideal_angle=90, tolerance=30),
                    "leftHip": PydanticJointAngleRuleSchema(min_angle=0, max_angle=180, ideal_angle=90, tolerance=30),
                })
            },
            joints=["leftKnee", "rightKnee", "leftHip", "rightHip"]
        ),
        movement_phases=dict(
            start_phase=MovementPhaseDefinition(
                description="Standing upright",
                triggers={
                    "next": MovementPhaseTrigger(
                        target_phase="descent_phase",
                        conditions=[Condition(joint="leftKnee", condition="angle", value=150, comparator="<")]
                    )
                }
            ),
            descent_phase=MovementPhaseDefinition(
                description="Lowering body",
                triggers={
                    "next": MovementPhaseTrigger(
                        target_phase="ascent_phase",
                        conditions=[Condition(joint="leftKnee", condition="angle", value=95, comparator="<")]
                    ),
                    "previous": MovementPhaseTrigger(
                        target_phase="start_phase",
                        conditions=[Condition(joint="leftKnee", condition="angle", value=160, comparator=">")]
                    )
                }
            ),
            ascent_phase=MovementPhaseDefinition(
                description="Returning to standing",
                triggers={
                    "next": MovementPhaseTrigger(
                        target_phase="start_phase",
                        conditions=[Condition(joint="leftKnee", condition="angle", value=165, comparator=">")]
                    ),
                    "previous": MovementPhaseTrigger(
                        target_phase="descent_phase",
                        conditions=[Condition(joint="leftKnee", condition="angle", value=100, comparator=">")]
                    )
                }
            )
        ),
        feedback_templates=dict(
            knee_too_bent_start=PydanticFeedbackTemplateSchema(message="Knees too bent at start: {joint} at {actual:.1f}", severity="low", type="form"),
            knee_not_bent_enough_descent=PydanticFeedbackTemplateSchema(message="Squat deeper: {joint} at {actual:.1f}, expected < 100", severity="medium", type="range"),
            hip_too_upright_descent=PydanticFeedbackTemplateSchema(message="Hips not back enough in descent: {joint} at {actual:.1f}", severity="medium", type="form"),
            general_issue=PydanticFeedbackTemplateSchema(message="General issue with {joint}", severity="low", type="form")
        ),
        classification_metadata=PydanticClassificationMetadata(
            keypoints=["leftKnee", "leftHip"], frame_count=30, features={}
        )
    )
    return config

@pytest.fixture
def sample_angle_data_one_rep() -> List[Dict[str, Any]]:
    """Provides angle data for a single, typical squat repetition."""
    return [
        {"frame_num": 0, "angles": {"leftKnee": 175.0, "leftHip": 175.0}},
        {"frame_num": 1, "angles": {"leftKnee": 140.0, "leftHip": 140.0}},
        {"frame_num": 2, "angles": {"leftKnee": 90.0,  "leftHip": 90.0}},
        {"frame_num": 3, "angles": {"leftKnee": 140.0, "leftHip": 140.0}},
        {"frame_num": 4, "angles": {"leftKnee": 175.0, "leftHip": 175.0}},
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
        {"frame_num": 0, "angles": {"leftKnee": 175.0, "leftHip": 175.0}},
        {"frame_num": 1, "angles": {"leftKnee": 140.0, "leftHip": 140.0}},
        {"frame_num": 2, "angles": {"leftKnee": 110.0, "leftHip": 110.0}},
        {"frame_num": 3, "angles": {"leftKnee": 140.0, "leftHip": 140.0}},
        {"frame_num": 4, "angles": {"leftKnee": 175.0, "leftHip": 175.0}},
    ]

@pytest.fixture
def sample_video_model():
    return Video(
        id=uuid4(),
        user_id=uuid4(),
        filename="test_video_model.mp4",
        mime_type="video/mp4",
        angle_data=json.dumps([]),
        object_key="processed/video.mp4",
        processed_object_key="processed/video.mp4",
        status=VideoStatus.ANGLES_CALCULATED,
        duration_seconds=10.0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

@pytest.fixture
def sample_form_check_model(sample_video_model: Video):
    return FormCheck(
        id=uuid4(),
        video_id=sample_video_model.id,
        user_id=uuid4(),
        exercise_id=uuid4(),
        video_url="http://fakeurl.com/fake.mp4",
        status=FormCheckStatus.PENDING,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

@pytest.fixture
def sample_squat_config_fsm() -> ExerciseConfig:
    joint_angle_rules_data = {
        "phases": {
            "start_phase": {
                "angles": {
                    "leftKnee": {"min_angle": 160, "max_angle": 180, "ideal_angle": 170, "tolerance": 10, "feedback_template_key": "knee_start_angle"},
                    "rightKnee": {"min_angle": 160, "max_angle": 180, "ideal_angle": 170, "tolerance": 10, "feedback_template_key": "knee_start_angle"},
                    "leftHip": {"min_angle": 160, "max_angle": 180, "ideal_angle": 170, "tolerance": 10, "feedback_template_key": "hip_start_angle"},
                    "rightHip": {"min_angle": 160, "max_angle": 180, "ideal_angle": 170, "tolerance": 10, "feedback_template_key": "hip_start_angle"}
                }
            },
            "descent_phase": {
                "angles": {
                    "leftKnee": {"min_angle": 70, "max_angle": 170, "ideal_angle": 90, "tolerance": 10, "feedback_template_key": "knee_descent_angle"},
                    "rightKnee": {"min_angle": 70, "max_angle": 170, "ideal_angle": 90, "tolerance": 10, "feedback_template_key": "knee_descent_angle"},
                }
            },
            "bottom_phase": {
                "angles": {
                    "leftKnee": {"min_angle": 60, "max_angle": 90, "ideal_angle": 75, "tolerance": 10, "feedback_template_key": "knee_bottom_angle"},
                    "rightKnee": {"min_angle": 60, "max_angle": 90, "ideal_angle": 75, "tolerance": 10, "feedback_template_key": "knee_bottom_angle"},
                }
            },
            "ascent_phase": {
                "angles": {
                    "leftKnee": {"min_angle": 70, "max_angle": 180, "ideal_angle": 170, "tolerance": 10, "feedback_template_key": "knee_ascent_angle"},
                    "rightKnee": {"min_angle": 70, "max_angle": 180, "ideal_angle": 170, "tolerance": 10, "feedback_template_key": "knee_ascent_angle"},
                }
            },
            "default": {
                "angles": {
                    "default": {"min_angle": 0, "max_angle": 180, "tolerance": 20}
                }
            }
        },
        "joints": ["leftKnee", "rightKnee", "leftHip", "rightHip"]
    }

    return ExerciseConfig(
        id=uuid4(),
        exercise_id=uuid4(),
        name="Squat FSM Config",
        version=1,
        is_active=True,
        movement_phases={
            "start_phase": MovementPhaseDefinition(
                name="Start Phase",
                description="Standing, preparing for squat.",
                triggers={
                    "next": MovementPhaseTrigger(target_phase="descent_phase", conditions=[
                        Condition(joint="leftHip", comparator="<", value=160, condition="angle")
                    ])
                }
            ),
            "descent_phase": MovementPhaseDefinition(
                name="Descent Phase",
                description="Lowering into the squat.",
                triggers={
                     "next": MovementPhaseTrigger(target_phase="bottom_phase", conditions=[
                         Condition(joint="leftKnee", comparator="<", value=90, condition="angle")
                     ])
                }
            ),
            "bottom_phase": MovementPhaseDefinition(
                name="Bottom Phase",
                description="Lowest point of the squat.",
                triggers={
                    "next": MovementPhaseTrigger(target_phase="ascent_phase", conditions=[
                        Condition(joint="leftKnee", comparator=">", value=95, condition="angle")
                    ])
                }
            ),
            "ascent_phase": MovementPhaseDefinition(
                name="Ascent Phase",
                description="Rising from the squat.",
                triggers={
                    "next": MovementPhaseTrigger(target_phase="start_phase", conditions=[
                        Condition(joint="leftHip", comparator=">", value=170, condition="angle")
                    ])
                }
            )
        },
        joint_angle_rules=joint_angle_rules_data,
        feedback_templates={
            "knee_descent_angle": FeedbackTemplateDefinition(message="Knee angle in descent: {actual:.1f} vs ideal {ideal:.1f}", severity="medium", type="form"),
            "knee_bottom_angle": FeedbackTemplateDefinition(message="Knee angle at bottom: {actual:.1f} vs ideal {ideal:.1f}", severity="high", type="form"),
            "knee_start_angle": FeedbackTemplateDefinition(message="Ensure full extension at the start/end.", severity="low", type="form"),
            "hip_start_angle": FeedbackTemplateDefinition(message="Ensure full hip extension at the start/end.", severity="low", type="form"),
            "knee_ascent_angle": FeedbackTemplateDefinition(message="Knee angle in ascent: {actual:.1f} vs ideal {ideal:.1f}", severity="medium", type="form"),
            "back_angle_general_below_min": FeedbackTemplateDefinition(
                message="Your back is rounding too much ({actual:.1f}°). Keep it straighter.",
                severity=ModelFeedbackSeverity.HIGH.value, type=ModelFeedbackType.POSTURE.value
            ),
            "torso_lean_too_much": FeedbackTemplateDefinition(
                message="Torso lean is excessive ({actual:.1f}°). Try to keep more upright.",
                severity=ModelFeedbackSeverity.HIGH.value, type=ModelFeedbackType.POSTURE.value
            ),
            "general_default_feedback": FeedbackTemplateDefinition(
                message="Form issue with {joint} during {phase}. Angle: {actual:.1f}°.",
                severity=ModelFeedbackSeverity.LOW.value, type=ModelFeedbackType.FORM.value
            )
        },
        rom_rules=[
            {
                "rule_name": "Knee ROM Check",
                "joint_name": "leftKnee",
                "min_angle_overall": 70,
                "max_angle_overall": 175,
                "target_rom": 100,
                "tolerance_degrees": 15,
                "severity": ModelFeedbackSeverity.MEDIUM.value
            }
        ],
        posture_rules=[
            {
                "rule_name": "Torso Upright (Vertical Check)",
                "applicable_phases": ["start_phase", "bottom_phase"],
                "conditions": [
                    {
                        "condition_type": "vector_angle_from_vertical",
                        "keypoints_for_vector": ["leftShoulder", "leftHip"],
                        "expected_angle_degrees": 0,
                        "max_deviation_degrees": 20,
                        "feedback_template_key": "torso_lean_too_much"
                    }
                ],
                "severity": ModelFeedbackSeverity.MEDIUM.value
            }
        ],
        symmetry_rules=[
            {
                "rule_name": "Knee Angle Symmetry",
                "joint_pair": ["leftKnee", "rightKnee"],
                "max_difference_degrees": 15,
                "applicable_phases": ["descent_phase", "bottom_phase", "ascent_phase"],
                "severity": ModelFeedbackSeverity.MEDIUM.value
            }
        ],
        classification_metadata={
            "keypoints": ["leftKnee", "leftHip", "rightKnee", "rightHip"],
            "frame_count": 60,
            "features": {}
        }
    )

@pytest.fixture
def sample_angle_data_one_good_rep() -> List[Dict[str, Any]]:
    return [
        {"frame_num": 0, "timestamp": 0.0, "angles": {"leftHip": 175, "leftKnee": 170, "rightKnee": 170, "backTilt": 0}, "raw_landmarks": [{"name": "leftShoulder", "x": 0.5, "y": 0.2}, {"name": "leftHip", "x": 0.5, "y": 0.5}]},
        {"frame_num": 1, "timestamp": 0.03, "angles": {"leftHip": 170, "leftKnee": 165, "rightKnee": 165, "backTilt": 1}, "raw_landmarks": [{"name": "leftShoulder", "x": 0.5, "y": 0.2}, {"name": "leftHip", "x": 0.5, "y": 0.5}]},
        {"frame_num": 2, "timestamp": 0.06, "angles": {"leftHip": 150, "leftKnee": 140, "rightKnee": 140, "backTilt": 2}, "raw_landmarks": [{"name": "leftShoulder", "x": 0.5, "y": 0.22}, {"name": "leftHip", "x": 0.5, "y": 0.5}]},
        {"frame_num": 3, "timestamp": 0.09, "angles": {"leftHip": 120, "leftKnee": 110, "rightKnee": 110, "backTilt": 3}, "raw_landmarks": [{"name": "leftShoulder", "x": 0.5, "y": 0.25}, {"name": "leftHip", "x": 0.5, "y": 0.5}]},
        {"frame_num": 4, "timestamp": 0.12, "angles": {"leftHip": 100, "leftKnee": 85, "rightKnee": 85, "backTilt": 2}, "raw_landmarks": [{"name": "leftShoulder", "x": 0.5, "y": 0.3}, {"name": "leftHip", "x": 0.5, "y": 0.5}]},
        {"frame_num": 5, "timestamp": 0.15, "angles": {"leftHip": 95, "leftKnee": 80, "rightKnee": 80, "backTilt": 1}, "raw_landmarks": [{"name": "leftShoulder", "x": 0.5, "y": 0.3}, {"name": "leftHip", "x": 0.5, "y": 0.5}]},
        {"frame_num": 6, "timestamp": 0.18, "angles": {"leftHip": 98, "leftKnee": 96, "rightKnee": 96, "backTilt": 0}, "raw_landmarks": [{"name": "leftShoulder", "x": 0.5, "y": 0.28}, {"name": "leftHip", "x": 0.5, "y": 0.5}]},
        {"frame_num": 7, "timestamp": 0.21, "angles": {"leftHip": 110, "leftKnee": 120, "rightKnee": 120, "backTilt": -1}, "raw_landmarks": [{"name": "leftShoulder", "x": 0.5, "y": 0.25}, {"name": "leftHip", "x": 0.5, "y": 0.5}]},
        {"frame_num": 8, "timestamp": 0.24, "angles": {"leftHip": 140, "leftKnee": 150, "rightKnee": 150, "backTilt": 0}, "raw_landmarks": [{"name": "leftShoulder", "x": 0.5, "y": 0.22}, {"name": "leftHip", "x": 0.5, "y": 0.5}]},
        {"frame_num": 9, "timestamp": 0.27, "angles": {"leftHip": 175, "leftKnee": 170, "rightKnee": 170, "backTilt": 1}, "raw_landmarks": [{"name": "leftShoulder", "x": 0.5, "y": 0.2}, {"name": "leftHip", "x": 0.5, "y": 0.5}]},
        {"frame_num": 10, "timestamp": 0.30, "angles": {"leftHip": 178, "leftKnee": 175, "rightKnee": 175, "backTilt": 0}, "raw_landmarks": [{"name": "leftShoulder", "x": 0.5, "y": 0.2}, {"name": "leftHip", "x": 0.5, "y": 0.5}]},
    ]

@pytest.fixture
def sample_angle_data_two_reps_one_bad() -> List[Dict[str, Any]]:
    def create_landmarks(left_shoulder_y=0.2, left_hip_y=0.5, left_shoulder_x=0.5, left_hip_x=0.5):
        return [
            {"name": "nose", "x": 0, "y": 0}, {"name": "left_eye_inner", "x": 0, "y": 0},
            {"name": "leftShoulder", "x": left_shoulder_x, "y": left_shoulder_y},
            {"name": "leftHip", "x": left_hip_x, "y": left_hip_y},
        ]
    return [
        {"frame_num": 0, "timestamp": 0.0,  "angles": {"leftHip": 175, "leftKnee": 170, "rightKnee": 165, "backTilt": 0},   "raw_landmarks": create_landmarks(left_shoulder_y=0.2, left_hip_y=0.5)},
        {"frame_num": 1, "timestamp": 0.03, "angles": {"leftHip": 150, "leftKnee": 140, "rightKnee": 120, "backTilt": 2},   "raw_landmarks": create_landmarks(left_shoulder_y=0.22, left_hip_y=0.5)},
        {"frame_num": 2, "timestamp": 0.06, "angles": {"leftHip": 100, "leftKnee": 85,  "rightKnee": 70,  "backTilt": 2},   "raw_landmarks": create_landmarks(left_shoulder_y=0.3, left_hip_y=0.5)},
        {"frame_num": 3, "timestamp": 0.09, "angles": {"leftHip": 130, "leftKnee": 130, "rightKnee": 110, "backTilt": 0},   "raw_landmarks": create_landmarks(left_shoulder_y=0.25, left_hip_y=0.5)},
        {"frame_num": 4, "timestamp": 0.12, "angles": {"leftHip": 175, "leftKnee": 170, "rightKnee": 165, "backTilt": 1},   "raw_landmarks": create_landmarks(left_shoulder_y=0.2, left_hip_y=0.5)},
        {"frame_num": 5, "timestamp": 0.15, "angles": {"leftHip": 176, "leftKnee": 172, "rightKnee": 140, "backTilt": 0},   "raw_landmarks": create_landmarks(left_shoulder_y=0.2, left_hip_y=0.5)},
        {"frame_num": 6, "timestamp": 0.18, "angles": {"leftHip": 175, "leftKnee": 170, "rightKnee": 100, "backTilt": 0},   "raw_landmarks": create_landmarks(left_shoulder_y=0.2, left_hip_y=0.5)},
        {"frame_num": 7, "timestamp": 0.21, "angles": {"leftHip": 150, "leftKnee": 140, "rightKnee": 60, "backTilt": -20}, "raw_landmarks": create_landmarks(left_shoulder_y=0.4, left_hip_y=0.5, left_shoulder_x=0.4)},
        {"frame_num": 8, "timestamp": 0.24, "angles": {"leftHip": 100, "leftKnee": 85,  "rightKnee": 65,  "backTilt": -22}, "raw_landmarks": create_landmarks(left_shoulder_y=0.45, left_hip_y=0.5, left_shoulder_x=0.35)},
        {"frame_num": 9, "timestamp": 0.27, "angles": {"leftHip": 130, "leftKnee": 130, "rightKnee": 140, "backTilt": -18}, "raw_landmarks": create_landmarks(left_shoulder_y=0.4, left_hip_y=0.5, left_shoulder_x=0.4)},
        {"frame_num": 10, "timestamp": 0.30, "angles": {"leftHip": 175, "leftKnee": 170, "rightKnee": 170, "backTilt": 0},  "raw_landmarks": create_landmarks(left_shoulder_y=0.2, left_hip_y=0.5)},
        {"frame_num": 11, "timestamp": 0.33, "angles": {"leftHip": 178, "leftKnee": 175, "rightKnee": 175, "backTilt": 0}, "raw_landmarks": create_landmarks(left_shoulder_y=0.2, left_hip_y=0.5)}
    ]

@pytest.fixture
def sample_angle_data_knee_rom_violation_shallow() -> List[Dict[str, Any]]:
    def create_landmarks(y_offset=0.0):
        return [{"name": "leftShoulder", "x": 0.5, "y": 0.2 + y_offset}, {"name": "leftHip", "x": 0.5, "y": 0.5 + y_offset}]
    return [
        {"frame_num": 0, "timestamp": 0.0,  "angles": {"leftHip": 175, "leftKnee": 170, "rightKnee": 170, "backTilt": 0}, "raw_landmarks": create_landmarks()},
        {"frame_num": 1, "timestamp": 0.03, "angles": {"leftHip": 160, "leftKnee": 150, "rightKnee": 150, "backTilt": 1}, "raw_landmarks": create_landmarks()},
        {"frame_num": 2, "timestamp": 0.06, "angles": {"leftHip": 130, "leftKnee": 120, "rightKnee": 120, "backTilt": 2}, "raw_landmarks": create_landmarks(0.02)},
        {"frame_num": 3, "timestamp": 0.09, "angles": {"leftHip": 120, "leftKnee": 100, "rightKnee": 100, "backTilt": 2}, "raw_landmarks": create_landmarks(0.05)},
        {"frame_num": 4, "timestamp": 0.12, "angles": {"leftHip": 130, "leftKnee": 120, "rightKnee": 120, "backTilt": 1}, "raw_landmarks": create_landmarks(0.02)},
        {"frame_num": 5, "timestamp": 0.15, "angles": {"leftHip": 160, "leftKnee": 150, "rightKnee": 150, "backTilt": 0}, "raw_landmarks": create_landmarks(0.01)},
        {"frame_num": 6, "timestamp": 0.18, "angles": {"leftHip": 175, "leftKnee": 170, "rightKnee": 170, "backTilt": 0}, "raw_landmarks": create_landmarks()},
    ]

@pytest.fixture
def sample_angle_data_knee_rom_violation_incomplete_extension() -> List[Dict[str, Any]]:
    def create_landmarks(y_offset=0.0):
        return [{"name": "leftShoulder", "x": 0.5, "y": 0.2 + y_offset}, {"name": "leftHip", "x": 0.5, "y": 0.5 + y_offset}]
    return [
        {"frame_num": 0, "timestamp": 0.0,  "angles": {"leftHip": 150, "leftKnee": 145, "rightKnee": 145, "backTilt": 0}, "raw_landmarks": create_landmarks()},
        {"frame_num": 1, "timestamp": 0.03, "angles": {"leftHip": 130, "leftKnee": 120, "rightKnee": 120, "backTilt": 1}, "raw_landmarks": create_landmarks()},
        {"frame_num": 2, "timestamp": 0.06, "angles": {"leftHip": 100, "leftKnee": 80,  "rightKnee": 80,  "backTilt": 2}, "raw_landmarks": create_landmarks(0.02)},
        {"frame_num": 3, "timestamp": 0.09, "angles": {"leftHip": 130, "leftKnee": 120, "rightKnee": 120, "backTilt": 1}, "raw_landmarks": create_landmarks()},
        {"frame_num": 4, "timestamp": 0.12, "angles": {"leftHip": 150, "leftKnee": 145, "rightKnee": 145, "backTilt": 0}, "raw_landmarks": create_landmarks()},
    ] 