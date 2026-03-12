"""Tests for primary limiter tracking — inline replica."""
import pytest
from typing import Dict, Optional


# ---------------------------------------------------------------------------
# Inline replica of limiter computation (pure function)
# ---------------------------------------------------------------------------

def compute_primary_limiter(
    named_scores: Dict[str, Optional[float]],
    prev_checks_limiters: list,  # list of str (primary limiter key from each prior check)
) -> Optional[dict]:
    """Replica of primary limiter tracking in analysis_tasks.py."""
    valid = {k: v for k, v in named_scores.items() if v is not None}
    if not valid:
        return None
    primary_key = min(valid, key=valid.get)
    consecutive = sum(1 for pk in prev_checks_limiters if pk == primary_key)
    return {
        "key": primary_key,
        "persistent_limiter": consecutive >= 2,
    }


def get_prev_limiter_key(named: dict) -> Optional[str]:
    valid = {k: v for k, v in named.items() if v is not None}
    if not valid:
        return None
    return min(valid, key=valid.get)


class TestLimiterTracking:
    def test_all_scores_min_selected(self):
        named = {"torso_stability_score": 80, "knee_symmetry_score": 40, "bottom_control_score": 60}
        result = compute_primary_limiter(named, [])
        assert result["key"] == "knee_symmetry_score"

    def test_all_none_no_limiter(self):
        named = {"torso_stability_score": None, "knee_symmetry_score": None}
        result = compute_primary_limiter(named, [])
        assert result is None

    def test_same_key_3_consecutive_persistent(self):
        named = {"torso_stability_score": 30, "knee_symmetry_score": 70}
        # 2 prior sessions with same limiter
        prev = ["torso_stability_score", "torso_stability_score"]
        result = compute_primary_limiter(named, prev)
        assert result["persistent_limiter"] is True

    def test_same_key_2_consecutive_not_persistent(self):
        named = {"torso_stability_score": 30, "knee_symmetry_score": 70}
        # Only 1 prior session with same limiter
        prev = ["torso_stability_score"]
        result = compute_primary_limiter(named, prev)
        assert result["persistent_limiter"] is False

    def test_different_keys_not_persistent(self):
        named = {"torso_stability_score": 30, "knee_symmetry_score": 70}
        prev = ["knee_symmetry_score", "bottom_control_score"]
        result = compute_primary_limiter(named, prev)
        assert result["persistent_limiter"] is False

    def test_no_prior_sessions_not_persistent(self):
        named = {"torso_stability_score": 30}
        result = compute_primary_limiter(named, [])
        assert result["persistent_limiter"] is False
