"""
PostureV2 feature-spec guards (draft spec — nothing trains or serves on it yet).

v1's failure mode was a spec that drifted from its code (AUDIT.md G-24), so v2
gets its guards written before its first training run, not after.
"""
import numpy as np
import pytest

from app.ml.posture_v2 import features as F

pytestmark = pytest.mark.unit


def _synthetic_squat(T: int = 60, fps: float = 30.0) -> np.ndarray:
    """A crude but well-formed squat: hips and knees drop, then return."""
    kp = np.zeros((T, 33, 3), dtype=np.float64)
    drop = np.concatenate([np.linspace(0, 0.25, T // 2), np.linspace(0.25, 0, T - T // 2)])
    for t in range(T):
        d = drop[t]
        kp[t, F.L_SHOULDER] = [0.45, 0.30 + d * 0.5, 0.0]
        kp[t, F.R_SHOULDER] = [0.55, 0.30 + d * 0.5, 0.0]
        kp[t, F.L_ELBOW] = [0.42, 0.42 + d * 0.5, 0.0]
        kp[t, F.R_ELBOW] = [0.58, 0.42 + d * 0.5, 0.0]
        kp[t, F.L_WRIST] = [0.40, 0.52 + d * 0.5, 0.0]
        kp[t, F.R_WRIST] = [0.60, 0.52 + d * 0.5, 0.0]
        kp[t, F.L_HIP] = [0.46, 0.55 + d, 0.0]
        kp[t, F.R_HIP] = [0.54, 0.55 + d, 0.0]
        kp[t, F.L_KNEE] = [0.46, 0.72 + d * 0.4, 0.0]
        kp[t, F.R_KNEE] = [0.54, 0.72 + d * 0.4, 0.0]
        kp[t, F.L_ANKLE] = [0.46, 0.90, 0.0]
        kp[t, F.R_ANKLE] = [0.54, 0.90, 0.0]
        kp[t, F.L_HEEL] = [0.45, 0.92, 0.0]
        kp[t, F.R_HEEL] = [0.55, 0.92, 0.0]
        kp[t, F.L_FOOT] = [0.44, 0.95, 0.0]
        kp[t, F.R_FOOT] = [0.56, 0.95, 0.0]
    return kp


def test_spec_uses_body_joints_only():
    """The whole point of v2: no face landmarks anywhere."""
    assert min(F.BODY_JOINTS) >= F.FIRST_BODY_LANDMARK
    assert len(F.BODY_JOINTS) == len(set(F.BODY_JOINTS)) == 16
    for face in range(F.FIRST_BODY_LANDMARK):
        assert face not in F.BODY_JOINTS


def test_names_and_values_stay_aligned():
    kp = _synthetic_squat()
    values, names = F.compute_features(kp)
    assert len(values) == len(names) == F.feature_dim()
    assert len(set(names)) == len(names), "duplicate feature names"
    assert np.isfinite(values).all(), "non-finite values in the feature vector"
    assert names == F.get_feature_names(), "get_feature_names() disagrees with compute_features()"


def test_features_are_invariant_to_camera_distance_and_position():
    """
    The headline property. v1 fed raw frame coordinates, so the same squat filmed
    closer produced different inputs. v2 must not.
    """
    kp = _synthetic_squat()
    moved = kp.copy()
    moved[:, :, :2] = moved[:, :, :2] * 0.5 + np.array([0.2, 0.1])  # zoom out + pan

    a, _ = F.compute_features(kp)
    b, _ = F.compute_features(moved)

    # Tempo/frame-count features are scale-free by construction; positions and
    # angles must match after torso normalisation.
    np.testing.assert_allclose(a, b, rtol=1e-4, atol=1e-4)


def test_resampling_makes_tempo_fps_independent():
    """Same squat at 60fps must produce the same features as at 30fps."""
    kp30 = _synthetic_squat(T=60, fps=30.0)
    kp60 = np.repeat(kp30, 2, axis=0)  # same motion, twice the frames

    a, names = F.compute_features(kp30, source_fps=30.0)
    b, _ = F.compute_features(kp60, source_fps=60.0)

    idx = {n: i for i, n in enumerate(names)}
    for key in ("tempo_descent_frames", "tempo_ascent_frames", "tempo_total_frames"):
        assert abs(a[idx[key]] - b[idx[key]]) <= 2, (
            f"{key} differs across fps: {a[idx[key]]} vs {b[idx[key]]}"
        )


def test_depth_and_lean_respond_to_the_movement():
    """A deeper squat must register as deeper — sanity that the spec measures something."""
    shallow = _synthetic_squat()
    deep = _synthetic_squat()
    deep[:, [F.L_HIP, F.R_HIP], 1] += 0.15  # drive the hips lower

    s, names = F.compute_features(shallow)
    d, _ = F.compute_features(deep)
    idx = {n: i for i, n in enumerate(names)}
    assert d[idx["depth_hip_below_knee_max"]] > s[idx["depth_hip_below_knee_max"]]


def test_spec_hash_is_stable_and_covers_the_names():
    h1 = F.spec_hash()
    assert h1 == F.spec_hash(), "spec_hash must be deterministic"
    assert len(h1) == 64
    m = F.build_manifest()
    assert m["spec_hash"] == h1
    assert m["feature_dim"] == F.feature_dim() == len(m["feature_names"])
    assert m["excludes_face_landmarks"] is True


def test_degenerate_input_does_not_explode():
    """All-zero keypoints (no detection) must yield a finite vector, not NaNs."""
    values, _ = F.compute_features(np.zeros((10, 33, 3)))
    assert np.isfinite(values).all()
