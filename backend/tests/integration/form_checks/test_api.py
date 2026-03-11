"""
FormCheck API — integration tests with real PostgreSQL.

These tests exercise the full request path (routing → deps → service → DB)
with only two things mocked:
  - StorageService.upload_file  (no real S3 calls)
  - process_form_check_task.delay  (no real Celery dispatch)

Fixtures are provided by conftest.py in this directory.

To run:
  docker compose -f tests/docker-compose.test.yml up -d
  cd backend
  pytest -q -m integration tests/integration/form_checks/ \\
    --override-ini="addopts=-q --asyncio-mode=auto"
"""
import io
import uuid

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SUBMIT = "/api/v1/form-checks/submit"
_HISTORY = "/api/v1/form-checks/history"
_DETAIL = "/api/v1/form-checks/{fc_id}"

_FAKE_VIDEO_BYTES = b"\x00" * 32   # minimal payload; storage is mocked


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _video_files():
    """Build the multipart 'files' dict for a /submit request."""
    return {
        "video_upload": (
            "squat_test.mp4",
            io.BytesIO(_FAKE_VIDEO_BYTES),
            "video/mp4",
        )
    }


async def _submit(client: AsyncClient) -> dict:
    """POST /submit and assert 202; return the JSON body."""
    resp = await client.post(
        _SUBMIT,
        params={"exercise_name": "squat"},
        files=_video_files(),
    )
    assert resp.status_code == 202, (
        f"Expected 202 from /submit but got {resp.status_code}: {resp.text}"
    )
    return resp.json()


# ---------------------------------------------------------------------------
# Test: submit endpoint
# ---------------------------------------------------------------------------

class TestSubmitFormCheck:
    """Tests for POST /api/v1/form-checks/submit."""

    @pytest.mark.integration
    async def test_happy_path_returns_202_with_pending_status(
        self, auth_client: AsyncClient, squat_template, int_user
    ):
        """
        A valid upload request must return 202 with status='pending' and
        the mocked S3 URL.
        """
        data = await _submit(auth_client)

        assert "id" in data, "Response missing 'id' field"
        assert data["status"] == "pending", (
            f"Expected status='pending', got {data['status']!r}"
        )
        assert data["video_url"].startswith("https://s3.example.com/test/")
        assert str(data["exercise_id"]) == str(squat_template.id)
        assert str(data["user_id"]) == str(int_user.id)

    @pytest.mark.integration
    async def test_requires_auth_returns_401(
        self, anon_client: AsyncClient
    ):
        """
        A request without an Authorization header must be rejected with 401.
        """
        resp = await anon_client.post(
            _SUBMIT,
            params={"exercise_name": "squat"},
            files=_video_files(),
        )
        assert resp.status_code == 401, (
            f"Expected 401 (Unauthorized) but got {resp.status_code}: {resp.text}"
        )

    @pytest.mark.integration
    async def test_unknown_exercise_name_returns_404(
        self, auth_client: AsyncClient
    ):
        """
        Unknown exercise names fall back to ExerciseType.OTHER ('other').
        No ExerciseTemplate with name='other' is seeded, so the service raises
        NotFoundException and the endpoint must return 404 — not a 500 crash.
        """
        resp = await auth_client.post(
            _SUBMIT,
            params={"exercise_name": "totally_unknown_exercise_xyz"},
            files=_video_files(),
        )
        # Endpoint propagates NotFoundException as 404 (not 500).
        assert resp.status_code == 404, (
            f"Expected 404 (no 'other' template seeded) but got {resp.status_code}: {resp.text}"
        )


# ---------------------------------------------------------------------------
# Test: history endpoint
# ---------------------------------------------------------------------------

class TestFormCheckHistory:
    """Tests for GET /api/v1/form-checks/history."""

    @pytest.mark.integration
    async def test_history_contains_submitted_form_check(
        self, auth_client: AsyncClient
    ):
        """
        After submitting a form check, GET /history must list it.
        """
        submitted = await _submit(auth_client)
        submitted_id = str(submitted["id"])

        resp = await auth_client.get(_HISTORY)
        assert resp.status_code == 200, resp.text

        ids = [str(fc["id"]) for fc in resp.json()]
        assert submitted_id in ids, (
            f"Submitted form-check {submitted_id} not found in history. Got: {ids}"
        )


# ---------------------------------------------------------------------------
# Test: detail / 404 endpoints
# ---------------------------------------------------------------------------

class TestFormCheckDetail:
    """Tests for GET /api/v1/form-checks/{id}."""

    @pytest.mark.integration
    async def test_get_by_id_returns_correct_form_check(
        self, auth_client: AsyncClient
    ):
        """
        GET /{id} for a form check that exists must return 200 with matching id.
        """
        submitted = await _submit(auth_client)
        fc_id = str(submitted["id"])

        resp = await auth_client.get(_DETAIL.format(fc_id=fc_id))
        assert resp.status_code == 200, resp.text
        assert str(resp.json()["id"]) == fc_id

    @pytest.mark.integration
    async def test_get_nonexistent_id_returns_404(
        self, auth_client: AsyncClient
    ):
        """
        GET /{id} for a UUID that doesn't exist must return 404.
        """
        fake_id = str(uuid.uuid4())
        resp = await auth_client.get(_DETAIL.format(fc_id=fake_id))
        assert resp.status_code == 404, (
            f"Expected 404 for unknown id but got {resp.status_code}: {resp.text}"
        )
