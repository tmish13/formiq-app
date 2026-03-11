"""Tests for the level system compute_level function."""
import pytest


class TestLevelSystem:
    def test_score_0_beginner(self):
        from app.ml.posture_v1.scoring import compute_level
        r = compute_level(0)
        assert r["current_level"] == "Beginner"

    def test_score_59_beginner(self):
        from app.ml.posture_v1.scoring import compute_level
        r = compute_level(59)
        assert r["current_level"] == "Beginner"

    def test_score_60_developing(self):
        from app.ml.posture_v1.scoring import compute_level
        r = compute_level(60)
        assert r["current_level"] == "Developing"

    def test_score_74_developing(self):
        from app.ml.posture_v1.scoring import compute_level
        r = compute_level(74)
        assert r["current_level"] == "Developing"

    def test_score_75_solid(self):
        from app.ml.posture_v1.scoring import compute_level
        r = compute_level(75)
        assert r["current_level"] == "Solid"

    def test_score_84_solid(self):
        from app.ml.posture_v1.scoring import compute_level
        r = compute_level(84)
        assert r["current_level"] == "Solid"

    def test_score_85_advanced(self):
        from app.ml.posture_v1.scoring import compute_level
        r = compute_level(85)
        assert r["current_level"] == "Advanced"

    def test_score_91_advanced(self):
        from app.ml.posture_v1.scoring import compute_level
        r = compute_level(91)
        assert r["current_level"] == "Advanced"

    def test_score_92_elite(self):
        from app.ml.posture_v1.scoring import compute_level
        r = compute_level(92)
        assert r["current_level"] == "Elite"
        assert r["percent_to_next_level"] == 100.0

    def test_score_100_elite(self):
        from app.ml.posture_v1.scoring import compute_level
        r = compute_level(100)
        assert r["current_level"] == "Elite"
        assert r["percent_to_next_level"] == 100.0

    def test_score_none_returns_none(self):
        from app.ml.posture_v1.scoring import compute_level
        r = compute_level(None)
        assert r["current_level"] is None
        assert r["percent_to_next_level"] is None

    def test_percent_clamped_max_100(self):
        from app.ml.posture_v1.scoring import compute_level
        r = compute_level(100)
        assert r["percent_to_next_level"] <= 100.0

    def test_developing_67_5_percent(self):
        """Developing 67.5 → percent_to_next = round((67.5-60)/15*100, 1) = 50.0"""
        from app.ml.posture_v1.scoring import compute_level
        r = compute_level(67.5)
        assert r["current_level"] == "Developing"
        assert r["percent_to_next_level"] == 50.0

    def test_percent_non_negative(self):
        from app.ml.posture_v1.scoring import compute_level
        r = compute_level(30)
        assert r["percent_to_next_level"] is not None
        assert r["percent_to_next_level"] >= 0
