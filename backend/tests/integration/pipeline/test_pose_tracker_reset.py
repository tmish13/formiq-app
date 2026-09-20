"""Regression test for the MediaPipe cross-video state leak.

Phase 0 measured the defect (bench/results/2026-09-19-mediapipe-state-leak.md):
``AIService`` is a per-worker singleton holding one
``mp.solutions.pose.Pose(static_image_mode=False)``.  That tracker seeds each
frame from the previous frame's landmarks, which is correct inside one video and
wrong across videos.  The same bytes scored:

    cold tracker            0.618214
    after 33348_2           0.439524   (-0.178690)
    after 36049_2           0.652968   (+0.034754)
    after itself            0.586389

a spread of 0.214 straddling the 0.525 decision threshold.

``AIService.reset_pose_tracker()`` is called once per video by
``_extract_pose_from_video``.  This test drives that live call site and asserts
the predecessor no longer moves the score.

Needs the video fixtures and the PostureV1 weights, so it runs in the container:

    docker compose -f backend/deployment/docker-compose.yml exec \
      -v "$HOME/Desktop/Squat More/Labeled_Dataset/videos:/videos:ro" \
      app pytest -m integration tests/integration/pipeline/test_pose_tracker_reset.py \
      --override-ini="addopts=--asyncio-mode=auto" --import-mode=importlib -p no:randomly
"""
import asyncio
import os
from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.slow]

VIDEO_DIR = Path(os.getenv("FORMIQ_TEST_VIDEO_DIR", "/videos"))
TARGET = "33387_1"
PREDECESSORS = ["33348_2", "36049_2"]

# The tracker leak moved prob_fault by up to 0.179.  Post-fix the only remaining
# variation should be float non-determinism, which the Phase 0 cold-vs-cold run
# measured at exactly 0.000000.  Allow a small tolerance rather than demanding
# bit-equality across machines.
MAX_ALLOWED_SHIFT = 1e-6

_REQUIRED = [TARGET, *PREDECESSORS]


def _video(name: str) -> Path:
    return VIDEO_DIR / f"{name}.mp4"


pytestmark.append(
    pytest.mark.skipif(
        not all(_video(v).exists() for v in _REQUIRED),
        reason=f"video fixtures not mounted at {VIDEO_DIR}",
    )
)


@pytest.fixture(scope="module")
def settings_obj():
    from app.core.config import get_settings

    return get_settings()


@pytest.fixture(scope="module")
def posture_loader(settings_obj):
    from app.ml.posture_v1.loader import PostureV1TorchLoader

    loader = PostureV1TorchLoader(settings_obj)
    loader._ensure_loaded()
    return loader


def _score(ai_service, loader, settings_obj, video: str) -> float:
    """Run one video through the live extraction path and score it."""
    from app.tasks.analysis_tasks import _extract_pose_from_video

    pose_data, _seq_len, _fps = asyncio.run(
        _extract_pose_from_video(str(_video(video)), ai_service, settings_obj)
    )
    return float(loader.predict_posture(pose_data)["prob_fault"])


def test_score_is_independent_of_the_previous_video(settings_obj, posture_loader):
    """One AIService instance, several videos: the target must not drift.

    This is the exact shape of the defect — a long-lived worker singleton
    processing videos back to back.
    """
    from app.services.ai_service import AIService

    ai = AIService(app_settings=settings_obj)

    cold = _score(ai, posture_loader, settings_obj, TARGET)

    observed = {}
    for prev in PREDECESSORS:
        _score(ai, posture_loader, settings_obj, prev)
        observed[prev] = _score(ai, posture_loader, settings_obj, TARGET)

    # and after itself, which also shifted the score pre-fix
    _score(ai, posture_loader, settings_obj, TARGET)
    observed["itself"] = _score(ai, posture_loader, settings_obj, TARGET)

    drift = {k: abs(v - cold) for k, v in observed.items()}
    worst = max(drift.values())
    assert worst <= MAX_ALLOWED_SHIFT, (
        f"prob_fault still depends on the preceding video. cold={cold:.6f}, "
        + ", ".join(f"after {k}={v:.6f} (Δ{v - cold:+.6f})" for k, v in observed.items())
    )


def test_fresh_instances_agree_with_a_reused_instance(settings_obj, posture_loader):
    """A reused singleton must now match a process that only ever saw one video.

    Pre-fix this was the practical failure: the Celery worker (long-lived) and an
    offline one-shot run disagreed on 17 of 20 videos.
    """
    from app.services.ai_service import AIService

    fresh = _score(
        AIService(app_settings=settings_obj), posture_loader, settings_obj, TARGET
    )

    reused = AIService(app_settings=settings_obj)
    for prev in PREDECESSORS:
        _score(reused, posture_loader, settings_obj, prev)
    warm = _score(reused, posture_loader, settings_obj, TARGET)

    assert abs(warm - fresh) <= MAX_ALLOWED_SHIFT, (
        f"reused worker {warm:.6f} != fresh process {fresh:.6f} "
        f"(Δ{warm - fresh:+.6f})"
    )


def test_reset_pose_tracker_preserves_the_complexity_fallback(settings_obj):
    """A worker that fell back to complexity=1 must not silently jump to 2.

    G-21 was a silent complexity downgrade; the reset must not reintroduce a
    model switch halfway through a run.
    """
    from app.services.ai_service import AIService

    ai = AIService(app_settings=settings_obj)
    ai._pose_complexity_used = 1
    ai._pose_complexity_fallback = True

    ai.reset_pose_tracker()

    assert ai._pose_complexity_used == 1
    assert ai._pose_complexity_fallback is True
