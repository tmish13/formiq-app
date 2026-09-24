"""End to end, against the running stack: one corpus clip through the API, the worker, and the trail.

    pytest -m e2e tests/e2e/test_live_pipeline.py --override-ini="addopts=--asyncio-mode=auto"

Env: E2E_API_BASE (default http://localhost:8000), E2E_VIDEO (a squat .mp4; default: the first
file under $E2E_VIDEO_DIR or /videos), E2E_TIMEOUT_S (default 300). The trail assertions need the
compose DB reachable through the app's own settings (POSTGRES_SERVER etc.), i.e. run this from the
deployment image on the compose network, or on the host with the DB port published.

This replaces tests/integration/tasks/test_analysis_tasks.py, which patched names that no longer
existed and asserted a function defined nowhere, and passed nothing because it was never run
(G-13). Marked e2e: excluded from the CI default like every test that needs the stack.
"""
import os
import time
import uuid
from pathlib import Path

import pytest
import requests

pytestmark = [pytest.mark.e2e, pytest.mark.slow]

API = os.getenv("E2E_API_BASE", "http://localhost:8000")
TIMEOUT_S = int(os.getenv("E2E_TIMEOUT_S", "600"))


def _video() -> Path:
    if os.getenv("E2E_VIDEO"):
        return Path(os.environ["E2E_VIDEO"])
    for d in (os.getenv("E2E_VIDEO_DIR"), "/videos", os.path.expanduser("~/Desktop/Squat More/Labeled_Dataset/videos")):
        if d and Path(d).is_dir():
            files = sorted(Path(d).glob("*.mp4"))
            if files:
                return files[0]
    pytest.skip("no video available: set E2E_VIDEO")


@pytest.fixture(scope="module")
def session():
    email = f"e2e_{int(time.time())}_{uuid.uuid4().hex[:6]}@example.com"
    password = "E2eSmoke123!"
    r = requests.post(f"{API}/api/v1/auth/register", json={
        "email": email, "password": password, "confirm_password": password, "full_name": "E2E"}, timeout=30)
    assert r.status_code in (200, 201), r.text
    r = requests.post(f"{API}/api/v1/auth/login", data={"username": email, "password": password}, timeout=30)
    assert r.status_code == 200, r.text
    return {"email": email, "headers": {"Authorization": f"Bearer {r.json()['access_token']}"}}


@pytest.mark.timeout(TIMEOUT_S + 120)   # pytest.ini's 300 s default is shorter than a cold worker + a queue
def test_one_clip_reaches_a_terminal_state_with_a_verdict(session):
    video = _video()
    with video.open("rb") as fh:
        r = requests.post(f"{API}/api/v1/form-checks/submit", params={"exercise_name": "squat"},
                          headers=session["headers"], files={"video_upload": (video.name, fh, "video/mp4")}, timeout=120)
    assert r.status_code == 202, r.text
    fc_id = r.json()["id"]
    deadline = time.time() + TIMEOUT_S
    status = None
    while time.time() < deadline:
        s = requests.get(f"{API}/api/v1/form-checks/{fc_id}", headers=session["headers"], timeout=30)
        assert s.status_code == 200, s.text
        status = str(s.json()["status"]).upper()      # the API serialises the enum VALUE ("completed"); the DB stores the NAME
        if status in ("COMPLETED", "FAILED"):
            break
        time.sleep(3)
    assert status == "COMPLETED", f"form check {fc_id} ended as {status!r}"
    ml = requests.get(f"{API}/api/v1/form-checks/{fc_id}/ml-analysis", headers=session["headers"], timeout=30)
    assert ml.status_code == 200, ml.text
    pv1 = ml.json().get("posture_v1") or {}
    assert pv1.get("decision") in ("good_form", "fault", "uncertain"), pv1
    session["form_check_id"] = fc_id


@pytest.mark.asyncio
async def test_the_trail_for_that_user_passes_a1_to_a10(session):
    """The same assertions as bench/trail_report.sh, scoped to this run's user."""
    from sqlalchemy import text
    from app.core.database import get_async_session_for_celery

    ids = ("SELECT id FROM form_checks WHERE user_id IN "
           f"(SELECT id FROM users WHERE email = '{session['email']}')")
    checks = {
        "A1 terminal form checks with no run row":
            f"SELECT count(*) FROM form_checks f WHERE f.id IN ({ids}) AND f.status IN ('COMPLETED','FAILED') "
            "AND NOT EXISTS (SELECT 1 FROM analysis_runs r WHERE r.form_check_id = f.id)",
        "A2 completed runs with no checker decision":
            f"SELECT count(*) FROM analysis_runs r WHERE r.form_check_id IN ({ids}) AND r.status='completed' "
            "AND NOT EXISTS (SELECT 1 FROM checker_decisions d WHERE d.run_id = r.id)",
        "A3 closed runs missing a pose_pass_id":
            f"SELECT count(*) FROM analysis_runs WHERE form_check_id IN ({ids}) AND finished_at IS NOT NULL "
            "AND status='completed' AND pose_pass_id IS NULL",
        "A4 runs still open":
            f"SELECT count(*) FROM analysis_runs WHERE form_check_id IN ({ids}) AND finished_at IS NULL",
        "A5 form checks carrying a depth_score":
            f"SELECT count(*) FROM form_checks WHERE id IN ({ids}) AND depth_score IS NOT NULL",
        "A6 rule decisions not marked unfitted+advisory":
            f"SELECT count(*) FROM checker_decisions d JOIN analysis_runs r ON r.id = d.run_id WHERE r.form_check_id IN ({ids}) "
            "AND d.checker_kind = 'rule' AND NOT (d.fitted = false AND d.advisory = true)",
        "A7 answered rule decisions with no score":
            f"SELECT count(*) FROM checker_decisions d JOIN analysis_runs r ON r.id = d.run_id WHERE r.form_check_id IN ({ids}) "
            "AND d.checker_kind = 'rule' AND d.abstained = false AND d.score IS NULL",
        "A8 decisions with no inputs_digest":
            f"SELECT count(*) FROM checker_decisions d JOIN analysis_runs r ON r.id = d.run_id WHERE r.form_check_id IN ({ids}) "
            "AND d.checker_kind = 'rule' AND d.inputs_digest IS NULL",
        "A9 completed runs with no n_frames":
            f"SELECT count(*) FROM analysis_runs WHERE form_check_id IN ({ids}) AND status = 'completed' AND n_frames IS NULL",
        "A10 terminal rows disagreeing with their latest closed run, or judged twice":
            f"SELECT (SELECT count(*) FROM form_checks f JOIN LATERAL (SELECT outcome_status FROM analysis_runs r "
            "WHERE r.form_check_id = f.id AND r.status IN ('completed','failed') ORDER BY finished_at DESC LIMIT 1) lr ON true "
            f"WHERE f.id IN ({ids}) AND f.status IN ('COMPLETED','FAILED') AND upper(lr.outcome_status) <> f.status::text) "
            f"+ (SELECT count(*) FROM (SELECT form_check_id FROM analysis_runs WHERE form_check_id IN ({ids}) AND status = 'completed' "
            "AND COALESCE(pose_source,'') <> 'cache' GROUP BY form_check_id HAVING count(*) > 1) d)",
    }
    async with get_async_session_for_celery() as db:
        n = (await db.execute(text(f"SELECT count(*) FROM ({ids}) x"))).scalar_one()
        assert n >= 1, "the submit test must run first"
        done = (await db.execute(text(f"SELECT count(*) FROM form_checks WHERE id IN ({ids}) AND status = 'COMPLETED'"))).scalar_one()
        assert done >= 1, "no COMPLETED form check for this user: the trail assertions would pass vacuously"
        failures = []
        for name, sql in checks.items():
            got = (await db.execute(text(sql))).scalar_one()
            if got != 0:
                failures.append(f"{name}: got {got}, want 0")
    assert not failures, "\n".join(failures)
