"""/ml-analysis carries the knees-forward localisation and the verdict's bar status."""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.main import app

pytestmark = pytest.mark.api

USER = MagicMock(); USER.id = uuid.uuid4(); USER.is_active = True; USER.is_superuser = False


def _client_with(form_check):
    session = AsyncMock()
    res = MagicMock(); res.scalars.return_value.first.return_value = form_check
    session.execute = AsyncMock(return_value=res)

    async def _db():
        yield session
    app.dependency_overrides[deps.get_current_active_user] = lambda: USER
    app.dependency_overrides[deps.get_async_db] = _db
    return TestClient(app, raise_server_exceptions=False)


def _fc(rules_shadow):
    fc = MagicMock()
    fc.results = {"posture_v1": {"decision": "fault", "prob_fault": 0.81, "confidence": 0.62},
                  "rules_shadow": rules_shadow}
    fc.posture_score = 41; fc.stability_score = None; fc.depth_score = None; fc.confidence_score = 0.62
    return fc


def teardown_module(_):
    app.dependency_overrides.clear()


def test_localisation_is_surfaced_from_the_recorded_rule_verdict():
    kf = {"decision": "OBSERVED", "score": 0.0656, "threshold": 0.05, "coverage": 1.0, "abstain_reason": None,
          "view": {"kind": "oblique"}, "indicators": [{"detail": {"peak_time_sec": 1.267, "peak_frame": 38}}]}
    with _client_with(_fc({"knees_forward": kf})) as c:
        r = c.get(f"/api/v1/form-checks/{uuid.uuid4()}/ml-analysis")
    assert r.status_code == 200, r.text
    loc = r.json()["localisation"]["knees_forward"]
    assert loc["observed"] is True and loc["peak_time_sec"] == 1.267 and loc["view"] == "oblique"
    assert loc["travel_torso_lengths"] == 0.0656 and "polarity only" in loc["validated"]


def test_verdict_status_says_experimental_and_below_the_bar():
    with _client_with(_fc({"knees_forward": {"decision": "UNCERTAIN", "abstain_reason": "no_bottom"}})) as c:
        r = c.get(f"/api/v1/form-checks/{uuid.uuid4()}/ml-analysis")
    body = r.json()
    assert body["verdict_status"]["meets_acceptance_bar"] is False
    assert body["verdict_status"]["presentation"] == "experimental"
    assert body["localisation"]["knees_forward"]["observed"] is False
    assert body["localisation"]["knees_forward"]["abstain_reason"] == "no_bottom"


def test_no_rules_recorded_means_no_localisation_not_a_crash():
    with _client_with(_fc({})) as c:
        r = c.get(f"/api/v1/form-checks/{uuid.uuid4()}/ml-analysis")
    assert r.status_code == 200
    assert r.json()["localisation"]["knees_forward"] is None
