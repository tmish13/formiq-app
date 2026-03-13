"""
Tests for MediaPipe model_complexity configuration alignment.

Validates that:
1. AI_MODEL_COMPLEXITY defaults to 2 (matching PostureV1 training data)
2. Environment variable override works
3. AIService passes settings value to MediaPipe Pose init
4. Fallback from complexity=2 to complexity=1 on init failure
"""

import os
import pytest
from unittest.mock import patch, MagicMock, call


# ---------------------------------------------------------------------------
# Test 1: Default AI_MODEL_COMPLEXITY is 2 when env var absent
# ---------------------------------------------------------------------------

class TestModelComplexityConfig:
    def test_default_complexity_is_2(self):
        """AI_MODEL_COMPLEXITY should default to 2 when env var is not set."""
        env = os.environ.copy()
        env.pop("AI_MODEL_COMPLEXITY", None)

        with patch.dict(os.environ, env, clear=True):
            # Force re-import to pick up env changes
            from app.core.config import Settings
            # Create a fresh Settings instance (not cached singleton)
            settings = Settings(
                SECRET_KEY="test-secret-key-for-unit-testing",
                POSTGRES_USER="test",
                POSTGRES_PASSWORD="test",
                POSTGRES_DB="test",
                POSTGRES_HOST="localhost",
                _env_file=None,
            )
            assert settings.AI_MODEL_COMPLEXITY == 2, (
                f"Expected default AI_MODEL_COMPLEXITY=2, got {settings.AI_MODEL_COMPLEXITY}"
            )

    def test_env_override_complexity_1(self):
        """AI_MODEL_COMPLEXITY=1 env var should override default."""
        with patch.dict(os.environ, {"AI_MODEL_COMPLEXITY": "1"}):
            from app.core.config import Settings
            settings = Settings(
                SECRET_KEY="test-secret-key-for-unit-testing",
                POSTGRES_USER="test",
                POSTGRES_PASSWORD="test",
                POSTGRES_DB="test",
                POSTGRES_HOST="localhost",
                _env_file=None,
            )
            assert settings.AI_MODEL_COMPLEXITY == 1, (
                f"Expected AI_MODEL_COMPLEXITY=1 from env, got {settings.AI_MODEL_COMPLEXITY}"
            )

    def test_env_override_complexity_0(self):
        """AI_MODEL_COMPLEXITY=0 env var should override default."""
        with patch.dict(os.environ, {"AI_MODEL_COMPLEXITY": "0"}):
            from app.core.config import Settings
            settings = Settings(
                SECRET_KEY="test-secret-key-for-unit-testing",
                POSTGRES_USER="test",
                POSTGRES_PASSWORD="test",
                POSTGRES_DB="test",
                POSTGRES_HOST="localhost",
                _env_file=None,
            )
            assert settings.AI_MODEL_COMPLEXITY == 0


# ---------------------------------------------------------------------------
# Test 2: AIService uses settings.AI_MODEL_COMPLEXITY in Pose init
# ---------------------------------------------------------------------------

class TestAIServicePoseInit:
    @patch("app.services.ai_service.mp.solutions.pose.Pose")
    @patch("app.services.ai_service.MLModelService")
    @patch("app.services.ai_service.EnhancedSquatModelLoader")
    @patch("app.services.ai_service.EnhancedSquatFeatureExtractor")
    def test_pose_uses_settings_complexity(
        self, mock_extractor, mock_squat_loader, mock_ml_service, mock_pose_cls
    ):
        """AIService should pass settings.AI_MODEL_COMPLEXITY to MediaPipe Pose."""
        mock_pose_cls.return_value = MagicMock()

        from app.core.config import Settings
        settings = Settings(
            SECRET_KEY="test-secret-key-for-unit-testing",
            POSTGRES_USER="test",
            POSTGRES_PASSWORD="test",
            POSTGRES_DB="test",
            POSTGRES_HOST="localhost",
            _env_file=None,
        )
        # Ensure complexity is 2
        settings.AI_MODEL_COMPLEXITY = 2

        from app.services.ai_service import AIService
        service = AIService(app_settings=settings)

        # First call should be the main Pose init with complexity=2
        first_call = mock_pose_cls.call_args_list[0]
        assert first_call == call(
            static_image_mode=False,
            model_complexity=2,
            min_detection_confidence=settings.AI_MIN_DETECTION_CONFIDENCE,
            min_tracking_confidence=settings.AI_MIN_TRACKING_CONFIDENCE,
        ), f"Expected Pose(model_complexity=2), got {first_call}"

        assert service._pose_complexity_used == 2
        assert service._pose_complexity_fallback is False

    @patch("app.services.ai_service.mp.solutions.pose.Pose")
    @patch("app.services.ai_service.MLModelService")
    @patch("app.services.ai_service.EnhancedSquatModelLoader")
    @patch("app.services.ai_service.EnhancedSquatFeatureExtractor")
    def test_pose_fallback_on_init_failure(
        self, mock_extractor, mock_squat_loader, mock_ml_service, mock_pose_cls
    ):
        """AIService should fall back to complexity=1 if complexity=2 init fails."""
        # First call (complexity=2) raises, second call (complexity=1) succeeds
        mock_pose_cls.side_effect = [
            RuntimeError("Simulated init failure at complexity=2"),
            MagicMock(),  # fallback succeeds
            MagicMock(),  # gpu_pose init (may or may not be called)
        ]

        from app.core.config import Settings
        settings = Settings(
            SECRET_KEY="test-secret-key-for-unit-testing",
            POSTGRES_USER="test",
            POSTGRES_PASSWORD="test",
            POSTGRES_DB="test",
            POSTGRES_HOST="localhost",
            _env_file=None,
        )
        settings.AI_MODEL_COMPLEXITY = 2

        from app.services.ai_service import AIService
        service = AIService(app_settings=settings)

        assert service._pose_complexity_used == 1
        assert service._pose_complexity_fallback is True

        # Second call should be the fallback with complexity=1
        fallback_call = mock_pose_cls.call_args_list[1]
        assert fallback_call == call(
            static_image_mode=False,
            model_complexity=1,
            min_detection_confidence=settings.AI_MIN_DETECTION_CONFIDENCE,
            min_tracking_confidence=settings.AI_MIN_TRACKING_CONFIDENCE,
        ), f"Expected fallback Pose(model_complexity=1), got {fallback_call}"

    @patch("app.services.ai_service.mp.solutions.pose.Pose")
    @patch("app.services.ai_service.MLModelService")
    @patch("app.services.ai_service.EnhancedSquatModelLoader")
    @patch("app.services.ai_service.EnhancedSquatFeatureExtractor")
    def test_pose_uses_complexity_1_when_configured(
        self, mock_extractor, mock_squat_loader, mock_ml_service, mock_pose_cls
    ):
        """AIService should use complexity=1 when explicitly configured."""
        mock_pose_cls.return_value = MagicMock()

        from app.core.config import Settings
        settings = Settings(
            SECRET_KEY="test-secret-key-for-unit-testing",
            POSTGRES_USER="test",
            POSTGRES_PASSWORD="test",
            POSTGRES_DB="test",
            POSTGRES_HOST="localhost",
            _env_file=None,
        )
        settings.AI_MODEL_COMPLEXITY = 1

        from app.services.ai_service import AIService
        service = AIService(app_settings=settings)

        first_call = mock_pose_cls.call_args_list[0]
        assert first_call == call(
            static_image_mode=False,
            model_complexity=1,
            min_detection_confidence=settings.AI_MIN_DETECTION_CONFIDENCE,
            min_tracking_confidence=settings.AI_MIN_TRACKING_CONFIDENCE,
        )
        assert service._pose_complexity_used == 1
        assert service._pose_complexity_fallback is False
