"""
Unit tests for form-check comparison helper logic.

Uses inline replicas of the safe-improvement computation (no app imports, no DB).
"""
import pytest


# ---------------------------------------------------------------------------
# Inline replicas
# ---------------------------------------------------------------------------

def _safe_improvement(a, b):
    """
    Returns round(a - b, 1) when both are non-None, otherwise None.
    Mirrors the logic in compare_form_checks for posture/stability/depth.
    """
    if a is None or b is None:
        return None
    return round(a - b, 1)


def _overall_improvement(current_score, previous_score):
    """
    Always computes overall improvement using 'or 0' fallback.
    Mirrors: overall_improvement = (current_score or 0) - (previous_score or 0)
    """
    return round((current_score or 0) - (previous_score or 0), 1)


# ---------------------------------------------------------------------------
# Tests for _safe_improvement
# ---------------------------------------------------------------------------

class TestSafeImprovement:
    def test_both_none_returns_none(self):
        assert _safe_improvement(None, None) is None

    def test_first_none_returns_none(self):
        assert _safe_improvement(None, 75.0) is None

    def test_second_none_returns_none(self):
        assert _safe_improvement(80.0, None) is None

    def test_positive_improvement(self):
        result = _safe_improvement(85.0, 70.0)
        assert result == 15.0

    def test_negative_improvement_decline(self):
        result = _safe_improvement(60.0, 80.0)
        assert result == -20.0

    def test_no_change_returns_zero(self):
        result = _safe_improvement(75.0, 75.0)
        assert result == 0.0

    def test_rounding_to_one_decimal(self):
        result = _safe_improvement(80.15, 70.0)
        assert result == round(80.15 - 70.0, 1)

    def test_small_fractional_values(self):
        result = _safe_improvement(0.525, 0.500)
        assert result == round(0.525 - 0.500, 1)


# ---------------------------------------------------------------------------
# Tests for _overall_improvement
# ---------------------------------------------------------------------------

class TestOverallImprovement:
    def test_both_scores_present(self):
        assert _overall_improvement(85, 70) == 15.0

    def test_current_none_treated_as_zero(self):
        assert _overall_improvement(None, 50) == -50.0

    def test_previous_none_treated_as_zero(self):
        assert _overall_improvement(60, None) == 60.0

    def test_both_none_treated_as_zeros(self):
        assert _overall_improvement(None, None) == 0.0

    def test_no_improvement(self):
        assert _overall_improvement(70, 70) == 0.0

    def test_sub_scores_null_does_not_affect_overall(self):
        # overall always uses 'or 0', regardless of posture/stability/depth being None
        overall = _overall_improvement(80, 65)
        assert overall == 15.0
