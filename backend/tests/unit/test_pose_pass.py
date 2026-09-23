"""The pose-pass identity must change for what changes keypoints, and only that.

Motivation is measured, not hypothetical: two MediaPipe passes over the same
221 videos moved 33 PostureV1 verdicts (14.9%) while the paired CI on aggregate
F1 spanned zero (bench/results/2026-09-23-pose-pass-verdict-instability.md).
The id is how a stored decision stays explicable afterwards, so its stability
properties are worth pinning rather than assuming.
"""
import pytest

from app.core.pose_pass import (
    HASHED_KEYS,
    POSE_PASS_SPEC_VERSION,
    extraction_contract,
    pose_pass_id,
)


def _contract(**over):
    """A complete, valid contract. MediaPipe is not required to be installed."""
    c = {
        "mediapipe_version": "0.10.18",
        "model_complexity_used": 2,
        "static_image_mode": False,
        "min_detection_confidence": 0.5,
        "min_tracking_confidence": 0.5,
        "max_frames": 300,
        "landmark_count": 33,
        "fresh_tracker_per_video": True,
        "extraction_path": "app.tasks.analysis_tasks._extract_pose_from_video",
        "coordinate_note": "prose",
        "fresh_tracker_mechanism": "prose",
    }
    c.update(over)
    return c


def test_id_is_deterministic():
    assert pose_pass_id(_contract()) == pose_pass_id(_contract())


def test_id_is_insensitive_to_key_order():
    c = _contract()
    shuffled = {k: c[k] for k in reversed(list(c))}
    assert pose_pass_id(shuffled) == pose_pass_id(c)


def test_id_has_a_readable_shape():
    pid = pose_pass_id(_contract())
    assert pid.startswith("pp1_")
    assert len(pid) == len("pp1_") + 16
    int(pid[4:], 16)          # the tail is hex


@pytest.mark.parametrize("key,value", [
    ("mediapipe_version", "0.10.20"),
    ("model_complexity_used", 1),
    ("static_image_mode", True),
    ("min_detection_confidence", 0.6),
    ("min_tracking_confidence", 0.6),
    ("max_frames", 600),
    ("landmark_count", 25),
    ("fresh_tracker_per_video", False),
    ("extraction_path", "somewhere.else"),
])
def test_every_hashed_field_changes_the_id(key, value):
    """If one of these could change without changing the id, a verdict could be
    attributed to a pass that did not produce it."""
    assert key in HASHED_KEYS
    assert pose_pass_id(_contract(**{key: value})) != pose_pass_id(_contract())


@pytest.mark.parametrize("key,value", [
    ("coordinate_note", "reworded"),
    ("fresh_tracker_mechanism", "reworded"),
    ("model_complexity_configured", 1),
    ("complexity_fallback", True),
    ("complexity_source", "ai_service"),
    ("landmark_fields", ["x", "y"]),
])
def test_descriptive_fields_do_not_change_the_id(key, value):
    """Rewording a docstring must not invalidate the identity of every stored
    verdict. `model_complexity_configured` is deliberately here: what matters
    is the complexity actually USED, which is a separate, hashed field."""
    assert key not in HASHED_KEYS
    assert pose_pass_id(_contract(**{key: value})) == pose_pass_id(_contract())


def test_fallback_to_complexity_1_is_a_different_pass():
    """The case this exists for: a worker that could not load complexity 2 and
    quietly dropped to 1 produced different keypoints. Configured stays 2."""
    used_2 = _contract(model_complexity_used=2, model_complexity_configured=2)
    fell_back = _contract(model_complexity_used=1, model_complexity_configured=2,
                          complexity_fallback=True)
    assert pose_pass_id(used_2) != pose_pass_id(fell_back)


def test_missing_hashed_key_is_refused():
    c = _contract()
    del c["max_frames"]
    with pytest.raises(ValueError, match="missing hashed key"):
        pose_pass_id(c)


@pytest.mark.parametrize("version", [None, "unavailable", "unknown"])
def test_absent_mediapipe_refuses_to_mint_an_id(version):
    """Otherwise a host without MediaPipe hands back a plausible id for a pass
    that could not have produced keypoints -- and one that differs from the
    container's purely because of where the call was made."""
    with pytest.raises(ValueError, match="mediapipe_version"):
        pose_pass_id(_contract(mediapipe_version=version))


def test_contract_reports_the_complexity_actually_used():
    class _AI:
        _pose_complexity_used = 1
        _pose_complexity_fallback = True

    c = extraction_contract(ai_service=_AI())
    assert c["model_complexity_used"] == 1
    assert c["complexity_fallback"] is True
    assert c["complexity_source"] == "ai_service"


def test_contract_admits_when_it_cannot_see_the_fallback():
    c = extraction_contract()
    assert c["complexity_source"] == "configured_only"
    assert c["complexity_fallback"] is None


def test_contract_carries_every_hashed_key():
    c = extraction_contract()
    assert not [k for k in HASHED_KEYS if k not in c]
    assert c["pose_pass_spec_version"] == POSE_PASS_SPEC_VERSION


def test_calibration_corpus_id_is_pinned():
    """The 711-clip live-extraction corpus every Phase 2 negative was measured
    on. Pinned so that a change to HASHED_KEYS or the digest cannot silently
    orphan those results from the pass that produced them."""
    corpus = _contract(
        mediapipe_version="0.10.18",
        model_complexity_used=2,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
        max_frames=300,
    )
    assert pose_pass_id(corpus) == "pp1_f9850424580ae186"
