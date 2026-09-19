"""
E2E: the analysis pipeline actually produces a result.

tests/e2e/test_full_flow.py stops at status == "pending" — it never runs the
Celery task, so nothing in the suite asserts that a video is ever analysed.
This test closes that gap (audit gap G-13).

It exercises the real pipeline: OpenCV decode -> MediaPipe pose extraction ->
151-d feature extraction -> PostureV1 CNN-LSTM inference -> scoring -> DB write
-> telemetry row. Only S3 is mocked (the video is read from local disk).

Run (inside the app container, which has torch + mediapipe):

    # one-time: test-only plugins are in requirements-test.txt, not the image
    docker compose -f backend/deployment/docker-compose.yml exec --user root app \
      pip install pytest-timeout==2.2.0 pytest-env==1.1.1
    docker compose -f backend/deployment/docker-compose.yml exec -T db \
      psql -U postgres -c "CREATE DATABASE formiq_test;"

    docker compose -f backend/deployment/docker-compose.yml exec \
      -e ENVIRONMENT=test \
      -e TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/formiq_test \
      -e REDIS_URL=redis://redis:6379/0 -e REDIS_HOST=redis -e REDIS_PORT=6379 \
      app pytest -m e2e tests/e2e/test_pipeline_completes.py \
      --override-ini="addopts=--asyncio-mode=auto" \
      --import-mode=importlib -p no:randomly

`--import-mode=importlib` is required in the container: backend/ is mounted at
/app and contains __init__.py, so pytest's default "prepend" mode walks up past
it and inserts "/" on sys.path, making `import app` resolve to /app (the backend
package) instead of /app/app. importlib mode skips that insertion.

Measured runtime: ~9 s once the image is warm.
"""
import io
import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy import select

from app.models.form_check import FormCheck
from app.models.video import Video
from app.models.enums import FormCheckStatus
from app.models.telemetry import PostureV1InferenceLog

pytestmark = pytest.mark.e2e

_FC_SUBMIT = "/api/v1/form-checks/submit"

# A known-good squat from the repo's own fixture set. scripts/output/
# posture_v1_labels_and_results.csv labels this video good_form.
_TEST_VIDEO = (
    Path(__file__).resolve().parents[2] / "test_videos" / "good" / "T6ad8Et3C5Q_good_rep_1.mp4"
)


@pytest.mark.e2e
async def test_pipeline_produces_a_real_posture_v1_result(e2e_client, pg_factory):
    """Submit a real squat video, run the analysis task, assert a real result."""
    assert _TEST_VIDEO.exists(), f"fixture video missing: {_TEST_VIDEO}"

    # ------------------------------------------------------------------
    # 1. Submit — the conftest patches process_form_check_task.delay, so the
    #    task is NOT dispatched here. We drive it explicitly in step 3.
    # ------------------------------------------------------------------
    resp = await e2e_client.post(
        _FC_SUBMIT,
        params={"exercise_name": "squat", "threshold_mode": "default"},
        files={
            "video_upload": (
                f"{uuid.uuid4().hex}.mp4",
                io.BytesIO(_TEST_VIDEO.read_bytes()),
                "video/mp4",
            )
        },
    )
    assert resp.status_code == 202, f"submit failed: {resp.status_code} {resp.text}"
    form_check_id = uuid.UUID(resp.json()["id"])
    assert resp.json()["status"] == "pending"

    # ------------------------------------------------------------------
    # 2. Point the Video row at the real file on local disk.
    #    _resolve_video_local_path (analysis_tasks.py:190-191) accepts an
    #    object_key that is already an existing absolute path.
    # ------------------------------------------------------------------
    async with pg_factory() as session:
        form_check = (
            await session.execute(select(FormCheck).where(FormCheck.id == form_check_id))
        ).scalar_one()
        video_id = form_check.video_id
        assert video_id is not None, "submit must link a Video row to the FormCheck"

        video = (
            await session.execute(select(Video).where(Video.id == video_id))
        ).scalar_one()
        video.object_key = str(_TEST_VIDEO)
        await session.commit()

    # ------------------------------------------------------------------
    # 3. Run the analysis task body.
    #    We call the async body directly rather than process_form_check_task:
    #    the Celery wrapper (analysis_tasks.py:437-441) calls asyncio.run(),
    #    which cannot nest inside pytest-asyncio's running loop. `self` is only
    #    used for Celery retry plumbing, which this path never invokes.
    # ------------------------------------------------------------------
    from app.tasks.analysis_tasks import _process_form_check_task_async

    result = await _process_form_check_task_async(
        MagicMock(), str(video_id), str(form_check_id)
    )
    assert result["status"] == FormCheckStatus.COMPLETED.value, (
        f"task did not complete: {result}"
    )

    # ------------------------------------------------------------------
    # 4. Assert a real, persisted result — not merely a terminal status.
    # ------------------------------------------------------------------
    async with pg_factory() as session:
        form_check = (
            await session.execute(select(FormCheck).where(FormCheck.id == form_check_id))
        ).scalar_one()

        assert form_check.status == FormCheckStatus.COMPLETED, (
            f"expected COMPLETED, got {form_check.status} "
            f"(error_details={form_check.error_details!r})"
        )

        results = form_check.results or {}
        assert "posture_v1" in results, (
            f"PostureV1 block missing from results; keys={list(results)}"
        )
        pv1 = results["posture_v1"]

        # Decision must be a real classification, not the uncertain fallback —
        # an uncertain result would mean a quality gate fired and no inference
        # was applied, which would make this test vacuous.
        assert pv1.get("decision") in {"good_form", "fault"}, (
            f"expected a decided classification, got {pv1.get('decision')!r} "
            f"(quality={pv1.get('quality')})"
        )

        prob_fault = pv1.get("prob_fault")
        assert isinstance(prob_fault, (int, float)) and 0.0 <= prob_fault <= 1.0, (
            f"prob_fault must be a probability, got {prob_fault!r}"
        )
        assert pv1.get("model", {}).get("name") == "posture_v1"

        # PostureV1 is the sole writer of posture_score for squats
        # (analysis_tasks.py:656-672), so a non-null score proves it ran.
        assert form_check.posture_score is not None, "posture_score was not written"
        assert 0 <= form_check.posture_score <= 100

        # This video is labelled good_form. The margin is not large — measured
        # prob_fault 0.4739 against threshold 0.525 when MediaPipe runs at
        # complexity 1 — so a flip here is a genuine regression signal, not
        # flakiness. See bench/results/2026-09-19-day1.md.
        assert pv1["decision"] == "good_form", (
            f"known-good squat classified as {pv1['decision']!r} "
            f"(prob_fault={prob_fault}, threshold={pv1.get('model', {}).get('threshold')})"
        )

        # ------------------------------------------------------------------
        # 5. Telemetry row must exist with a real measured latency.
        # ------------------------------------------------------------------
        telemetry = (
            await session.execute(
                select(PostureV1InferenceLog).where(
                    PostureV1InferenceLog.form_check_id == form_check_id
                )
            )
        ).scalars().all()
        assert len(telemetry) == 1, f"expected exactly 1 telemetry row, got {len(telemetry)}"
        row = telemetry[0]
        assert row.decision == pv1["decision"]
        assert row.latency_ms is not None and row.latency_ms > 0, (
            f"inference latency not recorded: {row.latency_ms!r}"
        )
        assert row.model_version is not None
