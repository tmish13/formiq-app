"""G-52: an unsampled trace's all-zero id must not become the response's correlation id."""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

pytestmark = pytest.mark.unit


def _ids(n=6):
    with TestClient(app, raise_server_exceptions=False) as c:
        return [c.get("/health").headers.get("X-Correlation-ID") for _ in range(n)]


def test_unsampled_trace_yields_a_generated_id_not_zeros():
    with patch("app.core.middleware.trace_context.is_tracing_enabled", return_value=True), \
         patch("app.core.middleware.trace_context.get_trace_context",
               return_value={"trace_id": "0" * 32, "span_id": "0" * 16, "correlation_id": "0" * 16}):
        ids = _ids()
    assert all(i and i.strip("0") for i in ids), ids
    assert len(set(ids)) == len(ids), ids


def test_a_real_trace_id_is_kept():
    with patch("app.core.middleware.trace_context.is_tracing_enabled", return_value=True), \
         patch("app.core.middleware.trace_context.get_trace_context",
               return_value={"trace_id": "a" * 32, "span_id": "b" * 16, "correlation_id": "b" * 16}):
        ids = _ids(2)
    assert ids == ["b" * 16, "b" * 16]


def test_an_incoming_header_wins():
    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.get("/health", headers={"X-Correlation-ID": "client-supplied"})
    assert r.headers.get("X-Correlation-ID") == "client-supplied"
