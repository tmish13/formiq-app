"""The two HTTPException handlers: status, body shape, and forwarded headers.

Written after a header-forwarding edit mangled the Starlette handler into
`str(exc.detail, headers=...)` -- syntactically valid, a TypeError at runtime, and every
404 on the live API became a 500 for a night. The FastAPI handler had a test; this one did not.
"""
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.main import app

pytestmark = pytest.mark.api


@pytest.fixture()
def client():
    app.dependency_overrides.clear()
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def test_an_unknown_route_is_a_404_with_the_error_body(client):
    resp = client.get("/api/v1/definitely-not-a-route")
    assert resp.status_code == 404, resp.text
    body = resp.json()
    assert body.get("code") == "HTTP_ERROR" and body.get("status") == 404, body


def test_starlette_exception_headers_are_forwarded(client):
    @app.get("/__test_starlette_headers")
    async def _boom():
        raise StarletteHTTPException(status_code=429, detail="slow down", headers={"Retry-After": "7"})
    try:
        resp = client.get("/__test_starlette_headers")
    finally:
        app.router.routes[:] = [r for r in app.router.routes if getattr(r, "path", "") != "/__test_starlette_headers"]
    assert resp.status_code == 429
    assert resp.headers.get("Retry-After") == "7"
    assert resp.json()["message"] == "slow down"


def test_fastapi_exception_headers_are_forwarded(client):
    @app.get("/__test_fastapi_headers")
    async def _boom():
        raise HTTPException(status_code=401, detail="nope", headers={"WWW-Authenticate": "Bearer"})
    try:
        resp = client.get("/__test_fastapi_headers")
    finally:
        app.router.routes[:] = [r for r in app.router.routes if getattr(r, "path", "") != "/__test_fastapi_headers"]
    assert resp.status_code == 401
    assert resp.headers.get("WWW-Authenticate") == "Bearer"


def test_a_validation_failure_on_register_does_not_log_the_submitted_password(client):
    """G-16: pydantic's error objects carry `input`, i.e. the whole submitted body. The app's
    loggers do not propagate to root, so the handler's logger is observed directly."""
    from unittest.mock import MagicMock, patch
    from app.core.redis import get_redis

    app.dependency_overrides[get_redis] = lambda: MagicMock()
    try:
        with patch("app.core.exception_handlers.logger") as lg:
            resp = client.post(
                "/api/v1/auth/register",
                json={"email": "not-an-email", "password": "hunter2-secret-value",
                      "confirm_password": "hunter2-secret-value", "full_name": "X"},
            )
    finally:
        app.dependency_overrides.pop(get_redis, None)
    assert resp.status_code == 422
    calls = [c for c in lg.warning.call_args_list if "Request validation failed" in str(c.args[0])]
    assert calls, "the validation handler did not log"
    for c in calls:
        assert "hunter2-secret-value" not in str(c.args[0])
        errors = c.kwargs["extra"]["validation_errors"]
        assert errors and all("input" not in e for e in errors)
        assert "hunter2-secret-value" not in str(errors)
