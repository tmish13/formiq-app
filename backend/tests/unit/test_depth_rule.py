"""The depth rule, tested against synthetic skeletons with known geometry.

Synthetic rather than recorded, deliberately: these assert the rule computes what
it claims, independently of whether any dataset agrees. A test built from labelled
clips would only prove the rule reproduces one annotator.

Coordinates are MediaPipe normalised image space -- **y increases DOWNWARD**, so
a bigger y is lower in the frame. Getting that backwards is the single easiest
way to invert this entire module, so the first test pins it.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

from app.rules import evaluate_depth, load_params, rules_spec_hash
from app.rules.kinematics import SIDES, scale_reference, to_array, usable_sides
from app.rules.segmentation import find_bottom, smoothing_window_frames
from app.rules.types import (
    ABSTAIN_BAD_SCALE,
    ABSTAIN_NEAR_PARALLEL,
    ABSTAIN_NO_BOTTOM,
    AT_DEPTH,
    SHALLOW,
    UNCERTAIN,
)

pytestmark = pytest.mark.unit

N_LM = 33


# --------------------------------------------------------------- fixtures --
def _frame(hip_y, knee_y, *, vis=1.0, hip_x=0.50, knee_x=0.50,
           shoulder_y=None, ankle_y=None, shoulder_sep=0.02, vis_right=None):
    """One synthetic frame. Torso length is (hip_y - shoulder_y).

    shoulder_sep controls the apparent view: small = side-on, large = front-on.
    """
    if shoulder_y is None:
        shoulder_y = hip_y - 0.20          # 0.20 torso, hips below shoulders
    if ankle_y is None:
        ankle_y = 0.95
    lm = [{"x": 0.5, "y": 0.5, "z": 0.0, "visibility": vis} for _ in range(N_LM)]
    vr = vis if vis_right is None else vis_right

    def put(i, x, y, v):
        lm[i] = {"x": x, "y": y, "z": 0.0, "visibility": v}

    put(11, 0.50 - shoulder_sep / 2, shoulder_y, vis)     # L shoulder
    put(12, 0.50 + shoulder_sep / 2, shoulder_y, vr)      # R shoulder
    put(23, hip_x - 0.005, hip_y, vis)                    # L hip
    put(24, hip_x + 0.005, hip_y, vr)                     # R hip
    put(25, knee_x - 0.005, knee_y, vis)                  # L knee
    put(26, knee_x + 0.005, knee_y, vr)                   # R knee
    put(27, 0.50 - 0.005, ankle_y, vis)                   # L ankle
    put(28, 0.50 + 0.005, ankle_y, vr)                    # R ankle
    return lm


def squat(bottom_hip_y, knee_y=0.60, n=60, stand_hip_y=0.40, **kw):
    """A descent-and-return with a single bottom -- one rep, as the corpus has.

    knee_y is held fixed: the knee does not travel much vertically in a squat,
    and holding it constant makes the intended (hip_y - knee_y) exact.
    """
    half = n // 2
    down = np.linspace(stand_hip_y, bottom_hip_y, half)
    up = np.linspace(bottom_hip_y, stand_hip_y, n - half)
    return [_frame(float(y), knee_y, **kw) for y in np.concatenate([down, up])]


@pytest.fixture(scope="module")
def params():
    return load_params()


# ------------------------------------------------------- the sign convention
class TestCoordinateConvention:
    def test_y_grows_downward_so_deeper_means_larger_hip_y(self, params):
        """Pins the convention the whole module rests on."""
        deep = evaluate_depth(squat(0.70), 30.0, params)     # hip well below knee
        shallow = evaluate_depth(squat(0.50), 30.0, params)  # hip above knee
        assert deep.score > shallow.score
        assert deep.verdict == AT_DEPTH
        assert shallow.verdict == SHALLOW

    def test_bottom_is_the_max_hip_y_frame(self):
        pose = squat(0.75, n=41)
        kp = to_array(pose)
        w = find_bottom(kp, 30.0, 0.4, 0.15, 0.1, 0.15, 0.5, 3, 30.0)
        assert w is not None
        ys = [f[23]["y"] for f in pose]
        assert abs(w.index - int(np.argmax(ys))) <= 2


# --------------------------------------------------------- the criterion ---
class TestDefinitionalCriterion:
    def test_exactly_parallel_abstains_rather_than_guessing(self, params):
        """hip level with knee is the boundary -- the honest answer is 'unsure'."""
        v = evaluate_depth(squat(0.60, knee_y=0.60), 30.0, params)
        assert v.verdict == UNCERTAIN
        assert v.abstain_reason == ABSTAIN_NEAR_PARALLEL
        assert abs(v.score) < params["deadband"]

    def test_clearly_below_parallel_is_at_depth(self, params):
        v = evaluate_depth(squat(0.72, knee_y=0.60), 30.0, params)
        assert v.verdict == AT_DEPTH
        assert v.score > 0

    def test_clearly_above_parallel_is_shallow(self, params):
        v = evaluate_depth(squat(0.48, knee_y=0.60), 30.0, params)
        assert v.verdict == SHALLOW
        assert v.score < 0

    def test_score_is_hip_knee_delta_over_torso(self, params):
        """The score must BE the measured quantity, not a transform of it.

        torso = 0.20, hip - knee = 0.70 - 0.60 = 0.10  ->  0.50
        """
        v = evaluate_depth(squat(0.70, knee_y=0.60), 30.0, params)
        assert v.score == pytest.approx(0.50, abs=0.02)

    def test_threshold_is_zero_not_fitted(self, params):
        """The offsets may be fitted; the threshold may not."""
        assert set(params["offset_by_view"]) == {"side", "oblique", "front"}
        assert "threshold" not in params, (
            "a fitted threshold would make the criterion empirical rather than "
            "definitional -- parallel is 0 because that is what parallel means")


# ------------------------------------------------------------ scale-free ---
class TestScaleInvariance:
    def test_uniform_scaling_does_not_change_the_verdict(self, params):
        """Same squat, camera twice as far away."""
        base = squat(0.70, knee_y=0.60)

        def shrink(frames, k=0.5, cx=0.5, cy=0.5):
            return [[{**lm, "x": cx + (lm["x"] - cx) * k,
                      "y": cy + (lm["y"] - cy) * k} for lm in f] for f in frames]

        a = evaluate_depth(base, 30.0, params)
        b = evaluate_depth(shrink(base), 30.0, params)
        assert a.verdict == b.verdict
        assert a.score == pytest.approx(b.score, abs=1e-6)

    def test_translation_does_not_change_the_verdict(self, params):
        base = squat(0.70, knee_y=0.60)
        moved = [[{**lm, "x": lm["x"] + 0.1, "y": lm["y"] - 0.05} for lm in f]
                 for f in base]
        a, b = evaluate_depth(base, 30.0, params), evaluate_depth(moved, 30.0, params)
        assert a.verdict == b.verdict
        assert a.score == pytest.approx(b.score, abs=1e-6)


# ------------------------------------------------------------- per side ----
class TestPerSideGating:
    def test_a_side_view_with_one_leg_occluded_still_works(self, params):
        """THE regression test for the provenance-gate bug.

        Requiring all eight core landmarks rejected 11 of 30 videos, because a
        side view -- the best view for depth -- always occludes one leg.
        32991_2: left side 0.93-1.00, right knee 0.198, right ankle 0.225.
        """
        pose = squat(0.72, knee_y=0.60, vis=0.95, vis_right=0.2)
        v = evaluate_depth(pose, 30.0, params)
        assert v.verdict == AT_DEPTH, (
            "one occluded leg must not prevent a verdict -- that was the bug")

    def test_usable_sides_reports_only_the_visible_one(self):
        f = _frame(0.70, 0.60, vis=0.95, vis_right=0.2)
        assert usable_sides(to_array([f])[0], 0.4) == ["L"]

    def test_both_legs_occluded_abstains(self, params):
        pose = squat(0.72, knee_y=0.60, vis=0.1, vis_right=0.1)
        v = evaluate_depth(pose, 30.0, params)
        assert v.verdict == UNCERTAIN


# ------------------------------------------------------------- abstain -----
class TestAbstention:
    def test_degenerate_torso_abstains_with_bad_scale(self, params):
        """Shoulders exactly coincident with hips -- no torso to scale by.

        The first version of this fixture set only shoulder_y == hip_y and left
        the x offsets, giving a torso of 0.005 rather than 0. It abstained for
        the wrong reason (no_bottom_found), which is why the reason is asserted
        and not just the verdict.
        """
        flat = []
        for _ in range(30):
            f = _frame(0.5, 0.6, shoulder_y=0.5, shoulder_sep=0.0)
            for sh, hp in ((11, 23), (12, 24)):
                f[sh] = {**f[sh], "x": f[hp]["x"], "y": f[hp]["y"]}
            flat.append(f)
        v = evaluate_depth(flat, 30.0, params)
        assert v.verdict == UNCERTAIN
        assert v.abstain_reason == ABSTAIN_BAD_SCALE

    def test_no_movement_abstains_with_no_bottom(self, params):
        still = [_frame(0.55, 0.60) for _ in range(40)]
        v = evaluate_depth(still, 30.0, params)
        assert v.verdict == UNCERTAIN
        assert v.abstain_reason == ABSTAIN_NO_BOTTOM

    def test_empty_input_abstains(self, params):
        assert evaluate_depth([], 30.0, params).verdict == UNCERTAIN

    def test_all_frames_undetected_abstains(self, params):
        assert evaluate_depth([None] * 30, 30.0, params).verdict == UNCERTAIN

    def test_abstention_never_carries_a_verdict(self, params):
        for pose in ([], [None] * 30, [_frame(0.55, 0.60)] * 40):
            v = evaluate_depth(pose, 30.0, params)
            if v.verdict == UNCERTAIN:
                assert v.abstained is True
                assert v.abstain_reason is not None
                assert v.verdict not in (SHALLOW, AT_DEPTH)


# --------------------------------------------------------- determinism -----
class TestDeterminism:
    def test_identical_input_gives_byte_identical_output(self, params):
        pose = squat(0.70, knee_y=0.60)
        a = json.dumps(evaluate_depth(pose, 30.0, params).as_dict(), sort_keys=True)
        for _ in range(20):
            b = json.dumps(evaluate_depth(pose, 30.0, params).as_dict(), sort_keys=True)
            assert a == b

    def test_fps_only_sizes_the_smoothing_window(self, params):
        """Duplicating every frame at 60fps is the same movement."""
        pose30 = squat(0.70, knee_y=0.60, n=60)
        pose60 = [f for f in pose30 for _ in (0, 1)]
        a = evaluate_depth(pose30, 30.0, params)
        b = evaluate_depth(pose60, 60.0, params)
        assert a.verdict == b.verdict
        assert a.score == pytest.approx(b.score, abs=1e-3)

    def test_smoothing_window_is_odd_and_scales_with_fps(self):
        assert smoothing_window_frames(0.15, 30.0, 30.0) % 2 == 1
        assert (smoothing_window_frames(0.15, 60.0, 30.0)
                > smoothing_window_frames(0.15, 30.0, 30.0))

    def test_outputs_are_rounded_to_six_dp(self, params):
        """Matches loader.py:604 so both checkers quote depth at one resolution."""
        v = evaluate_depth(squat(0.70, knee_y=0.60), 30.0, params)
        assert v.score == round(v.score, 6)


# ------------------------------------------------------------ the spec -----
class TestSpec:
    def test_hash_changes_when_any_constant_changes(self, params):
        before = rules_spec_hash(params)
        bumped = {**params, "deadband": params["deadband"] + 0.01}
        assert rules_spec_hash(bumped) != before

    def test_hash_is_stable_across_calls(self, params):
        assert rules_spec_hash(params) == rules_spec_hash(params)

    def test_verdict_carries_its_own_provenance(self, params):
        v = evaluate_depth(squat(0.70, knee_y=0.60), 30.0, params)
        assert v.rules_spec_hash == rules_spec_hash(params)
        assert v.params_id == params["params_id"]

    def test_no_numeric_literals_in_the_rule_modules(self):
        """Every constant that can change a verdict must live in the params file.

        A number added "temporarily" while debugging becomes an unversioned part
        of the decision, which is how the v1 manifest drifted from its own
        extractor (G-24).
        """
        import ast

        # Integers 0..32 are MediaPipe landmark indices and array offsets -- fixed
        # by the library, not tunable. What this must catch is FLOATS: thresholds,
        # weights, quantiles, bands. Those are the things that change a verdict.
        allowed_floats = {0.0, 1.0, -1.0, 0.5}   # identity, clamp bounds, midpoint
        offenders = []
        for mod in ("depth.py", "segmentation.py", "view.py", "indicators.py"):
            path = Path(__file__).resolve().parents[1].parent / "app" / "rules" / mod
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if not isinstance(node, ast.Constant):
                    continue
                v = node.value
                if isinstance(v, bool) or not isinstance(v, (int, float)):
                    continue
                if isinstance(v, int):
                    if 0 <= v <= 32:          # landmark index / small offset
                        continue
                    offenders.append(f"{mod}:{node.lineno} -> {v}")
                    continue
                if v in allowed_floats or abs(v) < 1e-6:
                    continue
                offenders.append(f"{mod}:{node.lineno} -> {v}")
        assert not offenders, (
            "numeric literals found in rule code; move them to params/depth_v1.json:\n"
            + "\n".join(offenders))

    def test_params_declare_the_resolved_label_semantics(self, params):
        """Stage 0's finding has to travel with the rule, not live in a doc."""
        ls = params["label_semantics"]
        assert ls["positive_class"] == "SHALLOW"
        assert ls["p_target_class"] == "AT_DEPTH"
        assert ls["p_target"] == 0.85
        assert "NOT a synonym for at-depth" in ls["label_0"]
