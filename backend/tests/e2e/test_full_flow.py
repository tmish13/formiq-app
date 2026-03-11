"""
Golden-path E2E test: full video-to-form-check user journey.

This single test chains the entire happy path:
  1. Request a presigned upload URL (video upload-url)
  2. Confirm the upload (upload-complete)  → video is now PROCESSING
  3. Submit a form check for analysis      → form check created (PENDING)
  4. Verify the form check appears in history

Services used:
  - Real Postgres + Redis (via docker-compose.test.yml on :5434/:6380)
  - Mocked StorageService   (no real AWS calls)
  - Mocked Celery tasks      (no real workers)

To run:
  docker compose -f tests/docker-compose.test.yml up -d
  cd backend
  pytest -q -m e2e tests/e2e/ \\
    --override-ini="addopts=-q --asyncio-mode=auto"
"""
import io
import uuid
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import select

pytestmark = pytest.mark.e2e

# ---------------------------------------------------------------------------
# API paths (must match app/api/v1/api.py prefixes)
# ---------------------------------------------------------------------------

_UPLOAD_URL      = "/api/v1/videos/upload-url"
_UPLOAD_COMPLETE = "/api/v1/videos/upload-complete"
_VIDEO_DETAIL    = "/api/v1/videos/{video_id}"
_FC_SUBMIT       = "/api/v1/form-checks/submit"
_FC_HISTORY      = "/api/v1/form-checks/history"

# Minimal bytes — storage is mocked so content doesn't matter
_FAKE_VIDEO_BYTES = b"\x00" * 64


# ---------------------------------------------------------------------------
# Golden-path test
# ---------------------------------------------------------------------------

@pytest.mark.e2e
async def test_full_video_to_form_check_flow(
    e2e_client: AsyncClient,
    pg_factory,
    e2e_user,
    squat_template,
):
    """
    Complete user journey:
      upload-url → upload-complete → form-check submit → history

    Each step asserts the HTTP contract and the DB state written by the
    service layer, so failures are easy to pinpoint.
    """

    # ------------------------------------------------------------------
    # Step 1 — Request a presigned upload URL
    # ------------------------------------------------------------------
    unique_filename = f"e2e_{uuid.uuid4().hex[:10]}.mp4"
    resp = await e2e_client.post(
        _UPLOAD_URL,
        json={"filename": unique_filename, "content_type": "video/mp4"},
    )
    assert resp.status_code == 200, (
        f"[Step 1] Expected 200 from upload-url, got {resp.status_code}: {resp.text}"
    )
    upload_data = resp.json()
    assert "uploadUrl" in upload_data and upload_data["uploadUrl"], (
        "[Step 1] uploadUrl must be non-null in the response"
    )
    assert "videoId" in upload_data and upload_data["videoId"], (
        "[Step 1] videoId must be non-null in the response"
    )
    video_id: str = upload_data["videoId"]

    # ------------------------------------------------------------------
    # Step 2 — Retrieve the object_key from DB and confirm the upload
    # ------------------------------------------------------------------
    from app.models.video import Video

    async with pg_factory() as session:
        result = await session.execute(select(Video).where(Video.id == UUID(video_id)))
        video_row = result.scalar_one()
        object_key = video_row.object_key

    assert object_key, "[Step 2] object_key must be stored in DB after upload-url"

    resp = await e2e_client.post(
        _UPLOAD_COMPLETE,
        json={"videoId": video_id, "object_key": object_key},
    )
    assert resp.status_code == 200, (
        f"[Step 2] Expected 200 from upload-complete, got {resp.status_code}: {resp.text}"
    )
    complete_data = resp.json()
    assert str(complete_data["id"]) == video_id, (
        "[Step 2] Response id must match the requested video_id"
    )
    # After Celery dispatch the service transitions the video to PROCESSING
    assert complete_data["status"] == "processing", (
        f"[Step 2] Expected status='processing' after upload-complete, "
        f"got {complete_data['status']!r}"
    )

    # ------------------------------------------------------------------
    # Step 3 — Submit a form check for the same exercise
    #
    # The form-check submit endpoint accepts a multipart file upload
    # (StorageService.upload_file is mocked — no real S3 call).
    # ------------------------------------------------------------------
    resp = await e2e_client.post(
        _FC_SUBMIT,
        params={"exercise_name": "squat"},
        files={
            "video_upload": (
                unique_filename,
                io.BytesIO(_FAKE_VIDEO_BYTES),
                "video/mp4",
            )
        },
    )
    assert resp.status_code == 202, (
        f"[Step 3] Expected 202 from form-check submit, got {resp.status_code}: {resp.text}"
    )
    fc_data = resp.json()
    assert "id" in fc_data and fc_data["id"], (
        "[Step 3] Form check response must contain a non-null 'id'"
    )
    assert fc_data["status"] == "pending", (
        f"[Step 3] Newly submitted form check must have status='pending', "
        f"got {fc_data['status']!r}"
    )
    assert str(fc_data["user_id"]) == str(e2e_user.id), (
        "[Step 3] Form check must be associated with the authenticated user"
    )
    form_check_id: str = str(fc_data["id"])

    # ------------------------------------------------------------------
    # Step 4 — Verify the form check appears in history
    # ------------------------------------------------------------------
    resp = await e2e_client.get(_FC_HISTORY)
    assert resp.status_code == 200, (
        f"[Step 4] Expected 200 from /history, got {resp.status_code}: {resp.text}"
    )
    history_ids = [str(fc["id"]) for fc in resp.json()]
    assert form_check_id in history_ids, (
        f"[Step 4] Submitted form check {form_check_id} not found in history. "
        f"Got ids: {history_ids}"
    )
