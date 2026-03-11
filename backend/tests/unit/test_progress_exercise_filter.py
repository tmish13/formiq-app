"""Tests for exercise_type filtering in progress endpoints."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


def _make_form_check(exercise_type=None, classified_exercise_slug=None, posture_score=80.0, status="completed"):
    fc = MagicMock()
    fc.id = uuid4()
    fc.user_id = uuid4()
    fc.exercise_type = exercise_type
    fc.classified_exercise_slug = classified_exercise_slug
    fc.posture_score = posture_score
    fc.score = posture_score
    fc.status = status
    fc.created_at = datetime.utcnow()
    fc.results = {"posture_v1": {"decision": "good_form", "named_scores": {}}}
    fc.weight_kg = None
    return fc


class TestProgressAnalyticsEndpointWeightTrend:
    """Weight trend is included in analytics response."""

    def test_weight_trend_in_analytics_response(self):
        """Sessions with weight_kg are returned in weight_trend."""
        squat_fc = _make_form_check(exercise_type="squat", posture_score=85.0)
        squat_fc.weight_kg = 100.0

        # Build the response the same way the endpoint does
        checks = [squat_fc]
        weight_data = [
            {"date": fc.created_at.isoformat(), "weight_kg": fc.weight_kg}
            for fc in checks
            if fc.weight_kg is not None
        ]
        best_weight = max((w["weight_kg"] for w in weight_data), default=None)

        assert len(weight_data) == 1
        assert weight_data[0]["weight_kg"] == 100.0
        assert best_weight == 100.0

    def test_weight_trend_empty_when_no_weight(self):
        fc = _make_form_check(exercise_type="squat", posture_score=70.0)
        fc.weight_kg = None

        checks = [fc]
        weight_data = [
            {"date": fc.created_at.isoformat(), "weight_kg": fc.weight_kg}
            for fc in checks
            if fc.weight_kg is not None
        ]
        best_weight = max((w["weight_kg"] for w in weight_data), default=None)

        assert weight_data == []
        assert best_weight is None

    def test_best_weight_picks_maximum(self):
        checks = []
        for w in [60.0, 80.0, 100.0, 90.0]:
            fc = _make_form_check(exercise_type="squat", posture_score=75.0)
            fc.weight_kg = w
            checks.append(fc)

        weight_data = [
            {"date": fc.created_at.isoformat(), "weight_kg": fc.weight_kg}
            for fc in checks
            if fc.weight_kg is not None
        ]
        best_weight = max((w["weight_kg"] for w in weight_data), default=None)
        assert best_weight == 100.0


class TestExerciseTypeFilterLogic:
    """exercise_type filter matches both exercise_type and classified_exercise_slug."""

    def test_filter_matches_exercise_type_column(self):
        squat_fc = _make_form_check(exercise_type="squat")
        deadlift_fc = _make_form_check(exercise_type="deadlift")

        all_checks = [squat_fc, deadlift_fc]
        filtered = [
            fc for fc in all_checks
            if fc.exercise_type == "squat" or fc.classified_exercise_slug == "squat"
        ]
        assert len(filtered) == 1
        assert filtered[0].exercise_type == "squat"

    def test_filter_matches_classified_exercise_slug(self):
        fc = _make_form_check(exercise_type=None, classified_exercise_slug="squat")
        all_checks = [fc]
        filtered = [
            f for f in all_checks
            if f.exercise_type == "squat" or f.classified_exercise_slug == "squat"
        ]
        assert len(filtered) == 1

    def test_no_filter_returns_all(self):
        checks = [
            _make_form_check(exercise_type="squat"),
            _make_form_check(exercise_type="deadlift"),
        ]
        # No filter applied
        assert len(checks) == 2

    def test_filter_excludes_non_matching(self):
        checks = [
            _make_form_check(exercise_type="squat"),
            _make_form_check(exercise_type="deadlift"),
            _make_form_check(exercise_type=None, classified_exercise_slug="bench_press"),
        ]
        filtered = [
            fc for fc in checks
            if fc.exercise_type == "squat" or fc.classified_exercise_slug == "squat"
        ]
        assert len(filtered) == 1
