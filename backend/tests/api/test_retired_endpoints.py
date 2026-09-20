"""Retired endpoints must answer 501, not 202.

Each of these used to accept a request and dispatch a Celery task that could
never execute -- the task bodies were async def under a plain @app.task, so
Celery returned an un-awaited coroutine. The caller got a success code and a
task id for work that never happened.

Returning 501 is the whole point: the failure class being removed on this branch
is "work silently accepted that can never run", and a route that still answers
202 keeps it alive.
"""
import uuid

import pytest
from fastapi import status
from fastapi.testclient import TestClient

pytestmark = [pytest.mark.api, pytest.mark.unit]


@pytest.fixture(scope="module")
def client():
    from app.main import app

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def _find_route(path_fragment: str, method: str = "POST"):
    from app.main import app

    for route in app.routes:
        if path_fragment in getattr(route, "path", "") and method in getattr(
            route, "methods", set()
        ):
            return route
    return None


def test_analyze_form_route_is_declared_501():
    """The route exists and its declared status code is 501, not 202."""
    route = _find_route("/analyze-form/")
    assert route is not None, "POST /analyze-form/{video_id} should still be routed"
    assert route.status_code == status.HTTP_501_NOT_IMPLEMENTED, (
        f"declared status is {route.status_code}; it must not be 202 Accepted"
    )


def test_submit_training_video_router_is_not_mounted():
    """training_data.py is not wired into any router.

    Nothing in app/api/v1 includes it, so POST /training-data/submit_video has
    never been reachable -- which is also why its ImportError on
    process_training_video_task (a task that was never defined anywhere) went
    unnoticed. The handler was still changed to refuse with 501 before reading
    the upload, so if the router is ever mounted it fails honestly rather than
    writing a temp file and returning 500.
    """
    assert _find_route("/submit_video") is None, (
        "training_data router is now mounted -- re-enable the 501 response test "
        "below, which asserts it refuses before writing a temp file"
    )


def test_submit_training_video_handler_refuses_before_reading_the_upload():
    """Called directly, since the router is not mounted."""
    import inspect

    from app.api.v1.endpoints import training_data

    import ast
    import textwrap

    src = textwrap.dedent(inspect.getsource(training_data.submit_training_video))
    assert "501" in src

    # Strip the docstring before looking for temp-file calls -- the docstring
    # names NamedTemporaryFile while explaining why it is gone.
    fn = ast.parse(src).body[0]
    if ast.get_docstring(fn) is not None:
        fn.body = fn.body[1:]
    code = ast.unparse(ast.Module(body=fn.body, type_ignores=[]))

    assert "NamedTemporaryFile" not in code, (
        "the handler writes a temp file again; it must refuse first"
    )
    assert ".delay(" not in code, "the handler dispatches a task again"


def test_analyze_form_returns_501_before_touching_the_database(client):
    """501 must come back without a DB lookup, so it cannot masquerade as 404.

    No dependency overrides are installed here: if the handler tried to resolve
    the video it would fail on the DB, not return 501.
    """
    resp = client.post(f"/api/v1/analysis/analyze-form/{uuid.uuid4()}")
    assert resp.status_code == status.HTTP_501_NOT_IMPLEMENTED, resp.text
    assert "retired" in resp.text.lower() or "not available" in resp.text.lower()
