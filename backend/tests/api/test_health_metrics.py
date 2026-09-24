"""/health/metrics used to 500 on every call (HealthService() without arguments, a method that
did not exist); /health/rate-limits did the same. Now: one real exposition endpoint, one 404."""
import pytest
from fastapi.testclient import TestClient

from app.main import app

pytestmark = pytest.mark.api


@pytest.fixture()
def client():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def test_metrics_is_a_prometheus_text_exposition(client):
    resp = client.get("/health/metrics")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")
    assert "# HELP" in resp.text and ("process_" in resp.text or "python_" in resp.text)


def test_rate_limits_route_is_gone(client):
    assert client.get("/health/rate-limits").status_code == 404
