"""The identity of a MediaPipe extraction pass.

WHY THIS EXISTS
---------------
A verdict is reproducible against a *named pose pass*, not against a model
version alone. `bench/results/2026-09-23-pose-pass-verdict-instability.md`
measured it: the same PostureV1 weights, at the same threshold, on the same 221
videos, scored from two different MediaPipe passes, changed **33 verdicts
(14.9%)**. A third of those flips started more than 0.10 away from the
threshold, so they are not tie-breaking -- one went 0.711 -> 0.103. Meanwhile
the paired 95% CI on aggregate F1 spanned zero, which is why no population
metric would ever have surfaced this.

So `spec_hash` (feature spec) and `model_version` (weights) are not sufficient
to explain a stored decision. The extraction contract is a co-equal input and
gets its own recorded identity: `pose_pass_id`.

WHAT IS AND IS NOT HASHED
-------------------------
Only fields that can change the numbers enter the hash -- `HASHED_KEYS`. Prose
fields (mechanism notes, coordinate reminders) are carried in the contract for
a human reader but excluded, because rewording a docstring must not invalidate
the identity of every verdict ever stored.

`model_complexity_used` is hashed, not `model_complexity_configured`: a worker
that failed to load complexity 2 and silently fell back to 1 produced different
keypoints, and that is exactly the case this must distinguish.

`max_frames` is hashed because it truncates the sequence
(`analysis_tasks._extract_pose_from_video`), which changes every downstream
aggregate over the clip.

The same function backs `bench/extract_keypoints.py`, so a calibration corpus
and a production verdict carry comparable ids. That is the point: it must be
possible to ask "was this decision produced by the pass I calibrated on?" and
get an answer rather than an educated guess.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Optional

# Bump only when the SET of hashed keys changes, never when a value changes --
# a value change is supposed to produce a new id, that is the mechanism working.
POSE_PASS_SPEC_VERSION = "pose_pass_v1"

#: Fields that can change the extracted keypoints. Order-independent (the
#: digest sorts keys), but explicit rather than "everything in the dict", so
#: that adding a descriptive field to the contract is not a silent re-identify.
HASHED_KEYS = (
    "mediapipe_version",
    "model_complexity_used",
    "static_image_mode",
    "min_detection_confidence",
    "min_tracking_confidence",
    "max_frames",
    "landmark_count",
    "fresh_tracker_per_video",
    "extraction_path",
)

_ID_PREFIX = "pp1"
_ID_HEX_LEN = 16


def extraction_contract(
    ai_service: Optional[Any] = None,
    settings: Optional[Any] = None,
) -> Dict[str, Any]:
    """Everything needed to reproduce an extraction, hashed and unhashed.

    `ai_service` supplies the complexity actually in use; without it the
    configured value is reported and `complexity_source` says so, because a
    contract that cannot see the fallback must not claim it did not happen.
    """
    if settings is None:
        from app.core.config import settings as _settings
        settings = _settings

    try:
        import mediapipe as mp
        mp_version = getattr(mp, "__version__", "unknown")
    except Exception:                                     # pragma: no cover
        mp_version = "unavailable"

    configured = getattr(settings, "AI_MODEL_COMPLEXITY", None)
    if ai_service is not None:
        used = getattr(ai_service, "_pose_complexity_used", configured)
        fallback = bool(getattr(ai_service, "_pose_complexity_fallback", False))
        source = "ai_service"
    else:
        used = configured
        fallback = None
        source = "configured_only"

    return {
        "pose_pass_spec_version": POSE_PASS_SPEC_VERSION,
        # ---- hashed ----
        "mediapipe_version": mp_version,
        "model_complexity_used": used,
        "static_image_mode": False,
        "min_detection_confidence": getattr(settings, "AI_MIN_DETECTION_CONFIDENCE", None),
        "min_tracking_confidence": getattr(settings, "AI_MIN_TRACKING_CONFIDENCE", None),
        "max_frames": getattr(settings, "AI_MAX_FRAMES_PER_VIDEO_ANALYSIS", 300) or 300,
        "landmark_count": 33,
        "fresh_tracker_per_video": True,
        "extraction_path": "app.tasks.analysis_tasks._extract_pose_from_video",
        # ---- descriptive, NOT hashed ----
        "model_complexity_configured": configured,
        "complexity_fallback": fallback,
        "complexity_source": source,
        "landmark_fields": ["x", "y", "z", "visibility"],
        "fresh_tracker_mechanism": (
            "AIService.reset_pose_tracker() is called before frame 0 "
            "(Phase 1, G-31)"
        ),
        "fps_resampling": (
            "none at extraction; source fps recorded per clip and normalised "
            "downstream in app/rules"
        ),
        "coordinate_note": "MediaPipe normalized image coords; y increases DOWNWARD",
    }


def pose_pass_id(contract: Optional[Dict[str, Any]] = None, **kwargs: Any) -> str:
    """Stable short id over the hashed subset of an extraction contract.

    Returns e.g. ``pp1_3f9c1a4b0e2d5678``. Deterministic: sorted keys, no
    whitespace, no clock, no RNG.
    """
    if contract is None:
        contract = extraction_contract(**kwargs)
    if contract.get("mediapipe_version") in (None, "unavailable", "unknown"):
        # Minting an id over an absent MediaPipe would hash the literal string
        # "unavailable" and hand back a plausible-looking id for a pass that
        # could not have produced any keypoints -- and it would differ from the
        # container's id purely because of where the call was made. Refuse.
        raise ValueError(
            "cannot compute pose_pass_id: mediapipe_version is "
            f"{contract.get('mediapipe_version')!r}. This is normal on a host "
            "without MediaPipe installed; the id is only meaningful where "
            "extraction actually runs."
        )
    missing = [k for k in HASHED_KEYS if k not in contract]
    if missing:
        raise ValueError(
            f"extraction contract is missing hashed key(s): {missing}. "
            "An id computed over a partial contract would collide across "
            "genuinely different passes."
        )
    payload = {
        "pose_pass_spec_version": POSE_PASS_SPEC_VERSION,
        **{k: contract[k] for k in HASHED_KEYS},
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(blob.encode("utf-8")).hexdigest()[:_ID_HEX_LEN]
    return f"{_ID_PREFIX}_{digest}"
