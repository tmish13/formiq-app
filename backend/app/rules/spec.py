"""Rule identity: version, parameters, and the hash that ties them together.

Mirrors `app/ml/posture_v2/features.py:spec_hash()`. The point is the same:
a verdict is only reproducible if you know exactly which rule produced it.
Changing a fitted constant changes `rules_spec_hash`, which changes the
idempotency key on `form_checks`, which means the video is legitimately
re-analysed rather than silently served a stale answer under a new rule.

NO NUMERIC LITERALS LIVE IN THE RULE CODE. Every threshold, weight, quantile and
band comes from the params file. A test enforces this by grepping the modules --
without it, a constant added "temporarily" during debugging becomes an
unversioned part of the decision, which is precisely how the v1 manifest drifted
from its own extractor (G-24).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Optional

from app.rules.indicators import INDICATOR_ORDER
from app.rules.kinematics import SIDES, SIDE_ORDER

RULES_SPEC_VERSION = "depth_rule_definitional_v1"

PARAMS_DIR = Path(__file__).resolve().parent / "params"
DEFAULT_PARAMS = PARAMS_DIR / "depth_v1.json"

# Keys every params file must define. Missing one is an error at load time, not
# a KeyError three layers into a verdict.
REQUIRED_KEYS = (
    "params_id",
    "fitted",
    "label_semantics",
    "min_visibility",
    "visibility_partial",
    "visibility_trusted",
    "standing_quantile",
    "smooth_seconds",
    "baseline_quantile",
    "bottom_band_frac",
    "max_window_seconds",
    "min_window_frames",
    "fallback_fps",
    "min_bottom_frames",
    "view_side_max",
    "view_front_min",
    "view_floors",
    "indicator_weights",
    "offset_by_view",
    "deadband",
    "coverage_floor",
)


class ParamsError(ValueError):
    """Raised when a params file is missing or malformed."""


def load_params(path: Optional[Path] = None) -> Dict[str, Any]:
    p = Path(path) if path else DEFAULT_PARAMS
    if not p.exists():
        raise ParamsError(
            f"no params at {p}. Fit them with bench/depth_rule_calibrate.py -- "
            "the rule has no built-in constants by design."
        )
    try:
        params = json.loads(p.read_text())
    except json.JSONDecodeError as e:
        raise ParamsError(f"{p} is not valid JSON: {e}") from e

    missing = [k for k in REQUIRED_KEYS if k not in params]
    if missing:
        raise ParamsError(f"{p} is missing required keys: {missing}")

    for name in INDICATOR_ORDER:
        if name not in params["indicator_weights"]:
            raise ParamsError(f"{p} has no weight for indicator {name}")
    return params


def rules_spec_hash(params: Dict[str, Any]) -> str:
    """Fingerprint of (version, indicator order, landmark set, every constant).

    Sorted keys so the hash is insensitive to file formatting but sensitive to
    every value that can change a verdict.
    """
    payload = {
        "rules_spec_version": RULES_SPEC_VERSION,
        "indicator_order": list(INDICATOR_ORDER),
        "side_order": list(SIDE_ORDER),
        "landmarks": {s: SIDES[s] for s in SIDE_ORDER},
        "params": {k: params[k] for k in sorted(params) if k != "provenance"},
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def build_manifest(params: Dict[str, Any]) -> Dict[str, Any]:
    """Everything needed to reproduce a verdict, generated from code.

    Generated rather than hand-written, deliberately: v1's manifest was written
    by hand and drifted from the extractor it described (G-24), which cost a day
    to diagnose.
    """
    return {
        "rules_spec_version": RULES_SPEC_VERSION,
        "rules_spec_hash": rules_spec_hash(params),
        "params_id": params.get("params_id"),
        "fitted": params.get("fitted"),
        "indicator_order": list(INDICATOR_ORDER),
        "verdict_indicator": "I2_hip_knee_delta",
        "criterion": "AT_DEPTH iff (hip_y - knee_y)/S + offset(view) >= 0",
        "criterion_note": (
            "The threshold is 0 because that is what parallel MEANS -- the femur "
            "reaching horizontal. It is not fitted. Only the measurement "
            "correction (offset, view dependence) is fitted."
        ),
        "coordinate_note": "MediaPipe normalised image space; y increases DOWNWARD",
        "label_semantics": params.get("label_semantics"),
        "provenance": params.get("provenance"),
    }
