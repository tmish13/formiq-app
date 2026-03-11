"""Tests for the delta engine — inline replica of computation logic."""
import pytest
from typing import Optional


# ---------------------------------------------------------------------------
# Inline replica of delta computation (pure function — no DB)
# ---------------------------------------------------------------------------

def compute_delta(
    cur_score: Optional[float],
    prev_score: Optional[float],
    best_prev: Optional[float],
    cur_named: dict,
    prev_named: dict,
    prev_is_none: bool,
) -> dict:
    """Replica of the delta computation block in analysis_tasks.py."""
    if prev_is_none:
        return {"baseline_session": True}

    def _named_delta(key):
        c, p = cur_named.get(key), prev_named.get(key)
        return round(c - p, 1) if c is not None and p is not None else None

    return {
        "baseline_session": False,
        "overall_score_delta": round(cur_score - prev_score, 1) if prev_score is not None and cur_score is not None else None,
        "posture_delta": round(cur_score - prev_score, 1) if prev_score is not None and cur_score is not None else None,
        "torso_stability_delta": _named_delta("torso_stability_score"),
        "knee_symmetry_delta": _named_delta("knee_symmetry_score"),
        "bottom_control_delta": _named_delta("bottom_control_score"),
        "forward_lean_delta": _named_delta("forward_lean_score"),
        "personal_best": bool(
            cur_score is not None and (best_prev is None or cur_score > best_prev)
        ),
    }


class TestDeltaEngine:
    def test_no_prior_session_baseline(self):
        result = compute_delta(75, None, None, {}, {}, prev_is_none=True)
        assert result == {"baseline_session": True}

    def test_positive_delta(self):
        result = compute_delta(75, 70, 70, {}, {}, prev_is_none=False)
        assert result["overall_score_delta"] == 5.0
        assert result["baseline_session"] is False

    def test_negative_delta(self):
        result = compute_delta(75, 80, 80, {}, {}, prev_is_none=False)
        assert result["overall_score_delta"] == -5.0

    def test_named_score_delta_none_when_prev_missing(self):
        result = compute_delta(
            75, 70, 70,
            cur_named={"torso_stability_score": 80},
            prev_named={},
            prev_is_none=False,
        )
        assert result["torso_stability_delta"] is None

    def test_cur_score_none_delta_none(self):
        result = compute_delta(None, 70, 70, {}, {}, prev_is_none=False)
        assert result["overall_score_delta"] is None

    def test_personal_best_true_when_no_prior(self):
        result = compute_delta(75, 70, None, {}, {}, prev_is_none=False)
        assert result["personal_best"] is True

    def test_personal_best_false_when_lower_than_best(self):
        result = compute_delta(75, 70, 80, {}, {}, prev_is_none=False)
        assert result["personal_best"] is False

    def test_personal_best_true_when_higher_than_best(self):
        result = compute_delta(85, 70, 80, {}, {}, prev_is_none=False)
        assert result["personal_best"] is True
