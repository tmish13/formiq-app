"""G-36: above a bounded number of in-flight uploads the API answers 503 + Retry-After.

At 20 simultaneous uploads gunicorn workers were OOM-killed and requests vanished with
no server-side log. The bound is checked before the file is read, so a refused upload
costs no memory.
"""
import asyncio
import io
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.api.v1.endpoints import form_checks as ep
from app.main import app

pytestmark = pytest.mark.api

FAKE_USER = MagicMock()
FAKE_USER.id = uuid.uuid4()
FAKE_USER.email = "bp@example.com"
FAKE_USER.is_active = True
FAKE_USER.is_superuser = False


def _submit(client):
    return client.post(
        "/api/v1/form-checks/submit",
        params={"exercise_name": "squat"},
        files={"video_upload": ("v.mp4", io.BytesIO(b"\x00" * 64), "video/mp4")},
    )


@pytest.fixture()
def client():
    svc = AsyncMock()
    svc.submit_form_check = AsyncMock(return_value={          # the shape FormCheckResponse requires
        "id": str(uuid.uuid4()), "user_id": str(FAKE_USER.id), "exercise_id": str(uuid.uuid4()),
        "video_url": "https://s3.example.com/video.mp4", "status": "PENDING",
        "created_at": "2026-09-24T00:00:00", "notes": None,
        "classified_exercise_slug": None, "classification_confidence": None,
    })
    app.dependency_overrides[deps.get_current_active_user] = lambda: FAKE_USER
    app.dependency_overrides[deps.get_async_form_check_service] = lambda: svc
    with TestClient(app, raise_server_exceptions=False) as c:
        c.svc = svc
        yield c
    app.dependency_overrides.clear()


def test_a_full_house_answers_503_with_retry_after_and_reads_nothing(client):
    with patch.object(ep, "_upload_slots", asyncio.Semaphore(0)):      # every slot taken
        resp = _submit(client)
    assert resp.status_code == 503, resp.text
    assert resp.headers.get("Retry-After") == "5"
    body = resp.json()
    assert "in flight" in (body.get("message") or body.get("detail") or ""), body
    client.svc.submit_form_check.assert_not_awaited()                   # refused before the read


def test_a_free_slot_admits_the_upload(client):
    with patch.object(ep, "_upload_slots", asyncio.Semaphore(1)):
        resp = _submit(client)
    assert resp.status_code in (200, 202), resp.text
    client.svc.submit_form_check.assert_awaited_once()


def test_the_slot_is_released_after_the_upload(client):
    sem = asyncio.Semaphore(1)
    with patch.object(ep, "_upload_slots", sem):
        _submit(client)
        assert not sem.locked()                                         # released on the way out
        resp = _submit(client)
    assert resp.status_code in (200, 202)


def test_the_bound_is_documented_and_at_least_one():
    assert ep.UPLOAD_MAX_INFLIGHT >= 1
    route = next(r for r in app.routes if getattr(r, "path", "") == "/api/v1/form-checks/submit")
    assert 503 in route.responses
