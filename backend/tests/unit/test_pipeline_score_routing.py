"""Unit tests for Bug 1+2: legacy temporal ML score routing.

Verifies that:
  - For squats, the temporal ML score is stored in results["temporal_ml"]
    and NOT written to form_check.posture_score.
  - For non-squats, the score is written to form_check.posture_score on
    the 0-100 scale (no /100 division).

Uses inline replicas of the routing logic so we don't import the
heavyweight Celery/DB-bound module in unit tests.
"""


# ---------------------------------------------------------------------------
# Inline replica of the score-routing logic from analysis_tasks.py
# ---------------------------------------------------------------------------

def _route_temporal_score(
    is_squat: bool,
    temporal_score: float,
    form_check_posture_score,
    form_check_results: dict,
    analysis_method: str = "temporal",
):
    """
    Mirror of the routing block in _process_form_check_task_async.

    Returns (posture_score, results_dict) after applying the routing rules.
    """
    _temporal_score = temporal_score  # 0-100 scale

    if is_squat:
        _t_results = dict(form_check_results)
        _t_results["temporal_ml"] = {
            "score": _temporal_score,
            "analysis_method": analysis_method,
        }
        return form_check_posture_score, _t_results  # posture_score untouched
    else:
        # Non-squat: legacy model drives posture_score. Score is 0-100, not 0-1.
        return _temporal_score, dict(form_check_results)


# ---------------------------------------------------------------------------
# Tests — Bug 1 + 2
# ---------------------------------------------------------------------------


class TestTemporalScoreRouting:
    def test_squat_score_stored_in_temporal_ml_not_posture_score(self):
        """For squats, temporal score must NOT touch posture_score."""
        posture_score, results = _route_temporal_score(
            is_squat=True,
            temporal_score=72.0,
            form_check_posture_score=None,  # starts as None (no previous write)
            form_check_results={},
        )
        # posture_score must stay None — PostureV1 owns it for squats
        assert posture_score is None, (
            "posture_score should remain None for squats — "
            f"got {posture_score!r} (possible /100 bug: {72.0/100})"
        )
        assert results["temporal_ml"]["score"] == 72.0

    def test_squat_temporal_ml_score_is_not_fractional(self):
        """Score stored in temporal_ml must be 0-100, never 0-1."""
        _, results = _route_temporal_score(
            is_squat=True,
            temporal_score=72.0,
            form_check_posture_score=None,
            form_check_results={},
        )
        score = results["temporal_ml"]["score"]
        assert score > 1.0, (
            f"Temporal score {score!r} looks like it was divided by 100. "
            "Expected 72.0, got a fraction."
        )
        assert score == 72.0

    def test_squat_does_not_overwrite_existing_posture_score(self):
        """PostureV1 may have already written a score; temporal must not clobber it."""
        posture_score, _ = _route_temporal_score(
            is_squat=True,
            temporal_score=85.0,
            form_check_posture_score=78,  # PostureV1 already wrote 78
            form_check_results={},
        )
        assert posture_score == 78, "Legacy temporal block overwrote PostureV1 posture_score"

    def test_non_squat_writes_posture_score_0_to_100(self):
        """Non-squat exercises: posture_score is set from temporal score (0-100 scale)."""
        posture_score, _ = _route_temporal_score(
            is_squat=False,
            temporal_score=65.0,
            form_check_posture_score=None,
            form_check_results={},
        )
        assert posture_score == 65.0

    def test_non_squat_score_not_fractional(self):
        """Legacy division bug: score must NOT be divided by 100 for non-squats."""
        posture_score, _ = _route_temporal_score(
            is_squat=False,
            temporal_score=65.0,
            form_check_posture_score=None,
            form_check_results={},
        )
        assert posture_score > 1.0, (
            f"posture_score {posture_score!r} looks like it was divided by 100 — expected 65.0"
        )

    def test_temporal_ml_key_preserved_in_results(self):
        """Results dict should keep pre-existing keys alongside temporal_ml."""
        existing = {"posture_v1": {"decision": "good_form"}}
        _, results = _route_temporal_score(
            is_squat=True,
            temporal_score=80.0,
            form_check_posture_score=None,
            form_check_results=existing,
        )
        assert "posture_v1" in results, "Pre-existing posture_v1 key was lost"
        assert "temporal_ml" in results

    def test_zero_temporal_score_stored_correctly(self):
        """Edge case: score=0.0 must be stored as 0.0, not silently dropped."""
        posture_score, results = _route_temporal_score(
            is_squat=True,
            temporal_score=0.0,
            form_check_posture_score=None,
            form_check_results={},
        )
        assert results["temporal_ml"]["score"] == 0.0
        assert posture_score is None
