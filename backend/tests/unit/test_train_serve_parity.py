"""
Train/serve parity guards for PostureV1.

The model is served from a checkpoint whose training code and dataset are NOT in
this repo (AUDIT.md §9.3). All we have to hold serving honest is the manifest
that shipped with the weights. These tests assert that what we feed the model at
inference time still matches what the manifest says it was trained on.

They exist because two parity defects were found in production paths (audit gaps
G-21 and G-22) that produced no error, only a logged warning:

  G-21  MediaPipe silently served complexity-1 keypoints to a model evaluated on
        complexity-2 keypoints. On one fixture video that moved prob_fault from
        0.0001 to 0.4739 against a 0.525 threshold.
  G-22  The feature StandardScaler is unpickled across scikit-learn versions
        (fitted 1.6.1, runtime pinned 1.4.0), which emits InconsistentVersionWarning.

Each test below fails loudly on the thing that previously only warned.
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pytest

pytestmark = pytest.mark.unit

_ARTIFACTS = Path(__file__).resolve().parents[2] / "app" / "ml" / "posture_v1" / "artifacts"
_MANIFEST_PATH = _ARTIFACTS / "posture_v1_manifest.json"
_SCALER_PATH = _ARTIFACTS / "posture_v1_scaler.joblib"


@pytest.fixture(scope="module")
def manifest() -> dict:
    assert _MANIFEST_PATH.exists(), f"manifest missing: {_MANIFEST_PATH}"
    return json.loads(_MANIFEST_PATH.read_text())


# ---------------------------------------------------------------------------
# 1. The manifest is the contract. Pin it, so a silent artifact swap is caught.
# ---------------------------------------------------------------------------
def test_manifest_declares_the_expected_input_contract(manifest):
    spec = manifest["input_spec"]

    assert spec["keypoints_shape"] == [300, 33, 3], (
        "model input geometry changed; preprocess.py pads/truncates to [300,33,3]"
    )
    assert spec["feature_dim"] == 151
    assert spec["sequence_policy"] == "first_300_truncate_zero_pad_tail"
    assert spec["uses_sequence_length"] is True

    # These two are easy to get wrong at serving time and silently degrade scores.
    assert spec["visibility_dropped"] is True, (
        "training dropped the visibility channel; serving must drop it too"
    )
    assert spec["keypoint_normalization"] == "none_raw_mediapipe_0_1", (
        "training used raw MediaPipe 0-1 coords; serving must not normalize them"
    )
    assert spec["feature_normalization"] == "standard_scaler_train_only"

    assert manifest["feature_order_version"] == "truth_spec_151d_v1"
    assert manifest["threshold"] == 0.525


def test_model_architecture_config_matches_manifest(manifest):
    """The instantiated nn.Module must match the checkpoint's recorded config."""
    from app.ml.posture_v1.model import PostureV1Model

    cfg = manifest["model_config"]
    model = PostureV1Model(cfg)

    assert model.config["feature_dim"] == 151
    assert model.config["num_joints"] == 33
    assert model.config["joint_dim"] == 3
    assert model.config["output_dim"] == 2

    # Fusion MLP consumes concat(lstm_hidden, rep_features); if either side drifts
    # the checkpoint's state_dict would load into the wrong shape.
    first_linear = model.fusion_mlp[0]
    assert first_linear.in_features == cfg["lstm_hidden"] + cfg["feature_dim"], (
        f"fusion input is {first_linear.in_features}, expected "
        f"{cfg['lstm_hidden']} + {cfg['feature_dim']}"
    )


# ---------------------------------------------------------------------------
# 2. G-22: the scaler must still hold its TRAINING statistics after unpickling.
#    This is the assertion that actually matters — far more than the sklearn pin.
# ---------------------------------------------------------------------------
def test_scaler_still_carries_its_training_statistics(manifest):
    """
    StandardScaler.transform is (X - mean_) / scale_. A cross-version unpickle is
    only dangerous if those fitted attributes change. Assert they are numerically
    identical to the statistics the manifest recorded at fit time, so the
    InconsistentVersionWarning can never quietly become a real corruption.
    """
    joblib = pytest.importorskip("joblib")
    assert _SCALER_PATH.exists(), f"scaler missing: {_SCALER_PATH}"

    scaler = joblib.load(_SCALER_PATH)
    stats = manifest["scaler_stats"]

    assert scaler.n_features_in_ == manifest["input_spec"]["feature_dim"] == 151

    np.testing.assert_allclose(
        [float(scaler.mean_.min()), float(scaler.mean_.max())],
        stats["mean_range"],
        rtol=0, atol=1e-12,
        err_msg="scaler mean_ no longer matches the manifest training statistics",
    )
    np.testing.assert_allclose(
        [float(scaler.scale_.min()), float(scaler.scale_.max())],
        stats["std_range"],
        rtol=0, atol=1e-12,
        err_msg="scaler scale_ no longer matches the manifest training statistics",
    )

    assert np.isfinite(scaler.mean_).all(), "scaler mean_ contains non-finite values"
    assert np.isfinite(scaler.scale_).all(), "scaler scale_ contains non-finite values"
    assert (scaler.scale_ > 0).all(), "scaler scale_ has non-positive entries (divide-by-zero)"


def test_scaler_transform_is_exactly_the_documented_arithmetic():
    """
    Guard against a future sklearn changing transform() semantics under us: the
    result must equal the hand-computed (X - mean_) / scale_.
    """
    joblib = pytest.importorskip("joblib")
    scaler = joblib.load(_SCALER_PATH)

    rng = np.random.default_rng(0)
    x = rng.normal(size=(4, scaler.n_features_in_))

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # cross-version unpickle warning is the point of G-22
        got = scaler.transform(x)

    expected = (x - scaler.mean_) / scaler.scale_
    np.testing.assert_allclose(got, expected, rtol=0, atol=1e-12)


# ---------------------------------------------------------------------------
# 3. The feature vector fed to the model.
# ---------------------------------------------------------------------------
def test_feature_extractor_emits_exactly_151_features_in_a_stable_order():
    """
    Pins the ACTUAL feature layout produced by features_151d.get_feature_names().

    NOTE — the manifest's human-readable `feature_order` block disagrees with the
    implementation for the first two groups. The manifest says:
        "0_32":  "joint{0..32}_x_mean"      (33 joints, x only)
        "33_65": "joint{0..32}_x_std"
    but the code emits:
        [0:33]   joint{0..10}_{x,y,z}_mean  (11 joints x 3 coords)
        [33:66]  joint{0..10}_{x,y,z}_std
    Both are 33 values, so the 151 total still lines up and nothing crashes —
    which is exactly why this went unnoticed. Serving is self-consistent (the
    same function builds the vector every time), but the manifest prose is not a
    reliable description of it. Asserting the real layout here so a future change
    to either one is caught. See audit gap G-24.
    """
    from app.ml.posture_v1.features_151d import get_feature_names

    names = get_feature_names()
    assert len(names) == 151, f"expected 151 feature names, got {len(names)}"
    assert len(set(names)) == 151, "feature names are not unique - order is ambiguous"

    # Block 1: per-joint means, 11 joints x (x,y,z)
    assert names[0:3] == ["joint0_x_mean", "joint0_y_mean", "joint0_z_mean"]
    assert names[32] == "joint10_z_mean"

    # Block 2: per-joint stds, same 11 joints x (x,y,z)
    assert names[33:36] == ["joint0_x_std", "joint0_y_std", "joint0_z_std"]
    assert names[65] == "joint10_z_std"

    # Block 3: per-joint ranges, 7 joints x (x,y,z) = 21  (matches the manifest)
    assert names[66] == "joint0_x_range"
    assert names[86] == "joint6_z_range"

    # Block 4: 4 angles x 15 stats = 60  (matches the manifest)
    assert names[87] == "left_knee_angle_mean"
    assert names[146] == "left_hip_angle_ascent_angular_velocity"

    # Block 5: 4 derived features  (matches the manifest)
    assert names[-4:] == [
        "bottom_trunk_wobble",
        "knee_asymmetry_mean",
        "bottom_knee_asymmetry",
        "trunk_forward_lean",
    ]


def test_preprocessing_drops_visibility_and_pads_to_300():
    """Serving must reproduce the manifest's sequence policy exactly."""
    from app.ml.posture_v1.preprocess import preprocess_pose_data

    # 10 frames x 33 landmarks, each with x/y/z/visibility.
    pose_data = [
        [{"x": 0.5, "y": 0.5, "z": 0.0, "visibility": 0.9} for _ in range(33)]
        for _ in range(10)
    ]
    result = preprocess_pose_data(pose_data)

    assert result.keypoints.shape == (300, 33, 3), (
        f"expected [300,33,3] (visibility dropped), got {result.keypoints.shape}"
    )
    assert result.sequence_length == 10, "sequence_length must be the pre-pad valid length"
    # Tail must be zero-padded, not resampled or edge-repeated.
    assert np.allclose(result.keypoints[10:], 0.0), "tail was not zero-padded"


# ---------------------------------------------------------------------------
# 4. G-21: serve the pose complexity the model was evaluated on.
# ---------------------------------------------------------------------------
def test_mediapipe_can_serve_complexity_2_without_falling_back():
    """
    AIService falls back to complexity=1 if Pose(model_complexity=2) raises
    (ai_service.py:95-105). In the container that happened on every start,
    because MediaPipe downloads pose_landmark_heavy.tflite into root-owned
    site-packages while the process runs as non-root appuser.

    The fallback is logged at WARNING and nothing else notices — so assert here
    that constructing the complexity-2 model actually succeeds.
    """
    mp = pytest.importorskip("mediapipe")

    try:
        pose = mp.solutions.pose.Pose(static_image_mode=False, model_complexity=2)
    except Exception as exc:  # pragma: no cover - this is the regression being guarded
        pytest.fail(
            "MediaPipe could not initialise at model_complexity=2, so AIService "
            f"would silently serve complexity-1 keypoints to a model evaluated at "
            f"complexity 2 (audit gap G-21). Underlying error: {exc!r}"
        )
    else:
        pose.close()


def test_configured_complexity_matches_what_postures_v1_was_trained_on():
    """AI_MODEL_COMPLEXITY must stay at 2; ai_service.py:76 ties it to training data."""
    from app.core.config import get_settings

    assert get_settings().AI_MODEL_COMPLEXITY == 2, (
        "PostureV1 was evaluated on complexity-2 keypoints "
        "(scripts/output/posture_v1_labels_and_results.csv, "
        "scripts/e2e_posture_v1_smoke.py:372)"
    )
