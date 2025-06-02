import pytest
from typing import List, Dict, Any
from unittest.mock import AsyncMock

from app.services.dynamic_form_analysis_service import DynamicFormAnalysisService
from app.models.exercise_config import ExerciseConfig
from app.models.form_check import FormCheck, FeedbackItem
from app.models.enums import FeedbackSeverity, FeedbackType


# --- Tests for evaluate_rep ---
@pytest.mark.asyncio
async def test_evaluate_rep_no_errors(
    dynamic_form_analysis_service: DynamicFormAnalysisService,
    sample_angle_data_one_rep: List[Dict[str, Any]],
    sample_squat_config: ExerciseConfig,
    sample_form_check_model: FormCheck
):
    """Test evaluating a single repetition with no expected errors."""
    feedback_items, score = await dynamic_form_analysis_service.evaluate_rep(
        rep_angle_data=sample_angle_data_one_rep,
        rep_index=0,
        config=sample_squat_config,
    )
    assert not feedback_items, "Expected no feedback items for a perfect rep."
    assert score == 100.0, "Expected full score for a perfect rep."

@pytest.mark.asyncio
async def test_evaluate_rep_one_good_rep_no_errors(
    dynamic_form_analysis_service: DynamicFormAnalysisService,
    sample_angle_data_one_good_rep: List[Dict[str, Any]],
    sample_squat_config_fsm: ExerciseConfig,
    sample_form_check_model: FormCheck
):
    """Test evaluate_rep with one good rep, expecting no errors."""
    
    # Manually determine phases for sample_angle_data_one_good_rep based on sample_squat_config_fsm
    # This replicates the logic of how segment_repetitions would assign phases.
    # Phases for sample_angle_data_one_good_rep with sample_squat_config_fsm:
    # Frames 0-1: start_phase
    # Frames 2-3: descent_phase (leftHip < 160)
    # Frames 4-5: bottom_phase (leftKnee < 90)
    # Frames 6-8: ascent_phase (leftKnee > 95)
    # Frames 9-10: start_phase (leftHip > 170)

    phases = (
        ['start_phase'] * 2 +
        ['descent_phase'] * 2 +
        ['bottom_phase'] * 2 +
        ['ascent_phase'] * 3 +
        ['start_phase'] * 2
    )

    augmented_rep_data = []
    for i, frame in enumerate(sample_angle_data_one_good_rep):
        if i < len(phases): # Ensure we don't go out of bounds if data/phases mismatch
            augmented_rep_data.append({**frame, 'phase_context': phases[i]})
        else: # Should not happen if phases list is correct for the data
            augmented_rep_data.append({**frame, 'phase_context': 'unknown'}) 


    feedback_items, score = await dynamic_form_analysis_service.evaluate_rep(
        rep_angle_data=augmented_rep_data,
        rep_index=0,
        config=sample_squat_config_fsm,
    )
    assert feedback_items, f"Expected feedback items for this rep based on config. Got none."
    assert score < 100.0, "Score should be less than 100 for a rep with ideal range deviations."
    # Add more specific assertions if needed, e.g., checking for specific violation types
    # Example: Check for 'above_ideal_range' for leftKnee in descent_phase (frame 2)
    assert any(
        item.get("joint_name") == "leftKnee" and
        item.get("phase") == "descent_phase" and
        item.get("violation_type") == "above_ideal_range" and
        item.get("frame_index_in_rep") == 2
        for item in feedback_items
    ), "Expected 'above_ideal_range' for leftKnee in descent_phase (frame 2)"

    # Example: Check for 'below_ideal_range' for leftKnee in ascent_phase (frame 6)
    assert any(
        item.get("joint_name") == "leftKnee" and
        item.get("phase") == "ascent_phase" and
        item.get("violation_type") == "below_ideal_range" and
        item.get("frame_index_in_rep") == 6
        for item in feedback_items
    ), "Expected 'below_ideal_range' for leftKnee in ascent_phase (frame 6)"


@pytest.mark.asyncio
async def test_evaluate_rep_with_errors(
    dynamic_form_analysis_service: DynamicFormAnalysisService,
    sample_angle_data_with_errors: List[Dict[str, Any]],
    sample_squat_config: ExerciseConfig,
    sample_form_check_model: FormCheck
):
    """Test evaluating a single repetition with expected errors."""
    
    # Phases for sample_angle_data_with_errors with sample_squat_config:
    # Frame 0 (lk: 175): start_phase
    # Frame 1 (lk: 140): descent_phase (140 < 150 from start_phase next)
    # Frame 2 (lk: 110): descent_phase (110 not < 95 for ascent, 110 not > 160 for start from descent_phase triggers)
    # Frame 3 (lk: 140): descent_phase (140 not < 95 for ascent, 140 not > 160 for start from descent_phase triggers)
    # Frame 4 (lk: 175): start_phase (175 > 160 from descent_phase prev trigger)
    phases = ['start_phase', 'descent_phase', 'descent_phase', 'descent_phase', 'start_phase']
    augmented_rep_data = [{**frame, 'phase_context': phases[i]} for i, frame in enumerate(sample_angle_data_with_errors)]

    feedback_items, score = await dynamic_form_analysis_service.evaluate_rep(
        rep_angle_data=augmented_rep_data,
        rep_index=0,
        config=sample_squat_config,
    )
    # assert feedback_items, "Expected feedback items for a rep with errors."
    # Based on sample_angle_data_with_errors, knee angle is 110 in descent, config expects 80-100.
    # So, it's above max for descent_phase.
    expected_violation_found = any(
        item.get("joint_name") == "leftKnee" and 
        item.get("phase") == "descent_phase" and 
        item.get("violation_type") == "above_max" and
        item.get("frame_index_in_rep") == 2 and # Be specific to the frame where 110.0 occurs
        item.get("current_value") == 110.0 and
        isinstance(item.get("expected_value"), dict) and item["expected_value"].get("max_angle") == 100.0
        for item in feedback_items
    )
    assert expected_violation_found, f"Expected specific knee angle violation (angle 110 > max 100 in descent) not found. Feedback: {feedback_items}"
    assert score < 100.0, "Score should be less than 100 due to errors."


@pytest.mark.asyncio
async def test_evaluate_rep_with_errors_fsm(
    dynamic_form_analysis_service: DynamicFormAnalysisService,
    sample_angle_data_two_reps_one_bad: List[Dict[str, Any]], # Using the 'bad rep' part
    sample_squat_config_fsm: ExerciseConfig,
    sample_form_check_model: FormCheck
):
    """
    Test evaluate_rep with a rep known to have issues based on FSM config.
    This test focuses on the second rep of 'sample_angle_data_two_reps_one_bad'
    which is designed to trigger back angle and symmetry issues.
    """
    # Extract the second rep (frames 6-11) which is the 'bad' one
    bad_rep_data_raw = sample_angle_data_two_reps_one_bad[6:12]

    # Phases for bad_rep_data_raw based on sample_squat_config_fsm:
    # F6 (orig_idx) LH:175 -> start
    # F7 (orig_idx) LH:150 -> descent
    # F8 (orig_idx) LK:85  -> bottom
    # F9 (orig_idx) LK:130 -> ascent
    # F10(orig_idx) LH:175 -> start
    # F11(orig_idx) LH:178 -> start
    phases = ['start_phase', 'descent_phase', 'bottom_phase', 'ascent_phase', 'start_phase', 'start_phase']
    
    augmented_bad_rep_data = [
        {**frame, 'phase_context': phases[i]} 
        for i, frame in enumerate(bad_rep_data_raw)
    ]

    feedback_items, score = await dynamic_form_analysis_service.evaluate_rep(
        rep_angle_data=augmented_bad_rep_data, # Use augmented data
        rep_index=1, # This is the second rep
        config=sample_squat_config_fsm,
    )

    assert feedback_items, "Expected feedback items for a rep with errors."
    assert score < 100.0, "Score should be less than 100 due to errors."

    # Enhanced assertions for posture violations
    posture_violations = [item for item in feedback_items if item.get("rule_type") == "posture"]
    assert posture_violations, "Expected at least one posture violation"
    
    torso_upright_violations = [
        item for item in posture_violations 
        if "Torso Upright" in item.get("violation_type", "")
    ]
    assert torso_upright_violations, "Expected torso upright violations"
    
    # Check specific posture violation details
    for violation in torso_upright_violations:
        assert "violation_type" in violation, "Posture violation should have violation_type"
        assert violation["violation_type"] == "Torso Upright (Vertical Check)_deviation", "Expected specific violation_type"
        assert "details" in violation, "Posture violation should have details"
        assert "current_value" in violation, "Posture violation should include current_value"
        assert "expected_value" in violation, "Posture violation should include expected_value"
        assert isinstance(violation["expected_value"], dict), "expected_value should be a dictionary"
        assert "phase" in violation, "Posture violation should include phase context"
        assert violation["phase"] in phases, f"Phase should be one of {phases}"
    
    # Enhanced assertions for symmetry violations
    symmetry_violations = [item for item in feedback_items if item.get("rule_type") == "symmetry"]
    assert symmetry_violations, "Expected at least one symmetry violation"
    
    knee_symmetry_violations = [
        item for item in symmetry_violations 
        if "leftKnee_rightKnee" in item.get("violation_type", "")
    ]
    assert knee_symmetry_violations, "Expected knee symmetry violations"
    
    # Check specific symmetry violation details
    for violation in knee_symmetry_violations:
        assert "violation_type" in violation, "Symmetry violation should have violation_type"
        assert violation["violation_type"] == "asymmetry_leftKnee_rightKnee", "Expected specific violation_type"
        assert "details" in violation, "Symmetry violation should have details"
        assert "current_value" in violation, "Symmetry violation should include current_value"
        assert isinstance(violation["current_value"], dict), "current_value in symmetry violation should be a dict"
        assert "joint_name" in violation, "Symmetry violation should include joint_name"
        assert violation["joint_name"] == "leftKnee", "Expected leftKnee as joint_name"
        assert "compared_to_joint" in violation, "Symmetry violation should include compared_to_joint"
        assert violation["compared_to_joint"] == "rightKnee", "Expected rightKnee as compared_to_joint"
        assert "difference" in violation["current_value"], "Symmetry violation current_value should include difference value"
        assert isinstance(violation["current_value"]["difference"], (int, float)), "difference should be numeric"
        assert "expected_value" in violation, "Symmetry violation should include expected_value"
        assert isinstance(violation["expected_value"], dict), "expected_value in symmetry violation should be a dict"
        assert "max_difference_degrees" in violation["expected_value"], "Symmetry violation expected_value should include max_difference_degrees as threshold"
        assert isinstance(violation["expected_value"]["max_difference_degrees"], (int, float)), "max_difference_degrees threshold should be numeric"
        assert "phase" in violation, "Symmetry violation should include phase context"
        assert violation["phase"] in phases, f"Phase should be one of {phases}"

@pytest.mark.asyncio
async def test_evaluate_rep_knee_rom_violations(
    dynamic_form_analysis_service: DynamicFormAnalysisService,
    sample_squat_config_fsm: ExerciseConfig, # Config with ROM rules
    sample_angle_data_knee_rom_violation_shallow: List[Dict[str, Any]],
    sample_angle_data_knee_rom_violation_incomplete_extension: List[Dict[str, Any]],
    sample_form_check_model: FormCheck
):
    """Test evaluate_rep for knee ROM violations (too shallow, incomplete extension)."""

    # --- Test 1: Squat too shallow ---
    # Phases for sample_angle_data_knee_rom_violation_shallow (7 frames) with sample_squat_config_fsm:
    # F0 LH:175 -> start
    # F1 LH:160 -> start (160 !< 160)
    # F2 LH:130 -> descent (130 < 160)
    # F3 LK:100 -> descent (100 !< 90)
    # F4 LK:120 -> ascent (120 > 95)
    # F5 LH:160 -> ascent (160 !> 170)
    # F6 LH:175 -> start (175 > 170)
    phases_shallow = ['start_phase', 'start_phase', 'descent_phase', 'descent_phase', 'ascent_phase', 'ascent_phase', 'start_phase']
    augmented_data_shallow = [
        {**frame, 'phase_context': phases_shallow[i]} 
        for i, frame in enumerate(sample_angle_data_knee_rom_violation_shallow)
    ]

    feedback_items_shallow, score_shallow = await dynamic_form_analysis_service.evaluate_rep(
        rep_angle_data=augmented_data_shallow,
        rep_index=0,
        config=sample_squat_config_fsm,
    )
    assert feedback_items_shallow, "Expected feedback for shallow squat (ROM)."
    assert any(
        item.get("rule_type") == "rom" and item.get("violation_type") == "failed_to_reach_min_rom"
        for item in feedback_items_shallow
    ), f"Expected ROM violation (failed_to_reach_min_rom) for shallow squat. Got: {feedback_items_shallow}"
    assert score_shallow < 100.0, "Score should be less than perfect for shallow squat."

    # Test 2: Incomplete extension at the top
    # Phases for sample_angle_data_knee_rom_violation_incomplete_extension (5 frames) with sample_squat_config_fsm:
    # Assuming rep starts mid-movement, or segmenter provides initial phase context.
    # F0 LH:150 -> descent (e.g. coming from start: 150 < 160)
    # F1 LH:130 -> descent (no trigger)
    # F2 LK:80  -> bottom (80 < 90)
    # F3 LK:120 -> ascent (120 > 95)
    # F4 LH:150 -> ascent (150 !> 170)
    phases_incomplete = ['descent_phase', 'descent_phase', 'bottom_phase', 'ascent_phase', 'ascent_phase']
    augmented_data_incomplete = [
        {**frame, 'phase_context': phases_incomplete[i]} 
        for i, frame in enumerate(sample_angle_data_knee_rom_violation_incomplete_extension)
    ]

    feedback_items_incomplete, score_incomplete = await dynamic_form_analysis_service.evaluate_rep(
        rep_angle_data=augmented_data_incomplete,
        rep_index=0,
        config=sample_squat_config_fsm,
    )
    assert feedback_items_incomplete, "Expected feedback for incomplete extension (ROM)."
    assert any(
        item.get("rule_type") == "rom" and item.get("violation_type") == "failed_to_reach_min_rom"
        for item in feedback_items_incomplete
    ), f"Expected ROM violation (failed_to_reach_min_rom) for this data based on current rule logic. Got: {feedback_items_incomplete}"
    assert score_incomplete < 100.0, "Score should be less than perfect for incomplete extension."

@pytest.mark.asyncio
async def test_evaluate_rep_posture_violation_torso_lean(
    dynamic_form_analysis_service: DynamicFormAnalysisService,
    sample_squat_config_fsm: ExerciseConfig, # Config with posture rules
    sample_angle_data_two_reps_one_bad: List[Dict[str, Any]], # Second rep has torso lean
    sample_form_check_model: FormCheck
):
    """Test evaluate_rep for posture violation (excessive torso lean)."""
    # The second rep (frames 6-11) in sample_angle_data_two_reps_one_bad is designed to have torso lean
    bad_rep_data_raw = sample_angle_data_two_reps_one_bad[6:12]

    # Phases for bad_rep_data_raw based on sample_squat_config_fsm:
    # F6 (orig_idx) LH:175 -> start
    # F7 (orig_idx) LH:150 -> descent
    # F8 (orig_idx) LK:85  -> bottom
    # F9 (orig_idx) LK:130 -> ascent
    # F10(orig_idx) LH:175 -> start
    # F11(orig_idx) LH:178 -> start
    phases = ['start_phase', 'descent_phase', 'bottom_phase', 'ascent_phase', 'start_phase', 'start_phase']
    
    augmented_bad_rep_data = [
        {**frame, 'phase_context': phases[i]} 
        for i, frame in enumerate(bad_rep_data_raw)
    ]

    feedback_items, score = await dynamic_form_analysis_service.evaluate_rep(
        rep_angle_data=augmented_bad_rep_data, # Use augmented data
        rep_index=1, # This is the second rep
        config=sample_squat_config_fsm,
    )
    assert feedback_items, "Expected feedback for torso lean."
    assert any(
        item.get("rule_type") == "posture" and "torso lean" in item.get("details", "").lower() # Check details for posture
        and "Torso Upright (Vertical Check)" in item.get("details", "") # Ensure it is the correct rule.
        or item.get("violation_type", "").startswith("Torso Upright (Vertical Check)")
        for item in feedback_items
    ), f"Expected posture violation (torso lean) feedback not found. Feedback: {feedback_items}"
    assert score < 100.0, "Score should be less than perfect due to torso lean."


@pytest.mark.asyncio
async def test_evaluate_rep_symmetry_violation_knee_angles(
    dynamic_form_analysis_service: DynamicFormAnalysisService,
    sample_squat_config_fsm: ExerciseConfig, # Config with symmetry rules
    sample_angle_data_two_reps_one_bad: List[Dict[str, Any]], # First rep has knee asymmetry
    sample_form_check_model: FormCheck
):
    """Test evaluate_rep for symmetry violation (knee angle difference)."""
    # The first rep (frames 0-5) in sample_angle_data_two_reps_one_bad has knee asymmetry
    asymmetric_rep_data_raw = sample_angle_data_two_reps_one_bad[0:6]

    # Phases for asymmetric_rep_data based on sample_squat_config_fsm:
    # Frame 0: leftHip: 175 -> start_phase (initial)
    # Frame 1: leftHip: 150 -> descent_phase (150 < 160 from start_phase next)
    # Frame 2: leftKnee: 85 -> bottom_phase (85 < 90 from descent_phase next)
    # Frame 3: leftKnee: 130 -> ascent_phase (130 > 95 from bottom_phase next)
    # Frame 4: leftHip: 175 -> start_phase (175 > 170 from ascent_phase next)
    # Frame 5: leftHip: 176 -> start_phase (no trigger from start_phase)
    phases = ['start_phase', 'descent_phase', 'bottom_phase', 'ascent_phase', 'start_phase', 'start_phase']
    
    augmented_asymmetric_rep_data = []
    for i, frame in enumerate(asymmetric_rep_data_raw):
        if i < len(phases):
            augmented_asymmetric_rep_data.append({**frame, 'phase_context': phases[i]})
        else:
            augmented_asymmetric_rep_data.append({**frame, 'phase_context': 'unknown'}) # Should not happen

    feedback_items, score = await dynamic_form_analysis_service.evaluate_rep(
        rep_angle_data=augmented_asymmetric_rep_data, # Use augmented data
        rep_index=0,
        config=sample_squat_config_fsm,
    )
    assert feedback_items, "Expected feedback for knee angle asymmetry."
    assert any(
        item.get("rule_type") == "symmetry" and "Knee Angle Symmetry" in item.get("details", "") # Check details for symmetry
        or item.get("violation_type", "").startswith("asymmetry_leftKnee_rightKnee") # Check violation_type for specific knee symmetry
        for item in feedback_items
    ), f"Expected symmetry violation (knee_angle_symmetry) feedback not found. Feedback: {feedback_items}"
    assert score < 100.0, "Score should be less than perfect due to symmetry violation." 