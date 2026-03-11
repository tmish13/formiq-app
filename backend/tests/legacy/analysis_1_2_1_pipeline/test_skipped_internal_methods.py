import pytest
from unittest.mock import AsyncMock, MagicMock
from typing import List, Dict, Any, Tuple

from app.services.dynamic_form_analysis_service import DynamicFormAnalysisService
from app.models.exercise_config import ExerciseConfig
from app.models.form_check import FeedbackItem # Only FeedbackItem needed for these
from app.schemas.form_check import FeedbackItemCreate # For type hinting if needed
from app.models.enums import FeedbackSeverity, FeedbackType

# --- Tests for internal methods that were removed or refactored --- 
# These tests are skipped as the direct methods are no longer part of the public API
# or their logic is now implicitly tested via the main service methods.

# @pytest.mark.skip(reason="Internal method _evaluate_phase_transitions removed/refactored into segment_repetitions.")
# @pytest.mark.asyncio
# async def test_evaluate_phase_transitions_basic(
#     dynamic_form_analysis_service: DynamicFormAnalysisService,
#     sample_angle_data_one_rep: List[Dict[str, Any]],
#     sample_squat_config: ExerciseConfig
# ):
#     # This test is conceptually covered by tests for segment_repetitions or evaluate_rep
#     # which use the FSM logic from the config.
#     pass
#
# @pytest.mark.skip(reason="Internal method _aggregate_feedback_and_score removed/refactored into analyze_form_dynamically.")
# @pytest.mark.asyncio
# async def test_aggregate_feedback_and_score(
#     dynamic_form_analysis_service: DynamicFormAnalysisService
# ):
#     # Aggregation logic is now part of the main analyze_form_dynamically flow
#     # and tested through its E2E tests.
#     # Example of what it might have tested:
#     # all_reps_feedback = [
#     #     [FeedbackItemCreate(message="Issue 1 Rep 1", rule_id="rule1", severity=FeedbackSeverity.LOW, type=FeedbackType.FORM)],
#     #     [FeedbackItemCreate(message="Issue 1 Rep 2", rule_id="rule1", severity=FeedbackSeverity.LOW, type=FeedbackType.FORM)]
#     # ]
#     # all_reps_scores = [90.0, 80.0]
#     # aggregated_feedback, final_score = dynamic_form_analysis_service._aggregate_feedback_and_score(
#     #     all_reps_feedback=all_reps_feedback, 
#     #     all_reps_scores=all_reps_scores, 
#     #     rep_count=2
#     # )
#     # assert final_score == 85.0
#     # assert len(aggregated_feedback) > 0 
#     pass
#
# @pytest.mark.skip(reason="Internal method _aggregate_feedback_and_score removed/refactored.")
# @pytest.mark.asyncio
# async def test_aggregate_feedback_no_reps(
#     dynamic_form_analysis_service: DynamicFormAnalysisService
# ):
#     # aggregated_feedback, final_score = dynamic_form_analysis_service._aggregate_feedback_and_score(
#     #     all_reps_feedback=[], 
#     #     all_reps_scores=[], 
#     #     rep_count=0
#     # )
#     # assert final_score == 0 # Or 100, depending on desired behavior for no reps
#     # assert not aggregated_feedback
#     pass
#
# @pytest.mark.skip(reason="Internal method _aggregate_feedback_and_score removed/refactored.")
# @pytest.mark.asyncio
# async def test_aggregate_feedback_perfect_reps(
#     dynamic_form_analysis_service: DynamicFormAnalysisService
# ):
#     # all_reps_feedback = [[], []] # No feedback items for two perfect reps
#     # all_reps_scores = [100.0, 100.0]
#     # aggregated_feedback, final_score = dynamic_form_analysis_service._aggregate_feedback_and_score(
#     #     all_reps_feedback=all_reps_feedback, 
#     #     all_reps_scores=all_reps_scores, 
#     #     rep_count=2
#     # )
#     # assert final_score == 100.0
#     # assert not aggregated_feedback
#     pass 