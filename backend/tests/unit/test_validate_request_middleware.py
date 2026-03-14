"""
Unit tests for EnhancedValidateRequestMiddleware.

Covers the production bug where HEAD / and GET / were rejected with
400 "Invalid content type" because _validate_content_type() checked
content-type on ALL methods including those that never carry a body.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch


# ---------------------------------------------------------------------------
# Helpers — build a minimal mock Request
# ---------------------------------------------------------------------------

def _make_request(method: str, path: str, headers: dict | None = None):
    """Return a mock Request-like object for unit-testing middleware methods."""
    req = MagicMock()
    req.method = method.upper()
    req.url.path = path
    req.headers = {k.lower(): v for k, v in (headers or {}).items()}
    return req


# ---------------------------------------------------------------------------
# _validate_content_type — the method that caused the production bug
# ---------------------------------------------------------------------------

class TestValidateContentType:
    """_validate_content_type() must pass GET/HEAD/OPTIONS regardless of headers."""

    @pytest.fixture(autouse=True)
    def middleware(self):
        from app.core.middleware.validate_request import EnhancedValidateRequestMiddleware
        with patch("app.core.middleware.validate_request.settings") as mock_settings:
            mock_settings.MAX_CONTENT_LENGTH = 10 * 1024 * 1024
            mock_settings.CUSTOM_VALIDATORS = {}
            mw = EnhancedValidateRequestMiddleware.__new__(EnhancedValidateRequestMiddleware)
            mw.max_content_length = mock_settings.MAX_CONTENT_LENGTH
            mw.allowed_content_types = {
                "application/json",
                "application/x-www-form-urlencoded",
                "multipart/form-data",
            }
            mw.custom_validators = {}
            mw.skip_paths = ["/api/", "/health", "/docs", "/redoc", "/openapi.json"]
        self.mw = mw

    # -- Methods that must always pass (no body possible) --

    def test_get_no_content_type_passes(self):
        req = _make_request("GET", "/some/path")
        assert self.mw._validate_content_type(req) is True

    def test_head_no_content_type_passes(self):
        """HEAD / is the exact Render health-probe case that was failing."""
        req = _make_request("HEAD", "/")
        assert self.mw._validate_content_type(req) is True

    def test_options_no_content_type_passes(self):
        """OPTIONS pre-flight must never be blocked."""
        req = _make_request("OPTIONS", "/api/v1/auth/login")
        assert self.mw._validate_content_type(req) is True

    def test_get_with_irrelevant_content_type_still_passes(self):
        """Even if a GET somehow includes a content-type header, don't block it."""
        req = _make_request("GET", "/", {"content-type": "text/html"})
        assert self.mw._validate_content_type(req) is True

    # -- POST/PUT/PATCH — body methods keep existing behavior --

    def test_post_json_passes(self):
        req = _make_request("POST", "/api/v1/auth/register",
                            {"content-type": "application/json"})
        assert self.mw._validate_content_type(req) is True

    def test_post_form_passes(self):
        req = _make_request("POST", "/api/v1/auth/login",
                            {"content-type": "application/x-www-form-urlencoded"})
        assert self.mw._validate_content_type(req) is True

    def test_post_multipart_with_boundary_passes(self):
        req = _make_request("POST", "/api/v1/videos/upload",
                            {"content-type": "multipart/form-data; boundary=----abc"})
        assert self.mw._validate_content_type(req) is True

    def test_post_multipart_without_boundary_fails(self):
        """multipart/form-data without boundary= is malformed — must fail."""
        req = _make_request("POST", "/api/v1/videos/upload",
                            {"content-type": "multipart/form-data"})
        assert self.mw._validate_content_type(req) is False

    def test_post_unknown_content_type_fails(self):
        req = _make_request("POST", "/some/endpoint",
                            {"content-type": "text/plain"})
        assert self.mw._validate_content_type(req) is False

    def test_post_no_content_type_passes(self):
        """Existing relaxed behavior: POST with no content-type is allowed through."""
        req = _make_request("POST", "/api/v1/auth/register")
        assert self.mw._validate_content_type(req) is True


# ---------------------------------------------------------------------------
# _should_skip_validation — confirm root path is in skip list
# ---------------------------------------------------------------------------

class TestShouldSkipValidation:

    @pytest.fixture(autouse=True)
    def middleware(self):
        from app.core.middleware.validate_request import EnhancedValidateRequestMiddleware
        with patch("app.core.middleware.validate_request.settings") as mock_settings:
            mock_settings.MAX_CONTENT_LENGTH = 10 * 1024 * 1024
            mock_settings.CUSTOM_VALIDATORS = {}
            mw = EnhancedValidateRequestMiddleware.__new__(EnhancedValidateRequestMiddleware)
            mw.max_content_length = mock_settings.MAX_CONTENT_LENGTH
            mw.allowed_content_types = {
                "application/json",
                "application/x-www-form-urlencoded",
                "multipart/form-data",
            }
            mw.custom_validators = {}
            mw.skip_paths = ["/api/", "/health", "/docs", "/redoc", "/openapi.json"]
        self.mw = mw

    def test_root_path_is_skipped(self):
        # "/" is skipped via exact match (not startswith, which would match all paths).
        req = _make_request("GET", "/")
        assert self.mw._should_skip_validation(req) is True

    def test_head_root_path_is_skipped(self):
        req = _make_request("HEAD", "/")
        assert self.mw._should_skip_validation(req) is True

    def test_health_is_skipped(self):
        req = _make_request("GET", "/health")
        assert self.mw._should_skip_validation(req) is True

    def test_api_routes_are_skipped(self):
        req = _make_request("POST", "/api/v1/auth/login")
        assert self.mw._should_skip_validation(req) is True

    def test_docs_is_skipped(self):
        req = _make_request("GET", "/docs")
        assert self.mw._should_skip_validation(req) is True

    def test_non_skipped_path_is_not_skipped(self):
        req = _make_request("POST", "/webhook/stripe")
        assert self.mw._should_skip_validation(req) is False
