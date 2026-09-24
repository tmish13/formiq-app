"""G-06: the 18-sample demo model is quarantined and the legacy loader reports it absent."""
from pathlib import Path
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit
APP = Path(__file__).resolve().parents[2] / "app"


def test_no_directory_named_squat_under_ml_models():
    assert not (APP / "ml_models" / "squat").exists()
    assert (APP / "ml_models" / "_deprecated_demo_squat" / "production_metadata.json").exists()
    assert (APP / "ml_models" / "README.md").exists()


def test_the_legacy_loader_reports_the_model_unavailable():
    from app.services.ml_model_service import EnhancedSquatModelLoader
    loader = EnhancedSquatModelLoader(MagicMock())
    assert loader.is_model_available() is False
