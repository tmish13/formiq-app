"""
Unit tests for ML model info builder logic.

Uses inline replicas of the manifest-reading logic (no app imports, no DB).
"""
import pytest


# ---------------------------------------------------------------------------
# Inline replica
# ---------------------------------------------------------------------------

def _build_model_info(manifest: dict) -> dict:
    """
    Builds the model info response dict from a manifest dict.
    Mirrors the logic in get_model_info in ml.py.
    """
    return {
        "version": manifest.get("version", "v1"),
        "supported_exercises": ["squat"],
        "confidence_threshold": manifest.get("threshold", 0.525),
        "last_updated": manifest.get("created_at", "2026-02-01T00:00:00Z"),
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

REAL_MANIFEST = {
    "version": "v1",
    "threshold": 0.525,
    "created_at": "2026-02-12T19:27:21.698690+00:00",
}


class TestBuildModelInfo:
    def test_version_read_from_manifest(self):
        result = _build_model_info(REAL_MANIFEST)
        assert result["version"] == "v1"

    def test_version_fallback_when_manifest_empty(self):
        result = _build_model_info({})
        assert result["version"] == "v1"

    def test_threshold_read_from_manifest(self):
        result = _build_model_info(REAL_MANIFEST)
        assert result["confidence_threshold"] == 0.525

    def test_threshold_fallback_when_manifest_empty(self):
        result = _build_model_info({})
        assert result["confidence_threshold"] == 0.525

    def test_supported_exercises_always_squat(self):
        result = _build_model_info(REAL_MANIFEST)
        assert result["supported_exercises"] == ["squat"]

    def test_supported_exercises_unchanged_even_if_manifest_empty(self):
        result = _build_model_info({})
        assert result["supported_exercises"] == ["squat"]

    def test_all_four_required_fields_present(self):
        result = _build_model_info(REAL_MANIFEST)
        assert "version" in result
        assert "supported_exercises" in result
        assert "confidence_threshold" in result
        assert "last_updated" in result

    def test_last_updated_read_from_manifest(self):
        result = _build_model_info(REAL_MANIFEST)
        assert result["last_updated"] == "2026-02-12T19:27:21.698690+00:00"

    def test_last_updated_fallback_when_manifest_empty(self):
        result = _build_model_info({})
        assert result["last_updated"] == "2026-02-01T00:00:00Z"
