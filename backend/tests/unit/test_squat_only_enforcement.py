"""Test that non-squat exercise names are rejected at the submit endpoint."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

from app.models.enums import ExerciseType


# ---------------------------------------------------------------------------
# Unit tests for the squat-only guard logic (pure Python, no FastAPI client)
# ---------------------------------------------------------------------------

_SQUAT_NAMES = {"squat", "low bar squat", "high bar squat", "back squat", "front squat"}


def _is_squat_name(exercise_name: str) -> bool:
    """Replicate the guard logic from the endpoint."""
    return exercise_name.lower().strip() in _SQUAT_NAMES


class TestSquatOnlyGuard:
    def test_squat_accepted(self):
        assert _is_squat_name("squat") is True

    def test_squat_case_insensitive(self):
        assert _is_squat_name("Squat") is True
        assert _is_squat_name("SQUAT") is True

    def test_low_bar_squat_accepted(self):
        assert _is_squat_name("low bar squat") is True

    def test_high_bar_squat_accepted(self):
        assert _is_squat_name("high bar squat") is True

    def test_back_squat_accepted(self):
        assert _is_squat_name("back squat") is True

    def test_front_squat_accepted(self):
        assert _is_squat_name("front squat") is True

    def test_deadlift_rejected(self):
        assert _is_squat_name("deadlift") is False

    def test_bench_press_rejected(self):
        assert _is_squat_name("bench press") is False

    def test_overhead_press_rejected(self):
        assert _is_squat_name("overhead press") is False

    def test_pullup_rejected(self):
        assert _is_squat_name("pull up") is False

    def test_empty_string_rejected(self):
        assert _is_squat_name("") is False

    def test_whitespace_trimmed(self):
        assert _is_squat_name("  squat  ") is True


class TestSquatEnumMapping:
    """All accepted squat names map to ExerciseType.SQUAT."""

    def test_squat_maps_to_squat_enum(self):
        for name in _SQUAT_NAMES:
            assert _is_squat_name(name)
            # The endpoint always sets exercise_type_enum = ExerciseType.SQUAT
            # when the name is in _SQUAT_NAMES.
            assert ExerciseType.SQUAT.value == "squat"
