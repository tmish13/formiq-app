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
