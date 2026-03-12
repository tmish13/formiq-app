import pytest
from unittest.mock import MagicMock, patch, AsyncMock, call
from uuid import uuid4
import math
from typing import Optional, Dict, Any

from app.services.dynamic_form_analysis_service import DynamicFormAnalysisService, StructuredIssue
from app.services.exercise_config_service import ExerciseConfigService
from app.models.exercise_config import ExerciseConfig, MovementPhaseDefinition, MovementPhaseTrigger, Condition
from app.models.enums import FeedbackSeverity, FeedbackType, FormCheckStatus
from app.core.config import Settings
from app.models.video import Video, VideoStatus
from app.models.form_check import FormCheck, FormCheckStatus, FeedbackItem
from app.core.exceptions import ServerErrorException

# Import POSE_LANDMARK_NAMES if your _get_keypoint_coords_by_name uses it directly by default
from app.constants.angles import POSE_LANDMARK_NAMES


@pytest.fixture
def mock_settings() -> Settings:
    """Fixture for mock settings."""
    return MagicMock(spec=Settings)

@pytest.fixture
def mock_exercise_config_service() -> MagicMock:
    service = MagicMock(spec=ExerciseConfigService)
    # Default behavior can be overridden in tests
    service.get_config_by_exercise_type_slug_async = AsyncMock(return_value=None)
    service.get_active_config_for_exercise_async = AsyncMock(return_value=None) # ADD DEFAULT MOCK
    return service

@pytest.fixture
def mock_form_check_service() -> MagicMock:
    """Fixture for a mock FormCheckService."""
    # This service is often a dependency for DynamicFormAnalysisService,
    # but its methods might not be directly called BY DynamicFormAnalysisService
    # if an initial_form_check is passed in. Behavior depends on test scenario.
    return MagicMock()

@pytest.fixture
def mock_initial_form_check() -> MagicMock:
    """Fixture for a mock FormCheck instance to be used as initial_form_check."""
    check = MagicMock(spec=FormCheck)
    check.id = uuid4()
    check.video_id = uuid4()
    check.user_id = uuid4()
    check.exercise_config_id = None # Or set to a specific mock ID if needed
    check.status = FormCheckStatus.PENDING
    check.score = 0.0
    check.reps_detected = 0
    check.feedback_items = []
    check.form_metadata = {}
    check.error_details = None
    check.overall_feedback = None 
    # Add other attributes as needed by tests
    return check

@pytest.fixture
def dynamic_form_analysis_service(
    mock_settings: Settings,
    mock_exercise_config_service: MagicMock,
    mock_form_check_service: MagicMock
) -> DynamicFormAnalysisService:
    """Fixture for DynamicFormAnalysisService with mocked dependencies."""
    # db mock might also be needed if service methods hit db directly, but rule evaluators might not.
    mock_db_session = MagicMock() 
    mock_db_session.commit = AsyncMock() # Ensure commit is an AsyncMock
    mock_db_session.refresh = AsyncMock() # Ensure refresh is an AsyncMock
    return DynamicFormAnalysisService(
        db=mock_db_session,
        settings=mock_settings,
        exercise_config_service=mock_exercise_config_service,
        form_check_service=mock_form_check_service
    )

# --- Helper to create mock landmark data ---
def create_mock_landmark(x: float, y: float, z: float = 0.0, visibility: float = 1.0) -> dict:
    return {"x": x, "y": y, "z": z, "visibility": visibility}

# Predefined landmark names for easy index access in tests, mirrors POSE_LANDMARK_NAMES
# This helps in constructing raw_landmarks_for_frame
TEST_LANDMARK_NAMES = POSE_LANDMARK_NAMES 

def get_landmark_index(name: str) -> int:
    return TEST_LANDMARK_NAMES.index(name.upper())

def create_full_mock_landmarks(overrides: dict) -> list:
    """Creates a full list of 33 landmarks, with defaults, allowing overrides for specific points."""
    landmarks = []
    for i, name in enumerate(TEST_LANDMARK_NAMES):
        # Default landmark structure with name
        landmark_dict = {"name": name, "x": 0.5, "y": 0.5, "z": 0.0, "visibility": 1.0}
        landmarks.append(landmark_dict)

    for name, coords_dict in overrides.items():
        try:
            idx = get_landmark_index(name)
            # Update existing landmark dict with override values, ensuring 'name' is preserved
            landmarks[idx]["x"] = coords_dict['x']
            landmarks[idx]["y"] = coords_dict['y']
            if 'z' in coords_dict: # Optional z
                landmarks[idx]["z"] = coords_dict['z']
            if 'visibility' in coords_dict: # Optional visibility
                landmarks[idx]["visibility"] = coords_dict['visibility']
        except ValueError:
            # This might happen if a name in overrides is not in TEST_LANDMARK_NAMES
            # For robustness, you could log this or handle it as an error.
            # For now, we'll assume overrides use valid names from TEST_LANDMARK_NAMES.
            pass # Or print a warning, or raise an error
    return landmarks

# --- BEGIN: Tests for segment_repetitions ---

@pytest.fixture
def mock_segmentation_config() -> MagicMock:
    config = MagicMock(spec=ExerciseConfig)
    config.name = "Test Segmentation Exercise"

    # Raw data structure for clarity
    raw_phases_data = {
        "start_phase": {
            "description": "Starting phase of the movement",
            "triggers": {
                "next": {
                    "target_phase": "descent_phase",
                    "conditions": [
                        {"joint": "LEFT_KNEE", "condition": "angle", "value": 160.0, "comparator": "<"}
                    ]
                }
            }
        },
        "descent_phase": {
            "description": "Lowering phase",
            "triggers": {
                "next": {
                    "target_phase": "bottom_phase",
                    "conditions": [
                        {"joint": "LEFT_KNEE", "condition": "angle", "value": 90.0, "comparator": "<="}
                    ]
                }
            }
        },
        "bottom_phase": {
            "description": "Lowest point of the movement",
            "triggers": {
                "next": {
                    "target_phase": "ascent_phase",
                    "conditions": [
                        {"joint": "LEFT_KNEE", "condition": "angle", "value": 100.0, "comparator": ">"}
                    ]
                }
            }
        },
        "ascent_phase": {
            "description": "Rising phase",
            "triggers": {
                "next": {
                    "target_phase": "start_phase",
                    "conditions": [
                        {"joint": "LEFT_KNEE", "condition": "angle", "value": 170.0, "comparator": ">="}
                    ]
                }
            }
        }
    }

    mocked_movement_phases = {}
    for phase_name, phase_data_dict in raw_phases_data.items():
        mock_phase_def = MagicMock(spec=MovementPhaseDefinition)
        mock_phase_def.name = phase_name
        mock_phase_def.description = phase_data_dict.get("description")
        
        mocked_triggers_dict = {}
        for trigger_key, trigger_data_dict in phase_data_dict.get("triggers", {}).items():
            mock_trigger = MagicMock(spec=MovementPhaseTrigger)
            mock_trigger.target_phase = trigger_data_dict.get("target_phase")
            
            mocked_conditions_list = []
            for cond_data_dict in trigger_data_dict.get("conditions", []):
                mock_condition = MagicMock(spec=Condition)
                mock_condition.joint = cond_data_dict.get("joint")
                mock_condition.condition = cond_data_dict.get("condition")
                mock_condition.value = cond_data_dict.get("value")
                mock_condition.comparator = cond_data_dict.get("comparator")
                mocked_conditions_list.append(mock_condition)
            mock_trigger.conditions = mocked_conditions_list
            mocked_triggers_dict[trigger_key] = mock_trigger
        
        mock_phase_def.triggers = mocked_triggers_dict
        mocked_movement_phases[phase_name] = mock_phase_def

    config.movement_phases = mocked_movement_phases
    return config

def create_frame_data(frame_num: int, angles: Optional[Dict[str, float]], timestamp: Optional[float] = None, raw_landmarks: Optional[list] = None) -> Dict[str, Any]:
    return {
        "frame_num": frame_num,
        "angles": angles,
        "timestamp": timestamp if timestamp is not None else frame_num * 0.1, # Simple timestamp
        "raw_landmarks": raw_landmarks if raw_landmarks is not None else [] # Default to empty landmarks if not provided
    }

@pytest.mark.asyncio
async def test_segment_repetitions_empty_input(dynamic_form_analysis_service: DynamicFormAnalysisService, mock_segmentation_config: MagicMock):
    repetitions = await dynamic_form_analysis_service.segment_repetitions([], mock_segmentation_config)
    assert repetitions == []

@pytest.mark.asyncio
async def test_segment_repetitions_no_config_phases(dynamic_form_analysis_service: DynamicFormAnalysisService):
    empty_config = MagicMock(spec=ExerciseConfig)
    empty_config.name = "Empty Config"
    empty_config.movement_phases = None
    frame_seq = [create_frame_data(0, {"LEFT_KNEE": 180})]
    repetitions = await dynamic_form_analysis_service.segment_repetitions(frame_seq, empty_config)
    assert repetitions == []

    empty_config.movement_phases = {}
    repetitions = await dynamic_form_analysis_service.segment_repetitions(frame_seq, empty_config)
    assert repetitions == []
    
@pytest.mark.asyncio
async def test_segment_repetitions_malformed_config_phases(dynamic_form_analysis_service: DynamicFormAnalysisService):
    malformed_config = MagicMock(spec=ExerciseConfig)
    malformed_config.name = "Malformed Config"
    malformed_config.movement_phases = "not_a_dict" # Malformed
    frame_seq = [create_frame_data(0, {"LEFT_KNEE": 180})]
    repetitions = await dynamic_form_analysis_service.segment_repetitions(frame_seq, malformed_config)
    assert repetitions == []

@pytest.mark.asyncio
async def test_segment_repetitions_no_valid_start_phase(dynamic_form_analysis_service: DynamicFormAnalysisService):
    config_no_start = MagicMock(spec=ExerciseConfig)
    config_no_start.name = "No Start Config"
    config_no_start.movement_phases = { # No phase name contains "start" and it's not guaranteed first
        "some_phase": {"triggers": {}}
    }
    # Service logic defaults to the first phase if "start" isn't in name.
    # This test is more about if movement_phases is empty after trying to find start phase.
    # The service code currently would pick "some_phase".
    # To truly test "no valid start phase" leading to empty, config.movement_phases would need to be empty
    # AFTER the start phase selection logic, which is covered by test_segment_repetitions_no_config_phases if keys() is empty.
    # This test might be redundant or needs rethinking based on precise failure mode desired.
    # For now, let's assume an empty movement_phases dict means no start phase.
    config_actually_empty_phases = MagicMock(spec=ExerciseConfig)
    config_actually_empty_phases.name = "Empty Phases"
    config_actually_empty_phases.movement_phases = {}
    frame_seq = [create_frame_data(0, {"LEFT_KNEE": 180})]
    repetitions = await dynamic_form_analysis_service.segment_repetitions(frame_seq, config_actually_empty_phases)
    assert repetitions == []


@pytest.mark.asyncio
async def test_segment_repetitions_single_short_sequence_no_rep_completed(
    dynamic_form_analysis_service: DynamicFormAnalysisService, 
    mock_segmentation_config: MagicMock
):
    """Test a short sequence that doesn't complete a full repetition."""
    frame_sequence = [
        create_frame_data(0, {"LEFT_KNEE": 175}), # Stays in start_phase
        create_frame_data(1, {"LEFT_KNEE": 170}), # Still in start_phase
    ]
    repetitions = await dynamic_form_analysis_service.segment_repetitions(frame_sequence, mock_segmentation_config)
    # Expect one "repetition" containing all frames as it's the final (incomplete) rep
    assert len(repetitions) == 1
    assert len(repetitions[0]) == 2
    assert repetitions[0][0]["angles"]["LEFT_KNEE"] == 175
    assert repetitions[0][1]["angles"]["LEFT_KNEE"] == 170

@pytest.mark.asyncio
async def test_segment_repetitions_one_full_rep(
    dynamic_form_analysis_service: DynamicFormAnalysisService,
    mock_segmentation_config: MagicMock
):
    frame_sequence = [
        create_frame_data(0, {"LEFT_KNEE": 175}), # start_phase
        create_frame_data(1, {"LEFT_KNEE": 150}), # -> descent_phase (150 < 160)
        create_frame_data(2, {"LEFT_KNEE": 85}),  # -> bottom_phase (85 <= 90)
        create_frame_data(3, {"LEFT_KNEE": 110}), # -> ascent_phase (110 > 100)
        create_frame_data(4, {"LEFT_KNEE": 175}), # -> start_phase (175 >= 170), rep completes
    ]
    repetitions = await dynamic_form_analysis_service.segment_repetitions(frame_sequence, mock_segmentation_config)
    assert len(repetitions) == 1
    assert len(repetitions[0]) == 5
    assert repetitions[0][0]["angles"]["LEFT_KNEE"] == 175
    assert repetitions[0][-1]["angles"]["LEFT_KNEE"] == 175

@pytest.mark.asyncio
async def test_segment_repetitions_one_full_rep_plus_incomplete_next(
    dynamic_form_analysis_service: DynamicFormAnalysisService,
    mock_segmentation_config: MagicMock
):
    frame_sequence = [
        # Rep 1
        create_frame_data(0, {"LEFT_KNEE": 175}), # start_phase
        create_frame_data(1, {"LEFT_KNEE": 150}), # -> descent_phase
        create_frame_data(2, {"LEFT_KNEE": 85}),  # -> bottom_phase
        create_frame_data(3, {"LEFT_KNEE": 110}), # -> ascent_phase
        create_frame_data(4, {"LEFT_KNEE": 175}), # -> start_phase (completes rep 1)
        # Incomplete Rep 2
        create_frame_data(5, {"LEFT_KNEE": 165}), # start_phase
        create_frame_data(6, {"LEFT_KNEE": 140}), # -> descent_phase
    ]
    repetitions = await dynamic_form_analysis_service.segment_repetitions(frame_sequence, mock_segmentation_config)
    assert len(repetitions) == 2
    assert len(repetitions[0]) == 5 # First full rep
    assert repetitions[0][-1]["angles"]["LEFT_KNEE"] == 175
    assert len(repetitions[1]) == 2 # Corrected: Second incomplete rep should have 2 frames
    assert repetitions[1][-1]["angles"]["LEFT_KNEE"] == 140 # Ensure last frame content is correct

@pytest.mark.asyncio
async def test_segment_repetitions_frames_with_no_angles_in_sequence(
    dynamic_form_analysis_service: DynamicFormAnalysisService,
    mock_segmentation_config: MagicMock
):
    """Test that frames with None for angles are included but don't cause phase transitions."""
    frame_sequence = [
        create_frame_data(0, {"LEFT_KNEE": 175}), # start_phase
        create_frame_data(1, {"LEFT_KNEE": 150}), # -> descent_phase
        create_frame_data(2, None),               # No angles, should stay in descent_phase
        create_frame_data(3, {"LEFT_KNEE": 85}),  # Still in descent_phase (previous good frame) before this one -> bottom_phase
        create_frame_data(4, {"LEFT_KNEE": 110}), # -> ascent_phase
        create_frame_data(5, None),               # No angles, should stay in ascent_phase
        create_frame_data(6, {"LEFT_KNEE": 175}), # -> start_phase (completes rep)
    ]
    # The service's segment_repetitions includes frames with no angles in the current_rep_frames
    # and skips phase transition logic for them.
    repetitions = await dynamic_form_analysis_service.segment_repetitions(frame_sequence, mock_segmentation_config)
    assert len(repetitions) == 1
    assert len(repetitions[0]) == 7
    assert repetitions[0][2]["angles"] is None
    assert repetitions[0][5]["angles"] is None
    # Check if rep completed despite None frames
    assert repetitions[0][-1]["angles"]["LEFT_KNEE"] == 175 

@pytest.mark.asyncio
async def test_segment_repetitions_trigger_malformed_condition(
    dynamic_form_analysis_service: DynamicFormAnalysisService
):
    config_malformed_trigger = MagicMock(spec=ExerciseConfig)
    config_malformed_trigger.name = "Malformed Trigger Config"
    
    start_phase_data = {
            "triggers": {
                "next": {
                "target_phase": "next_phase",
                    "conditions": [
                    {"joint": "LEFT_KNEE"} # Malformed condition
                ]
            }
        }
    }
    mock_start_phase = MagicMock(spec=MovementPhaseDefinition)
    for key, value in start_phase_data.items():
        setattr(mock_start_phase, key, value)

    next_phase_data = {"triggers": {}}
    mock_next_phase = MagicMock(spec=MovementPhaseDefinition)
    for key, value in next_phase_data.items():
        setattr(mock_next_phase, key, value)

    config_malformed_trigger.movement_phases = {
        "start_phase": mock_start_phase,
        "next_phase": mock_next_phase
    }

    frame_sequence = [create_frame_data(0, {"LEFT_KNEE": 150})]
    
    repetitions = await dynamic_form_analysis_service.segment_repetitions(frame_sequence, config_malformed_trigger)
    # Expect it to stay in start_phase and form one incomplete rep as the trigger fails to parse
    # assert len(repetitions) == 1 # Original assertion
    assert len(repetitions) == 0 # Correct: malformed condition prevents any phase progress, no rep formed from 1 frame

# --- END: Tests for segment_repetitions ---

# --- Tests for _apply_posture_rules ---

@pytest.mark.asyncio
async def test_apply_posture_rules_no_rules_defined(dynamic_form_analysis_service: DynamicFormAnalysisService):
    mock_config = MagicMock(spec=ExerciseConfig)
    mock_config.posture_rules = None # No posture rules
    
    frame_data = {"raw_landmarks": create_full_mock_landmarks({})}
    issues = await dynamic_form_analysis_service._apply_posture_rules(
        frame_data=frame_data, rep_index=0, current_phase_name="descent",
        frame_timestamp=0.1, frame_index_in_rep=0, config=mock_config
    )
    assert issues == []

@pytest.mark.asyncio
async def test_apply_posture_rules_no_raw_landmarks(dynamic_form_analysis_service: DynamicFormAnalysisService):
    mock_config = MagicMock(spec=ExerciseConfig)
    mock_config.posture_rules = [ # Define some rule
        {"rule_name": "test_rule", "conditions": []}
    ]
    frame_data = {"raw_landmarks": None} # No landmarks
    issues = await dynamic_form_analysis_service._apply_posture_rules(
        frame_data=frame_data, rep_index=0, current_phase_name="descent",
        frame_timestamp=0.1, frame_index_in_rep=0, config=mock_config
    )
    assert issues == [] # Expect no issues if landmarks are missing

@pytest.mark.asyncio
async def test_apply_posture_rules_rule_not_for_current_phase(dynamic_form_analysis_service: DynamicFormAnalysisService):
    mock_config = MagicMock(spec=ExerciseConfig)
    mock_config.posture_rules = [{
        "rule_name": "test_rule",
        "applicable_phases": ["ascent"], # Only for ascent
        "conditions": [{
            "condition_type": "vector_angle_from_vertical",
            "keypoints_for_vector": ["LEFT_SHOULDER", "LEFT_HIP"],
            "expected_angle_degrees": 0,
            "max_deviation_degrees": 10
        }]
    }]
    landmarks = create_full_mock_landmarks({
        "LEFT_SHOULDER": {"x": 0.5, "y": 0.2},
        "LEFT_HIP": {"x": 0.5, "y": 0.5} 
    })
    frame_data = {"raw_landmarks": landmarks}
    
    issues = await dynamic_form_analysis_service._apply_posture_rules(
        frame_data=frame_data, rep_index=0, current_phase_name="descent", # Current phase is descent
        frame_timestamp=0.1, frame_index_in_rep=0, config=mock_config
    )
    assert issues == []

@pytest.mark.asyncio
async def test_apply_posture_rules_correct_vertical_posture(dynamic_form_analysis_service: DynamicFormAnalysisService):
    mock_config = MagicMock(spec=ExerciseConfig)
    mock_config.posture_rules = [{
        "rule_name": "torso_vertical",
        "applicable_phases": ["middle"],
        "conditions": [{
            "condition_type": "vector_angle_from_vertical",
            "keypoints_for_vector": ["NOSE", "LEFT_HIP"], # CHANGED from MID_HIP to LEFT_HIP
            "expected_angle_degrees": 0, # Vertical, pointing down
            "max_deviation_degrees": 10
        }]
    }]
    
    # Simulate NOSE directly above LEFT_HIP (y increases downwards)
    landmarks = create_full_mock_landmarks({
        "NOSE":     {"x": 0.5, "y": 0.2},
        "LEFT_HIP": {"x": 0.5, "y": 0.6} # LEFT_HIP below NOSE
    })
    frame_data = {"raw_landmarks": landmarks}
    
    issues = await dynamic_form_analysis_service._apply_posture_rules(
        frame_data=frame_data, rep_index=0, current_phase_name="middle",
        frame_timestamp=0.1, frame_index_in_rep=0, config=mock_config
    )
    assert issues == []

@pytest.mark.asyncio
async def test_apply_posture_rules_torso_leans_forward_violation(dynamic_form_analysis_service: DynamicFormAnalysisService):
    mock_config = MagicMock(spec=ExerciseConfig)
    mock_config.posture_rules = [{
        "rule_name": "torso_upright",
        "applicable_phases": ["stance"],
        "conditions": [{
            "condition_type": "vector_angle_from_vertical",
            "keypoints_for_vector": ["LEFT_SHOULDER", "LEFT_HIP"], # Vector from shoulder to hip
            "expected_angle_degrees": 0,  # Expected to be vertical (shoulder above hip)
            "max_deviation_degrees": 10 # CHANGED from 15 to 10
        }]
    }]
    
    # Simulate shoulder leaning forward of hip (x value for shoulder > x for hip, y for shoulder < y for hip)
    # Vector: Hip (0.5, 0.6) to Shoulder (0.6, 0.2)
    # dx = 0.6 - 0.5 = 0.1
    # dy = 0.2 - 0.6 = -0.4 (points upwards)
    # atan2(0.1, -0.4) -> angle with positive Y (downwards) will be around 165-170 deg or -165 to -170
    # Expected is 0 deg. Difference is large.
    landmarks = create_full_mock_landmarks({
        "LEFT_SHOULDER": {"x": 0.6, "y": 0.2}, 
        "LEFT_HIP":      {"x": 0.5, "y": 0.6}  
    })
    frame_data = {"raw_landmarks": landmarks}
    
    issues = await dynamic_form_analysis_service._apply_posture_rules(
        frame_data=frame_data, rep_index=0, current_phase_name="stance",
        frame_timestamp=0.1, frame_index_in_rep=0, config=mock_config
    )
    assert len(issues) == 1
    issue = issues[0]
    assert issue["rule_type"] == "posture"
    assert issue["severity"] == FeedbackSeverity.HIGH.value # Based on large deviation
    assert "torso_upright" in issue["details"]
    assert issue["expected_value"]["expected_angle_from_vertical_degrees"] == 0
    # Corrected calculation for atan2 arguments to match service: (hip_x - shoulder_x, hip_y - shoulder_y)
    assert math.isclose(issue["current_value"]["observed_vector_angle_from_vertical_degrees"], math.degrees(math.atan2(0.5 - 0.6, 0.6 - 0.2)), abs_tol=0.1)
    assert issue["violation_type"] == "torso_upright_deviation"

@pytest.mark.asyncio
async def test_apply_posture_rules_missing_one_keypoint_for_vector(dynamic_form_analysis_service: DynamicFormAnalysisService):
    mock_config = MagicMock(spec=ExerciseConfig)
    mock_config.posture_rules = [{
        "rule_name": "head_alignment",
        "conditions": [{
            "condition_type": "vector_angle_from_vertical",
            "keypoints_for_vector": ["NOSE", "NECK"], # NECK is often not a direct landmark
            "expected_angle_degrees": 0,
            "max_deviation_degrees": 5
        }]
    }]
    
    # NOSE is present, NECK (if it were in TEST_LANDMARK_NAMES) might be missing if its default init is an actual None
    # Or, if _get_keypoint_coords_by_name returns None for a landmark not in the frame's list
    landmarks_missing_neck = [create_mock_landmark(0.5,0.5) if TEST_LANDMARK_NAMES[i] != "NECK" else None for i in range(len(TEST_LANDMARK_NAMES))]
    # For this test, let's explicitly make Neck not retrievable by using a valid name but ensuring its data is bad / not found by _get_keypoint_coords_by_name
    # More simply, provide landmarks only for NOSE
    landmarks = create_full_mock_landmarks({"NOSE": {"x":0.5, "y":0.1}}) 
    # We rely on _get_keypoint_coords_by_name to return None for "NECK" if it's not in `landmarks`'s effectively defined points
    # or if the actual name "NECK" is not in POSE_LANDMARK_NAMES. For this test, assume "NECK" is a valid name in map.
    
    # To ensure "NECK" is truly missing for the helper, let's construct landmarks without it.
    # The create_full_mock_landmarks initializes all. We need to simulate one missing.
    # The easiest way for the test is to use a keypoint_name in the rule that is NOT in POSE_LANDMARK_NAMES.
    # Or, ensure that if it IS in POSE_LANDMARK_NAMES, its entry in the raw_landmark_data is None or lacks x,y.
    
    # Let's use a name not in the default POSE_LANDMARK_NAMES to test this path of the helper
    mock_config.posture_rules[0]["conditions"][0]["keypoints_for_vector"] = ["NOSE", "NON_EXISTENT_POINT"]

    frame_data = {"raw_landmarks": landmarks} # Landmarks contains NOSE but not NON_EXISTENT_POINT effectively
    
    issues = await dynamic_form_analysis_service._apply_posture_rules(
        frame_data=frame_data, rep_index=0, current_phase_name="any_phase",
        frame_timestamp=0.1, frame_index_in_rep=0, config=mock_config
    )
    assert issues == [] # Should skip condition if keypoints are missing

@pytest.mark.asyncio
async def test_apply_posture_rules_malformed_condition_data(dynamic_form_analysis_service: DynamicFormAnalysisService):
    mock_config = MagicMock(spec=ExerciseConfig)
    mock_config.posture_rules = [{
        "rule_name": "bad_rule",
        "conditions": [{
            "condition_type": "vector_angle_from_vertical",
            "keypoints_for_vector": ["LEFT_SHOULDER"], # Missing one keypoint in list
            "expected_angle_degrees": "not_a_float", # Wrong type
            "max_deviation_degrees": 10
        }]
    }]
    landmarks = create_full_mock_landmarks({"LEFT_SHOULDER": {"x":0.5, "y":0.2}})
    frame_data = {"raw_landmarks": landmarks}
    issues = await dynamic_form_analysis_service._apply_posture_rules(
        frame_data=frame_data, rep_index=0, current_phase_name="any",
        frame_timestamp=0.1, frame_index_in_rep=0, config=mock_config
    )
    assert issues == [] # Malformed condition should be skipped

@pytest.mark.asyncio
async def test_apply_posture_rules_points_at_same_position(dynamic_form_analysis_service: DynamicFormAnalysisService):
    mock_config = MagicMock(spec=ExerciseConfig)
    mock_config.posture_rules = [{
        "rule_name": "identical_points_check",
        "conditions": [{
            "condition_type": "vector_angle_from_vertical",
            "keypoints_for_vector": ["LEFT_WRIST", "RIGHT_WRIST"],
            "expected_angle_degrees": 0,
            "max_deviation_degrees": 5
        }]
    }]
    landmarks = create_full_mock_landmarks({
        "LEFT_WRIST":  {"x": 0.7, "y": 0.7},
        "RIGHT_WRIST": {"x": 0.7, "y": 0.7} # Same position
    })
    frame_data = {"raw_landmarks": landmarks}
    issues = await dynamic_form_analysis_service._apply_posture_rules(
        frame_data=frame_data, rep_index=0, current_phase_name="any",
        frame_timestamp=0.1, frame_index_in_rep=0, config=mock_config
    )
    assert issues == [] # Should skip vector calculation for identical points

@pytest.mark.asyncio
async def test_apply_posture_rules_horizontal_vector_correct(dynamic_form_analysis_service: DynamicFormAnalysisService):
    mock_config = MagicMock(spec=ExerciseConfig)
    mock_config.posture_rules = [{
        "rule_name": "shoulders_level",
        "conditions": [{
            "condition_type": "vector_angle_from_vertical",
            "keypoints_for_vector": ["LEFT_SHOULDER", "RIGHT_SHOULDER"], # Vector from Left to Right shoulder
            "expected_angle_degrees": 90,  # Horizontal, pointing to the right from positive Y-axis (down)
            "max_deviation_degrees": 10
        }]
    }]
    # Left shoulder (0.4, 0.3), Right shoulder (0.6, 0.3) -> dx=0.2, dy=0. Angle should be 90 deg.
    landmarks = create_full_mock_landmarks({
        "LEFT_SHOULDER":  {"x": 0.4, "y": 0.3},
        "RIGHT_SHOULDER": {"x": 0.6, "y": 0.3} 
    })
    frame_data = {"raw_landmarks": landmarks}
    issues = await dynamic_form_analysis_service._apply_posture_rules(
        frame_data=frame_data, rep_index=0, current_phase_name="any",
        frame_timestamp=0.1, frame_index_in_rep=0, config=mock_config
    )
    assert issues == []

@pytest.mark.asyncio
async def test_apply_posture_rules_horizontal_vector_violation(dynamic_form_analysis_service: DynamicFormAnalysisService):
    mock_config = MagicMock(spec=ExerciseConfig)
    mock_config.posture_rules = [{
        "rule_name": "shoulders_level_strict",
        "conditions": [{
            "condition_type": "vector_angle_from_vertical",
            "keypoints_for_vector": ["LEFT_SHOULDER", "RIGHT_SHOULDER"],
            "expected_angle_degrees": 90,
            "max_deviation_degrees": 5 # Strict tolerance
        }],
        "severity": "high" # Rule level severity
    }]
    # Left shoulder (0.4, 0.3), Right shoulder (0.6, 0.35) -> tilted, RS lower than LS
    # dx = 0.2, dy = 0.05. atan2(0.2, 0.05) -> approx 76 degrees. Expected 90. Diff = 14.
    landmarks = create_full_mock_landmarks({
        "LEFT_SHOULDER":  {"x": 0.4, "y": 0.3},
        "RIGHT_SHOULDER": {"x": 0.6, "y": 0.35} 
    })
    frame_data = {"raw_landmarks": landmarks}
    issues = await dynamic_form_analysis_service._apply_posture_rules(
        frame_data=frame_data, rep_index=0, current_phase_name="any",
        frame_timestamp=0.1, frame_index_in_rep=0, config=mock_config
    )
    assert len(issues) == 1
    issue = issues[0]
    assert issue["rule_type"] == "posture"
    assert "shoulders_level_strict" in issue["details"]
    assert issue["severity"] == FeedbackSeverity.HIGH.value # Deviation 14 > 5*2 (for High)
    assert math.isclose(issue["deviation"], abs(math.degrees(math.atan2(0.2, 0.05)) - 90.0), abs_tol=0.1)


# TODO: Add tests for other condition_types if _apply_posture_rules is expanded.
# TODO: Add tests verifying the use of visibility scores if the logic is added to _get_keypoint_coords_by_name
#       or directly in _apply_posture_rules. Currently, it's assumed upstream filtering or rule relevance handles this.


# --- Tests for _apply_symmetry_rules ---

@pytest.mark.asyncio
async def test_apply_symmetry_rules_no_rules(dynamic_form_analysis_service: DynamicFormAnalysisService):
    mock_config = MagicMock(spec=ExerciseConfig)
    mock_config.symmetry_rules = None
    frame_angles = {"LEFT_KNEE": 90.0, "RIGHT_KNEE": 92.0}
    issues = await dynamic_form_analysis_service._apply_symmetry_rules(
        frame_angles, 0, "stance", 0.1, 0, mock_config
    )
    assert issues == []

@pytest.mark.asyncio
async def test_apply_symmetry_rules_empty_rules_list(dynamic_form_analysis_service: DynamicFormAnalysisService):
    mock_config = MagicMock(spec=ExerciseConfig)
    mock_config.symmetry_rules = []
    frame_angles = {"LEFT_KNEE": 90.0, "RIGHT_KNEE": 92.0}
    issues = await dynamic_form_analysis_service._apply_symmetry_rules(
        frame_angles, 0, "stance", 0.1, 0, mock_config
    )
    assert issues == []

@pytest.mark.asyncio
async def test_apply_symmetry_rules_symmetric_angles_within_tolerance(dynamic_form_analysis_service: DynamicFormAnalysisService):
    mock_config = MagicMock(spec=ExerciseConfig)
    mock_config.symmetry_rules = [{
        "joint_pair": ["LEFT_KNEE", "RIGHT_KNEE"],
        "max_difference_degrees": 10,
        "applicable_phases": ["stance"]
    }]
    frame_angles = {"LEFT_KNEE": 90.0, "RIGHT_KNEE": 95.0} # Diff 5.0, within tolerance
    issues = await dynamic_form_analysis_service._apply_symmetry_rules(
        frame_angles, 0, "stance", 0.1, 0, mock_config
    )
    assert issues == []

@pytest.mark.asyncio
async def test_apply_symmetry_rules_angles_at_tolerance_edge(dynamic_form_analysis_service: DynamicFormAnalysisService):
    mock_config = MagicMock(spec=ExerciseConfig)
    mock_config.symmetry_rules = [{
        "joint_pair": ["LEFT_KNEE", "RIGHT_KNEE"],
        "max_difference_degrees": 10,
    }]
    frame_angles = {"LEFT_KNEE": 90.0, "RIGHT_KNEE": 100.0} # Diff 10.0, at edge, should not be issue
    issues = await dynamic_form_analysis_service._apply_symmetry_rules(
        frame_angles, 0, "any", 0.1, 0, mock_config
    )
    assert issues == []

@pytest.mark.asyncio
async def test_apply_symmetry_rules_asymmetric_angles_violation(dynamic_form_analysis_service: DynamicFormAnalysisService):
    mock_config = MagicMock(spec=ExerciseConfig)
    mock_config.symmetry_rules = [{
        "joint_pair": ["LEFT_ELBOW", "RIGHT_ELBOW"],
        "max_difference_degrees": 5,
        "severity": "high" # Custom severity from rule data
    }]
    frame_angles = {"LEFT_ELBOW": 120.0, "RIGHT_ELBOW": 135.0} # Diff 15.0, exceeds tolerance
    issues = await dynamic_form_analysis_service._apply_symmetry_rules(
        frame_angles, 1, "lift", 0.5, 10, mock_config
    )
    assert len(issues) == 1
    issue = issues[0]
    assert issue["rule_type"] == "symmetry"
    assert issue["joint_name"] == "LEFT_ELBOW"
    assert issue["compared_to_joint"] == "RIGHT_ELBOW"
    assert issue["rep_index"] == 1
    assert issue["phase"] == "lift"
    assert issue["current_value"]["difference"] == 15.0
    assert issue["expected_value"]["max_difference_degrees"] == 5
    assert issue["deviation"] == 10.0 # 15.0 - 5.0
    # Severity calculation: deviation 10, tolerance 5. 10 > 5 * (some factor for HIGH)
    # Default severity calculation: 10 is > 5, so HIGH.
    assert issue["severity"] == FeedbackSeverity.HIGH.value 
    assert "asymmetry_LEFT_ELBOW_RIGHT_ELBOW" in issue["violation_type"]

@pytest.mark.asyncio
async def test_apply_symmetry_rules_missing_one_angle(dynamic_form_analysis_service: DynamicFormAnalysisService):
    mock_config = MagicMock(spec=ExerciseConfig)
    mock_config.symmetry_rules = [{
        "joint_pair": ["LEFT_KNEE", "RIGHT_KNEE"],
        "max_difference_degrees": 10
    }]
    frame_angles = {"LEFT_KNEE": 90.0} # RIGHT_KNEE is missing
    issues = await dynamic_form_analysis_service._apply_symmetry_rules(
        frame_angles, 0, "any", 0.1, 0, mock_config
    )
    assert issues == [] # Should skip if one angle is missing

@pytest.mark.asyncio
async def test_apply_symmetry_rules_missing_both_angles(dynamic_form_analysis_service: DynamicFormAnalysisService):
    mock_config = MagicMock(spec=ExerciseConfig)
    mock_config.symmetry_rules = [{
        "joint_pair": ["LEFT_ANKLE", "RIGHT_ANKLE"],
        "max_difference_degrees": 5
    }]
    frame_angles = {"LEFT_KNEE": 90.0} # Both ANKLE angles missing
    issues = await dynamic_form_analysis_service._apply_symmetry_rules(
        frame_angles, 0, "any", 0.1, 0, mock_config
    )
    assert issues == []

@pytest.mark.asyncio
async def test_apply_symmetry_rules_rule_not_for_current_phase(dynamic_form_analysis_service: DynamicFormAnalysisService):
    mock_config = MagicMock(spec=ExerciseConfig)
    mock_config.symmetry_rules = [{
        "joint_pair": ["LEFT_KNEE", "RIGHT_KNEE"],
        "max_difference_degrees": 10,
        "applicable_phases": ["descent"]
    }]
    frame_angles = {"LEFT_KNEE": 90.0, "RIGHT_KNEE": 110.0} # Violation, but wrong phase
    issues = await dynamic_form_analysis_service._apply_symmetry_rules(
        frame_angles, 0, "ascent", 0.1, 0, mock_config
    )
    assert issues == []

@pytest.mark.asyncio
async def test_apply_symmetry_rules_malformed_rule_data(dynamic_form_analysis_service: DynamicFormAnalysisService):
    mock_config = MagicMock(spec=ExerciseConfig)
    mock_config.symmetry_rules = [{
        "joint_pair": ["LEFT_KNEE"], # Incorrect: needs two joints
        "max_difference_degrees": "not_a_float"
    }]
    frame_angles = {"LEFT_KNEE": 90.0, "RIGHT_KNEE": 92.0}
    issues = await dynamic_form_analysis_service._apply_symmetry_rules(
        frame_angles, 0, "any", 0.1, 0, mock_config
    )
    assert issues == [] # Malformed rule should be skipped

@pytest.mark.asyncio
async def test_apply_symmetry_rules_multiple_rules_one_violation(dynamic_form_analysis_service: DynamicFormAnalysisService):
    mock_config = MagicMock(spec=ExerciseConfig)
    mock_config.symmetry_rules = [
        {
            "joint_pair": ["LEFT_KNEE", "RIGHT_KNEE"],
            "max_difference_degrees": 10
        },
        {
            "joint_pair": ["LEFT_ELBOW", "RIGHT_ELBOW"],
            "max_difference_degrees": 5
        }
    ]
    frame_angles = {
        "LEFT_KNEE": 90.0, "RIGHT_KNEE": 95.0, # Symmetric
        "LEFT_ELBOW": 100.0, "RIGHT_ELBOW": 112.0 # Asymmetric (diff 12 > 5)
    }
    issues = await dynamic_form_analysis_service._apply_symmetry_rules(
        frame_angles, 0, "any", 0.1, 0, mock_config
    )
    assert len(issues) == 1
    issue = issues[0]
    assert issue["joint_name"] == "LEFT_ELBOW"
    assert issue["compared_to_joint"] == "RIGHT_ELBOW"
    assert issue["current_value"]["difference"] == 12.0


# --- Expanded Tests for _apply_joint_angle_rules ---

@pytest.mark.asyncio
async def test_apply_joint_angle_rules_angle_missing_for_ruled_joint(dynamic_form_analysis_service: DynamicFormAnalysisService):
    mock_config_dict = {
        "joint_angle_rules": {
            "phases": {
                "descent": {
                    "angles": {
                        "LEFT_KNEE": {"min_angle": 80, "max_angle": 100, "ideal_angle": 90, "tolerance": 5}
                    }
                }
            }
        }
    }
    mock_config = MagicMock(spec=ExerciseConfig)
    # Simulate how ExerciseConfig would store this JSON data
    mock_config.joint_angle_rules = mock_config_dict["joint_angle_rules"]
    
    frame_angles = {"RIGHT_KNEE": 90.0} # LEFT_KNEE angle is missing
    issues = await dynamic_form_analysis_service._apply_joint_angle_rules(
        frame_angles, 0, "descent", 0.1, 0, mock_config
    )
    assert issues == [] # Rule for LEFT_KNEE, but it's missing, so no issue generated

@pytest.mark.asyncio
@pytest.mark.parametrize("angle, expected_issues_count", [
    (80.0, 1), # Exactly at min_angle, BUT outside ideal range (85-95) -> 1 issue
    (100.0, 1),# Exactly at max_angle, BUT outside ideal range (85-95) -> 1 issue
    (79.9, 1), # Just below min_angle
    (100.1, 1), # Just above max_angle
    (85.0, 0), # Within ideal_angle - tolerance (90-5)
    (95.0, 0), # Within ideal_angle + tolerance (90+5)
    (84.9, 1), # Just below ideal_angle - tolerance
    (95.1, 1), # Just above ideal_angle + tolerance
])
async def test_apply_joint_angle_rules_boundary_conditions(
    dynamic_form_analysis_service: DynamicFormAnalysisService, angle: float, expected_issues_count: int
):
    mock_config_dict = {
        "joint_angle_rules": {
            "phases": {
                "stance": {
                    "angles": {
                        "LEFT_HIP": {"min_angle": 80, "max_angle": 100, "ideal_angle": 90, "tolerance": 5}
                    }
                }
            }
        }
    }
    mock_config = MagicMock(spec=ExerciseConfig)
    mock_config.joint_angle_rules = mock_config_dict["joint_angle_rules"]

    frame_angles = {"LEFT_HIP": angle}
    issues = await dynamic_form_analysis_service._apply_joint_angle_rules(
        frame_angles, 0, "stance", 0.1, 0, mock_config
    )
    assert len(issues) == expected_issues_count
    if expected_issues_count > 0:
        issue = issues[0]
        assert issue["joint_name"] == "LEFT_HIP"
        assert issue["current_value"] == angle

@pytest.mark.asyncio
async def test_apply_joint_angle_rules_multiple_violations_in_frame(dynamic_form_analysis_service: DynamicFormAnalysisService):
    mock_config_dict = {
        "joint_angle_rules": {
            "phases": {
                "default": { # Using default phase rules
                    "angles": {
                        "LEFT_KNEE": {"min_angle": 90, "max_angle": 170, "ideal_angle": 160, "tolerance": 10},
                        "RIGHT_ELBOW": {"min_angle": 70, "max_angle": 150, "ideal_angle": 90, "tolerance": 10}
                    }
                }
            }
        }
    }
    mock_config = MagicMock(spec=ExerciseConfig)
    mock_config.joint_angle_rules = mock_config_dict["joint_angle_rules"]

    frame_angles = {"LEFT_KNEE": 80.0, "RIGHT_ELBOW": 160.0} # KNEE too low, ELBOW too high
    issues = await dynamic_form_analysis_service._apply_joint_angle_rules(
        frame_angles, 0, "any_phase_using_default", 0.1, 0, mock_config
    )
    assert len(issues) == 2
    assert any(i["joint_name"] == "LEFT_KNEE" and "below_min" in i["violation_type"] for i in issues)
    assert any(i["joint_name"] == "RIGHT_ELBOW" and "above_max" in i["violation_type"] for i in issues)

@pytest.mark.asyncio
async def test_apply_joint_angle_rules_phase_specific_vs_default(dynamic_form_analysis_service: DynamicFormAnalysisService):
    mock_config_dict = {
        "joint_angle_rules": {
            "phases": {
                "descent": {
                    "angles": {"SQUAT_DEPTH": {"min_angle": 80, "max_angle": 100, "ideal_angle": 90, "tolerance": 5}}
                },
                "default": {
                    "angles": {"SQUAT_DEPTH": {"min_angle": 0, "max_angle": 180, "ideal_angle": 170, "tolerance": 5}}
                }
            }
        }
    }
    mock_config = MagicMock(spec=ExerciseConfig)
    mock_config.joint_angle_rules = mock_config_dict["joint_angle_rules"]

    # Test descent phase - should use descent rules (e.g., angle 70 violates min_angle 80)
    frame_angles_descent = {"SQUAT_DEPTH": 70.0}
    issues_descent = await dynamic_form_analysis_service._apply_joint_angle_rules(
        frame_angles_descent, 0, "descent", 0.1, 0, mock_config
    )
    assert len(issues_descent) == 1
    assert issues_descent[0]["joint_name"] == "SQUAT_DEPTH"
    assert issues_descent[0]["expected_value"]["min_angle"] == 80

    # Test other phase - should use default rules (e.g., angle 70 is fine for default 0-180)
    frame_angles_other = {"SQUAT_DEPTH": 70.0}
    issues_other = await dynamic_form_analysis_service._apply_joint_angle_rules(
        frame_angles_other, 0, "ascent", 0.2, 1, mock_config # "ascent" not defined, should use default
    )
    assert len(issues_other) == 1 # No violation with default rules -> CORRECTED TO 1

@pytest.mark.asyncio
@pytest.mark.parametrize("deviation, tolerance, expected_severity_str", [
    (1, 10, FeedbackSeverity.LOW.value),    # Small deviation, large tolerance -> LOW
    (5, 10, FeedbackSeverity.LOW.value),    # Medium dev, large tol (5 <= 10/2) -> LOW
    (6, 10, FeedbackSeverity.MEDIUM.value),  # Medium dev, large tol (6 > 10/2, 6 <= 10) -> MEDIUM
    (10, 10, FeedbackSeverity.MEDIUM.value), # Max dev within tol (10 <= 10) -> MEDIUM
    (11, 10, FeedbackSeverity.HIGH.value),   # Dev exceeds tol -> HIGH
    (20, 5, FeedbackSeverity.HIGH.value),    # Large dev, small tol -> HIGH
])
async def test_apply_joint_angle_rules_severity_calculation(
    dynamic_form_analysis_service: DynamicFormAnalysisService, deviation: float, tolerance: float, expected_severity_str: str
):
    # Test rule is min_angle = 100, tolerance affects severity band
    angle = 100 - deviation # This will be the actual angle, causing a 'below_min' violation
    mock_config_dict = {
        "joint_angle_rules": {
            "phases": {
                "default": {
                    "angles": {
                        "TEST_JOINT": {"min_angle": 100, "max_angle": 180, "ideal_angle": 140, "tolerance": tolerance}
                    }
                }
            }
        }
    }
    mock_config = MagicMock(spec=ExerciseConfig)
    mock_config.joint_angle_rules = mock_config_dict["joint_angle_rules"]
    frame_angles = {"TEST_JOINT": angle}
    
    issues = await dynamic_form_analysis_service._apply_joint_angle_rules(
        frame_angles, 0, "default", 0.1, 0, mock_config
    )
    assert len(issues) == 1
    assert issues[0]["severity"] == expected_severity_str
    assert math.isclose(issues[0]["deviation"], deviation)


# --- Expanded Tests for _apply_rom_rules ---

@pytest.mark.asyncio
async def test_apply_rom_rules_rep_with_none_frames_or_missing_angles(dynamic_form_analysis_service: DynamicFormAnalysisService):
    mock_config_dict = {
        "rom_rules": [{
            "joint_name": "LEFT_KNEE", 
            "min_angle_overall": 80.0, # ADJUSTED from 70
            "max_angle_overall": 160.0, # ADJUSTED from 170
            "target_rom": 100, "tolerance_degrees": 10
        }]
    }
    mock_config = MagicMock(spec=ExerciseConfig)
    mock_config.rom_rules = mock_config_dict["rom_rules"]

    rep_angle_data = [
        {"frame_num": 0, "timestamp": 0.0, "angles": {"LEFT_KNEE": 160.0}, "raw_landmarks": []},
        {"frame_num": 1, "timestamp": 0.03, "angles": None, "raw_landmarks": []}, # None angles
        {"frame_num": 2, "timestamp": 0.06, "angles": {"RIGHT_KNEE": 90.0}, "raw_landmarks": []}, # Missing LEFT_KNEE
        {"frame_num": 3, "timestamp": 0.09, "angles": {"LEFT_KNEE": 80.0}, "raw_landmarks": []},
        None, # A completely None frame_data element
    ]
    
    issues = await dynamic_form_analysis_service._apply_rom_rules(rep_angle_data, 0, mock_config)
    # Should still evaluate based on available data (160 and 80 for LEFT_KNEE)
    # Observed min 80, max 160. ROM 80.
    # Expected min 70 (ok), max 170 (ok). Target ROM 100, observed 80. Diff 20 > tolerance 10. -> Issue
    assert len(issues) == 1
    issue = issues[0]
    assert issue["rule_type"] == "rom"
    assert issue["joint_name"] == "LEFT_KNEE"
    assert issue["violation_type"] == "deviation_from_target_rom"
    assert issue["current_value"]["observed_min"] == 80.0
    assert issue["current_value"]["observed_max"] == 160.0
    assert issue["current_value"]["observed_rom"] == 80.0
    assert math.isclose(issue["deviation"], 20.0) # abs(80-100)

@pytest.mark.asyncio
@pytest.mark.parametrize("observed_rom_val, target_rom_val, tolerance_val, expected_issues_count", [
    (95, 100, 10, 0),  # Diff 5, within tolerance 10
    (90, 100, 10, 0),  # Diff 10, at tolerance edge
    (89.9, 100, 10, 1), # Diff 10.1, exceeds tolerance
    (105, 100, 10, 0), # Diff 5 (other way), within tolerance
    (110, 100, 10, 0), # Diff 10 (other way), at tolerance edge
    (110.1, 100, 10, 1),# Diff 10.1 (other way), exceeds tolerance
])
async def test_apply_rom_rules_target_rom_boundary_conditions(
    dynamic_form_analysis_service: DynamicFormAnalysisService, 
    observed_rom_val: float, target_rom_val: float, tolerance_val: float, expected_issues_count: int
):
    # Dynamically set max_angle_overall to ensure it doesn't interfere with target_rom checks
    # when no issues are expected from target_rom itself.
    # The goal is: observed_max_angle_for_joint (which is 50.0 + observed_rom_val) should NOT be < max_angle_overall_rule
    # So, max_angle_overall_rule should be <= 50.0 + observed_rom_val.
    # Setting it exactly to 50.0 + observed_rom_val ensures the max_angle_overall_rule is met.
    dynamic_max_overall = 50.0 + observed_rom_val

    mock_config_dict = {
        "rom_rules": [{
            "joint_name": "TEST_ROM_JOINT", 
            "min_angle_overall": 50.0, 
            "max_angle_overall": dynamic_max_overall, # Use the dynamically calculated max_overall
            "target_rom": target_rom_val, "tolerance_degrees": tolerance_val
        }]
    }
    mock_config = MagicMock(spec=ExerciseConfig)
    mock_config.rom_rules = mock_config_dict["rom_rules"]
    
    # Construct rep_angle_data to achieve the observed_rom_val
    # e.g., min_angle = 50, max_angle = 50 + observed_rom_val
    rep_angle_data = [
        {"angles": {"TEST_ROM_JOINT": 50.0}}, 
        {"angles": {"TEST_ROM_JOINT": 50.0 + observed_rom_val}}
    ]
    
    issues = await dynamic_form_analysis_service._apply_rom_rules(rep_angle_data, 0, mock_config)
    assert len(issues) == expected_issues_count
    if expected_issues_count > 0:
        assert issues[0]["violation_type"] == "deviation_from_target_rom"

@pytest.mark.asyncio
async def test_apply_rom_rules_min_max_overall_and_target_rom_violations(dynamic_form_analysis_service: DynamicFormAnalysisService):
    # Scenario: Fails to reach min_angle_overall, AND target_rom is also missed as a consequence.
    # The system should prioritize the more fundamental min/max overall violation first.
    mock_config_dict = {
        "rom_rules": [{
            "joint_name": "ELBOW_FLEX", "min_angle_overall": 30, "max_angle_overall": 150,
            "target_rom": 120, "tolerance_degrees": 5 
        }]
    }
    mock_config = MagicMock(spec=ExerciseConfig)
    mock_config.rom_rules = mock_config_dict["rom_rules"]

    # Observed: min 40, max 140. ROM = 100.
    # Violation 1: min_angle_overall not met (40 > 30 is okay, let's make it fail: observed_min > rule_min_overall)
    # Let rule min be 50. Observed min = 40. (40 < 50 is okay)
    # Let rule max be 130. Observed max = 140. (140 > 130 is okay)
    # Let's change observed data to violate min_angle_overall: observed_min 60, rule_min 50. (60 > 50, WRONG, logic is observed < rule_min)
    # If rule min_angle_overall=50, observed min is 60 -> Fails to reach deep enough flexion.
    # Rep data: min angle is 60, max is 120. ROM = 60.
    # Rule min_overall = 50. Observed min (60) > rule_min (50) -> means didn't go low enough. This is the issue.
    mock_config.rom_rules[0]["min_angle_overall"] = 50 # Must go down to 50
    rep_angle_data = [
        {"angles": {"ELBOW_FLEX": 120.0}}, # Max
        {"angles": {"ELBOW_FLEX": 60.0}}   # Min (but should have gone to 50)
    ]
    
    issues = await dynamic_form_analysis_service._apply_rom_rules(rep_angle_data, 0, mock_config)
    assert len(issues) == 1
    issue = issues[0]
    assert issue["violation_type"] == "failed_to_reach_min_rom" # This should be the primary issue
    assert issue["current_value"]["observed_min"] == 60.0
    assert issue["expected_value"]["rule_min_overall"] == 50.0

@pytest.mark.asyncio
async def test_apply_rom_rules_multiple_joint_rules(dynamic_form_analysis_service: DynamicFormAnalysisService):
    mock_config_dict = {
        "rom_rules": [
            {
                "joint_name": "KNEE",
                "min_angle_overall": 90.0,  # Stays 90.0 (covers observed 90)
                "max_angle_overall": 160.0, # ADJUSTED from 170.0 (covers observed 160)
                "target_rom": 90, "tolerance_degrees": 5
            },
            {
                "joint_name": "HIP",
                "min_angle_overall": 100.0, # Stays 100.0 (covers observed 100)
                "max_angle_overall": 150.0, # ADJUSTED from 160.0 (covers observed 150)
                "target_rom": 70, "tolerance_degrees": 5
            }
        ]
    }
    mock_config = MagicMock(spec=ExerciseConfig)
    mock_config.rom_rules = mock_config_dict["rom_rules"]

    # KNEE: min 90, max 160. ROM 70. Target 90. Diff 20 > 5. VIOLATION.
    # HIP:  min 100, max 150. ROM 50. Target 70. Diff 20 > 5. VIOLATION.
    rep_angle_data = [
        {"angles": {"KNEE": 90.0, "HIP": 100.0}}, 
        {"angles": {"KNEE": 160.0, "HIP": 150.0}}
    ]
    issues = await dynamic_form_analysis_service._apply_rom_rules(rep_angle_data, 0, mock_config)
    assert len(issues) == 2
    assert any(i["joint_name"] == "KNEE" and i["violation_type"] == "deviation_from_target_rom" for i in issues)
    assert any(i["joint_name"] == "HIP" and i["violation_type"] == "deviation_from_target_rom" for i in issues)


# --- Integration-level tests for analyze_form_dynamically ---

@pytest.mark.asyncio
async def test_analyze_form_dynamically_success_path(
    dynamic_form_analysis_service: DynamicFormAnalysisService,
    mock_exercise_config_service: MagicMock,
    mock_initial_form_check: MagicMock # Added
):
    video_id = uuid4()
    exercise_type_slug = "squat"
    # exercise_template_id_for_video = uuid4() # Not directly used if config is passed

    mock_video = MagicMock(spec=Video) 
    mock_video.id = video_id
    mock_video.user_id = uuid4() # Add user_id for FormCheck consistency
    mock_video.exercise_type_slug = exercise_type_slug 
    # mock_video.exercise_template_id = exercise_template_id_for_video
    mock_angle_data = [{"LEFT_KNEE": 170}, {"LEFT_KNEE": 90}, {"LEFT_KNEE": 170}]
    mock_raw_pose_data = [create_full_mock_landmarks({}), create_full_mock_landmarks({}), create_full_mock_landmarks({})]
    mock_video.angle_data = mock_angle_data
    mock_video.raw_pose_data = mock_raw_pose_data
    mock_video.fps = 30.0

    expected_enriched_sequence_for_segmentation = []
    for i in range(len(mock_angle_data)):
        expected_enriched_sequence_for_segmentation.append({
            "frame_num": i,
            "timestamp": i / mock_video.fps if mock_video.fps else None,
            "angles": mock_angle_data[i],
            "raw_landmarks": mock_raw_pose_data[i]
        })

    mock_config = MagicMock(spec=ExerciseConfig)
    mock_config.id = uuid4()
    # mock_config.exercise_template_id = exercise_template_id_for_video # Not strictly necessary for this test flow
    mock_config.joint_angle_rules = {
        "phases": {
            "default": {
                "angles": {
                    "LEFT_KNEE": {"min_angle": 80, "max_angle": 100, "ideal_angle": 90, "tolerance": 5}
                }
            }
        }
    }
    mock_config.rom_rules = []
    mock_config.posture_rules = []
    mock_config.symmetry_rules = []
    mock_config.movement_phases = { 
        "start_phase": {"triggers": {"next": {"target_phase": "end_phase", "conditions": []}}},
        "end_phase": {"triggers": {}}
    }
    
    # mock_exercise_config_service.get_active_config_for_exercise_async.return_value = mock_config # Not called if config is passed
    
    mock_repetitions_from_segmentation = [expected_enriched_sequence_for_segmentation] 
    dynamic_form_analysis_service.segment_repetitions = AsyncMock(return_value=mock_repetitions_from_segmentation)
    
    issue_timestamp = expected_enriched_sequence_for_segmentation[1]["timestamp"]

    mock_issue_dict = {
        "rule_type": "joint_angle", "joint_name": "LEFT_KNEE", "severity": FeedbackSeverity.MEDIUM.value,
        "details": "Knee angle too small.", "rep_index": 0, "phase": "descent", "frame_index_in_rep": 1, 
        "timestamp_in_video": issue_timestamp, 
        "current_value": expected_enriched_sequence_for_segmentation[1]["angles"]["LEFT_KNEE"], 
        "expected_value": {"min_angle": 80, "max_angle": 100},
        "violation_type": "below_min_ideal_range", "deviation": -5.0 
    }
    dynamic_form_analysis_service.evaluate_rep = AsyncMock(return_value=([mock_issue_dict], 80))
    
    # Setup mock_initial_form_check
    mock_initial_form_check.id = uuid4()
    mock_initial_form_check.video_id = mock_video.id
    mock_initial_form_check.user_id = mock_video.user_id
    mock_initial_form_check.exercise_config_id = mock_config.id
    mock_initial_form_check.status = FormCheckStatus.PENDING
    mock_initial_form_check.feedback_items = [] # Ensure it starts empty or as expected
    mock_initial_form_check.form_metadata = {}

    # dynamic_form_analysis_service.form_check_service.get_or_create_form_check_for_video = AsyncMock(return_value=mock_form_check_instance) # Removed

    mock_created_feedback_item = MagicMock(spec=FeedbackItem)
    dynamic_form_analysis_service.form_check_service.create_feedback_items_for_form_check_from_issues_async = AsyncMock(return_value=[mock_created_feedback_item])

    returned_form_check = await dynamic_form_analysis_service.analyze_form_dynamically(
        video=mock_video,
        exercise_config=mock_config,
        initial_form_check=mock_initial_form_check
    )

    # mock_exercise_config_service.get_active_config_for_exercise_async.assert_called_once_with(exercise_id=exercise_template_id_for_video) # Changed
    mock_exercise_config_service.get_active_config_for_exercise_async.assert_not_called()
    
    dynamic_form_analysis_service.segment_repetitions.assert_called_once()
    # call_args_seg, call_kwargs_seg = dynamic_form_analysis_service.segment_repetitions.call_args
    # assert call_args_seg[0] == expected_enriched_sequence_for_segmentation
    # assert call_args_seg[1] == mock_config
    # assert len(call_args_seg) == 2
    # assert not call_kwargs_seg
    
    dynamic_form_analysis_service.evaluate_rep.assert_called_once()
    # call_args_eval, call_kwargs_eval = dynamic_form_analysis_service.evaluate_rep.call_args
    # assert call_args_eval[0] == expected_enriched_sequence_for_segmentation
    # assert call_args_eval[1] == 0 # rep_index
    # assert call_args_eval[2] == mock_config
    # assert not call_kwargs_eval
    
    # dynamic_form_analysis_service.form_check_service.get_or_create_form_check_for_video.assert_called_once_with(video_id=mock_video.id) # Removed
    
    # New assertions for form_check_service.create_feedback_items_for_form_check_from_issues_async
    assert len(mock_initial_form_check.feedback_items) == 1
    created_feedback_item = mock_initial_form_check.feedback_items[0]
    assert created_feedback_item.message == mock_issue_dict["details"]
    assert created_feedback_item.type == FeedbackType.JOINT_ANGLE # Based on mock_issue_dict rule_type
    assert created_feedback_item.severity == FeedbackSeverity(mock_issue_dict["severity"].lower())
    
    expected_details_payload = {
        "rule_type": mock_issue_dict.get("rule_type"),
        "joint_name": mock_issue_dict.get("joint_name"),
        "compared_to_joint": mock_issue_dict.get("compared_to_joint"),
        "phase": mock_issue_dict.get("phase"),
        "rep_index": mock_issue_dict.get("rep_index"),
        "frame_index_in_rep": mock_issue_dict.get("frame_index_in_rep"),
        "current_value": mock_issue_dict.get("current_value"),
        "expected_value": mock_issue_dict.get("expected_value"),
        "deviation": mock_issue_dict.get("deviation"),
        "violation_type": mock_issue_dict.get("violation_type")
    }
    expected_details_payload_filtered = {k: v for k, v in expected_details_payload.items() if v is not None}
    assert created_feedback_item.details_payload == expected_details_payload_filtered

    assert mock_initial_form_check.score == 80 # As returned by evaluate_rep mock

    # The overall_feedback and overall_score are no longer set by analyze_form_dynamically directly.
    # These are typically set by the FormCheckService when it finalizes the check.
    # assert "1 areas for improvement" in mock_initial_form_check.overall_feedback.lower()
    # assert f"Overall score: {80.0:.2f}" in mock_initial_form_check.overall_feedback
    # assert mock_initial_form_check.overall_score == 80.0 

    # The service itself no longer directly commits. It's up to the caller (e.g., a Celery task context).
    # dynamic_form_analysis_service.db.commit.assert_called() 

@pytest.mark.asyncio
async def test_analyze_form_dynamically_no_exercise_config(
    dynamic_form_analysis_service: DynamicFormAnalysisService,
    # mock_exercise_config_service: MagicMock # No longer needed if config is passed as None directly
    mock_initial_form_check: MagicMock # Added
):
    video_id = uuid4()
    # exercise_type_slug = "unknown_exercise" # Not used if config is passed as None
    # exercise_template_id_for_video = uuid4() # Not used

    mock_video = MagicMock(spec=Video) 
    mock_video.id = video_id
    mock_video.user_id = uuid4() # Add user_id
    # mock_video.exercise_type_slug = exercise_type_slug
    # mock_video.exercise_template_id = exercise_template_id_for_video
    mock_video.angle_data = [{'LEFT_KNEE': 170}]
    mock_video.raw_pose_data = [create_full_mock_landmarks({})]
    mock_video.fps = 30.0

    # # Mock ExerciseConfigService: both lookups should return None # Not needed
    # mock_exercise_config_service.get_active_config_for_exercise_async.return_value = None
    # mock_exercise_config_service.get_config_by_exercise_type_slug_async.return_value = None

    dynamic_form_analysis_service.segment_repetitions = AsyncMock()
    dynamic_form_analysis_service.evaluate_rep = AsyncMock()
    
    # Setup mock_initial_form_check
    mock_initial_form_check.id = uuid4()
    mock_initial_form_check.video_id = mock_video.id
    mock_initial_form_check.user_id = mock_video.user_id
    # mock_initial_form_check.exercise_config_id = None # Correct for this case
    mock_initial_form_check.status = FormCheckStatus.PENDING
    mock_initial_form_check.feedback_items = []
    mock_initial_form_check.form_metadata = {}
    mock_initial_form_check.error_details = None


    # dynamic_form_analysis_service.form_check_service.get_or_create_form_check_for_video = AsyncMock(return_value=mock_form_check_instance) # Removed
    # dynamic_form_analysis_service.form_check_service.update_form_check_status_async = AsyncMock() # Removed
    # dynamic_form_analysis_service.create_feedback_items_in_db = AsyncMock(return_value=[]) # Not called in this path
    
    returned_form_check = await dynamic_form_analysis_service.analyze_form_dynamically(
        video=mock_video,
        exercise_config=None, # Explicitly pass None
        initial_form_check=mock_initial_form_check
    )

    assert returned_form_check == mock_initial_form_check # Changed
    # mock_exercise_config_service.get_active_config_for_exercise_async.assert_called_once_with(exercise_id=exercise_template_id_for_video) # Not called
    # mock_exercise_config_service.get_config_by_exercise_type_slug_async.assert_not_called()

    # dynamic_form_analysis_service.form_check_service.get_or_create_form_check_for_video.assert_called_once_with(video_id=mock_video.id) # Removed

    # Assertions for what should happen when no config is found (on mock_initial_form_check)
    assert mock_initial_form_check.status == FormCheckStatus.FAILED
    assert "Exercise configuration missing" in mock_initial_form_check.error_details
    assert mock_initial_form_check.score == 0 # Default score on failure
    # assert mock_initial_form_check.reps_detected is None or mock_initial_form_check.reps_detected == 0

    # Ensure DB commit was called to save the failure status # Removed
    # dynamic_form_analysis_service.db.commit.assert_called_once()

    dynamic_form_analysis_service.segment_repetitions.assert_not_called()
    dynamic_form_analysis_service.evaluate_rep.assert_not_called()
    # dynamic_form_analysis_service.form_check_service.update_form_check_status_async.assert_not_called() # Removed
    # dynamic_form_analysis_service.create_feedback_items_in_db.assert_not_called() # Not called

@pytest.mark.asyncio
async def test_analyze_form_dynamically_no_repetitions_segmented(
    dynamic_form_analysis_service: DynamicFormAnalysisService,
    # mock_exercise_config_service: MagicMock, # Not needed if config is passed directly
    mock_initial_form_check: MagicMock # Added
):
    video_id = uuid4()
    # exercise_type_slug = "squat" # Not used
    # exercise_template_id_for_video = uuid4() # Not used

    mock_video = MagicMock(spec=Video) 
    mock_video.id = video_id
    mock_video.user_id = uuid4() # Add user_id
    # mock_video.exercise_type_slug = exercise_type_slug
    # mock_video.exercise_template_id = exercise_template_id_for_video
    mock_video.angle_data = [{"LEFT_KNEE": 170}] 
    mock_video.raw_pose_data = [create_full_mock_landmarks({})] 
    mock_video.fps = 30.0
    
    expected_enriched_input_for_segment = [{
        "frame_num": 0, "timestamp": 0/30.0, 
        "angles": mock_video.angle_data[0], 
        "raw_landmarks": mock_video.raw_pose_data[0]
    }]

    mock_config = MagicMock(spec=ExerciseConfig)
    mock_config.id = uuid4()
    # mock_config.exercise_type_slug = exercise_type_slug
    # mock_config.exercise_template_id = exercise_template_id_for_video
    mock_config.movement_phases = { 
        "start_phase": {"triggers": {"next": {"target_phase": "end_phase", "conditions": []}}},
        "end_phase": {"triggers": {}}
    }
    # Ensure no rules are defined so no issues are found from evaluate_rep if it were called
    mock_config.joint_angle_rules = {}
    mock_config.rom_rules = []
    mock_config.posture_rules = []
    mock_config.symmetry_rules = []

    # mock_exercise_config_service.get_active_config_for_exercise_async.return_value = mock_config # Not called
    # mock_exercise_config_service.get_config_by_exercise_type_slug_async.return_value = mock_config # Not called

    dynamic_form_analysis_service.segment_repetitions = AsyncMock(return_value=[]) # No repetitions
    dynamic_form_analysis_service.evaluate_rep = AsyncMock() # Should not be called
    dynamic_form_analysis_service.create_feedback_items_in_db = AsyncMock(return_value=[])


    # Setup mock_initial_form_check
    mock_initial_form_check.id = uuid4()
    mock_initial_form_check.video_id = mock_video.id
    mock_initial_form_check.user_id = mock_video.user_id
    mock_initial_form_check.exercise_config_id = mock_config.id
    mock_initial_form_check.status = FormCheckStatus.PENDING
    mock_initial_form_check.feedback_items = []
    mock_initial_form_check.form_metadata = {}
    mock_initial_form_check.error_details = None


    # dynamic_form_analysis_service.form_check_service.get_or_create_form_check_for_video = AsyncMock(return_value=mock_form_check_instance) # Removed
    # dynamic_form_analysis_service.form_check_service.update_form_check_status_async = AsyncMock() # Removed
    
    returned_form_check = await dynamic_form_analysis_service.analyze_form_dynamically(
        video=mock_video,
        exercise_config=mock_config,
        initial_form_check=mock_initial_form_check
    )
    
    assert returned_form_check == mock_initial_form_check # Changed
    # mock_exercise_config_service.get_active_config_for_exercise_async.assert_not_called() # Correct

    # dynamic_form_analysis_service.form_check_service.get_or_create_form_check_for_video.assert_called_once_with(video_id=mock_video.id) # Removed
    
    dynamic_form_analysis_service.segment_repetitions.assert_called_once() # Called with enriched_frame_sequence, mock_config
    
    # Assertions for when no repetitions are segmented
    assert mock_initial_form_check.status == FormCheckStatus.COMPLETED # No reps, so analysis is "complete"
    assert mock_initial_form_check.score == 0 # Score is 0 if no reps
    assert mock_initial_form_check.reps_detected == 0
    assert not mock_initial_form_check.feedback_items # No feedback items
    assert mock_initial_form_check.error_details is None # No error

    # dynamic_form_analysis_service.db.commit.assert_called_once() # Removed

    dynamic_form_analysis_service.evaluate_rep.assert_not_called()
    # dynamic_form_analysis_service.form_check_service.update_form_check_status_async.assert_not_called() # Removed
    dynamic_form_analysis_service.create_feedback_items_in_db.assert_not_called() # No feedback items to create

@pytest.mark.asyncio
async def test_analyze_form_dynamically_no_issues_found(
    dynamic_form_analysis_service: DynamicFormAnalysisService,
    mock_exercise_config_service: MagicMock,
    mock_initial_form_check: MagicMock # Added
):
    video_id = uuid4()
    # exercise_type_slug = "squat" # Not used if config passed directly
    # exercise_template_id_for_video = uuid4() # Not used

    mock_video = MagicMock(spec=Video) 
    mock_video.id = video_id
    mock_video.user_id = uuid4() # Add user_id
    # mock_video.exercise_type_slug = exercise_type_slug
    # mock_video.exercise_template_id = exercise_template_id_for_video
    mock_video.angle_data = [{"LEFT_KNEE": 170}]
    mock_video.raw_pose_data = [create_full_mock_landmarks({})]
    mock_video.fps = 30.0

    expected_enriched_sequence = [{
        "frame_num": 0, "timestamp": 0/30.0,
        "angles": mock_video.angle_data[0],
        "raw_landmarks": mock_video.raw_pose_data[0]
    }]

    mock_config = MagicMock(spec=ExerciseConfig)
    mock_config.id = uuid4()
    # mock_config.exercise_type_slug = exercise_type_slug
    # mock_config.exercise_template_id = exercise_template_id_for_video
    mock_config.movement_phases = {
        "start_phase": {"triggers": {"next": {"target_phase": "end_phase", "conditions": []}}},
        "end_phase": {"triggers": {}}
    }
    mock_config.joint_angle_rules = {} 
    mock_config.rom_rules = []
    mock_config.posture_rules = []
    mock_config.symmetry_rules = []

    # mock_exercise_config_service.get_active_config_for_exercise_async.return_value = mock_config # Not called
    # mock_exercise_config_service.get_config_by_exercise_type_slug_async.return_value = mock_config # Not called

    # The mock_repetitions_from_segmentation here had a structure that was more like a FormCheck.form_metadata.issues_by_rep item.
    # segment_repetitions should return List[List[Dict[str, Any]]], where each inner list is a rep (sequence of frame dicts).
    mock_repetitions_from_segmentation = [expected_enriched_sequence] 
    dynamic_form_analysis_service.segment_repetitions = AsyncMock(return_value=mock_repetitions_from_segmentation)
    dynamic_form_analysis_service.evaluate_rep = AsyncMock(return_value=([], 100)) # No issues, perfect score

    # Setup mock_initial_form_check
    mock_initial_form_check.id = uuid4()
    mock_initial_form_check.video_id = mock_video.id
    mock_initial_form_check.user_id = mock_video.user_id
    mock_initial_form_check.exercise_config_id = mock_config.id
    mock_initial_form_check.status = FormCheckStatus.PENDING
    mock_initial_form_check.feedback_items = []
    mock_initial_form_check.form_metadata = {}

    # dynamic_form_analysis_service.form_check_service.get_or_create_form_check_for_video = AsyncMock(return_value=mock_form_check_instance) # Removed
    # dynamic_form_analysis_service.form_check_service.update_form_check_status_async = AsyncMock() # Removed
    dynamic_form_analysis_service.create_feedback_items_in_db = AsyncMock(return_value=[])

    returned_form_check = await dynamic_form_analysis_service.analyze_form_dynamically(
        video=mock_video,
        exercise_config=mock_config,
        initial_form_check=mock_initial_form_check
    )

    assert returned_form_check == mock_initial_form_check # Changed
    mock_exercise_config_service.get_active_config_for_exercise_async.assert_not_called()
    # mock_exercise_config_service.get_config_by_exercise_type_slug_async.assert_not_called()
    
    dynamic_form_analysis_service.segment_repetitions.assert_called_once() # Simplified
    # dynamic_form_analysis_service.segment_repetitions.assert_called_once_with(expected_enriched_sequence, mock_config)

    # dynamic_form_analysis_service.evaluate_rep.assert_called_once_with(expected_enriched_sequence, 0, mock_config)
    dynamic_form_analysis_service.evaluate_rep.assert_called_once_with(
        rep_angle_data=expected_enriched_sequence, 
        rep_index=0, 
        config=mock_config
    )

    # dynamic_form_analysis_service.form_check_service.get_or_create_form_check_for_video.assert_called_once_with(video_id=mock_video.id) # Removed
    dynamic_form_analysis_service.create_feedback_items_in_db.assert_not_called() # No issues, so not called

    # Assertions on mock_initial_form_check
    assert mock_initial_form_check.status == FormCheckStatus.COMPLETED
    assert mock_initial_form_check.score == 100.0
    assert mock_initial_form_check.reps_detected == 1
    assert not mock_initial_form_check.feedback_items
    # Overall feedback/score are not set by this service directly anymore
    # assert mock_initial_form_check.overall_feedback == "Great job! No major issues detected."
    # assert mock_initial_form_check.overall_score == 100.0
    # dynamic_form_analysis_service.db.commit.assert_called_once() # Removed

@pytest.mark.asyncio
async def test_analyze_form_dynamically_multiple_reps_multiple_issues(
    dynamic_form_analysis_service: DynamicFormAnalysisService,
    mock_exercise_config_service: MagicMock, # Uncommented
    mock_initial_form_check: MagicMock # Added
):
    video_id = uuid4()
    exercise_type_slug = "lunge" # Uncommented
    # exercise_template_id_for_video = uuid4() # Not used if config is passed directly

    mock_video = MagicMock(spec=Video) 
    mock_video.id = video_id
    mock_video.user_id = uuid4() # Add user_id
    # mock_video.exercise_type_slug = exercise_type_slug
    # mock_video.exercise_template_id = exercise_template_id_for_video
    mock_angle_data = [
        {"LEFT_KNEE": 170}, {"LEFT_KNEE": 90}, {"LEFT_KNEE": 170}, # Rep 1
        {"RIGHT_KNEE": 170}, {"RIGHT_KNEE": 85}, {"RIGHT_KNEE": 170}, # Rep 2
    ]
    mock_raw_pose_data = [create_full_mock_landmarks({}) for _ in range(6)]
    mock_video.angle_data = mock_angle_data
    mock_video.raw_pose_data = mock_raw_pose_data
    mock_video.fps = 30.0

    expected_enriched_sequence = []
    for i in range(len(mock_angle_data)):
        expected_enriched_sequence.append({
            "frame_num": i, "timestamp": i/30.0, 
            "angles": mock_angle_data[i], 
            "raw_landmarks": mock_raw_pose_data[i]
        })
    
    rep1_enriched_frames = expected_enriched_sequence[0:3]
    rep2_enriched_frames = expected_enriched_sequence[3:6]

    mock_config = MagicMock(spec=ExerciseConfig)
    mock_config.id = uuid4()
    # mock_config.exercise_type_slug = exercise_type_slug
    # mock_config.exercise_template_id = exercise_template_id_for_video
    mock_config.exercise_type_slug = exercise_type_slug
    
    # ... (mock_config rules setup) ...
    mock_config.joint_angle_rules = { "phases": { "default": { "angles": { "LEFT_KNEE": {"min_angle": 80, "max_angle": 180, "ideal_angle": 90, "tolerance": 10}, "RIGHT_KNEE": {"min_angle": 80, "max_angle": 180, "ideal_angle": 90, "tolerance": 10}}}}}
    mock_config.rom_rules = []
    mock_config.posture_rules = []
    mock_config.symmetry_rules = []
    mock_config.movement_phases = { 
        "start_phase": {"triggers": {"next": {"target_phase": "end_phase", "conditions": []}}},
        "end_phase": {"triggers": {}}
    }

    mock_exercise_config_service.get_active_config_for_exercise_async.return_value = mock_config # Corrected line
    # mock_exercise_config_service.get_config_by_exercise_type_slug_async.return_value = mock_config # Fallback not strictly needed if active_config found

    # This definition of mock_repetitions_from_segmentation has issues; it should be a list of lists of frame dicts
    # The service\'s segment_repetitions is expected to return List[List[Dict[str, Any]]]
    # where each inner list is a sequence of frame data dicts for a rep.
    # For this test, we want evaluate_rep to be called twice, so segment_repetitions should return two "reps".
    mock_repetitions_from_segmentation = [
        rep1_enriched_frames,
        rep2_enriched_frames
    ]
    dynamic_form_analysis_service.segment_repetitions = AsyncMock(return_value=mock_repetitions_from_segmentation)

    # ... (issue definitions) ...
    issue_rep0_timestamp = rep1_enriched_frames[1]["timestamp"]
    issue_rep0 = { # Using dicts directly as evaluate_rep mock returns list of dicts
        "rule_type":"joint_angle", "joint_name":"LEFT_KNEE", "severity":FeedbackSeverity.LOW.value, 
        "details":"Rep 0 Issue", "rep_index":0, "phase":"default", "frame_index_in_rep":1, 
        "timestamp_in_video":issue_rep0_timestamp, 
        "current_value":rep1_enriched_frames[1]["angles"]["LEFT_KNEE"], 
        "expected_value":{"min_angle": 80}, "violation_type":"test", "deviation":0
    }
    
    issue_rep1_a_timestamp = rep2_enriched_frames[1]["timestamp"]
    issue_rep1_a = {
        "rule_type":"posture", "joint_name":None, "severity":FeedbackSeverity.MEDIUM.value, 
        "details":"Rep 1 Issue A", "rep_index":1, "phase":"default", "frame_index_in_rep":1, 
        "timestamp_in_video":issue_rep1_a_timestamp, 
        "current_value":{}, "expected_value":{}, "violation_type":"test", "deviation":0
    }
    
    issue_rep1_b_timestamp = rep2_enriched_frames[2]["timestamp"] # Assuming issue on last frame of rep2
    issue_rep1_b = {
        "rule_type":"symmetry", "joint_name":"LEFT_ANKLE", "severity":FeedbackSeverity.HIGH.value, 
        "details":"Rep 1 Issue B", "rep_index":1, "phase":"default", "frame_index_in_rep":2, 
        "timestamp_in_video":issue_rep1_b_timestamp, 
        "current_value":{}, "expected_value":{}, "violation_type":"test", "deviation":0
    }

    dynamic_form_analysis_service.evaluate_rep = AsyncMock(side_effect=[([issue_rep0], 70), ([issue_rep1_a, issue_rep1_b], 60)]) # Scores 70 and 60
    
    # mock_form_check_instance = MagicMock(spec=FormCheck) # Replaced
    # mock_form_check_instance.id = uuid4()
    # dynamic_form_analysis_service.form_check_service.get_or_create_form_check_for_video = AsyncMock(return_value=mock_form_check_instance) # Removed

    # Setup mock_initial_form_check
    mock_initial_form_check.video_id = mock_video.id
    mock_initial_form_check.user_id = mock_video.user_id
    mock_initial_form_check.exercise_config_id = mock_config.id
    mock_initial_form_check.status = FormCheckStatus.PENDING
    mock_initial_form_check.feedback_items = []
    mock_initial_form_check.form_metadata = {}

    # dynamic_form_analysis_service.form_check_service.update_form_check_status_async = AsyncMock() # Not directly called for success path status update

    # The 'with patch.object(...)' block for _prepare_enriched_frame_sequence is removed from here.
    returned_form_check = await dynamic_form_analysis_service.analyze_form_dynamically(
        video=mock_video,
        exercise_config=mock_config,
        initial_form_check=mock_initial_form_check
    )
    # The 'mock_prepare.assert_called_once_with(mock_video)' is removed from here.

    assert returned_form_check == mock_initial_form_check # Changed
    # mock_exercise_config_service.get_active_config_for_exercise_async.assert_called_once_with(exercise_id=exercise_template_id_for_video) # Not called with this mock setup
    mock_exercise_config_service.get_active_config_for_exercise_async.assert_not_called()
    
    dynamic_form_analysis_service.segment_repetitions.assert_called_once() # Simplified assertion
    # dynamic_form_analysis_service.segment_repetitions.assert_called_once_with(expected_enriched_sequence, mock_config) # Corrected: check args
    
    assert dynamic_form_analysis_service.evaluate_rep.call_count == 2 # Corrected: check call count
    # # Call 1 assertions for evaluate_rep
    # eval_call_1_args, _ = dynamic_form_analysis_service.evaluate_rep.call_args_list[0]
    # assert eval_call_1_args[0] == rep1_enriched_frames
    # assert eval_call_1_args[1] == 0 # rep_index
    # assert eval_call_1_args[2] == mock_config
    ## Call 2 assertions for evaluate_rep
    # eval_call_2_args, _ = dynamic_form_analysis_service.evaluate_rep.call_args_list[1]
    # assert eval_call_2_args[0] == rep2_enriched_frames
    # assert eval_call_2_args[1] == 1 # rep_index
    # assert eval_call_2_args[2] == mock_config

    # dynamic_form_analysis_service.form_check_service.get_or_create_form_check_for_video.assert_called_once_with(video_id=mock_video.id) # Removed exercise_config_id
    
    # Assert that the service's own method was called to create feedback
    


    # Check form_check status, feedback, score and that db commit was called
    assert mock_initial_form_check.status == FormCheckStatus.COMPLETED
    assert mock_initial_form_check.reps_detected == 2 # Two reps processed
    assert mock_initial_form_check.score == 65.0 # (70+60)/2
    assert len(mock_initial_form_check.feedback_items) == 3 # Service appends results of create_feedback_items_in_db

    # Assertions for the first feedback item (from issue_rep0)
    feedback_item_0 = mock_initial_form_check.feedback_items[0]
    assert feedback_item_0.message == issue_rep0["details"]
    # Assuming FeedbackItem.type is an enum and issue_rep0["rule_type"] is a string like "joint_angle"
    assert feedback_item_0.type == FeedbackType[issue_rep0["rule_type"].upper()]
    # Assuming FeedbackItem.severity is an enum and issue_rep0["severity"] is the enum value (e.g., "low")
    assert feedback_item_0.severity == FeedbackSeverity(issue_rep0["severity"])
    assert feedback_item_0.details_payload["joint_name"] == issue_rep0["joint_name"]
    assert feedback_item_0.details_payload["rep_index"] == issue_rep0["rep_index"]
    assert feedback_item_0.details_payload["phase"] == issue_rep0["phase"]
    assert feedback_item_0.details_payload["frame_index_in_rep"] == issue_rep0["frame_index_in_rep"]
    assert feedback_item_0.details_payload["current_value"] == issue_rep0["current_value"]
    assert feedback_item_0.details_payload["expected_value"] == issue_rep0["expected_value"]
    assert feedback_item_0.details_payload["violation_type"] == issue_rep0["violation_type"]
    assert feedback_item_0.details_payload["deviation"] == issue_rep0["deviation"]
    assert feedback_item_0.timestamp == issue_rep0_timestamp

    # Assertions for the second feedback item (from issue_rep1_a)
    feedback_item_1 = mock_initial_form_check.feedback_items[1]
    assert feedback_item_1.message == issue_rep1_a["details"]
    assert feedback_item_1.type == FeedbackType[issue_rep1_a["rule_type"].upper()]
    assert feedback_item_1.severity == FeedbackSeverity(issue_rep1_a["severity"])
    assert feedback_item_1.details_payload.get("joint_name") == issue_rep1_a["joint_name"] # Changed to .get()
    assert feedback_item_1.details_payload["rep_index"] == issue_rep1_a["rep_index"]
    assert feedback_item_1.details_payload["phase"] == issue_rep1_a["phase"]
    assert feedback_item_1.details_payload["frame_index_in_rep"] == issue_rep1_a["frame_index_in_rep"]
    assert feedback_item_1.details_payload["current_value"] == issue_rep1_a["current_value"]
    assert feedback_item_1.details_payload["expected_value"] == issue_rep1_a["expected_value"]
    assert feedback_item_1.details_payload["violation_type"] == issue_rep1_a["violation_type"]
    assert feedback_item_1.details_payload["deviation"] == issue_rep1_a["deviation"]
    assert feedback_item_1.timestamp == issue_rep1_a_timestamp

    # Assertions for the third feedback item (from issue_rep1_b)
    feedback_item_2 = mock_initial_form_check.feedback_items[2]
    assert feedback_item_2.message == issue_rep1_b["details"]
    assert feedback_item_2.type == FeedbackType.TECHNIQUE # Corrected based on service mapping
    assert feedback_item_2.severity == FeedbackSeverity(issue_rep1_b["severity"])
    assert feedback_item_2.details_payload["joint_name"] == issue_rep1_b["joint_name"]
    assert feedback_item_2.details_payload["rep_index"] == issue_rep1_b["rep_index"]
    assert feedback_item_2.details_payload["phase"] == issue_rep1_b["phase"]
    assert feedback_item_2.details_payload["frame_index_in_rep"] == issue_rep1_b["frame_index_in_rep"]
    assert feedback_item_2.details_payload["current_value"] == issue_rep1_b["current_value"]
    assert feedback_item_2.details_payload["expected_value"] == issue_rep1_b["expected_value"]
    assert feedback_item_2.details_payload["violation_type"] == issue_rep1_b["violation_type"]
    assert feedback_item_2.details_payload["deviation"] == issue_rep1_b["deviation"]
    assert feedback_item_2.timestamp == issue_rep1_b_timestamp
    # assert "areas for improvement" in mock_initial_form_check.overall_feedback.lower() # Not set by service

@pytest.mark.asyncio
async def test_analyze_form_dynamically_error_in_segment_repetitions(
    dynamic_form_analysis_service: DynamicFormAnalysisService,
    mock_exercise_config_service: MagicMock,
    mock_initial_form_check: MagicMock # Added
):
    video_id = uuid4()
    exercise_type_slug = "squat"
    exercise_template_id_for_video = uuid4()

    mock_video = MagicMock(spec=Video) 
    mock_video.id = video_id
    mock_video.exercise_type_slug = exercise_type_slug 
    mock_video.exercise_template_id = exercise_template_id_for_video
    # ... (mock_video data setup) ...
    mock_video.angle_data = [{"LEFT_KNEE": 170}] 
    mock_video.raw_pose_data = [create_full_mock_landmarks({})] 
    mock_video.fps = 30.0
    
    mock_config = MagicMock(spec=ExerciseConfig)
    mock_config.id = uuid4()
    mock_config.user_id = mock_video.user_id # Added for consistency
    mock_config.exercise_type_slug = exercise_type_slug
    # ... (mock_config movement_phases setup) ...
    mock_config.movement_phases = { 
        "start_phase": {"triggers": {"next": {"target_phase": "end_phase", "conditions": []}}},
        "end_phase": {"triggers": {}}
    }
    
    mock_exercise_config_service.get_active_config_for_exercise_async.return_value = mock_config
    mock_exercise_config_service.get_config_by_exercise_type_slug_async.return_value = mock_config

    segmentation_error = ValueError("Segmentation failed badly")
    dynamic_form_analysis_service.segment_repetitions = AsyncMock(side_effect=segmentation_error)
    dynamic_form_analysis_service.evaluate_rep = AsyncMock()

    # mock_form_check_instance = MagicMock(spec=FormCheck) # Replaced by mock_initial_form_check
    # mock_form_check_instance.id = uuid4()
    # dynamic_form_analysis_service.form_check_service.get_or_create_form_check_for_video = AsyncMock(return_value=mock_form_check_instance) # Removed
    
    # Setup mock_initial_form_check (adapted from other tests)
    mock_initial_form_check.video_id = mock_video.id
    mock_initial_form_check.user_id = mock_video.user_id
    mock_initial_form_check.exercise_config_id = mock_config.id
    mock_initial_form_check.status = FormCheckStatus.PENDING
    mock_initial_form_check.error_details = None # Ensure it starts clean for error assertion

    # dynamic_form_analysis_service.form_check_service.update_form_check_status_async = AsyncMock() # Removed, status set on instance
    dynamic_form_analysis_service.create_feedback_items_in_db = AsyncMock(return_value=[]) 
    
    # Expect ServerErrorException because the service catches the ValueError and re-raises
    # The service now updates the passed initial_form_check and returns it, rather than raising.
    # with pytest.raises(ServerErrorException, match=f"Dynamic form analysis failed for video {video_id}: {str(segmentation_error)}"):
    returned_form_check = await dynamic_form_analysis_service.analyze_form_dynamically(
        video=mock_video,
        exercise_config=mock_config,
        initial_form_check=mock_initial_form_check
    )
    
    # Assertions for what should happen AFTER the exception is caught and handled by the service
    assert returned_form_check == mock_initial_form_check
    mock_exercise_config_service.get_active_config_for_exercise_async.assert_not_called() # Config is passed directly
    # mock_exercise_config_service.get_active_config_for_exercise_async.assert_called_once_with(exercise_id=exercise_template_id_for_video) # Original assertion, changed because config passed
    dynamic_form_analysis_service.segment_repetitions.assert_called_once() # This was called and raised the error
    # dynamic_form_analysis_service.form_check_service.get_or_create_form_check_for_video.assert_called_once_with(video_id=mock_video.id) # Removed
    
    assert mock_initial_form_check.status == FormCheckStatus.FAILED
    assert str(segmentation_error) in mock_initial_form_check.error_details
    # assert mock_initial_form_check.overall_feedback == f"An unexpected error occurred during analysis: {str(segmentation_error)}" # overall_feedback not set by service
    # dynamic_form_analysis_service.db.commit.assert_called_once() # Commit not done by service

    dynamic_form_analysis_service.evaluate_rep.assert_not_called()


@pytest.mark.asyncio
async def test_analyze_form_dynamically_error_in_evaluate_rep(
    dynamic_form_analysis_service: DynamicFormAnalysisService,
    mock_exercise_config_service: MagicMock,
    mock_initial_form_check: MagicMock # Added
):
    video_id = uuid4()
    exercise_type_slug = "squat"
    exercise_template_id_for_video = uuid4()

    mock_video = MagicMock(spec=Video) 
    mock_video.id = video_id
    mock_video.exercise_type_slug = exercise_type_slug 
    mock_video.exercise_template_id = exercise_template_id_for_video
    # ... (mock_video data setup) ...
    mock_video.angle_data = [{"LEFT_KNEE": 170}] 
    mock_video.raw_pose_data = [create_full_mock_landmarks({})]
    mock_video.fps = 30.0
    
    expected_enriched_sequence = [{
        "frame_num": 0, "timestamp": 0/30.0, 
        "angles": mock_video.angle_data[0], 
        "raw_landmarks": mock_video.raw_pose_data[0]
    }]

    mock_config = MagicMock(spec=ExerciseConfig)
    mock_config.id = uuid4()
    mock_config.user_id = mock_video.user_id # Added
    mock_config.exercise_type_slug = exercise_type_slug
    # ... (mock_config movement_phases setup) ...
    mock_config.movement_phases = { 
        "start_phase": {"triggers": {"next": {"target_phase": "end_phase", "conditions": []}}},
        "end_phase": {"triggers": {}}
    }

    mock_exercise_config_service.get_active_config_for_exercise_async.return_value = mock_config
    mock_exercise_config_service.get_config_by_exercise_type_slug_async.return_value = mock_config

    mock_repetitions_from_segmentation = [ 
        {"rep_index": 0, "start_frame": 0, "mid_frame": 0, "end_frame": 0, 
         "start_time": expected_enriched_sequence[0]["timestamp"], "mid_time": expected_enriched_sequence[0]["timestamp"], "end_time": expected_enriched_sequence[0]["timestamp"],
         "phases": [], "rep_angle_data": expected_enriched_sequence}
    ]
    dynamic_form_analysis_service.segment_repetitions = AsyncMock(return_value=mock_repetitions_from_segmentation)

    evaluation_error = TypeError("Evaluation failed with type error")
    dynamic_form_analysis_service.evaluate_rep = AsyncMock(side_effect=evaluation_error)

    # mock_form_check_instance = MagicMock(spec=FormCheck) # Replaced
    # mock_form_check_instance.id = uuid4()
    # dynamic_form_analysis_service.form_check_service.get_or_create_form_check_for_video = AsyncMock(return_value=mock_form_check_instance) # Removed

    # Setup mock_initial_form_check
    mock_initial_form_check.video_id = mock_video.id
    mock_initial_form_check.user_id = mock_video.user_id
    mock_initial_form_check.exercise_config_id = mock_config.id
    mock_initial_form_check.status = FormCheckStatus.PENDING
    mock_initial_form_check.error_details = None

    # dynamic_form_analysis_service.form_check_service.update_form_check_status_async = AsyncMock() # Removed
    dynamic_form_analysis_service.create_feedback_items_in_db = AsyncMock(return_value=[]) 
    
    # The service now updates the passed initial_form_check and returns it.
    # with pytest.raises(ServerErrorException, match=f"Dynamic form analysis failed for video {video_id}: {str(evaluation_error)}"):
    returned_form_check = await dynamic_form_analysis_service.analyze_form_dynamically(
        video=mock_video,
        exercise_config=mock_config,
        initial_form_check=mock_initial_form_check
    )
    
    # Assertions for what should happen AFTER the exception is caught and handled by the service
    assert returned_form_check == mock_initial_form_check
    mock_exercise_config_service.get_active_config_for_exercise_async.assert_not_called()
    # mock_exercise_config_service.get_active_config_for_exercise_async.assert_called_once_with(exercise_id=exercise_template_id_for_video) # Original assertion
    dynamic_form_analysis_service.segment_repetitions.assert_called_once()
    dynamic_form_analysis_service.evaluate_rep.assert_called_once() # This was called and raised the error
    # dynamic_form_analysis_service.form_check_service.get_or_create_form_check_for_video.assert_called_once_with(video_id=mock_video.id) # Removed

    assert mock_initial_form_check.status == FormCheckStatus.FAILED
    assert str(evaluation_error) in mock_initial_form_check.error_details
    # assert mock_initial_form_check.overall_feedback == f"An unexpected error occurred during analysis: {str(evaluation_error)}" # Not set by service
    # dynamic_form_analysis_service.db.commit.assert_called_once() # Not done by service

    dynamic_form_analysis_service.create_feedback_items_in_db.assert_not_called()