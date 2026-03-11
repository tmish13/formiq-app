"""
PostureV1 PyTorch model loader and inference wrapper.

Loads a CNN-LSTM checkpoint (.pt) saved as a dict:
    {'model_state_dict': ..., 'model_config': {...}, ...}

Constructs the model from model_config, loads state_dict, then runs
inference with the exact forward signature:
    logits = model(keypoints[B,300,33,3], rep_features[B,151], sequence_lengths[B])
    prob_fault = sigmoid(logits[:,1])
    threshold  = 0.525

Usage:
    loader = PostureV1TorchLoader(settings)
    result = loader.predict_posture(pose_data)
"""

import logging
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import torch

from app.core.config import Settings
from app.ml.posture_v1.preprocess import preprocess_pose_data, PreprocessingResult
from app.ml.posture_v1.features_151d import (
    compute_151d_features,
    compute_angle_validity,
    compute_outlier_counts,
    EXPECTED_DIM,
)

logger = logging.getLogger(__name__)

# Truth-spec threshold
DEFAULT_FAULT_THRESHOLD = 0.525

# Named threshold modes — adjusts decision boundary without retraining
THRESHOLD_MODES = {
    "default": 0.525,
    "strict": 0.60,
    "safety": 0.45,
}

# Safety gates — minimum quality for meaningful inference
MIN_SEQUENCE_LENGTH = 15        # < 0.5s at 30fps
MAX_MISSING_FRAME_RATIO = 0.50  # > 50% missing frames

# ANGLE_VALIDITY_GATE: if trunk angle has < 10% valid frames, or any key
# angle has < 5% valid frames, the pose data is likely out-of-domain
# (e.g. different dataset, malformed landmarks) and inference is unreliable.
# NOTE: ratios are computed over the full 300-frame padded window, so a
# 72-frame video can have at most ~24% valid. Thresholds must account for
# zero-padded tails.
TRUNK_ANGLE_MIN_VALID_RATIO = 0.10
ANY_ANGLE_MIN_VALID_RATIO = 0.05

# OUTLIER_GATE: if too many scaled features are extreme outliers, the input
# distribution is too far from training data for meaningful inference.
# z>6 = ~2e-9 probability under normal; z>3 = ~0.3%
# NOTE: In-domain fixtures commonly have 17-63 features at |z|>3 due to
# systematic x_std drift. Thresholds set high enough to not gate valid data
# but catch truly out-of-distribution inputs.
MAX_OUTLIERS_Z6 = 40   # more than 40 features at |z|>6 → uncertain
MAX_OUTLIERS_Z3 = 100  # more than 100 features at |z|>3 → uncertain (~66% of 151)

# Artifact filenames
_MODEL_FILENAME = "posture_v1.pt"
_MANIFEST_FILENAME = "posture_v1_manifest.json"


class PostureV1TorchLoader:
    """
    Loader and inference wrapper for the PostureV1 CNN-LSTM model.

    Parallel to EnhancedSquatModelLoader but for the PyTorch posture model.
    Designed to coexist — the two can be toggled via feature flag.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self._artifacts_dir = Path(__file__).parent / "artifacts"
        self._model: Optional[torch.nn.Module] = None
        self._manifest: Dict[str, Any] = {}
        self._loaded = False
        self._load_lock = threading.Lock()  # prevents double-load across Celery threads
        self._fault_threshold = DEFAULT_FAULT_THRESHOLD
        self._device = torch.device("cpu")

    # ------------------------------------------------------------------
    # Lazy loading
    # ------------------------------------------------------------------

    def _ensure_loaded(self) -> None:
        """Load model + manifest on first use (thread-safe double-checked locking)."""
        if self._loaded:
            return
        with self._load_lock:
            if self._loaded:  # re-check after acquiring lock
                return
            self._load_manifest()
            self._load_model()
            self._loaded = True

    def _load_manifest(self) -> None:
        """Load manifest JSON if present (threshold override, version, etc).

        Threshold priority (highest first):
          1. POSTURE_V1_THRESHOLD env var
          2. posture_v1_manifest.json "threshold" key
          3. DEFAULT_FAULT_THRESHOLD (0.525)
        """
        import os

        manifest_path = self._artifacts_dir / _MANIFEST_FILENAME
        if manifest_path.exists():
            import json
            try:
                with open(manifest_path, "r") as f:
                    self._manifest = json.load(f)
                self._fault_threshold = self._manifest.get(
                    "threshold", DEFAULT_FAULT_THRESHOLD
                )
                logger.info(
                    "PostureV1 manifest loaded: version=%s threshold=%.3f",
                    self._manifest.get("version", "unknown"),
                    self._fault_threshold,
                )
            except Exception as e:
                logger.warning("Failed to load PostureV1 manifest: %s", e)

        # Env var override (highest priority)
        env_threshold = os.environ.get("POSTURE_V1_THRESHOLD")
        if env_threshold is not None:
            try:
                val = float(env_threshold)
                if 0.0 < val < 1.0:
                    logger.info(
                        "PostureV1 threshold overridden by POSTURE_V1_THRESHOLD env var: %.3f -> %.3f",
                        self._fault_threshold, val,
                    )
                    self._fault_threshold = val
                else:
                    logger.warning(
                        "POSTURE_V1_THRESHOLD=%s out of (0,1) range, ignoring",
                        env_threshold,
                    )
            except ValueError:
                logger.warning(
                    "POSTURE_V1_THRESHOLD=%s not a valid float, ignoring",
                    env_threshold,
                )

    def _load_model(self) -> None:
        """
        Load the PyTorch checkpoint dict and construct model.

        Checkpoint format (from training repo):
            {
                'model_state_dict': OrderedDict(...),
                'model_config': { ... architecture hyperparams ... },
                ...  (may also contain optimizer_state_dict, epoch, etc.)
            }
        """
        model_path = self._artifacts_dir / _MODEL_FILENAME
        if not model_path.exists():
            logger.warning(
                "PostureV1 model not found at %s. "
                "predict_posture() will return uncertain results. "
                "Place posture_v1.pt in %s to enable inference.",
                model_path, self._artifacts_dir,
            )
            return

        try:
            from app.ml.posture_v1.model import PostureV1Model

            ckpt = torch.load(
                model_path,
                map_location=self._device,
                weights_only=False,
            )

            if not isinstance(ckpt, dict) or "model_state_dict" not in ckpt:
                raise ValueError(
                    "Checkpoint must be a dict with 'model_state_dict' key. "
                    f"Got type={type(ckpt).__name__}, "
                    f"keys={list(ckpt.keys()) if isinstance(ckpt, dict) else 'N/A'}"
                )

            model_config = ckpt.get("model_config", {})
            self._model = PostureV1Model(model_config)
            self._model.load_state_dict(ckpt["model_state_dict"])
            self._model.eval()
            self._model.to(self._device)

            logger.info(
                "PostureV1 model loaded from %s (config=%s)",
                model_path, model_config,
            )
        except Exception as e:
            logger.error("Failed to load PostureV1 model: %s", e, exc_info=True)
            self._model = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def predict_posture(
        self,
        pose_data: List[Optional[List[Optional[Dict[str, float]]]]],
    ) -> Dict[str, Any]:
        """
        Run posture fault classification on raw pose_data.

        Returns:
            Dict with keys: prob_fault, decision, confidence, threshold,
            quality_flags, quality_ok, preprocessing, model_version,
            feature_version, latency_ms.
        """
        t0 = time.monotonic()

        self._ensure_loaded()

        # --- Preprocess ---
        prep = preprocess_pose_data(pose_data)

        # Early exit if quality is too bad
        if not prep.quality_ok and "no_valid_frames" in prep.quality_flags:
            return self._make_result(
                prob_fault=0.5,
                decision="uncertain",
                confidence=0.0,
                prep=prep,
                latency_ms=(time.monotonic() - t0) * 1000,
                extra={"reason": "no_valid_frames"},
            )

        # Safety gate: too few valid frames for meaningful inference
        if prep.sequence_length < MIN_SEQUENCE_LENGTH:
            logger.warning(
                "PostureV1: sequence_length=%d < %d minimum — forcing uncertain",
                prep.sequence_length, MIN_SEQUENCE_LENGTH,
            )
            return self._make_result(
                prob_fault=0.5,
                decision="uncertain",
                confidence=0.0,
                prep=prep,
                latency_ms=(time.monotonic() - t0) * 1000,
                extra={"reason": f"sequence_too_short_{prep.sequence_length}"},
            )

        # Safety gate: too many missing frames
        if prep.original_frame_count > 0:
            missing_ratio = 1.0 - (prep.valid_frame_count / prep.original_frame_count)
            if missing_ratio > MAX_MISSING_FRAME_RATIO:
                logger.warning(
                    "PostureV1: %.0f%% frames missing (>%.0f%% threshold) — forcing uncertain",
                    missing_ratio * 100, MAX_MISSING_FRAME_RATIO * 100,
                )
                return self._make_result(
                    prob_fault=0.5,
                    decision="uncertain",
                    confidence=0.0,
                    prep=prep,
                    latency_ms=(time.monotonic() - t0) * 1000,
                    extra={"reason": f"too_many_missing_frames_{missing_ratio:.0%}"},
                )

        # --- Compute 151D features ---
        # Pass sequence_length so features are computed on real frames only
        # (not zero-padded tail) — matches training pipeline exactly.
        features_151d = compute_151d_features(
            prep.keypoints,
            artifacts_dir=self._artifacts_dir,
            sequence_length=prep.sequence_length,
        )
        # Raw (unscaled) for scoring module
        features_151d_raw = compute_151d_features(
            prep.keypoints,
            apply_scaler=False,
            sequence_length=prep.sequence_length,
        )

        # --- ANGLE_VALIDITY_GATE ---
        # Compute on real frames only (not padded) for meaningful ratios
        kp_real = prep.keypoints[:prep.sequence_length]
        angle_validity = compute_angle_validity(kp_real)
        gate_flags = []

        trunk_valid = angle_validity.get("trunk_angle", 0.0)
        if trunk_valid < TRUNK_ANGLE_MIN_VALID_RATIO:
            gate_flags.append(f"trunk_angle_valid_ratio_low_{trunk_valid:.2f}")
            logger.warning(
                "PostureV1 ANGLE_VALIDITY_GATE: trunk valid ratio %.2f < %.2f",
                trunk_valid, TRUNK_ANGLE_MIN_VALID_RATIO,
            )

        for angle_name, ratio in angle_validity.items():
            if ratio < ANY_ANGLE_MIN_VALID_RATIO:
                gate_flags.append(f"{angle_name}_valid_ratio_low_{ratio:.2f}")
                logger.warning(
                    "PostureV1 ANGLE_VALIDITY_GATE: %s valid ratio %.2f < %.2f",
                    angle_name, ratio, ANY_ANGLE_MIN_VALID_RATIO,
                )

        if gate_flags:
            # Merge gate flags into preprocessing quality_flags
            all_flags = prep.quality_flags + gate_flags
            return self._make_result(
                prob_fault=0.5,
                decision="uncertain",
                confidence=0.0,
                prep=prep,
                latency_ms=(time.monotonic() - t0) * 1000,
                extra={
                    "reason": "angle_validity_gate",
                    "angle_validity": angle_validity,
                    "gate_flags": gate_flags,
                    "_raw_features_151d": features_151d_raw,
                },
            )

        # --- OUTLIER_GATE ---
        outlier_counts = compute_outlier_counts(features_151d)
        n_z3 = outlier_counts["count_z3"]
        n_z6 = outlier_counts["count_z6"]

        if n_z6 > MAX_OUTLIERS_Z6 or n_z3 > MAX_OUTLIERS_Z3:
            gate_flags_outlier = []
            if n_z6 > MAX_OUTLIERS_Z6:
                gate_flags_outlier.append(f"outlier_z6_count_{n_z6}")
            if n_z3 > MAX_OUTLIERS_Z3:
                gate_flags_outlier.append(f"outlier_z3_count_{n_z3}")
            logger.warning(
                "PostureV1 OUTLIER_GATE: z3=%d (max=%d) z6=%d (max=%d)",
                n_z3, MAX_OUTLIERS_Z3, n_z6, MAX_OUTLIERS_Z6,
            )
            return self._make_result(
                prob_fault=0.5,
                decision="uncertain",
                confidence=0.0,
                prep=prep,
                latency_ms=(time.monotonic() - t0) * 1000,
                extra={
                    "reason": "outlier_gate",
                    "outlier_counts": outlier_counts,
                    "gate_flags": gate_flags_outlier,
                    "_raw_features_151d": features_151d_raw,
                },
            )

        # --- Inference ---
        if self._model is None:
            logger.warning(
                "PostureV1 model not loaded — returning uncertain. "
                "Features were computed successfully (%dD).",
                features_151d.shape[0],
            )
            return self._make_result(
                prob_fault=0.5,
                decision="uncertain",
                confidence=0.0,
                prep=prep,
                latency_ms=(time.monotonic() - t0) * 1000,
                extra={"reason": "model_not_loaded"},
            )

        prob_fault = self._run_inference(
            prep.keypoints, features_151d, prep.sequence_length,
        )
        decision = self._decide(prob_fault, prep.quality_ok)
        confidence = abs(prob_fault - 0.5) * 2  # distance from boundary

        latency_ms = (time.monotonic() - t0) * 1000
        logger.info(
            "PostureV1 inference: prob_fault=%.4f decision=%s confidence=%.3f latency=%.1fms",
            prob_fault, decision, confidence, latency_ms,
        )

        # --- Per-component visibility (extracted from raw pose_data, before preprocessing) ---
        # visibility channel is dropped by preprocess_pose_data(); we recover it here
        # from the original pose_data dict using real frames only.
        try:
            from app.ml.posture_v1.visibility import (
                compute_joint_visibility,
                compute_component_visibility,
            )
            joint_vis = compute_joint_visibility(pose_data, sequence_length=prep.sequence_length)
            comp_vis: dict = compute_component_visibility(joint_vis)
        except Exception as vis_exc:
            logger.debug("Visibility extraction failed (non-fatal): %s", vis_exc)
            comp_vis = {}

        return self._make_result(
            prob_fault=prob_fault,
            decision=decision,
            confidence=confidence,
            prep=prep,
            latency_ms=latency_ms,
            extra={
                "_raw_features_151d": features_151d_raw,
                "_component_visibility": comp_vis,
            },
        )

    def set_threshold_mode(self, mode: str) -> None:
        """Set the fault threshold from a named mode.

        Priority remains: env var > mode > manifest > default.
        Calling this only takes effect if no POSTURE_V1_THRESHOLD env var is set.
        """
        import os
        if os.environ.get("POSTURE_V1_THRESHOLD"):
            logger.info(
                "PostureV1 set_threshold_mode('%s') ignored — POSTURE_V1_THRESHOLD env var takes priority",
                mode,
            )
            return
        if mode not in THRESHOLD_MODES:
            logger.warning(
                "PostureV1 unknown threshold mode '%s', valid modes: %s",
                mode, list(THRESHOLD_MODES.keys()),
            )
            return
        old = self._fault_threshold
        self._fault_threshold = THRESHOLD_MODES[mode]
        logger.info(
            "PostureV1 threshold mode set to '%s': %.3f -> %.3f",
            mode, old, self._fault_threshold,
        )

    def is_available(self) -> bool:
        """Check if the model artifact exists and can be loaded."""
        try:
            self._ensure_loaded()
            return self._model is not None
        except Exception:
            return False

    def get_scaler_params(self) -> tuple:
        """Return (mean, std) arrays from the training scaler, or (None, None)."""
        self._ensure_loaded()
        from app.ml.posture_v1.features_151d import _scaler_cache, _SCALER_FILENAME
        scaler_path = str(self._artifacts_dir / _SCALER_FILENAME)
        # Trigger scaler loading if not yet cached
        if scaler_path not in _scaler_cache:
            from app.ml.posture_v1.features_151d import _apply_scaler
            _apply_scaler(np.zeros(EXPECTED_DIM, dtype=np.float32), self._artifacts_dir)
        scaler = _scaler_cache.get(scaler_path)
        if scaler is not None and hasattr(scaler, 'mean_') and hasattr(scaler, 'scale_'):
            return scaler.mean_, scaler.scale_
        return None, None

    def get_metadata(self) -> Dict[str, Any]:
        """Return manifest + availability info."""
        self._ensure_loaded()
        return {
            "model_available": self._model is not None,
            "model_version": self._manifest.get("version", "unknown"),
            "threshold": self._fault_threshold,
            "feature_dim": EXPECTED_DIM,
            "artifacts_dir": str(self._artifacts_dir),
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _run_inference(
        self,
        keypoints: np.ndarray,
        features_151d: np.ndarray,
        sequence_length: int,
    ) -> float:
        """
        Forward pass through the CNN-LSTM.

        Truth-spec forward:
            logits = model(keypoints[B,300,33,3], rep_features[B,151], sequence_lengths[B])
            prob_fault = sigmoid(logits[:,1])

        Args:
            keypoints: [300, 33, 3] numpy array
            features_151d: [151] numpy array (already scaler-normalized)
            sequence_length: actual valid frame count (for pack_padded_sequence)

        Returns:
            Probability of posture fault (float in [0, 1]).
        """
        with torch.inference_mode():
            torch.manual_seed(0)      # ensures any non-deterministic path is seeded
            kp_tensor = torch.from_numpy(keypoints).unsqueeze(0).float().to(self._device)
            # shape: [1, 300, 33, 3]

            feat_tensor = torch.from_numpy(features_151d).unsqueeze(0).float().to(self._device)
            # shape: [1, 151]

            seq_len_tensor = torch.tensor(
                [sequence_length], dtype=torch.long, device=self._device,
            )
            # shape: [1]

            logits = self._model(kp_tensor, feat_tensor, seq_len_tensor)
            # logits shape: [1, num_classes]

            # Truth spec: prob_fault = sigmoid(logits[:,1])
            prob_fault = torch.sigmoid(logits[:, 1]).item()

            return float(np.clip(prob_fault, 0.0, 1.0))

    def _decide(self, prob_fault: float, quality_ok: bool) -> str:
        """Map probability to a discrete decision."""
        if not quality_ok:
            return "uncertain"
        if prob_fault >= self._fault_threshold:
            return "fault"
        return "good_form"

    def _make_result(
        self,
        prob_fault: float,
        decision: str,
        confidence: float,
        prep: PreprocessingResult,
        latency_ms: float,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build the standardized result dict."""
        # Merge gate_flags from extra into quality_flags
        gate_flags = extra.pop("gate_flags", []) if extra else []
        all_quality_flags = prep.quality_flags + gate_flags

        result = {
            "prob_fault": round(prob_fault, 6),
            "decision": decision,
            "confidence": round(confidence, 4),
            "threshold": self._fault_threshold,
            "quality_flags": all_quality_flags,
            "quality_ok": prep.quality_ok and len(gate_flags) == 0,
            "preprocessing": {
                "original_frames": prep.original_frame_count,
                "valid_frames": prep.valid_frame_count,
                "sequence_length": prep.sequence_length,
                "frames_interpolated": prep.frames_interpolated,
                "frames_padded": prep.frames_padded,
                "frames_truncated": prep.frames_truncated,
            },
            "model_version": self._manifest.get("version", "posture_v1"),
            "feature_version": "151d_v1",
            "latency_ms": round(latency_ms, 1),
        }
        if extra:
            result.update(extra)
        return result
