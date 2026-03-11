"""Unit tests for progress endpoint pure helper functions.

These tests exercise logic that can be verified without a database by using
inline replicas of the pure helper functions (streak, weekly improvement,
cutoff date, risk level, trend, and the weekly-grouping algorithm).

Naming convention:
    TestCalculateStreak           – streak counting from consecutive dates
    TestCalculateWeeklyImprovement – week-over-week % change
    TestGetCutoffDate             – time-range string → datetime
    TestCalculateRiskLevel        – score → "low/medium/high"
    TestDetermineRecentTrend      – improvement_rate → "improving/stable/declining"
    TestProcessWeeklyGrouping     – the weekly-grouping algorithm from /progress/trends
"""

from datetime import datetime, timedelta, date
from typing import Dict, List, Any, Optional
import pytest


# ---------------------------------------------------------------------------
# Inline replicas of pure helper functions (no DB, no imports from app)
# ---------------------------------------------------------------------------

def _get_cutoff_date(time_range: Optional[str]) -> Optional[datetime]:
    if not time_range:
        return None
    now = datetime.now()
    mapping = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}
    days = mapping.get(time_range)
    return now - timedelta(days=days) if days else None


def _calculate_risk_level(score: float) -> str:
    if score >= 80:
        return "low"
    if score >= 60:
        return "medium"
    return "high"


def _determine_recent_trend(improvement_rate: float) -> str:
    if improvement_rate > 5:
        return "improving"
    if improvement_rate < -5:
        return "declining"
    return "stable"


def _calculate_streak_from_dates(completed_dates: List[date]) -> int:
    """Replica of _calculate_streak logic (date-based)."""
    if not completed_dates:
        return 0
    dates_set = set(completed_dates)
    streak = 0
    current = date.today()
    while current in dates_set:
        streak += 1
        current -= timedelta(days=1)
    return streak


def _calculate_weekly_improvement_from_scores(
    this_week_scores: List[float],
    last_week_scores: List[float],
) -> float:
    """Replica of _calculate_weekly_improvement logic."""
    if not this_week_scores or not last_week_scores:
        return 0.0
    this_avg = sum(this_week_scores) / len(this_week_scores)
    last_avg = sum(last_week_scores) / len(last_week_scores)
    if last_avg == 0:
        return 0.0
    return ((this_avg - last_avg) / last_avg) * 100


def _process_weekly_grouping(
    form_checks: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Replica of the weekly-grouping logic from the new /progress/trends endpoint."""
    weekly: Dict[str, Dict[str, Any]] = {}
    for fc in form_checks:
        created_at: datetime = fc["created_at"]
        iso_monday = created_at.date() - timedelta(days=created_at.weekday())
        key = iso_monday.isoformat()
        if key not in weekly:
            weekly[key] = {"week_start": key, "scores": [], "sessions": 0}
        weekly[key]["scores"].append(fc["score"])
        weekly[key]["sessions"] += 1

    weekly_progress = []
    for key in sorted(weekly):
        entry = weekly[key]
        avg_score = sum(entry["scores"]) / len(entry["scores"])
        weekly_progress.append(
            {
                "week_start": entry["week_start"],
                "avg_score": round(avg_score, 1),
                "sessions": entry["sessions"],
            }
        )

    improvement_rate = 0.0
    if len(weekly_progress) >= 2:
        first_avg = weekly_progress[0]["avg_score"]
        last_avg = weekly_progress[-1]["avg_score"]
        if first_avg > 0:
            improvement_rate = round(((last_avg - first_avg) / first_avg) * 100, 2)

    return {"weekly_progress": weekly_progress, "improvement_rate": improvement_rate}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGetCutoffDate:
    def test_none_returns_none(self):
        assert _get_cutoff_date(None) is None

    def test_unknown_string_returns_none(self):
        assert _get_cutoff_date("forever") is None

    def test_7d(self):
        result = _get_cutoff_date("7d")
        assert result is not None
        diff = datetime.now() - result
        assert 6 < diff.total_seconds() / 86400 < 8

    def test_30d(self):
        result = _get_cutoff_date("30d")
        assert result is not None
        diff = datetime.now() - result
        assert 29 < diff.total_seconds() / 86400 < 31

    def test_90d(self):
        result = _get_cutoff_date("90d")
        diff = datetime.now() - result
        assert 89 < diff.total_seconds() / 86400 < 91

    def test_1y(self):
        result = _get_cutoff_date("1y")
        diff = datetime.now() - result
        assert 364 < diff.total_seconds() / 86400 < 366


class TestCalculateRiskLevel:
    def test_high_score_low_risk(self):
        assert _calculate_risk_level(85) == "low"
        assert _calculate_risk_level(80) == "low"

    def test_medium_score_medium_risk(self):
        assert _calculate_risk_level(75) == "medium"
        assert _calculate_risk_level(60) == "medium"

    def test_low_score_high_risk(self):
        assert _calculate_risk_level(59) == "high"
        assert _calculate_risk_level(0) == "high"

    def test_boundary_exactly_80(self):
        assert _calculate_risk_level(80) == "low"

    def test_boundary_exactly_60(self):
        assert _calculate_risk_level(60) == "medium"


class TestDetermineRecentTrend:
    def test_improving(self):
        assert _determine_recent_trend(10) == "improving"
        assert _determine_recent_trend(5.1) == "improving"

    def test_stable_zero(self):
        assert _determine_recent_trend(0) == "stable"

    def test_stable_small_positive(self):
        assert _determine_recent_trend(3) == "stable"

    def test_stable_small_negative(self):
        assert _determine_recent_trend(-3) == "stable"

    def test_declining(self):
        assert _determine_recent_trend(-10) == "declining"
        assert _determine_recent_trend(-5.1) == "declining"

    def test_boundary_exactly_5(self):
        # 5.0 is NOT strictly > 5 → stable
        assert _determine_recent_trend(5.0) == "stable"

    def test_boundary_exactly_negative_5(self):
        # -5.0 is NOT strictly < -5 → stable
        assert _determine_recent_trend(-5.0) == "stable"


class TestCalculateStreakFromDates:
    def test_no_dates_returns_zero(self):
        assert _calculate_streak_from_dates([]) == 0

    def test_only_today_returns_one(self):
        assert _calculate_streak_from_dates([date.today()]) == 1

    def test_consecutive_days_correct_streak(self):
        today = date.today()
        dates = [today, today - timedelta(1), today - timedelta(2)]
        assert _calculate_streak_from_dates(dates) == 3

    def test_gap_breaks_streak(self):
        today = date.today()
        # Today + day 3 ago (gap at day 2 → streak = 1)
        dates = [today, today - timedelta(3)]
        assert _calculate_streak_from_dates(dates) == 1

    def test_streak_starts_from_today_not_yesterday(self):
        # Only yesterday — no workout today → streak = 0
        yesterday = date.today() - timedelta(1)
        assert _calculate_streak_from_dates([yesterday]) == 0

    def test_duplicates_in_same_day_count_as_one(self):
        today = date.today()
        dates = [today, today, today - timedelta(1)]
        assert _calculate_streak_from_dates(dates) == 2

    def test_long_streak(self):
        today = date.today()
        dates = [today - timedelta(i) for i in range(10)]
        assert _calculate_streak_from_dates(dates) == 10


class TestCalculateWeeklyImprovement:
    def test_both_empty_returns_zero(self):
        assert _calculate_weekly_improvement_from_scores([], []) == 0.0

    def test_this_week_empty_returns_zero(self):
        assert _calculate_weekly_improvement_from_scores([], [80.0]) == 0.0

    def test_last_week_empty_returns_zero(self):
        assert _calculate_weekly_improvement_from_scores([80.0], []) == 0.0

    def test_improvement(self):
        # this=90, last=80 → (90-80)/80*100 = 12.5
        result = _calculate_weekly_improvement_from_scores([90.0], [80.0])
        assert abs(result - 12.5) < 0.01

    def test_decline(self):
        # this=70, last=80 → (70-80)/80*100 = -12.5
        result = _calculate_weekly_improvement_from_scores([70.0], [80.0])
        assert abs(result - (-12.5)) < 0.01

    def test_no_change(self):
        result = _calculate_weekly_improvement_from_scores([80.0], [80.0])
        assert result == 0.0

    def test_last_week_zero_returns_zero(self):
        result = _calculate_weekly_improvement_from_scores([80.0], [0.0])
        assert result == 0.0

    def test_multiple_scores_averages_correctly(self):
        # this_week avg = (80+90)/2 = 85, last_week avg = 75
        result = _calculate_weekly_improvement_from_scores([80.0, 90.0], [75.0])
        expected = (85 - 75) / 75 * 100  # ≈ 13.33
        assert abs(result - expected) < 0.01


class TestProcessWeeklyGrouping:
    def _make_fc(self, dt: datetime, score: float) -> Dict[str, Any]:
        return {"created_at": dt, "score": score}

    def test_no_data(self):
        result = _process_weekly_grouping([])
        assert result["weekly_progress"] == []
        assert result["improvement_rate"] == 0.0

    def test_single_session_one_week(self):
        fc = self._make_fc(datetime(2026, 2, 11, 10, 0), 80.0)
        result = _process_weekly_grouping([fc])
        assert len(result["weekly_progress"]) == 1
        assert result["weekly_progress"][0]["avg_score"] == 80.0
        assert result["weekly_progress"][0]["sessions"] == 1
        # Only 1 week → improvement_rate = 0
        assert result["improvement_rate"] == 0.0

    def test_multiple_sessions_same_week_averages(self):
        # Both fall on the week starting 2026-02-09 (Monday)
        fcs = [
            self._make_fc(datetime(2026, 2, 9, 10, 0), 80.0),
            self._make_fc(datetime(2026, 2, 11, 10, 0), 90.0),
        ]
        result = _process_weekly_grouping(fcs)
        assert len(result["weekly_progress"]) == 1
        assert result["weekly_progress"][0]["avg_score"] == 85.0
        assert result["weekly_progress"][0]["sessions"] == 2

    def test_two_weeks_improvement_rate(self):
        # Week 1 (2026-02-02): score 80
        # Week 2 (2026-02-09): score 90
        # improvement = (90-80)/80*100 = 12.5
        fcs = [
            self._make_fc(datetime(2026, 2, 2, 10, 0), 80.0),
            self._make_fc(datetime(2026, 2, 9, 10, 0), 90.0),
        ]
        result = _process_weekly_grouping(fcs)
        assert len(result["weekly_progress"]) == 2
        assert abs(result["improvement_rate"] - 12.5) < 0.01

    def test_two_weeks_decline(self):
        fcs = [
            self._make_fc(datetime(2026, 2, 2, 10, 0), 90.0),
            self._make_fc(datetime(2026, 2, 9, 10, 0), 80.0),
        ]
        result = _process_weekly_grouping(fcs)
        expected = round((80 - 90) / 90 * 100, 2)  # ≈ -11.11
        assert abs(result["improvement_rate"] - expected) < 0.01

    def test_weeks_ordered_chronologically(self):
        fcs = [
            self._make_fc(datetime(2026, 2, 9, 10, 0), 90.0),
            self._make_fc(datetime(2026, 2, 2, 10, 0), 80.0),  # earlier, added later
        ]
        result = _process_weekly_grouping(fcs)
        weeks = result["weekly_progress"]
        # Weeks should be sorted by week_start ascending
        assert weeks[0]["week_start"] < weeks[1]["week_start"]
        assert weeks[0]["avg_score"] == 80.0
        assert weeks[1]["avg_score"] == 90.0

    def test_week_start_is_always_monday(self):
        # 2026-02-11 is a Wednesday; its Monday is 2026-02-09
        fc = self._make_fc(datetime(2026, 2, 11, 10, 0), 80.0)
        result = _process_weekly_grouping([fc])
        assert result["weekly_progress"][0]["week_start"] == "2026-02-09"

    def test_multiple_weeks_sessions_correct(self):
        fcs = [
            self._make_fc(datetime(2026, 2, 2, 10, 0), 75.0),
            self._make_fc(datetime(2026, 2, 3, 10, 0), 80.0),  # same week as above
            self._make_fc(datetime(2026, 2, 9, 10, 0), 85.0),
            self._make_fc(datetime(2026, 2, 10, 10, 0), 90.0), # same week as above
            self._make_fc(datetime(2026, 2, 10, 14, 0), 95.0), # same week as above
        ]
        result = _process_weekly_grouping(fcs)
        assert len(result["weekly_progress"]) == 2
        w1 = result["weekly_progress"][0]
        w2 = result["weekly_progress"][1]
        assert w1["sessions"] == 2
        assert w1["avg_score"] == 77.5  # (75+80)/2
        assert w2["sessions"] == 3
        assert w2["avg_score"] == 90.0  # (85+90+95)/3
