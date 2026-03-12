"""
FormCheck API — HTTP contract tests.

These tests exercise the HTTP layer only:
  - auth checks (401 / 403)
  - input validation (400 / 422)
  - successful response shape (200 / 202)

They use FastAPI's TestClient with dependency_overrides so they never touch
a real database, S3, or Celery.  They are marked @pytest.mark.api so the
default CI gate (`pytest -m "not integration"`) picks them up.
"""
import io
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.api import deps
from app.core.exceptions import NotFoundException

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_user() -> MagicMock:
    """Return a MagicMock that quacks like an active User for auth overrides.

    We deliberately avoid instantiating the real SQLAlchemy User model here
    because SQLAlchemy's descriptor machinery raises AttributeError when the
    mapper hasn't been fully initialised outside a session context.
    """
    u = MagicMock()
    u.id = uuid.uuid4()
    u.email = "contract@formiq.com"
    u.username = "contractuser"
    u.full_name = "Contract Tester"
    u.is_active = True
    u.is_verified = True
    u.is_superuser = False
    u.hashed_password = "irrelevant"
    return u


FAKE_USER = _fake_user()


def _form_check_response_dict(**overrides) -> dict:
    """Minimal dict that satisfies FormCheckResponse schema."""
    fc_id = uuid.uuid4()
    base = {
        "id": str(fc_id),
        "user_id": str(FAKE_USER.id),
        "exercise_id": str(uuid.uuid4()),
        "video_url": "https://s3.example.com/video.mp4",
        "status": "PENDING",
        "created_at": datetime.utcnow().isoformat(),
        "notes": None,
        "classified_exercise_slug": None,
        "classification_confidence": None,
    }
    base.update(overrides)
    return base


def _detailed_response_dict(**overrides) -> dict:
    """Minimal dict satisfying FormCheckDetailedResponse schema."""
    base = _form_check_response_dict()
    base.update({
        "score": None,
        "overall_feedback": None,
        "exercise_name": None,
        "configuration_id": None,
        "configuration_name": None,
        "form_metadata": None,
        "issues": None,
        "posture_score": None,
        "stability_score": None,
        "depth_score": None,
        "feedback_items": [],
    })
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_form_check_service() -> AsyncMock:
    svc = AsyncMock()
    svc.submit_form_check = AsyncMock(return_value=_form_check_response_dict())
    svc.list_user_form_checks_detailed = AsyncMock(return_value=[_detailed_response_dict()])
    # The actual endpoint calls get_form_check_details_with_reference (not get_form_check_detailed)
    svc.get_form_check_details_with_reference = AsyncMock(return_value=_detailed_response_dict())
    return svc


@pytest.fixture()
def client(mock_form_check_service: AsyncMock) -> TestClient:
    """TestClient with auth + form-check service overridden."""
    app.dependency_overrides[deps.get_current_active_user] = lambda: FAKE_USER
    app.dependency_overrides[deps.get_async_form_check_service] = lambda: mock_form_check_service
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def unauthenticated_client() -> TestClient:
    """TestClient with NO auth override — exercises 401 paths."""
    app.dependency_overrides.clear()
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 1. Authentication guard — unauthenticated requests are rejected
# ---------------------------------------------------------------------------

@pytest.mark.api
class TestAuthGuard:
    def test_submit_requires_auth(self, unauthenticated_client: TestClient):
        """`POST /submit` with no token returns 401."""
        resp = unauthenticated_client.post(
            "/api/v1/form-checks/submit",
            params={"exercise_name": "squat"},
            files={"video_upload": ("v.mp4", io.BytesIO(b"x"), "video/mp4")},
        )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_history_requires_auth(self, unauthenticated_client: TestClient):
        """`GET /history` with no token returns 401."""
        resp = unauthenticated_client.get("/api/v1/form-checks/history")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_form_check_requires_auth(self, unauthenticated_client: TestClient):
        """`GET /{id}` with no token returns 401."""
        resp = unauthenticated_client.get(f"/api/v1/form-checks/{uuid.uuid4()}")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# 2. Input validation — bad params are rejected before calling the service
# ---------------------------------------------------------------------------

@pytest.mark.api
class TestInputValidation:
    def test_invalid_threshold_mode_returns_400(self, client: TestClient):
        """`POST /submit` with an unknown threshold_mode returns 400."""
        resp = client.post(
            "/api/v1/form-checks/submit",
            params={"exercise_name": "squat", "threshold_mode": "YOLO"},
            files={"video_upload": ("v.mp4", io.BytesIO(b"x"), "video/mp4")},
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        # Custom exception handler may use "message" key instead of FastAPI's default "detail"
        body = resp.json()
        error_text = body.get("detail", "") or body.get("message", "")
        assert "threshold_mode" in error_text

    def test_invalid_posture_v1_mode_returns_400(self, client: TestClient):
        """`POST /submit` with an unknown posture_v1_mode returns 400."""
        resp = client.post(
            "/api/v1/form-checks/submit",
            params={"exercise_name": "squat", "posture_v1_mode": "turbo"},
            files={"video_upload": ("v.mp4", io.BytesIO(b"x"), "video/mp4")},
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        body = resp.json()
        error_text = body.get("detail", "") or body.get("message", "")
        assert "posture_v1_mode" in error_text

    def test_history_invalid_status_returns_422(self, client: TestClient):
        """`GET /history?status=BOGUS` returns 422."""
        resp = client.get("/api/v1/form-checks/history?status=BOGUS_STATUS")
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_history_invalid_date_returns_400(self, client: TestClient):
        """`GET /history?start_date=not-a-date` returns 400."""
        resp = client.get("/api/v1/form-checks/history?start_date=not-a-date")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# 3. Successful response shapes
# ---------------------------------------------------------------------------

@pytest.mark.api
class TestSuccessfulResponses:
    def test_submit_returns_202_with_id(self, client: TestClient, mock_form_check_service: AsyncMock):
        """`POST /submit` with valid params returns 202 and a form check ID."""
        resp = client.post(
            "/api/v1/form-checks/submit",
            params={"exercise_name": "squat"},
            files={"video_upload": ("v.mp4", io.BytesIO(b"fake"), "video/mp4")},
        )
        assert resp.status_code == status.HTTP_202_ACCEPTED
        body = resp.json()
        assert "id" in body
        UUID(body["id"])  # must be a valid UUID

    def test_submit_known_exercise_names(self, client: TestClient, mock_form_check_service: AsyncMock):
        """`POST /submit` accepts squat variations and rejects other exercises (V1 squat-only)."""
        # Squat names should be accepted
        for name in ["squat", "low bar squat", "high bar squat", "back squat", "front squat"]:
            resp = client.post(
                "/api/v1/form-checks/submit",
                params={"exercise_name": name},
                files={"video_upload": ("v.mp4", io.BytesIO(b"x"), "video/mp4")},
            )
            assert resp.status_code == status.HTTP_202_ACCEPTED, \
                f"Expected 202 for exercise_name='{name}', got {resp.status_code}: {resp.text}"

        # Non-squat exercises should return 400 in V1
        for name in ["deadlift", "bench press", "push up", "plank"]:
            resp = client.post(
                "/api/v1/form-checks/submit",
                params={"exercise_name": name},
                files={"video_upload": ("v.mp4", io.BytesIO(b"x"), "video/mp4")},
            )
            assert resp.status_code == status.HTTP_400_BAD_REQUEST, \
                f"Expected 400 for non-squat exercise_name='{name}', got {resp.status_code}: {resp.text}"

    def test_history_returns_list(self, client: TestClient, mock_form_check_service: AsyncMock):
        """`GET /history` returns a JSON list."""
        resp = client.get("/api/v1/form-checks/history")
        assert resp.status_code == status.HTTP_200_OK
        assert isinstance(resp.json(), list)

    def test_history_status_filter_forwarded_to_service(
        self, client: TestClient, mock_form_check_service: AsyncMock
    ):
        """`GET /history?status=COMPLETED` parses correctly and calls the service."""
        resp = client.get("/api/v1/form-checks/history?status=COMPLETED")
        assert resp.status_code == status.HTTP_200_OK
        mock_form_check_service.list_user_form_checks_detailed.assert_called_once()
        call_kwargs = mock_form_check_service.list_user_form_checks_detailed.call_args.kwargs
        from app.models.enums import FormCheckStatus
        assert call_kwargs.get("status_filter") == FormCheckStatus.COMPLETED

    def test_get_form_check_by_id_returns_200(
        self, client: TestClient, mock_form_check_service: AsyncMock
    ):
        """`GET /{id}` for an existing form check returns 200 with the record."""
        fc_id = uuid.uuid4()
        detail = _detailed_response_dict(id=str(fc_id))
        # The endpoint calls get_form_check_details_with_reference (not get_form_check_detailed)
        mock_form_check_service.get_form_check_details_with_reference.return_value = detail
        resp = client.get(f"/api/v1/form-checks/{fc_id}")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["id"] == str(fc_id)


# ---------------------------------------------------------------------------
# 4. Service-layer error propagation
# ---------------------------------------------------------------------------

@pytest.mark.api
class TestServiceErrorPropagation:
    def test_get_form_check_not_found_returns_404(
        self, client: TestClient, mock_form_check_service: AsyncMock
    ):
        """`GET /{id}` propagates NotFoundException as 404."""
        mock_form_check_service.get_form_check_details_with_reference.side_effect = NotFoundException(
            "FormCheck not found"
        )
        resp = client.get(f"/api/v1/form-checks/{uuid.uuid4()}")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_submit_not_found_returns_404(
        self, client: TestClient, mock_form_check_service: AsyncMock
    ):
        """`POST /submit` propagates NotFoundException (e.g. exercise not found) as 404."""
        mock_form_check_service.submit_form_check.side_effect = NotFoundException(
            "Exercise template not found"
        )
        resp = client.post(
            "/api/v1/form-checks/submit",
            params={"exercise_name": "squat"},
            files={"video_upload": ("v.mp4", io.BytesIO(b"x"), "video/mp4")},
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND
