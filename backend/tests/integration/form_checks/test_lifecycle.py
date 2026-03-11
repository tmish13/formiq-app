"""
Integration test: form-check lifecycle end-to-end.

Runs against the real PostgreSQL test instance (docker-compose).

Flow:
  1. Submit a form check (POST /submit) → 202 Accepted, status=pending
  2. Directly mark it completed in the DB with ML scores (bypasses Celery)
  3. Fetch the form check (GET /form-checks/{id}) → scores must be present
  4. Fetch progress stats (GET /progress/stats) → totalAnalyses >= 1

Requires:
  docker compose -f tests/docker-compose.test.yml up -d

Run:
  cd backend
  pytest -q -m integration tests/integration/form_checks/test_lifecycle.py \\
    --override-ini="addopts=-q --asyncio-mode=auto"
"""
import io
import uuid
from datetime import datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.form_check import FormCheck
from app.models.enums import FormCheckStatus

pytestmark = pytest.mark.integration

_SUBMIT = "/api/v1/form-checks/submit"
_FAKE_VIDEO = b"\x00" * 32  # minimal payload; storage is mocked


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _video_files() -> dict:
    """Build multipart 'files' dict with a unique filename per call."""
    filename = f"squat_lifecycle_{uuid.uuid4().hex[:10]}.mp4"
    return {
        "video_upload": (filename, io.BytesIO(_FAKE_VIDEO), "video/mp4"),
    }


async def _submit_form_check(client: AsyncClient) -> str:
    """POST /submit and assert 202; return the new form-check UUID string."""
    resp = await client.post(
        _SUBMIT,
        params={"exercise_name": "squat"},
        files=_video_files(),
    )
    assert resp.status_code == 202, f"Expected 202, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["status"] == "pending"
    fc_id = data["id"]
    # Sanity-check: valid UUID
    uuid.UUID(fc_id)
    return fc_id


async def _mark_completed(pg_factory, fc_id: str) -> None:
    """Directly advance a FormCheck to completed with ML scores (no Celery)."""
    async with pg_factory() as session:
        fc = await session.get(FormCheck, uuid.UUID(fc_id))
        assert fc is not None, f"FormCheck {fc_id} not found in DB"
        fc.status = FormCheckStatus.COMPLETED
        fc.score = 82.0
        fc.posture_score = 78.0
        fc.stability_score = 85.0
        fc.depth_score = 83.0
        fc.confidence_score = 0.87
        fc.overall_feedback = "Good squat form. Focus on keeping knees tracking over toes."
        fc.updated_at = datetime.utcnow()
        await session.commit()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestFormCheckLifecycle:

    @pytest.mark.asyncio
    async def test_submit_returns_202_with_pending_status(self, auth_client: AsyncClient):
        """POST /submit must return 202 Accepted with status=pending."""
        fc_id = await _submit_form_check(auth_client)
        assert isinstance(fc_id, str)

    @pytest.mark.asyncio
    async def test_lifecycle_scores_visible_after_completion(
        self,
        auth_client: AsyncClient,
        pg_factory,
    ):
        """
        Full lifecycle:
          submit → directly mark completed → GET /{id} returns scores.
        """
        fc_id = await _submit_form_check(auth_client)
        await _mark_completed(pg_factory, fc_id)

        # GET form check — status and ML scores must be present
        resp = await auth_client.get(f"/api/v1/form-checks/{fc_id}")
        assert resp.status_code == 200, resp.text
        body = resp.json()

        assert body["status"] == "completed"
        assert body["score"] == 82.0
        # ML sub-scores (nullable in schema, must be present when set)
        assert body.get("posture_score") == 78.0
        assert body.get("stability_score") == 85.0
        assert body.get("depth_score") == 83.0
        # confidence_score is an ORM column but not exposed in FormCheckDetailedResponse;
        # assert that the field is absent or None rather than failing on the exact value.
        assert body.get("confidence_score") is None
        assert body.get("overall_feedback") is not None

    @pytest.mark.asyncio
    async def test_progress_stats_counts_completed_analysis(
        self,
        auth_client: AsyncClient,
        pg_factory,
    ):
        """
        After at least one completed check, /progress/stats must report
        totalAnalyses >= 1 and return a valid response shape.
        """
        fc_id = await _submit_form_check(auth_client)
        await _mark_completed(pg_factory, fc_id)

        resp = await auth_client.get("/api/v1/progress/stats")
        assert resp.status_code == 200, resp.text
        stats = resp.json()

        assert stats["totalAnalyses"] >= 1
        assert isinstance(stats["averageScore"], (int, float))
        assert stats["recentTrend"] in {"improving", "declining", "stable"}
        assert isinstance(stats["currentStreak"], int)
        assert isinstance(stats["exerciseTypeBreakdown"], dict)

    @pytest.mark.asyncio
    async def test_get_form_check_returns_exercise_info(
        self,
        auth_client: AsyncClient,
        pg_factory,
    ):
        """Form check GET response must include exercise-related fields."""
        fc_id = await _submit_form_check(auth_client)
        await _mark_completed(pg_factory, fc_id)

        resp = await auth_client.get(f"/api/v1/form-checks/{fc_id}")
        assert resp.status_code == 200, resp.text
        body = resp.json()

        # Exercise info must be present (wired via squat_template fixture)
        assert body.get("exercise_id") is not None or body.get("exercise_type") is not None

    @pytest.mark.asyncio
    async def test_unauthenticated_submit_returns_401(self, anon_client: AsyncClient):
        """Unauthenticated requests must be rejected at the gate."""
        resp = await anon_client.post(
            _SUBMIT,
            params={"exercise_name": "squat"},
            files=_video_files(),
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_unauthenticated_get_returns_401(self, anon_client: AsyncClient):
        """GET on a valid UUID without auth must return 401."""
        fake_id = str(uuid.uuid4())
        resp = await anon_client.get(f"/api/v1/form-checks/{fake_id}")
        assert resp.status_code == 401
