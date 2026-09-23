"""The knees-forward checker: polarity, gating, and the limits it must carry.

The measurement behind this module is a NEGATIVE result -- 80.2% within-video
agreement but between-video AUROC 0.572 against a trivial floor of F1 0.812.
Most of these tests exist to stop that from being quietly forgotten.
"""
import json
from pathlib import Path

import numpy as np
import pytest

from app.rules.knees_forward import (
    CHECKER_NAME,
    FOOT,
    TARGET,
    evaluate_knees_forward,
    forward_travel,
)
from app.rules.spec import (
    KNEES_FORWARD_PARAMS,
    ParamsError,
    load_knees_forward_params,
    load_params,
)
from app.rules.types import NOT_OBSERVED, OBSERVED, UNCERTAIN

RULES = Path(__file__).resolve().parents[2] / "app" / "rules"


@pytest.fixture()
def params():
    return load_knees_forward_params()


# ---------------------------------------------------------- synthetic rig --

def _frame(knee_x, toe_x=0.50, heel_x=0.40, vis=1.0, hip_y=0.50, knee_y=0.70):
    """One skeleton. Foot points +x (toe right of heel), so `forward` is +x."""
    lm = [{"x": 0.5, "y": 0.5, "z": 0.0, "visibility": vis} for _ in range(33)]
    for i, y in ((11, 0.20), (12, 0.20)):
        lm[i] = {"x": 0.5, "y": y, "z": 0.0, "visibility": vis}
    for i in (23, 24):
        lm[i] = {"x": 0.5, "y": hip_y, "z": 0.0, "visibility": vis}
    for i in (25, 26):
        lm[i] = {"x": knee_x, "y": knee_y, "z": 0.0, "visibility": vis}
    for i in (27, 28):
        lm[i] = {"x": 0.45, "y": 0.90, "z": 0.0, "visibility": vis}
    for s in ("L", "R"):
        lm[FOOT[s]["heel"]] = {"x": heel_x, "y": 0.95, "z": 0.0, "visibility": vis}
        lm[FOOT[s]["toe"]] = {"x": toe_x, "y": 0.95, "z": 0.0, "visibility": vis}
    return lm


def _clip(knee_xs, hip_ys):
    return [_frame(kx, hip_y=hy, knee_y=hy + 0.2)
            for kx, hy in zip(knee_xs, hip_ys)]


def _squat(knee_x_bottom, n=60):
    """Stand, descend, hold, ascend -- one rep, which is what this corpus is."""
    hip = ([0.40] * 12 + list(np.linspace(0.40, 0.72, 14)) + [0.72] * 10
           + list(np.linspace(0.72, 0.40, 14)) + [0.40] * 10)[:n]
    knee = [0.50] * 12 + [knee_x_bottom] * (n - 12)
    return _clip(knee, hip)


def _arr(frame):
    from app.rules.kinematics import to_array
    return to_array([frame])[0]


# ------------------------------------------------------------- polarity --

def test_knee_ahead_of_the_toe_is_positive():
    v = forward_travel(_arr(_frame(knee_x=0.60, toe_x=0.50)), 0.30, 0.4, 1e-6)
    assert v is not None and v > 0


def test_knee_behind_the_toe_is_negative():
    v = forward_travel(_arr(_frame(knee_x=0.40, toe_x=0.50)), 0.30, 0.4, 1e-6)
    assert v is not None and v < 0


def test_sign_survives_the_subject_facing_the_other_way():
    """The reason the direction comes from the foot's own orientation rather
    than from a fixed axis: a raw knee_x - ankle_x flips when the subject turns
    around, and would silently invert the measurement."""
    forward = forward_travel(_arr(_frame(knee_x=0.60, toe_x=0.50, heel_x=0.40)),
                             0.30, 0.4, 1e-6)
    mirrored = forward_travel(_arr(_frame(knee_x=0.40, toe_x=0.50, heel_x=0.60)),
                              0.30, 0.4, 1e-6)
    assert forward == pytest.approx(mirrored)


def test_magnitude_scales_with_the_torso_reference():
    small = forward_travel(_arr(_frame(knee_x=0.60)), 0.20, 0.4, 1e-6)
    large = forward_travel(_arr(_frame(knee_x=0.60)), 0.40, 0.4, 1e-6)
    assert small == pytest.approx(2 * large)


# ------------------------------------------------------------- gating --

def test_an_invisible_foot_yields_no_measurement():
    """A foot we cannot see cannot define a forward direction, so the sign
    would be taken from noise."""
    f = _frame(knee_x=0.60)
    for s in ("L", "R"):
        f[FOOT[s]["toe"]]["visibility"] = 0.05
    assert forward_travel(_arr(f), 0.30, 0.4, 1e-6) is None


def test_a_degenerate_foot_yields_no_measurement():
    """Heel and toe coincident: the direction is noise."""
    f = _frame(knee_x=0.60, toe_x=0.50, heel_x=0.50)
    assert forward_travel(_arr(f), 0.30, 0.4, 1e-6) is None


def test_zero_scale_yields_no_measurement():
    assert forward_travel(_arr(_frame(knee_x=0.60)), 0.0, 0.4, 1e-6) is None


# ------------------------------------------------------------ verdicts --

def test_a_deep_knee_travel_is_observed(params):
    v = evaluate_knees_forward(_squat(knee_x_bottom=0.75), 30.0, params)
    assert v.target == TARGET
    assert v.decision == OBSERVED
    assert v.score > params["observation_cut"]


def test_a_knee_behind_the_toe_is_not_observed(params):
    v = evaluate_knees_forward(_squat(knee_x_bottom=0.42), 30.0, params)
    assert v.decision == NOT_OBSERVED


def test_no_frames_abstains(params):
    v = evaluate_knees_forward([], 30.0, params)
    assert v.decision == UNCERTAIN
    assert v.abstain_reason == "no_usable_frames"


def test_a_clip_with_no_descent_abstains(params):
    """Same guard as the depth rule: 37941_3 has hip_y range 0.003 and no squat
    at all, and still received a confident verdict before this existed."""
    v = evaluate_knees_forward(_clip([0.60] * 40, [0.50] * 40), 30.0, params)
    assert v.decision == UNCERTAIN
    assert v.abstain_reason in ("no_bottom_found", "bad_scale_reference")


def test_an_unseeable_clip_abstains_rather_than_guessing(params):
    clip = _squat(knee_x_bottom=0.75)
    for f in clip:
        for s in ("L", "R"):
            f[FOOT[s]["toe"]]["visibility"] = 0.05
            f[FOOT[s]["heel"]]["visibility"] = 0.05
    v = evaluate_knees_forward(clip, 30.0, params)
    assert v.decision == UNCERTAIN


# ----------------------------------------------- the limits must travel --

def test_the_verdict_carries_fitted_false(params):
    """On the verdict, not only in the params file. By the time this has been
    through two layers the params file is out of sight."""
    v = evaluate_knees_forward(_squat(knee_x_bottom=0.75), 30.0, params)
    assert v.fitted is False


def test_every_decision_states_what_was_validated(params):
    v = evaluate_knees_forward(_squat(knee_x_bottom=0.75), 30.0, params)
    note = v.indicators[0]["detail"]["validated"]
    assert "polarity only" in note
    assert "0.572" in note and "0.812" in note


def test_params_record_the_measurement_that_refuted_the_rule(params):
    m = params["measured"]
    assert m["within_video_agreement"] == 0.802
    assert m["between_video_auroc_peak"] == 0.572
    assert m["trivial_floor_f1"] == 0.812
    assert m["split"].startswith("train + validation")
    assert m["conclusion"] == "polarity confirmed, video-level separation refuted"


def test_params_are_unfitted_and_the_loader_enforces_it(params, tmp_path):
    assert params["fitted"] is False
    assert params["provenance"]["advisory"] is True
    forged = json.loads(KNEES_FORWARD_PARAMS.read_text())
    forged["fitted"] = True
    p = tmp_path / "forged.json"
    p.write_text(json.dumps(forged))
    with pytest.raises(ParamsError, match="fitted=true"):
        load_knees_forward_params(p)


# --------------------------------------------------------- consistency --

SHARED_WITH_DEPTH = (
    "min_visibility", "visibility_partial", "visibility_trusted",
    "standing_quantile", "smooth_seconds", "baseline_quantile",
    "bottom_band_frac", "max_window_seconds", "min_window_frames",
    "fallback_fps", "min_usable_frames_for_scale", "min_standing_frames",
    "min_descent_ratio", "view_side_max", "view_front_min",
)


def test_segmentation_constants_match_the_depth_rule_exactly(params):
    """Both checkers must describe the same instant of the same rep, or their
    two decision rows stop being comparable. Three of these were mis-copied by
    hand when this file was written, which put 59% of clips in 'front' view
    against a measured corpus rate of ~5%."""
    depth = load_params()
    differing = {k: (depth[k], params[k]) for k in SHARED_WITH_DEPTH
                 if depth[k] != params[k]}
    assert not differing, f"drifted from depth_v1.json: {differing}"


def test_no_numeric_literals_in_the_checker():
    """Same rule as the depth modules: a constant added while debugging becomes
    an unversioned part of the decision (G-24)."""
    import ast
    allowed = {0.0, 1.0, -1.0, 0.5}
    offenders = []
    tree = ast.parse((RULES / "knees_forward.py").read_text())
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant):
            continue
        v = node.value
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            continue
        if isinstance(v, int):
            if 0 <= v <= 32:
                continue
            offenders.append(f"{node.lineno} -> {v}")
        elif v not in allowed and abs(v) >= 1e-6:
            offenders.append(f"{node.lineno} -> {v}")
    assert not offenders, (
        "numeric literals in knees_forward.py; move them to "
        f"params/knees_forward_v0.json: {offenders}")


def test_checker_name_is_stable():
    """It is the primary key of a decision row together with (run, target)."""
    assert CHECKER_NAME == "knees_forward_v0"
    assert TARGET == "knees_forward"
