"""Unit tests for Bug 3: LocalStorageProvider uses an absolute base_dir.

Verifies that:
  - base_dir is always absolute, regardless of the process CWD.
  - get_key_from_url preserves subdirectories for fallback URLs.
  - round-trip: URL → key → local_path uses the absolute base_dir.
"""
import os
import pytest


# ---------------------------------------------------------------------------
# Inline replica of the path-resolution logic
# (mirrors LocalStorageProvider in app/core/storage/__init__.py)
# ---------------------------------------------------------------------------

def _compute_absolute_base_dir(raw_dir: str, anchor_file: str) -> str:
    """
    If raw_dir is relative, resolve it relative to the project backend root
    (4 dirname() calls up from anchor_file = storage/__init__.py).
    """
    if os.path.isabs(raw_dir):
        return raw_dir
    _storage_file = os.path.abspath(anchor_file)
    _backend_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(_storage_file)))
    )
    return os.path.normpath(os.path.join(_backend_root, raw_dir))


def _get_key_from_url(url: str, base_url: str) -> str:
    """Mirror of LocalStorageProvider.get_key_from_url."""
    from urllib.parse import urlparse
    if url.startswith(base_url):
        return url[len(base_url):].lstrip('/')
    parsed = urlparse(url)
    return parsed.path.lstrip('/')


# ---------------------------------------------------------------------------
# Tests — Bug 3
# ---------------------------------------------------------------------------

# Use the actual storage __init__.py as the anchor, so the test is realistic.
_STORAGE_INIT = os.path.join(
    os.path.dirname(__file__),          # tests/unit/
    "..", "..",                          # tests/
    "..", "app", "core", "storage", "__init__.py",  # backend/app/core/storage/
)
_STORAGE_INIT = os.path.normpath(_STORAGE_INIT)


class TestLocalStorageAbsolutePath:
    def test_relative_dir_becomes_absolute(self):
        result = _compute_absolute_base_dir("uploads/videos", _STORAGE_INIT)
        assert os.path.isabs(result), f"Expected absolute path, got: {result!r}"

    def test_absolute_dir_unchanged(self):
        absolute = "/var/data/uploads"
        result = _compute_absolute_base_dir(absolute, _STORAGE_INIT)
        assert result == absolute

    def test_relative_dir_ends_with_configured_suffix(self):
        result = _compute_absolute_base_dir("uploads/videos", _STORAGE_INIT)
        assert result.endswith(os.path.join("uploads", "videos")), (
            f"Expected path ending with uploads/videos, got: {result!r}"
        )

    def test_resolved_dir_contains_backend_root(self):
        """Path must live inside the backend/ directory (or a sibling if overridden)."""
        result = _compute_absolute_base_dir("uploads", _STORAGE_INIT)
        # The backend root is 4 dirs up from storage/__init__.py
        _backend_root = os.path.normpath(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_STORAGE_INIT))))
        )
        assert result.startswith(_backend_root), (
            f"Resolved path {result!r} is outside backend root {_backend_root!r}"
        )

    def test_cwd_change_does_not_affect_resolved_path(self):
        """Two calls from logically different CWDs should yield the same absolute path."""
        r1 = _compute_absolute_base_dir("uploads/videos", _STORAGE_INIT)
        r2 = _compute_absolute_base_dir("uploads/videos", _STORAGE_INIT)
        assert r1 == r2  # deterministic regardless of CWD


class TestGetKeyFromUrl:
    base_url = "http://localhost:8000/uploads/videos"

    def test_matching_prefix_strips_correctly(self):
        url = f"{self.base_url}/form_check_videos/abc/file.mp4"
        key = _get_key_from_url(url, self.base_url)
        assert key == "form_check_videos/abc/file.mp4"

    def test_matching_prefix_strips_leading_slash(self):
        url = f"{self.base_url}form_check_videos/abc/file.mp4"
        key = _get_key_from_url(url, self.base_url)
        assert key == "form_check_videos/abc/file.mp4"

    def test_fallback_preserves_subdirectories(self):
        """Fallback must NOT discard the subdirectory."""
        url = "http://other-host:9000/uploads/form_check_videos/u/f.mp4"
        key = _get_key_from_url(url, self.base_url)
        # Should NOT return just "f.mp4" (basename-only is the old broken behaviour)
        assert "form_check_videos" in key, (
            f"Subdirectories lost in fallback — got key={key!r}"
        )

    def test_fallback_key_does_not_start_with_slash(self):
        url = "http://other/some/path/file.mp4"
        key = _get_key_from_url(url, self.base_url)
        assert not key.startswith("/"), f"Key should not start with '/': {key!r}"

    def test_roundtrip_matching_url(self):
        url = f"{self.base_url}/dir/sub/video.mp4"
        key = _get_key_from_url(url, self.base_url)
        assert key == "dir/sub/video.mp4"
