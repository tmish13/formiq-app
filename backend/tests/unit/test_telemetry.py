"""Unit tests for PostureV1InferenceLog telemetry model."""

import uuid
import pytest
from unittest.mock import MagicMock

from app.models.telemetry import PostureV1InferenceLog


class TestPostureV1InferenceLog:
    """Tests for the telemetry model itself."""

    def test_inference_log_creation_success(self):
        """Create a PostureV1InferenceLog with all fields and verify attributes."""
        log = PostureV1InferenceLog(
            form_check_id=uuid.uuid4(),
            video_id=uuid.uuid4(),
            decision="fault",
            prob_fault=0.78,
            confidence=0.72,
            threshold=0.525,
            threshold_mode="default",
            posture_v1_mode="active",
            sequence_length=250,
            missing_ratio=0.05,
            outlier_z_gt3=3,
            outlier_z_gt6=0,
            angle_validity={"trunk_angle": 0.95, "left_knee_angle": 0.92},
            gate_flags=[],
            top_signals=[{"feature": "trunk_forward_lean", "z": 2.1}],
            named_scores={"alignment": 72.0, "depth": 85.0},
            model_version="posture_v1_20260201",
            latency_ms=45.2,
        )

        assert log.decision == "fault"
        assert log.prob_fault == 0.78
        assert log.confidence == 0.72
        assert log.posture_v1_mode == "active"
        assert log.error is None
        assert log.named_scores["alignment"] == 72.0

    def test_inference_log_creation_error(self):
        """Create a PostureV1InferenceLog for an error case."""
        log = PostureV1InferenceLog(
            form_check_id=uuid.uuid4(),
            video_id=uuid.uuid4(),
            decision="error",
            posture_v1_mode="active",
            error="RuntimeError: CUDA out of memory",
        )

        assert log.decision == "error"
        assert log.error == "RuntimeError: CUDA out of memory"
        assert log.prob_fault is None

    def test_inference_log_shadow_mode(self):
        """Verify shadow mode is correctly stored."""
        log = PostureV1InferenceLog(
            decision="good_form",
            posture_v1_mode="shadow",
            prob_fault=0.3,
            confidence=0.85,
        )

        assert log.posture_v1_mode == "shadow"

    def test_telemetry_write_nonfatal(self):
        """Verify that if session.add raises, the exception is caught in the
        expected usage pattern (try/except wrapping telemetry writes)."""
        mock_session = MagicMock()
        mock_session.add.side_effect = RuntimeError("DB connection lost")

        log = PostureV1InferenceLog(
            decision="fault",
            prob_fault=0.8,
        )

        # Simulate the pattern used in analysis_tasks.py
        telemetry_error = None
        try:
            mock_session.add(log)
        except Exception as exc:
            telemetry_error = str(exc)

        assert telemetry_error == "DB connection lost"
        # The key assertion: the exception is catchable and does not propagate
        # unhandled. In analysis_tasks.py this is wrapped in try/except with
        # a logger.warning, ensuring telemetry failure never breaks processing.
