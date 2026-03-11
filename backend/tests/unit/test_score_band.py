"""Unit tests for compute_score_band."""
import pytest


# ---------------------------------------------------------------------------
# Inline replica (avoids pulling in ML/numpy at import time in isolation)
# ---------------------------------------------------------------------------
def compute_score_band(posture_score: int) -> str:
    """Map 0-100 posture score to qualitative band."""
    if posture_score >= 85:
        return "excellent"
    if posture_score >= 70:
        return "good"
    if posture_score >= 40:
        return "needs_work"
    return "poor"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestComputeScoreBand:
    def test_100_is_excellent(self):
        assert compute_score_band(100) == "excellent"

    def test_85_is_excellent(self):
        assert compute_score_band(85) == "excellent"

    def test_84_is_good(self):
        assert compute_score_band(84) == "good"

    def test_70_is_good(self):
        assert compute_score_band(70) == "good"

    def test_69_is_needs_work(self):
        assert compute_score_band(69) == "needs_work"

    def test_40_is_needs_work(self):
        assert compute_score_band(40) == "needs_work"

    def test_39_is_poor(self):
        assert compute_score_band(39) == "poor"

    def test_0_is_poor(self):
        assert compute_score_band(0) == "poor"
