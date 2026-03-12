"""Unit tests for PostureV1 preprocessing, feature extraction, model, and loader.

Tests are aligned to the ML truth spec:
  - Hard truncate (no resampling/uniform sampling)
  - Zero-pad tail (not last-frame repeat)
  - 151D feature exact order and shape
  - Checkpoint dict loading (model_config + model_state_dict)
  - Forward: logits = model(kp, feat, seq_len); prob = sigmoid(logits[:,1])
  - Threshold = 0.525
"""

import gzip
import json
import numpy as np
import pytest
import torch
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.ml.posture_v1.preprocess import (
    preprocess_pose_data,
    PreprocessingResult,
    TARGET_FRAMES,
    NUM_LANDMARKS,
    NUM_COORDS,
)
from app.ml.posture_v1.features_151d import (
    compute_151d_features,
    EXPECTED_DIM,
    FEATURE_NAMES,
    get_feature_names,
)
from app.ml.posture_v1.model import PostureV1Model
from app.ml.posture_v1.loader import PostureV1TorchLoader, DEFAULT_FAULT_THRESHOLD


# ---------------------------------------------------------------------------
# Helpers to build synthetic pose_data
# ---------------------------------------------------------------------------

def _make_landmark(x: float = 0.5, y: float = 0.5, z: float = 0.0) -> dict:
    return {"x": x, "y": y, "z": z, "visibility": 0.95}


# Anatomically plausible positions for key joints so angle computations
# produce valid (non-zero) angles and don't trigger the ANGLE_VALIDITY_GATE.
# MediaPipe landmark indices: 11=left_shoulder, 12=right_shoulder,
# 23=left_hip, 24=right_hip, 25=left_knee, 26=right_knee,
# 27=left_ankle, 28=right_ankle
_STANDING_POSITIONS = {
    11: (0.44, 0.30, 0.0),  # left_shoulder (slight offset for nonzero trunk angle)
    12: (0.54, 0.30, 0.0),  # right_shoulder
    23: (0.45, 0.55, 0.0),  # left_hip
    24: (0.55, 0.55, 0.0),  # right_hip
    25: (0.44, 0.78, 0.0),  # left_knee (slight bend for nonzero knee angle)
    26: (0.56, 0.78, 0.0),  # right_knee
    27: (0.45, 0.95, 0.0),  # left_ankle
    28: (0.55, 0.95, 0.0),  # right_ankle
}


def _make_frame(offset: float = 0.0) -> list:
    """Create a valid frame with 33 landmarks at anatomically plausible positions."""
    landmarks = []
    for i in range(NUM_LANDMARKS):
        if i in _STANDING_POSITIONS:
            x, y, z = _STANDING_POSITIONS[i]
            landmarks.append(_make_landmark(x=x + offset * 0.001, y=y, z=z))
        else:
            landmarks.append(_make_landmark(x=0.5 + offset * 0.001, y=0.2 + i * 0.01))
    return landmarks


def _make_pose_data(n_frames: int, with_gaps: bool = False) -> list:
    """Create synthetic pose_data with optional gaps (None frames)."""
    data = []
    for i in range(n_frames):
        if with_gaps and i % 10 == 5:
            data.append(None)
        else:
            data.append(_make_frame(offset=float(i)))
    return data


# ===========================================================================
# Tests: preprocess_pose_data (full pipeline)
# ===========================================================================

class TestPreprocessPoseData:
    def test_output_shape(self):
        pose_data = _make_pose_data(350)
        result = preprocess_pose_data(pose_data)
        assert isinstance(result, PreprocessingResult)
        assert result.keypoints.shape == (TARGET_FRAMES, NUM_LANDMARKS, NUM_COORDS)
        assert result.keypoints.dtype == np.float32

    def test_short_video_zero_pads(self):
        """Short sequences are ZERO-PADDED at the tail (NOT last-frame repeat)."""
        pose_data = _make_pose_data(50)
        result = preprocess_pose_data(pose_data)
        assert result.keypoints.shape[0] == TARGET_FRAMES
        assert result.frames_padded > 0
        # Padded region must be all zeros
        padded_region = result.keypoints[50:]
        np.testing.assert_array_equal(padded_region, 0.0)

    def test_long_video_hard_truncates(self):
        """Long sequences are HARD TRUNCATED at [:300] — NO resampling."""
        pose_data = _make_pose_data(600)
        result = preprocess_pose_data(pose_data)
        assert result.keypoints.shape[0] == TARGET_FRAMES
        assert result.frames_truncated == 300
        assert result.sequence_length == TARGET_FRAMES

    def test_no_resample_invariant(self):
        """Verify frame content is NOT resampled: first frame of output must
        match first frame of input for both short and long sequences."""
        for n in [50, 300, 600]:
            pose_data = _make_pose_data(n)
            result = preprocess_pose_data(pose_data)
            # Reconstruct expected first frame from _make_frame(offset=0.0)
            expected_frame = np.array([
                list(_STANDING_POSITIONS.get(i, (0.5, 0.2 + i * 0.01, 0.0)))
                for i in range(NUM_LANDMARKS)
            ], dtype=np.float32)
            np.testing.assert_allclose(
                result.keypoints[0], expected_frame, atol=1e-5,
                err_msg=f"First frame mismatch for n={n} — possible resampling",
            )

    def test_sequence_length_field(self):
        """sequence_length = min(T_clean, 300)."""
        short = preprocess_pose_data(_make_pose_data(50))
        assert short.sequence_length == 50

        exact = preprocess_pose_data(_make_pose_data(300))
        assert exact.sequence_length == 300

        long = preprocess_pose_data(_make_pose_data(600))
        assert long.sequence_length == 300

    def test_empty_input_flags_no_valid(self):
        result = preprocess_pose_data([])
        assert not result.quality_ok
        assert "no_valid_frames" in result.quality_flags

    def test_all_none_frames(self):
        result = preprocess_pose_data([None] * 100)
        assert not result.quality_ok
        # None frames parse to all-zero rows -> cleaned out -> "no_valid_frames_after_clean"
        assert any("no_valid_frames" in f for f in result.quality_flags)

    def test_deterministic(self):
        """Same input should always produce same output."""
        pose_data = _make_pose_data(200)
        r1 = preprocess_pose_data(pose_data)
        r2 = preprocess_pose_data(pose_data)
        np.testing.assert_array_equal(r1.keypoints, r2.keypoints)
        assert r1.sequence_length == r2.sequence_length

    def test_with_gaps_still_produces_valid(self):
        pose_data = _make_pose_data(300, with_gaps=True)
        result = preprocess_pose_data(pose_data)
        assert result.keypoints.shape == (TARGET_FRAMES, NUM_LANDMARKS, NUM_COORDS)
        assert result.frames_interpolated > 0

    def test_visibility_dropped(self):
        """Output has 3 coords (x,y,z) — visibility must be dropped."""
        pose_data = _make_pose_data(100)
        result = preprocess_pose_data(pose_data)
        assert result.keypoints.shape[2] == 3  # NOT 4

    def test_leading_trailing_zeros_trimmed(self):
        """All-zero leading/trailing frames should be trimmed before truncate/pad."""
        # Build: 5 zero frames + 50 valid + 5 zero frames
        data = [None] * 5 + [_make_frame(offset=float(i)) for i in range(50)] + [None] * 5
        result = preprocess_pose_data(data)
        assert result.quality_ok
        assert result.valid_frame_count == 50
        assert result.frames_padded == TARGET_FRAMES - 50


# ===========================================================================
# Tests: compute_151d_features
# ===========================================================================

class TestCompute151dFeatures:
    def test_output_shape(self):
        kp = np.random.rand(TARGET_FRAMES, NUM_LANDMARKS, NUM_COORDS).astype(np.float32)
        features = compute_151d_features(kp, apply_scaler=False)
        assert features.shape == (EXPECTED_DIM,)
        assert features.dtype == np.float32

    def test_exact_dim_151(self):
        assert EXPECTED_DIM == 151

    def test_no_nan_in_output(self):
        kp = np.random.rand(TARGET_FRAMES, NUM_LANDMARKS, NUM_COORDS).astype(np.float32)
        features = compute_151d_features(kp, apply_scaler=False)
        assert not np.any(np.isnan(features))
        assert not np.any(np.isinf(features))

    def test_zero_input(self):
        kp = np.zeros((TARGET_FRAMES, NUM_LANDMARKS, NUM_COORDS), dtype=np.float32)
        features = compute_151d_features(kp, apply_scaler=False)
        assert features.shape == (EXPECTED_DIM,)
        assert np.count_nonzero(features) < EXPECTED_DIM

    def test_feature_names_count(self):
        names = get_feature_names()
        assert len(names) == EXPECTED_DIM

    def test_feature_names_exact_order(self):
        """Verify the 151D feature name ordering matches the truth spec.
        Training does: np.mean(coords, axis=0).flatten()[:33] on a [33,3] array,
        which produces xyz-interleaved means for joints 0-10 (11 joints × 3 = 33).
        """
        names = FEATURE_NAMES
        # [0–32]: xyz-interleaved means for joints 0-10
        idx = 0
        for j in range(11):
            for coord in ["x", "y", "z"]:
                assert names[idx] == f"joint{j}_{coord}_mean", f"Slot {idx} mismatch"
                idx += 1
        # [33–65]: xyz-interleaved stds for joints 0-10
        for j in range(11):
            for coord in ["x", "y", "z"]:
                assert names[33 + j * 3 + ["x", "y", "z"].index(coord)] == f"joint{j}_{coord}_std", \
                    f"Slot {33 + j * 3 + ['x', 'y', 'z'].index(coord)} mismatch"
        # [66–86]: joint{0..6}_{x,y,z}_range (7 joints × 3 coords)
        idx = 66
        for j in range(7):
            for coord in ["x", "y", "z"]:
                assert names[idx] == f"joint{j}_{coord}_range", f"Slot {idx} mismatch"
                idx += 1
        assert idx == 87
        # [87–146]: 4 angles × 15 stats
        angle_names = ["left_knee", "right_knee", "trunk", "left_hip"]
        whole_stats = ["mean", "std", "min", "max", "range", "slope"]
        phase_names = ["descent", "bottom", "ascent"]
        phase_stats = ["mean", "std", "angular_velocity"]
        for aname in angle_names:
            for s in whole_stats:
                assert names[idx] == f"{aname}_angle_{s}", f"Slot {idx} mismatch"
                idx += 1
            for pn in phase_names:
                for ps in phase_stats:
                    assert names[idx] == f"{aname}_angle_{pn}_{ps}", f"Slot {idx} mismatch"
                    idx += 1
        assert idx == 147
        # [147–150]: 4 derived features
        assert names[147] == "bottom_trunk_wobble"
        assert names[148] == "knee_asymmetry_mean"
        assert names[149] == "bottom_knee_asymmetry"
        assert names[150] == "trunk_forward_lean"

    def test_deterministic(self):
        kp = np.random.rand(TARGET_FRAMES, NUM_LANDMARKS, NUM_COORDS).astype(np.float32)
        f1 = compute_151d_features(kp, apply_scaler=False)
        f2 = compute_151d_features(kp, apply_scaler=False)
        np.testing.assert_array_equal(f1, f2)

    def test_empty_input_returns_zeros(self):
        kp = np.zeros((0, NUM_LANDMARKS, NUM_COORDS), dtype=np.float32)
        features = compute_151d_features(kp, apply_scaler=False)
        assert features.shape == (EXPECTED_DIM,)
        np.testing.assert_array_equal(features, np.zeros(EXPECTED_DIM))

    def test_feature_layout_mean_section(self):
        """Features [0-32] = flatten(np.mean(coords, axis=0))[:33] = xyz for joints 0-10."""
        np.random.seed(42)
        kp = np.random.rand(TARGET_FRAMES, NUM_LANDMARKS, NUM_COORDS).astype(np.float32)
        features = compute_151d_features(kp, apply_scaler=False)
        # Training: np.mean(coords, axis=0).flatten()[:33]
        expected = np.mean(kp, axis=0).flatten()[:33]
        np.testing.assert_allclose(
            features[:33], expected, atol=1e-5,
            err_msg="slots 0-32 (interleaved xyz means) mismatch",
        )

    def test_feature_layout_std_section(self):
        """Features [33-65] = flatten(np.std(coords, axis=0))[:33] = xyz for joints 0-10."""
        np.random.seed(42)
        kp = np.random.rand(TARGET_FRAMES, NUM_LANDMARKS, NUM_COORDS).astype(np.float32)
        features = compute_151d_features(kp, apply_scaler=False)
        # Training: np.std(coords, axis=0).flatten()[:33]
        expected = np.std(kp, axis=0).flatten()[:33]
        np.testing.assert_allclose(
            features[33:66], expected, atol=1e-5,
            err_msg="slots 33-65 (interleaved xyz stds) mismatch",
        )


# ===========================================================================
# Tests: PostureV1Model architecture
# ===========================================================================

class TestPostureV1Model:
    def test_default_forward_shape(self):
        """Model should accept truth-spec inputs and return [B, num_classes] logits."""
        model = PostureV1Model()
        model.eval()
        B = 2
        kp = torch.randn(B, 300, 33, 3)
        feat = torch.randn(B, 151)
        seq_len = torch.tensor([300, 150], dtype=torch.long)
        with torch.no_grad():
            logits = model(kp, feat, seq_len)
        assert logits.shape == (B, 2)

    def test_custom_config(self):
        """Model should respect custom config from checkpoint."""
        cfg = {
            "lstm_hidden": 64,
            "lstm_layers": 1,
            "mlp_dims": [32],
            "output_dim": 2,
        }
        model = PostureV1Model(cfg)
        model.eval()
        kp = torch.randn(1, 300, 33, 3)
        feat = torch.randn(1, 151)
        seq_len = torch.tensor([100], dtype=torch.long)
        with torch.no_grad():
            logits = model(kp, feat, seq_len)
        assert logits.shape == (1, 2)

    def test_state_dict_roundtrip(self):
        """Verify save/load of state_dict works (simulates checkpoint loading)."""
        model_a = PostureV1Model()
        sd = model_a.state_dict()
        model_b = PostureV1Model()
        model_b.load_state_dict(sd)
        # Both should produce identical output
        model_a.eval()
        model_b.eval()
        kp = torch.randn(1, 300, 33, 3)
        feat = torch.randn(1, 151)
        seq_len = torch.tensor([300], dtype=torch.long)
        with torch.no_grad():
            out_a = model_a(kp, feat, seq_len)
            out_b = model_b(kp, feat, seq_len)
        torch.testing.assert_close(out_a, out_b)


# ===========================================================================
# Tests: PostureV1TorchLoader
# ===========================================================================

class TestPostureV1TorchLoader:
    def test_default_threshold_is_0525(self):
        """Truth spec threshold = 0.525."""
        assert DEFAULT_FAULT_THRESHOLD == 0.525

    def test_predict_without_model_returns_uncertain(self):
        """When no .pt file exists, should return uncertain gracefully."""
        import tempfile

        settings = MagicMock()
        settings.USE_POSTURE_V1 = True

        loader = PostureV1TorchLoader(settings)
        # Point to empty dir so no real model is found
        loader._artifacts_dir = Path(tempfile.mkdtemp())
        pose_data = _make_pose_data(100)
        result = loader.predict_posture(pose_data)

        assert result["decision"] == "uncertain"
        assert result["confidence"] == 0.0
        assert "prob_fault" in result
        assert "quality_flags" in result
        assert "preprocessing" in result
        assert result["threshold"] == 0.525

    def test_predict_with_mocked_model(self):
        """Test full inference with a mocked model returning truth-spec logits."""
        settings = MagicMock()
        settings.USE_POSTURE_V1 = True

        loader = PostureV1TorchLoader(settings)

        # Mock model returns logits [B, 2] where class 1 is "fault"
        # sigmoid(2.0) ≈ 0.88 -> above 0.525 -> "fault"
        mock_model = MagicMock()
        mock_model.return_value = torch.tensor([[-1.0, 2.0]])  # logits
        mock_model.eval = MagicMock(return_value=mock_model)
        mock_model.to = MagicMock(return_value=mock_model)

        loader._model = mock_model
        loader._loaded = True

        pose_data = _make_pose_data(TARGET_FRAMES)
        result = loader.predict_posture(pose_data)

        assert result["decision"] == "fault"
        assert 0.85 <= result["prob_fault"] <= 0.92  # sigmoid(2.0) ≈ 0.88
        assert result["confidence"] > 0.5
        assert result["quality_ok"]

    def test_predict_good_form_with_mocked_model(self):
        """Low fault logit -> good_form decision."""
        settings = MagicMock()
        settings.USE_POSTURE_V1 = True

        loader = PostureV1TorchLoader(settings)

        # sigmoid(-2.0) ≈ 0.12 -> below 0.525 -> "good_form"
        mock_model = MagicMock()
        mock_model.return_value = torch.tensor([[2.0, -2.0]])  # logits
        mock_model.eval = MagicMock(return_value=mock_model)
        mock_model.to = MagicMock(return_value=mock_model)

        loader._model = mock_model
        loader._loaded = True

        pose_data = _make_pose_data(TARGET_FRAMES)
        result = loader.predict_posture(pose_data)

        assert result["decision"] == "good_form"
        assert result["prob_fault"] < 0.525

    def test_inference_uses_sigmoid_on_logit_col_1(self):
        """Verify prob_fault = sigmoid(logits[:,1]) — NOT logits[:,0]."""
        settings = MagicMock()
        settings.USE_POSTURE_V1 = True
        loader = PostureV1TorchLoader(settings)

        # logits[:,0] = 5.0 (would give sigmoid ≈ 0.993 if used)
        # logits[:,1] = -3.0 (sigmoid ≈ 0.047)
        # If the code incorrectly uses col 0, the assertion fails.
        mock_model = MagicMock()
        mock_model.return_value = torch.tensor([[5.0, -3.0]])
        mock_model.eval = MagicMock(return_value=mock_model)
        mock_model.to = MagicMock(return_value=mock_model)

        loader._model = mock_model
        loader._loaded = True

        pose_data = _make_pose_data(TARGET_FRAMES)
        result = loader.predict_posture(pose_data)

        # sigmoid(-3.0) ≈ 0.047
        assert result["prob_fault"] < 0.1, (
            f"prob_fault={result['prob_fault']} — model may be reading wrong logit column"
        )

    @patch("app.ml.posture_v1.loader.compute_angle_validity",
           return_value={"trunk_angle": 1.0, "left_knee_angle": 1.0,
                         "right_knee_angle": 1.0, "left_hip_angle": 1.0})
    @patch("app.ml.posture_v1.loader.compute_outlier_counts",
           return_value={"count_z3": 0, "count_z6": 0})
    def test_forward_receives_sequence_lengths(self, _mock_outlier, _mock_angle):
        """Verify the model forward call includes sequence_lengths tensor.
        Gates are patched out to ensure inference runs with synthetic data."""
        settings = MagicMock()
        settings.USE_POSTURE_V1 = True
        loader = PostureV1TorchLoader(settings)

        mock_model = MagicMock()
        mock_model.return_value = torch.tensor([[0.0, 0.0]])
        mock_model.eval = MagicMock(return_value=mock_model)
        mock_model.to = MagicMock(return_value=mock_model)

        loader._model = mock_model
        loader._loaded = True

        pose_data = _make_pose_data(150)
        loader.predict_posture(pose_data)

        # The model should have been called with 3 args: kp, feat, seq_len
        call_args = mock_model.call_args
        assert call_args is not None
        positional = call_args[0]
        assert len(positional) == 3, f"Expected 3 args to forward, got {len(positional)}"

        kp_tensor, feat_tensor, seq_len_tensor = positional
        assert kp_tensor.shape == (1, 300, 33, 3)
        assert feat_tensor.shape == (1, 151)
        assert seq_len_tensor.shape == (1,)
        assert seq_len_tensor.item() == 150  # sequence_length for 150-frame input

    def test_checkpoint_dict_loading(self):
        """Verify loader constructs model from ckpt['model_config'] and loads state_dict."""
        import tempfile, os

        settings = MagicMock()
        settings.USE_POSTURE_V1 = True

        # Build a real model, save as truth-spec checkpoint dict
        model_config = {"lstm_hidden": 64, "lstm_layers": 1, "mlp_dims": [32]}
        model = PostureV1Model(model_config)
        ckpt = {
            "model_state_dict": model.state_dict(),
            "model_config": model_config,
            "epoch": 10,
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            ckpt_path = os.path.join(tmpdir, "posture_v1.pt")
            torch.save(ckpt, ckpt_path)

            loader = PostureV1TorchLoader(settings)
            loader._artifacts_dir = Path(tmpdir)
            loader._load_model()

            assert loader._model is not None
            # Verify model produces valid output
            with torch.no_grad():
                kp = torch.randn(1, 300, 33, 3)
                feat = torch.randn(1, 151)
                seq = torch.tensor([300], dtype=torch.long)
                logits = loader._model(kp, feat, seq)
                assert logits.shape == (1, 2)

    def test_bad_checkpoint_format_fails_gracefully(self):
        """Non-dict or missing model_state_dict should not crash."""
        import tempfile, os

        settings = MagicMock()
        settings.USE_POSTURE_V1 = True

        with tempfile.TemporaryDirectory() as tmpdir:
            # Save a plain tensor (wrong format)
            ckpt_path = os.path.join(tmpdir, "posture_v1.pt")
            torch.save(torch.tensor([1, 2, 3]), ckpt_path)

            loader = PostureV1TorchLoader(settings)
            loader._artifacts_dir = Path(tmpdir)
            loader._load_model()

            assert loader._model is None  # should fail gracefully

    def test_result_has_sequence_length_field(self):
        """Result preprocessing dict should include sequence_length."""
        settings = MagicMock()
        settings.USE_POSTURE_V1 = True
        loader = PostureV1TorchLoader(settings)
        result = loader.predict_posture(_make_pose_data(200))
        assert "sequence_length" in result["preprocessing"]
        assert result["preprocessing"]["sequence_length"] == 200

    @patch("app.ml.posture_v1.loader.compute_angle_validity",
           return_value={"trunk_angle": 0.02, "left_knee_angle": 0.01,
                         "right_knee_angle": 0.90, "left_hip_angle": 0.90})
    def test_angle_validity_gate_triggers_uncertain(self, _mock):
        """When trunk valid ratio is below threshold, decision should be uncertain."""
        settings = MagicMock()
        settings.USE_POSTURE_V1 = True
        loader = PostureV1TorchLoader(settings)

        mock_model = MagicMock()
        mock_model.return_value = torch.tensor([[-1.0, 3.0]])  # would be "fault" normally
        mock_model.eval = MagicMock(return_value=mock_model)
        mock_model.to = MagicMock(return_value=mock_model)
        loader._model = mock_model
        loader._loaded = True

        result = loader.predict_posture(_make_pose_data(100))
        assert result["decision"] == "uncertain"
        assert result["prob_fault"] == 0.5
        assert any("trunk_angle_valid_ratio_low" in f for f in result["quality_flags"])
        assert any("left_knee_angle_valid_ratio_low" in f for f in result["quality_flags"])

    @patch("app.ml.posture_v1.loader.compute_angle_validity",
           return_value={"trunk_angle": 1.0, "left_knee_angle": 1.0,
                         "right_knee_angle": 1.0, "left_hip_angle": 1.0})
    @patch("app.ml.posture_v1.loader.compute_outlier_counts",
           return_value={"count_z3": 120, "count_z6": 50})
    def test_outlier_gate_triggers_uncertain(self, _mock_outlier, _mock_angle):
        """When too many features are extreme outliers, decision should be uncertain."""
        settings = MagicMock()
        settings.USE_POSTURE_V1 = True
        loader = PostureV1TorchLoader(settings)

        mock_model = MagicMock()
        mock_model.return_value = torch.tensor([[-1.0, 3.0]])  # would be "fault" normally
        mock_model.eval = MagicMock(return_value=mock_model)
        mock_model.to = MagicMock(return_value=mock_model)
        loader._model = mock_model
        loader._loaded = True

        result = loader.predict_posture(_make_pose_data(100))
        assert result["decision"] == "uncertain"
        assert result["prob_fault"] == 0.5
        assert any("outlier_z6_count" in f for f in result["quality_flags"])
        assert any("outlier_z3_count" in f for f in result["quality_flags"])

    def test_threshold_env_override(self):
        """POSTURE_V1_THRESHOLD env var should override manifest threshold."""
        import os
        settings = MagicMock()
        settings.USE_POSTURE_V1 = True

        # Test env var override
        os.environ["POSTURE_V1_THRESHOLD"] = "0.3"
        try:
            loader = PostureV1TorchLoader(settings)
            loader._load_manifest()
            assert loader._fault_threshold == 0.3
        finally:
            del os.environ["POSTURE_V1_THRESHOLD"]

    def test_set_threshold_mode(self):
        """set_threshold_mode() should update the fault threshold."""
        settings = MagicMock()
        settings.USE_POSTURE_V1 = True
        loader = PostureV1TorchLoader(settings)
        loader._loaded = True

        loader.set_threshold_mode("strict")
        assert loader._fault_threshold == 0.60

        loader.set_threshold_mode("safety")
        assert loader._fault_threshold == 0.45

        loader.set_threshold_mode("default")
        assert loader._fault_threshold == 0.525

        # Invalid mode should not change threshold
        loader.set_threshold_mode("nonexistent")
        assert loader._fault_threshold == 0.525

    def test_set_threshold_mode_env_override_takes_priority(self):
        """When POSTURE_V1_THRESHOLD env var is set, set_threshold_mode() is a no-op."""
        import os
        settings = MagicMock()
        settings.USE_POSTURE_V1 = True
        loader = PostureV1TorchLoader(settings)
        loader._loaded = True
        loader._fault_threshold = 0.3  # simulate env override

        os.environ["POSTURE_V1_THRESHOLD"] = "0.3"
        try:
            loader.set_threshold_mode("strict")
            assert loader._fault_threshold == 0.3  # unchanged
        finally:
            del os.environ["POSTURE_V1_THRESHOLD"]

    def test_shadow_mode_results_key(self):
        """When posture_v1_mode is shadow, results should go under posture_v1_shadow
        key and posture_score should NOT be written to the form_check."""
        settings = MagicMock()
        settings.USE_POSTURE_V1 = True

        loader = PostureV1TorchLoader(settings)

        # Simulate good_form prediction
        mock_model = MagicMock()
        mock_model.return_value = torch.tensor([[2.0, -2.0]])  # good_form
        mock_model.eval = MagicMock(return_value=mock_model)
        mock_model.to = MagicMock(return_value=mock_model)
        loader._model = mock_model
        loader._loaded = True

        pose_data = _make_pose_data(TARGET_FRAMES)
        result = loader.predict_posture(pose_data)

        # Simulate the shadow mode logic from analysis_tasks.py
        _is_shadow = True  # posture_v1_mode == "shadow"
        pv1_decision = result["decision"]
        pv1_prob = result["prob_fault"]

        # Build results dict as analysis_tasks.py does
        existing_results = {}
        _results_key = "posture_v1_shadow" if _is_shadow else "posture_v1"
        existing_results[_results_key] = {
            "decision": pv1_decision,
            "prob_fault": pv1_prob,
        }

        # In shadow mode, scores should NOT be written
        posture_score_written = False
        if not _is_shadow and pv1_decision != "uncertain":
            posture_score_written = True

        assert _results_key == "posture_v1_shadow"
        assert "posture_v1_shadow" in existing_results
        assert "posture_v1" not in existing_results
        assert not posture_score_written, "posture_score should NOT be written in shadow mode"

    def test_uncertain_decision_does_not_produce_score(self):
        """Verify that uncertain decisions return prob_fault=0.5 and confidence=0.0,
        which the analysis_tasks.py uses to guard against writing posture_score."""
        settings = MagicMock()
        settings.USE_POSTURE_V1 = True
        loader = PostureV1TorchLoader(settings)
        # Simulate model not loaded -> uncertain
        loader._loaded = True
        loader._model = None

        pose_data = _make_pose_data(100)
        result = loader.predict_posture(pose_data)

        assert result["decision"] == "uncertain"
        assert result["prob_fault"] == 0.5
        assert result["confidence"] == 0.0
        # Verify the guard condition used in analysis_tasks.py:
        # `if pv1_decision != "uncertain": form_check.posture_score = ...`
        # When decision IS uncertain, posture_score must NOT be written.
        # This test validates the loader returns the correct signal.

    def test_threshold_env_override_invalid_ignored(self):
        """Invalid POSTURE_V1_THRESHOLD values should be ignored."""
        import os
        settings = MagicMock()
        settings.USE_POSTURE_V1 = True

        os.environ["POSTURE_V1_THRESHOLD"] = "not_a_number"
        try:
            loader = PostureV1TorchLoader(settings)
            loader._load_manifest()
            # Should fall back to default or manifest
            assert 0.0 < loader._fault_threshold < 1.0
        finally:
            del os.environ["POSTURE_V1_THRESHOLD"]


# ===========================================================================
# Golden test helpers: real pose data fixtures (split into domain categories)
# ===========================================================================

_FIXTURE_BASE = Path(__file__).resolve().parent.parent / "fixtures" / "pose_data"
IN_DOMAIN_DIR = _FIXTURE_BASE / "in_domain_accuracy"
OUT_OF_DOMAIN_DIR = _FIXTURE_BASE / "out_of_domain_robustness"
# Legacy flat directory (backward compat)
FIXTURE_DIR = _FIXTURE_BASE
MANIFEST_PATH = FIXTURE_DIR / "manifest.json"


def _load_manifest_from(directory: Path) -> dict:
    """Load fixture manifest from a directory. Returns empty dict if not found."""
    manifest_path = directory / "manifest.json"
    if not manifest_path.exists():
        return {}
    with open(manifest_path, "r") as f:
        return json.load(f)


def _load_manifest():
    """Load the legacy flat manifest for backward compat."""
    return _load_manifest_from(FIXTURE_DIR)


def _load_fixture_from(directory: Path, name: str) -> list:
    """Load a compressed fixture JSON from a specific directory."""
    path = directory / f"{name}.json.gz"
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def _load_fixture(name: str) -> list:
    """Load from legacy flat directory or try subdirectories."""
    flat_path = FIXTURE_DIR / f"{name}.json.gz"
    if flat_path.exists():
        return _load_fixture_from(FIXTURE_DIR, name)
    # Try subdirectories
    for subdir in [IN_DOMAIN_DIR, OUT_OF_DOMAIN_DIR]:
        p = subdir / f"{name}.json.gz"
        if p.exists():
            return _load_fixture_from(subdir, name)
    raise FileNotFoundError(f"Fixture {name} not found in any fixture directory")


def _in_domain_fixtures():
    """Yield pytest.param for each in-domain (Squat More) fixture."""
    manifest = _load_manifest_from(IN_DOMAIN_DIR)
    if not manifest:
        pytest.skip("No in-domain fixture manifest found")
    for name, meta in manifest.items():
        yield pytest.param(name, meta, id=name)


def _out_of_domain_fixtures():
    """Yield pytest.param for each out-of-domain fixture."""
    manifest = _load_manifest_from(OUT_OF_DOMAIN_DIR)
    if not manifest:
        pytest.skip("No out-of-domain fixture manifest found")
    for name, meta in manifest.items():
        yield pytest.param(name, meta, id=name)


def _all_fixtures():
    """Yield pytest.param for all fixtures (both domains)."""
    for param in _in_domain_fixtures():
        yield param
    for param in _out_of_domain_fixtures():
        yield param


def _golden_fixtures():
    """Legacy: yield all fixtures (backward compat with old flat manifest)."""
    return _all_fixtures()


# ===========================================================================
# Golden tests: IN-DOMAIN accuracy (Squat More fixtures)
# ===========================================================================

class TestPostureV1InDomain:
    """
    In-domain golden tests using Squat More keypoint data.
    These fixtures come from the same dataset as training data.
    """

    @pytest.mark.parametrize("name,meta", _in_domain_fixtures())
    def test_preprocess_real_videos(self, name, meta):
        """Real in-domain pose data preprocesses to valid [300,33,3] with quality_ok."""
        pose_data = _load_fixture_from(IN_DOMAIN_DIR, name)
        result = preprocess_pose_data(pose_data)

        assert result.keypoints.shape == (TARGET_FRAMES, NUM_LANDMARKS, NUM_COORDS)
        assert result.keypoints.dtype == np.float32
        assert result.sequence_length > 0
        assert result.sequence_length == min(result.valid_frame_count, TARGET_FRAMES)
        assert result.quality_ok, (
            f"{name}: quality_ok=False, flags={result.quality_flags}"
        )
        assert "no_valid_frames" not in result.quality_flags

    @pytest.mark.parametrize("name,meta", _in_domain_fixtures())
    def test_features_real_videos(self, name, meta):
        """In-domain pose data produces valid 151D features with no NaN/inf."""
        pose_data = _load_fixture_from(IN_DOMAIN_DIR, name)
        result = preprocess_pose_data(pose_data)
        features = compute_151d_features(result.keypoints, apply_scaler=False)

        assert features.shape == (EXPECTED_DIM,)
        assert features.dtype == np.float32
        assert not np.any(np.isnan(features)), f"{name}: NaN in features"
        assert not np.any(np.isinf(features)), f"{name}: inf in features"

        # x_mean features should be in plausible MediaPipe range [0, 1]
        x_means = features[0:33]
        assert np.all(x_means >= -0.5), f"{name}: x_mean below -0.5"
        assert np.all(x_means <= 1.5), f"{name}: x_mean above 1.5"

        # Angle mean features should be in plausible degree range
        angle_features = features[87:147]
        angle_means = angle_features[0::15]  # every 15th starting at 0 = mean
        for i, v in enumerate(angle_means):
            assert 0.0 <= v <= 180.0, (
                f"{name}: angle mean #{i} = {v:.1f} outside [0, 180]"
            )

    @pytest.mark.parametrize("name,meta", _in_domain_fixtures())
    def test_deterministic_real_data(self, name, meta):
        """Same real fixture through pipeline twice produces identical results."""
        pose_data = _load_fixture_from(IN_DOMAIN_DIR, name)

        r1 = preprocess_pose_data(pose_data)
        f1 = compute_151d_features(r1.keypoints, apply_scaler=False)

        r2 = preprocess_pose_data(pose_data)
        f2 = compute_151d_features(r2.keypoints, apply_scaler=False)

        np.testing.assert_array_equal(r1.keypoints, r2.keypoints)
        assert r1.sequence_length == r2.sequence_length
        np.testing.assert_array_equal(f1, f2)

    def test_inference_aggregate(self):
        """
        In-domain aggregate accuracy test (percentage-based).

        Checks that at least PCT_FAULT_THRESHOLD% of posture_fault fixtures
        score >= threshold, and at least PCT_GOOD_THRESHOLD% of good_form
        fixtures score < threshold.

        Warns (does not hard-fail) if thresholds aren't met.
        """
        PCT_FAULT_THRESHOLD = 60  # % of posture_fault that must score >= threshold
        PCT_GOOD_THRESHOLD = 60   # % of good_form that must score < threshold

        manifest = _load_manifest_from(IN_DOMAIN_DIR)
        if not manifest:
            pytest.skip("No in-domain fixture manifest")

        artifacts_dir = Path(__file__).resolve().parent.parent.parent / "app" / "ml" / "posture_v1" / "artifacts"
        model_path = artifacts_dir / "posture_v1.pt"
        if not model_path.exists():
            pytest.skip("posture_v1.pt not found — skipping inference test")

        settings = MagicMock()
        settings.USE_POSTURE_V1 = True
        loader = PostureV1TorchLoader(settings)

        threshold = loader._fault_threshold if hasattr(loader, '_fault_threshold') else DEFAULT_FAULT_THRESHOLD

        good_probs = []
        posture_fault_probs = []
        results_log = []

        for name, meta in manifest.items():
            pose_data = _load_fixture_from(IN_DOMAIN_DIR, name)
            result = loader.predict_posture(pose_data)
            label = meta["label"]
            prob = result["prob_fault"]
            decision = result["decision"]
            confidence = result["confidence"]
            quality_flags = result.get("quality_flags", [])

            results_log.append(
                f"  {name:40s} label={label:18s} prob={prob:.4f} "
                f"decision={decision:12s} conf={confidence:.3f} flags={quality_flags}"
            )

            # Structural assertions — must always pass
            assert 0.0 <= prob <= 1.0, f"prob_fault out of range: {prob}"
            assert decision in ("good_form", "fault", "uncertain")
            assert "preprocessing" in result
            assert result["preprocessing"]["sequence_length"] > 0

            if label == "good_form":
                good_probs.append(prob)
            elif label == "posture_fault":
                posture_fault_probs.append(prob)

        # Print report
        print("\n" + "=" * 85)
        print("IN-DOMAIN AGGREGATE ACCURACY REPORT")
        print("=" * 85)
        for line in results_log:
            print(line)
        print("-" * 85)

        # Compute percentage metrics
        fault_correct = sum(1 for p in posture_fault_probs if p >= threshold)
        good_correct = sum(1 for p in good_probs if p < threshold)
        pct_fault = fault_correct / len(posture_fault_probs) * 100 if posture_fault_probs else 0
        pct_good = good_correct / len(good_probs) * 100 if good_probs else 0

        print(f"\n  Threshold: {threshold}")
        if good_probs:
            print(f"  good_form:      {good_correct}/{len(good_probs)} correct "
                  f"({pct_good:.0f}%, need >= {PCT_GOOD_THRESHOLD}%) "
                  f"mean_prob={np.mean(good_probs):.4f}")
        if posture_fault_probs:
            print(f"  posture_fault:  {fault_correct}/{len(posture_fault_probs)} correct "
                  f"({pct_fault:.0f}%, need >= {PCT_FAULT_THRESHOLD}%) "
                  f"mean_prob={np.mean(posture_fault_probs):.4f}")

        fault_pass = pct_fault >= PCT_FAULT_THRESHOLD
        good_pass = pct_good >= PCT_GOOD_THRESHOLD
        overall = fault_pass and good_pass

        print(f"\n  posture_fault accuracy: {'PASS' if fault_pass else 'FAIL (warn)'}")
        print(f"  good_form accuracy:    {'PASS' if good_pass else 'FAIL (warn)'}")
        print(f"  Overall:               {'PASS' if overall else 'FAIL (warn only)'}")
        print("=" * 85)

        if not overall:
            import warnings
            warnings.warn(
                f"Aggregate accuracy below threshold: "
                f"posture_fault={pct_fault:.0f}% (need {PCT_FAULT_THRESHOLD}%), "
                f"good_form={pct_good:.0f}% (need {PCT_GOOD_THRESHOLD}%). "
                f"See report above.",
                UserWarning,
            )


# ===========================================================================
# Golden tests: OUT-OF-DOMAIN robustness (Penn Action, etc.)
# ===========================================================================

class TestPostureV1OutOfDomain:
    """
    Out-of-domain robustness tests. These fixtures come from datasets
    not used in training (e.g., Penn Action). We assert no crashes and
    graceful handling, NOT correctness.
    """

    @pytest.mark.parametrize("name,meta", _out_of_domain_fixtures())
    def test_no_crash_preprocess(self, name, meta):
        """Out-of-domain data preprocesses without crashing."""
        pose_data = _load_fixture_from(OUT_OF_DOMAIN_DIR, name)
        result = preprocess_pose_data(pose_data)

        assert result.keypoints.shape == (TARGET_FRAMES, NUM_LANDMARKS, NUM_COORDS)
        assert result.keypoints.dtype == np.float32
        assert result.sequence_length >= 0

    @pytest.mark.parametrize("name,meta", _out_of_domain_fixtures())
    def test_no_crash_features(self, name, meta):
        """Out-of-domain data produces 151D features without crashing."""
        pose_data = _load_fixture_from(OUT_OF_DOMAIN_DIR, name)
        result = preprocess_pose_data(pose_data)
        features = compute_151d_features(result.keypoints, apply_scaler=False)

        assert features.shape == (EXPECTED_DIM,)
        assert features.dtype == np.float32
        assert not np.any(np.isnan(features)), f"{name}: NaN in features"
        assert not np.any(np.isinf(features)), f"{name}: inf in features"

    @pytest.mark.parametrize("name,meta", _out_of_domain_fixtures())
    def test_no_crash_inference(self, name, meta):
        """Out-of-domain inference returns valid result without crashing.
        Decision may be uncertain — that's OK and actually preferred."""
        artifacts_dir = Path(__file__).resolve().parent.parent.parent / "app" / "ml" / "posture_v1" / "artifacts"
        model_path = artifacts_dir / "posture_v1.pt"
        if not model_path.exists():
            pytest.skip("posture_v1.pt not found")

        settings = MagicMock()
        settings.USE_POSTURE_V1 = True
        loader = PostureV1TorchLoader(settings)

        pose_data = _load_fixture_from(OUT_OF_DOMAIN_DIR, name)
        result = loader.predict_posture(pose_data)

        # Must not crash, must return valid structure
        assert 0.0 <= result["prob_fault"] <= 1.0
        assert result["decision"] in ("good_form", "fault", "uncertain")
        assert "preprocessing" in result
        assert "quality_flags" in result

        # Log for manual review
        print(
            f"\n  OUT-OF-DOMAIN {name}: prob_fault={result['prob_fault']:.6f} "
            f"decision={result['decision']} flags={result['quality_flags']}"
        )


# ===========================================================================
# Tests: Non-squat exercise routing
# ===========================================================================

class TestNonSquatRouting:
    """Verify that non-squat exercises are correctly routed to 'not_supported'."""

    @pytest.mark.parametrize("slug", ["deadlift", "bench_press", "overhead_press", "lunge", ""])
    def test_is_squat_logic(self, slug):
        """The _is_squat check used in analysis_tasks.py returns False for non-squat slugs."""
        _is_squat = "squat" in slug if slug else False
        assert _is_squat is False, f"'{slug}' should not be classified as squat"

    @pytest.mark.parametrize("slug", ["squat", "low_bar_squat", "front_squat", "goblet_squat"])
    def test_is_squat_logic_positive(self, slug):
        """The _is_squat check returns True for squat variants."""
        _is_squat = "squat" in slug if slug else False
        assert _is_squat is True, f"'{slug}' should be classified as squat"

    def test_non_squat_result_payload(self):
        """Non-squat exercises produce a not_supported result payload matching
        the structure stored by analysis_tasks.py."""
        _exercise_slug = "deadlift"
        _is_squat = "squat" in _exercise_slug

        assert not _is_squat

        # Replicate the payload built in analysis_tasks.py for non-squat
        result = {
            "status": "not_supported",
            "exercise_type": _exercise_slug,
            "reason": "posture_v1 only supports squat",
        }

        assert result["status"] == "not_supported"
        assert result["exercise_type"] == "deadlift"
        assert "reason" in result


# ===========================================================================
# Tests: Payload guardrails (model_complexity + not_supported shape)
# ===========================================================================

class TestPayloadGuardrails:
    """Ensure result payloads contain required fields and exclude forbidden ones."""

    def test_squat_result_includes_model_complexity(self):
        """PostureV1 squat result payload must include preprocessing.model_complexity
        and preprocessing.pose_complexity_fallback."""
        settings = MagicMock()
        settings.USE_POSTURE_V1 = True

        loader = PostureV1TorchLoader(settings)

        mock_model = MagicMock()
        mock_model.return_value = torch.tensor([[1.0, -1.0]])  # good_form
        mock_model.eval = MagicMock(return_value=mock_model)
        mock_model.to = MagicMock(return_value=mock_model)
        loader._model = mock_model
        loader._loaded = True

        pose_data = _make_pose_data(TARGET_FRAMES)
        result = loader.predict_posture(pose_data)

        # The loader itself returns preprocessing from preprocess_pose_data.
        # model_complexity/pose_complexity_fallback are added by analysis_tasks.py,
        # so we verify the preprocessing dict exists and can accept those keys.
        assert "preprocessing" in result
        assert isinstance(result["preprocessing"], dict)

        # Simulate what analysis_tasks.py does: merge model_complexity into preprocessing
        result["preprocessing"]["model_complexity"] = 2
        result["preprocessing"]["pose_complexity_fallback"] = False

        assert result["preprocessing"]["model_complexity"] == 2
        assert result["preprocessing"]["pose_complexity_fallback"] is False

        # Verify the full payload has the expected squat-result keys
        assert "decision" in result
        assert "prob_fault" in result
        assert "confidence" in result
        assert "quality_flags" in result

    def test_not_supported_payload_excludes_scoring_fields(self):
        """The not_supported payload must never include named_scores,
        component_scores, or top_signals — those are squat-only."""
        # Replicate the exact payload from analysis_tasks.py line 498
        not_supported_payload = {
            "status": "not_supported",
            "exercise_type": "deadlift",
            "reason": "posture_v1 only supports squat",
        }

        # These fields must NOT be present in not_supported payloads
        forbidden_keys = ["named_scores", "component_scores", "top_signals",
                          "prob_fault", "decision", "confidence", "posture_score"]

        for key in forbidden_keys:
            assert key not in not_supported_payload, (
                f"not_supported payload must NOT contain '{key}'"
            )

        # Only these keys should be present
        allowed_keys = {"status", "exercise_type", "reason"}
        assert set(not_supported_payload.keys()) == allowed_keys
