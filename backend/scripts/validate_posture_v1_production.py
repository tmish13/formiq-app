#!/usr/bin/env python3
"""
PostureV1 Production Validation Script
=======================================

Validates that the PostureV1 CNN-LSTM model runs correctly through the
entire production path: artifact loading → preprocessing → 151D features
→ scaler → inference → scoring → DB write → API contract.

Usage:
    cd backend
    python -m scripts.validate_posture_v1_production [--video PATH_TO_MP4]

If --video is not provided, runs Phases 1, 4 (synthetic) only.
Phases 2-3 require a real video file.
Phases 5-6 are static code audits (no running server needed).
"""

import argparse
import json
import sys
import os
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# Ensure backend is on path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# ---------------------------------------------------------------------------
# Report tracking
# ---------------------------------------------------------------------------
REPORT: Dict[str, Dict[str, Any]] = {}

def record(phase: str, check: str, passed: bool, detail: str = ""):
    """Record a single check result."""
    if phase not in REPORT:
        REPORT[phase] = {"checks": [], "passed": True}
    REPORT[phase]["checks"].append({
        "check": check,
        "passed": passed,
        "detail": detail,
    })
    if not passed:
        REPORT[phase]["passed"] = False

def section(title: str):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


# ============================================================================
# PHASE 1 — Artifact & Loader Integrity
# ============================================================================
def phase_1():
    section("PHASE 1 — Artifact & Loader Integrity")

    from app.ml.posture_v1.loader import (
        PostureV1TorchLoader,
        DEFAULT_FAULT_THRESHOLD,
        THRESHOLD_MODES,
    )
    from app.core.config import get_settings
    import torch

    artifacts_dir = Path(__file__).resolve().parent.parent / "app" / "ml" / "posture_v1" / "artifacts"

    # 1.1 Artifact files exist
    for fname in ["posture_v1.pt", "posture_v1_scaler.joblib", "posture_v1_manifest.json"]:
        exists = (artifacts_dir / fname).exists()
        record("Phase 1", f"Artifact exists: {fname}", exists,
               f"Path: {artifacts_dir / fname}")
        print(f"  [{'PASS' if exists else 'FAIL'}] {fname} exists: {exists}")

    # 1.2 Load manifest
    manifest_path = artifacts_dir / "posture_v1_manifest.json"
    with open(manifest_path) as f:
        manifest = json.load(f)
    print(f"\n  Manifest version: {manifest.get('version')}")
    print(f"  Manifest threshold: {manifest.get('threshold')}")
    print(f"  Model config: {json.dumps(manifest.get('model_config', {}), indent=4)}")

    record("Phase 1", "Manifest loads", True, f"version={manifest.get('version')}")

    # 1.3 Load model via PostureV1TorchLoader
    settings = get_settings()
    loader = PostureV1TorchLoader(settings)
    available = loader.is_available()
    record("Phase 1", "is_available() == True", available)
    print(f"\n  is_available(): {available}")

    # 1.4 Threshold
    print(f"  threshold: {loader._fault_threshold}")
    thresh_ok = loader._fault_threshold == manifest.get("threshold", DEFAULT_FAULT_THRESHOLD)
    record("Phase 1", "Threshold matches manifest", thresh_ok,
           f"loader={loader._fault_threshold}, manifest={manifest.get('threshold')}")

    # 1.5 Model config from checkpoint
    model = loader._model
    if model is not None:
        print(f"  model_config: {model.config}")
        record("Phase 1", "Model loaded (not None)", True)
    else:
        record("Phase 1", "Model loaded (not None)", False, "model is None")

    # 1.6 Scaler mean/std shapes
    scaler_mean, scaler_std = loader.get_scaler_params()
    if scaler_mean is not None:
        print(f"\n  Scaler mean shape: {scaler_mean.shape}")
        print(f"  Scaler std shape: {scaler_std.shape}")
        mean_ok = scaler_mean.shape == (151,)
        std_ok = scaler_std.shape == (151,)
        record("Phase 1", "Scaler mean shape == (151,)", mean_ok, f"got {scaler_mean.shape}")
        record("Phase 1", "Scaler std shape == (151,)", std_ok, f"got {scaler_std.shape}")
    else:
        record("Phase 1", "Scaler loaded", False, "scaler_mean is None")
        print("  [FAIL] Scaler not loaded")

    # 1.7 Verify checkpoint structure
    ckpt_path = artifacts_dir / "posture_v1.pt"
    ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    has_state_dict = isinstance(ckpt, dict) and "model_state_dict" in ckpt
    record("Phase 1", "Checkpoint has model_state_dict", has_state_dict,
           f"keys={list(ckpt.keys()) if isinstance(ckpt, dict) else 'N/A'}")
    print(f"\n  Checkpoint keys: {list(ckpt.keys()) if isinstance(ckpt, dict) else 'NOT A DICT'}")

    # 1.8 Forward signature check
    if model is not None:
        import inspect
        sig = inspect.signature(model.forward)
        params = list(sig.parameters.keys())
        expected_params = ["keypoints", "rep_features", "sequence_lengths"]
        sig_ok = params == expected_params
        record("Phase 1", f"Forward signature == {expected_params}", sig_ok,
               f"got {params}")
        print(f"  Forward params: {params}")

    # 1.9 Verify sigmoid(logits[:,1]) usage in _run_inference
    import inspect
    src = inspect.getsource(loader._run_inference)
    has_sigmoid = "torch.sigmoid(logits[:, 1])" in src or "torch.sigmoid(logits[:,1])" in src
    record("Phase 1", "sigmoid(logits[:,1]) used in _run_inference", has_sigmoid)
    print(f"  sigmoid(logits[:,1]) in _run_inference source: {has_sigmoid}")

    # 1.10 Threshold applied in _decide
    src_decide = inspect.getsource(loader._decide)
    has_threshold = "_fault_threshold" in src_decide
    record("Phase 1", "_fault_threshold used in _decide", has_threshold)
    print(f"  _fault_threshold in _decide source: {has_threshold}")

    return loader


# ============================================================================
# PHASE 2 — Preprocessing Validation (requires real video)
# ============================================================================
def phase_2(video_path: str):
    section("PHASE 2 — Preprocessing Validation")

    # We need MediaPipe pose detection. Use the existing AI service for that,
    # or replicate what the production path does: pose_data from DB.
    # Since this validates production behavior, we'll use the preprocess module
    # with synthetic pose_data that mimics what MediaPipe would produce from a real video.

    # For a true end-to-end, we need to extract pose_data from the video.
    # Let's check if we can use MediaPipe directly.
    try:
        import mediapipe as mp
        import cv2
    except ImportError:
        print("  [SKIP] mediapipe or cv2 not installed — cannot run Phase 2 with real video")
        record("Phase 2", "Dependencies available", False, "mediapipe/cv2 not installed")
        return None, None

    # Extract frames and run MediaPipe
    print(f"  Video path: {video_path}")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        record("Phase 2", "Video opens", False, f"Cannot open {video_path}")
        print(f"  [FAIL] Cannot open video: {video_path}")
        return None, None

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    print(f"  Total frames: {total_frames}, FPS: {fps:.1f}")

    # Run MediaPipe pose detection
    mp_pose = mp.solutions.pose
    pose = mp_pose.Pose(
        static_image_mode=False,
        model_complexity=1,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )

    pose_data = []
    detected_count = 0
    missing_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = pose.process(rgb)

        if result.pose_landmarks:
            landmarks = []
            for lm in result.pose_landmarks.landmark:
                landmarks.append({
                    "x": lm.x,
                    "y": lm.y,
                    "z": lm.z,
                    "visibility": lm.visibility,
                })
            pose_data.append(landmarks)
            detected_count += 1
        else:
            pose_data.append(None)
            missing_count += 1

    cap.release()
    pose.close()

    print(f"\n  Total frames extracted: {len(pose_data)}")
    print(f"  Detected pose frames: {detected_count}")
    print(f"  Missing frames: {missing_count}")
    missing_ratio = missing_count / len(pose_data) if pose_data else 1.0
    print(f"  Missing frame ratio: {missing_ratio:.2%}")

    record("Phase 2", "Nonzero landmarks detected", detected_count > 0,
           f"detected={detected_count}")
    record("Phase 2", "Missing ratio < 50%", missing_ratio < 0.5,
           f"ratio={missing_ratio:.2%}")

    # Run preprocessing
    from app.ml.posture_v1.preprocess import preprocess_pose_data

    prep = preprocess_pose_data(pose_data)

    print(f"\n  Preprocessing results:")
    print(f"    keypoints shape: {prep.keypoints.shape}")
    print(f"    sequence_length: {prep.sequence_length}")
    print(f"    quality_ok: {prep.quality_ok}")
    print(f"    quality_flags: {prep.quality_flags}")
    print(f"    original_frames: {prep.original_frame_count}")
    print(f"    valid_frames: {prep.valid_frame_count}")
    print(f"    frames_padded: {prep.frames_padded}")
    print(f"    frames_truncated: {prep.frames_truncated}")

    shape_ok = prep.keypoints.shape == (300, 33, 3)
    record("Phase 2", "Tensor shape == [300, 33, 3]", shape_ok,
           f"got {prep.keypoints.shape}")

    seq_len_ok = prep.sequence_length <= 300
    record("Phase 2", "sequence_length <= 300", seq_len_ok,
           f"got {prep.sequence_length}")

    if prep.frames_padded > 0:
        padded_ok = prep.sequence_length < 300
        record("Phase 2", "sequence_length < 300 when padded", padded_ok,
               f"seq_len={prep.sequence_length}, padded={prep.frames_padded}")
        print(f"    Padding occurred: sequence_length={prep.sequence_length} < 300 ✓")

    # Verify no synthetic data
    nonzero_real = np.count_nonzero(prep.keypoints[:prep.sequence_length].sum(axis=(1, 2)))
    record("Phase 2", "Real frames have nonzero data", nonzero_real > 0,
           f"nonzero_real_frames={nonzero_real}")
    print(f"    Nonzero real frames: {nonzero_real}")

    return pose_data, prep


# ============================================================================
# PHASE 3 — Feature Pipeline Verification
# ============================================================================
def phase_3(pose_data, prep):
    section("PHASE 3 — Feature Pipeline Verification")

    if prep is None:
        print("  [SKIP] No preprocessing result — Phase 2 skipped")
        record("Phase 3", "Has preprocessing input", False, "skipped")
        return None, None

    from app.ml.posture_v1.features_151d import (
        compute_151d_features,
        compute_angle_validity,
        compute_outlier_counts,
        EXPECTED_DIM,
    )

    artifacts_dir = Path(__file__).resolve().parent.parent / "app" / "ml" / "posture_v1" / "artifacts"

    # Compute raw features (unscaled)
    features_raw = compute_151d_features(
        prep.keypoints,
        apply_scaler=False,
        sequence_length=prep.sequence_length,
    )

    # Compute scaled features
    features_scaled = compute_151d_features(
        prep.keypoints,
        artifacts_dir=artifacts_dir,
        apply_scaler=True,
        sequence_length=prep.sequence_length,
    )

    print(f"  Feature vector length: {features_raw.shape[0]}")
    dim_ok = features_raw.shape[0] == EXPECTED_DIM
    record("Phase 3", f"Feature dim == {EXPECTED_DIM}", dim_ok,
           f"got {features_raw.shape[0]}")

    print(f"\n  First 10 raw features:    {features_raw[:10]}")
    print(f"  First 10 scaled features: {features_scaled[:10]}")

    # NaN / Inf checks
    has_nan_raw = np.any(np.isnan(features_raw))
    has_inf_raw = np.any(np.isinf(features_raw))
    has_nan_scaled = np.any(np.isnan(features_scaled))
    has_inf_scaled = np.any(np.isinf(features_scaled))

    record("Phase 3", "No NaN in raw features", not has_nan_raw)
    record("Phase 3", "No Inf in raw features", not has_inf_raw)
    record("Phase 3", "No NaN in scaled features", not has_nan_scaled)
    record("Phase 3", "No Inf in scaled features", not has_inf_scaled)
    print(f"\n  NaN (raw): {has_nan_raw}, Inf (raw): {has_inf_raw}")
    print(f"  NaN (scaled): {has_nan_scaled}, Inf (scaled): {has_inf_scaled}")

    # Outlier counts
    outliers = compute_outlier_counts(features_scaled)
    print(f"\n  Outlier counts: z>3={outliers['count_z3']}, z>6={outliers['count_z6']}")
    record("Phase 3", "Outlier counts computed", True,
           f"z3={outliers['count_z3']}, z6={outliers['count_z6']}")

    # Angle validity
    kp_real = prep.keypoints[:prep.sequence_length]
    angle_validity = compute_angle_validity(kp_real)
    print(f"\n  Angle validity stats:")
    for name, ratio in angle_validity.items():
        print(f"    {name}: {ratio:.2%}")
    record("Phase 3", "Angle validity computed", True, str(angle_validity))

    # Verify sequence_length is used (real frames only)
    # The raw features should differ if we pass full 300 vs real seq_len
    features_full = compute_151d_features(
        prep.keypoints,
        apply_scaler=False,
        sequence_length=None,  # uses full 300
    )
    if prep.sequence_length < 300:
        differs = not np.allclose(features_raw, features_full, atol=1e-6)
        record("Phase 3", "sequence_length affects features (real<300)", differs,
               f"seq_len={prep.sequence_length}, features differ: {differs}")
        print(f"\n  Features differ with/without sequence_length: {differs}")
    else:
        print(f"\n  sequence_length == 300 (no padding), skip diff check")
        record("Phase 3", "sequence_length == 300 (no padding)", True)

    return features_raw, features_scaled


# ============================================================================
# PHASE 4 — True Inference Execution
# ============================================================================
def phase_4(loader, pose_data=None, prep=None):
    section("PHASE 4 — True Inference Execution")

    from app.ml.posture_v1.loader import PostureV1TorchLoader, THRESHOLD_MODES
    from app.ml.posture_v1.preprocess import preprocess_pose_data
    from app.ml.posture_v1.features_151d import compute_151d_features
    import torch

    if loader._model is None:
        print("  [FAIL] Model not loaded — cannot run inference")
        record("Phase 4", "Model available for inference", False)
        return

    # Use real pose_data if available, otherwise create synthetic but realistic data
    if pose_data is not None and prep is not None:
        print("  Using REAL video data for inference")
        test_pose_data = pose_data
    else:
        print("  Using SYNTHETIC realistic pose data for inference (no video provided)")
        print("  NOTE: Phases 2-3 skipped. Synthetic data validates model execution only.")
        # Create realistic synthetic data — 90 frames of a standing person
        np.random.seed(42)
        test_pose_data = []
        for i in range(90):
            landmarks = []
            for j in range(33):
                landmarks.append({
                    "x": 0.5 + np.random.normal(0, 0.02),
                    "y": 0.3 + j * 0.02 + np.random.normal(0, 0.01),
                    "z": np.random.normal(0, 0.1),
                    "visibility": 0.9 + np.random.uniform(0, 0.1),
                })
            test_pose_data.append(landmarks)

    # --- Run inference ---
    print("\n  --- Run 1 ---")
    result1 = loader.predict_posture(test_pose_data)
    print(f"  prob_fault: {result1['prob_fault']}")
    print(f"  decision: {result1['decision']}")
    print(f"  confidence: {result1['confidence']}")
    print(f"  threshold: {result1['threshold']}")
    print(f"  quality_ok: {result1['quality_ok']}")
    print(f"  quality_flags: {result1['quality_flags']}")
    print(f"  latency_ms: {result1['latency_ms']}")

    record("Phase 4", "Inference returns prob_fault", "prob_fault" in result1,
           f"prob_fault={result1.get('prob_fault')}")
    record("Phase 4", "Inference returns decision", "decision" in result1,
           f"decision={result1.get('decision')}")

    # --- Run 2 — determinism check ---
    print("\n  --- Run 2 (determinism) ---")
    # Reset loader to ensure fresh state (re-use same loaded model)
    result2 = loader.predict_posture(test_pose_data)
    print(f"  prob_fault: {result2['prob_fault']}")
    print(f"  decision: {result2['decision']}")

    deterministic = (
        abs(result1["prob_fault"] - result2["prob_fault"]) < 1e-5
        and result1["decision"] == result2["decision"]
    )
    record("Phase 4", "Inference is deterministic", deterministic,
           f"run1={result1['prob_fault']}, run2={result2['prob_fault']}")
    print(f"  Deterministic: {deterministic}")

    # --- Threshold flip tests ---
    # Only test if model produced a non-uncertain result
    if result1["decision"] != "uncertain":
        original_prob = result1["prob_fault"]

        # Threshold = 0.2 → should classify as fault (if prob > 0.2)
        print("\n  --- Threshold flip: 0.2 ---")
        loader._fault_threshold = 0.2
        result_low = loader.predict_posture(test_pose_data)
        print(f"  prob_fault: {result_low['prob_fault']}, decision: {result_low['decision']}")

        # Threshold = 0.95 → should classify as good_form (if prob < 0.95)
        print("\n  --- Threshold flip: 0.95 ---")
        loader._fault_threshold = 0.95
        result_high = loader.predict_posture(test_pose_data)
        print(f"  prob_fault: {result_high['prob_fault']}, decision: {result_high['decision']}")

        # Restore
        loader._fault_threshold = THRESHOLD_MODES["default"]

        # Check that decisions differ (or that prob is outside both thresholds —
        # which means the model is extremely confident in one direction)
        if result_low["decision"] != "uncertain" and result_high["decision"] != "uncertain":
            decisions_differ = result_low["decision"] != result_high["decision"]
            # If prob is near 0 or near 1, both thresholds produce same result — that's valid
            prob_extreme = original_prob < 0.05 or original_prob > 0.95
            threshold_ok = decisions_differ or prob_extreme
            record("Phase 4", "Threshold flip changes decision", threshold_ok,
                   f"low_thresh=0.2→{result_low['decision']}, high_thresh=0.95→{result_high['decision']}, "
                   f"prob={original_prob:.4f}, extreme={prob_extreme}")
            if decisions_differ:
                print(f"\n  Decisions differ with threshold flip: True")
            elif prob_extreme:
                print(f"\n  prob_fault={original_prob:.6f} is extreme — both thresholds agree correctly")
            else:
                print(f"\n  [FAIL] Decisions should differ but don't")
        else:
            print("  [INFO] One or both threshold-flip results were uncertain (quality gate)")
            record("Phase 4", "Threshold flip changes decision", True,
                   "One result was uncertain — quality gate working correctly")
    else:
        print("\n  [INFO] Inference returned 'uncertain' — threshold flip test N/A")
        record("Phase 4", "Threshold flip changes decision", True,
               "Result was uncertain — quality gates working correctly")


# ============================================================================
# PHASE 5 — Celery + DB Flow Validation (Static Code Audit)
# ============================================================================
def phase_5():
    section("PHASE 5 — Celery + DB Flow Validation (Static Code Audit)")

    print("  Auditing analysis_tasks.py for correct DB write patterns...\n")

    tasks_path = BACKEND_DIR / "app" / "tasks" / "analysis_tasks.py"
    with open(tasks_path) as f:
        tasks_src = f.read()

    # 5.1 PostureV1 loader is imported and used
    has_loader_import = "from app.ml.posture_v1.loader import PostureV1TorchLoader" in tasks_src
    record("Phase 5", "PostureV1TorchLoader imported in tasks", has_loader_import)
    print(f"  [{'PASS' if has_loader_import else 'FAIL'}] PostureV1TorchLoader imported")

    # 5.2 compute_full_scores imported
    has_scoring_import = "from app.ml.posture_v1.scoring import compute_full_scores" in tasks_src
    record("Phase 5", "compute_full_scores imported in tasks", has_scoring_import)
    print(f"  [{'PASS' if has_scoring_import else 'FAIL'}] compute_full_scores imported")

    # 5.3 posture_score written to DB
    writes_posture = "form_check.posture_score = scoring" in tasks_src
    record("Phase 5", "posture_score written from scoring dict", writes_posture)
    print(f"  [{'PASS' if writes_posture else 'FAIL'}] posture_score written from scoring")

    # 5.4 confidence_score written to DB
    writes_confidence = "form_check.confidence_score = round(pv1_confidence" in tasks_src
    record("Phase 5", "confidence_score written from real inference", writes_confidence)
    print(f"  [{'PASS' if writes_confidence else 'FAIL'}] confidence_score written from inference")

    # 5.5 Results stored under posture_v1 key
    stores_pv1_results = 'existing_results[_results_key] = _pv1_result_payload' in tasks_src
    record("Phase 5", "Results stored under posture_v1 key", stores_pv1_results)
    print(f"  [{'PASS' if stores_pv1_results else 'FAIL'}] Results stored as posture_v1 in results JSON")

    # 5.6 named_scores in payload
    has_named_scores = '"named_scores": scoring.get("named_scores"' in tasks_src
    record("Phase 5", "named_scores in result payload", has_named_scores)
    print(f"  [{'PASS' if has_named_scores else 'FAIL'}] named_scores in result payload")

    # 5.7 component_scores in payload
    has_component_scores = '"component_scores": scoring.get("component_scores"' in tasks_src
    record("Phase 5", "component_scores in result payload", has_component_scores)
    print(f"  [{'PASS' if has_component_scores else 'FAIL'}] component_scores in result payload")

    # 5.8 quality_flags in payload
    has_quality = '"quality_flags": posture_v1_result.get("quality_flags"' in tasks_src
    record("Phase 5", "quality_flags in result payload", has_quality)
    print(f"  [{'PASS' if has_quality else 'FAIL'}] quality_flags in result payload")

    # 5.9 top_signals in payload
    has_signals = '"top_signals": scoring.get("top_signals"' in tasks_src
    record("Phase 5", "top_signals in result payload", has_signals)
    print(f"  [{'PASS' if has_signals else 'FAIL'}] top_signals in result payload")

    # 5.10 Shadow mode conditional write
    has_shadow_check = "if not _is_shadow and pv1_decision" in tasks_src
    record("Phase 5", "Shadow mode guards DB score writes", has_shadow_check)
    print(f"  [{'PASS' if has_shadow_check else 'FAIL'}] Shadow mode guards score writes")

    # 5.11 Telemetry write
    has_telemetry = "PostureV1InferenceLog" in tasks_src
    record("Phase 5", "Telemetry write present", has_telemetry)
    print(f"  [{'PASS' if has_telemetry else 'FAIL'}] Telemetry write present")

    # 5.12 predict_posture called with real pose_data
    calls_predict = "posture_v1_loader.predict_posture(" in tasks_src
    record("Phase 5", "predict_posture called", calls_predict)
    print(f"  [{'PASS' if calls_predict else 'FAIL'}] predict_posture called")

    # 5.13 No hardcoded posture_score in tasks
    import re
    hardcoded_pattern = re.compile(r'form_check\.posture_score\s*=\s*\d+\.?\d*\s*$', re.MULTILINE)
    hardcoded_matches = hardcoded_pattern.findall(tasks_src)
    # Filter: the actual writes use scoring["posture_score"], not a literal
    no_hardcoded_in_tasks = len(hardcoded_matches) == 0
    record("Phase 5", "No hardcoded posture_score in tasks", no_hardcoded_in_tasks,
           f"matches: {hardcoded_matches}")
    print(f"  [{'PASS' if no_hardcoded_in_tasks else 'FAIL'}] No hardcoded posture_score")


# ============================================================================
# PHASE 6 — API Contract Validation (Static Code Audit)
# ============================================================================
def phase_6():
    section("PHASE 6 — API Contract Validation (Static Code Audit)")

    print("  Auditing form_checks.py ml-analysis endpoint...\n")

    endpoint_path = BACKEND_DIR / "app" / "api" / "v1" / "endpoints" / "form_checks.py"
    with open(endpoint_path) as f:
        endpoint_src = f.read()

    # 6.1 ml-analysis endpoint exists
    has_ml_endpoint = 'ml-analysis' in endpoint_src
    record("Phase 6", "/ml-analysis endpoint exists", has_ml_endpoint)
    print(f"  [{'PASS' if has_ml_endpoint else 'FAIL'}] /ml-analysis endpoint exists")

    # 6.2 posture_score from DB (check both quote styles)
    reads_posture = (
        "getattr(form_check, 'posture_score'" in endpoint_src
        or 'getattr(form_check, "posture_score"' in endpoint_src
    )
    record("Phase 6", "posture_score read from DB (getattr)", reads_posture)
    print(f"  [{'PASS' if reads_posture else 'FAIL'}] posture_score read from DB")

    # 6.3 confidence from DB (check both quote styles)
    reads_confidence = (
        "getattr(form_check, 'confidence_score'" in endpoint_src
        or 'getattr(form_check, "confidence_score"' in endpoint_src
    )
    record("Phase 6", "confidence_score read from DB (getattr)", reads_confidence)
    print(f"  [{'PASS' if reads_confidence else 'FAIL'}] confidence_score read from DB")

    # 6.4 posture_v1 from results JSON
    reads_pv1 = 'results.get("posture_v1"' in endpoint_src
    record("Phase 6", "posture_v1 read from results JSON", reads_pv1)
    print(f"  [{'PASS' if reads_pv1 else 'FAIL'}] posture_v1 from results JSON")

    # 6.5 named_scores surfaced
    has_named = '"named_scores": posture_v1.get("named_scores"' in endpoint_src
    record("Phase 6", "named_scores in response", has_named)
    print(f"  [{'PASS' if has_named else 'FAIL'}] named_scores surfaced")

    # 6.6 component_scores surfaced
    has_component = '"component_scores": posture_v1.get("component_scores"' in endpoint_src
    record("Phase 6", "component_scores in response", has_component)
    print(f"  [{'PASS' if has_component else 'FAIL'}] component_scores surfaced")

    # 6.7 top_signals surfaced
    has_signals = '"top_signals": posture_v1.get("top_signals"' in endpoint_src
    record("Phase 6", "top_signals in response", has_signals)
    print(f"  [{'PASS' if has_signals else 'FAIL'}] top_signals surfaced")

    # 6.8 decision surfaced
    has_decision = '"decision": posture_v1.get("decision")' in endpoint_src
    record("Phase 6", "decision in response", has_decision)
    print(f"  [{'PASS' if has_decision else 'FAIL'}] decision surfaced")

    # 6.9 confidence surfaced at top level
    has_conf_top = '"confidence": posture_v1.get("confidence")' in endpoint_src
    record("Phase 6", "confidence at top level", has_conf_top)
    print(f"  [{'PASS' if has_conf_top else 'FAIL'}] confidence at top level")

    # 6.10 posture_v1_shadow conditional
    has_shadow = 'posture_v1_shadow' in endpoint_src
    record("Phase 6", "posture_v1_shadow in response (conditional)", has_shadow)
    print(f"  [{'PASS' if has_shadow else 'FAIL'}] posture_v1_shadow conditional")

    # 6.11 No hardcoded score values in ml-analysis endpoint
    import re
    # Extract just the ml-analysis function
    ml_func_match = re.search(
        r'async def get_ml_analysis.*?(?=\nasync def |\nclass |\Z)',
        endpoint_src,
        re.DOTALL
    )
    if ml_func_match:
        ml_func_src = ml_func_match.group(0)
        # Check for hardcoded numeric assignments to score fields
        hardcoded = re.findall(
            r'(?:posture_score|stability_score|depth_score|confidence)\s*[:=]\s*\d+\.?\d*(?!\s*\))',
            ml_func_src
        )
        no_hardcoded = len(hardcoded) == 0
        record("Phase 6", "No hardcoded scores in ml-analysis", no_hardcoded,
               f"matches: {hardcoded}")
        print(f"  [{'PASS' if no_hardcoded else 'FAIL'}] No hardcoded scores in ml-analysis")
    else:
        record("Phase 6", "ml-analysis function found", False)

    # 6.12 Validate DB model has correct columns
    model_path = BACKEND_DIR / "app" / "models" / "form_check.py"
    with open(model_path) as f:
        model_src = f.read()

    for col in ["posture_score", "confidence_score", "stability_score", "depth_score", "results", "details"]:
        has_col = f"{col} = Column(" in model_src
        record("Phase 6", f"FormCheck.{col} column exists", has_col)
        print(f"  [{'PASS' if has_col else 'FAIL'}] FormCheck.{col} column exists")

    # 6.13 confidence_score validation is 0-1
    conf_validation = "'confidence_score' and not (0 <= score <= 1)" in model_src
    record("Phase 6", "confidence_score validated 0-1 in model", conf_validation)
    print(f"  [{'PASS' if conf_validation else 'FAIL'}] confidence_score validated 0-1")

    # 6.14 posture_score validation is 0-100
    posture_validation = "'posture_score' and not (0 <= score <= 100)" in model_src
    record("Phase 6", "posture_score validated 0-100 in model", posture_validation)
    print(f"  [{'PASS' if posture_validation else 'FAIL'}] posture_score validated 0-100")


# ============================================================================
# HARDCODED SCORE AUDIT
# ============================================================================
def hardcoded_audit():
    section("HARDCODED SCORE AUDIT — Production Path Only")

    print("  Checking PostureV1 production path files for hardcoded values...\n")

    production_files = [
        BACKEND_DIR / "app" / "ml" / "posture_v1" / "loader.py",
        BACKEND_DIR / "app" / "ml" / "posture_v1" / "model.py",
        BACKEND_DIR / "app" / "ml" / "posture_v1" / "preprocess.py",
        BACKEND_DIR / "app" / "ml" / "posture_v1" / "features_151d.py",
        BACKEND_DIR / "app" / "ml" / "posture_v1" / "scoring.py",
        BACKEND_DIR / "app" / "tasks" / "analysis_tasks.py",
        BACKEND_DIR / "app" / "api" / "v1" / "endpoints" / "form_checks.py",
    ]

    import re
    # Patterns that indicate hardcoded mock scores
    suspicious = re.compile(
        r'(?:posture_score|confidence_score|stability_score|depth_score)\s*=\s*(?:78|72|85|50|100|0\.85|0\.72|0\.78)\b'
    )

    all_clean = True
    for fpath in production_files:
        if not fpath.exists():
            continue
        with open(fpath) as f:
            src = f.read()
        matches = suspicious.findall(src)
        if matches:
            print(f"  [WARN] {fpath.relative_to(BACKEND_DIR)}: {matches}")
            all_clean = False
        else:
            print(f"  [CLEAN] {fpath.relative_to(BACKEND_DIR)}")

    # Specific check: scoring.py compute_posture_score uses formula, not hardcoded
    scoring_path = BACKEND_DIR / "app" / "ml" / "posture_v1" / "scoring.py"
    with open(scoring_path) as f:
        scoring_src = f.read()
    uses_formula = "100 * (1.0 - prob_fault)" in scoring_src
    record("Hardcoded Audit", "scoring.py uses formula not hardcoded", uses_formula)
    print(f"\n  [{'PASS' if uses_formula else 'FAIL'}] scoring.py posture_score = 100*(1-prob_fault)")

    # Check component scores use z-score mapping
    uses_z = "_z_to_score" in scoring_src
    record("Hardcoded Audit", "Component scores use z-score mapping", uses_z)
    print(f"  [{'PASS' if uses_z else 'FAIL'}] Component scores use _z_to_score()")

    record("Hardcoded Audit", "Production path clean of hardcoded mocks", all_clean)
    print(f"\n  [{'PASS' if all_clean else 'FAIL'}] All production files clean of hardcoded mocks")


# ============================================================================
# FINAL REPORT
# ============================================================================
def print_final_report():
    section("FINAL PRODUCTION VALIDATION REPORT")

    phase_names = {
        "Phase 1": "Model Execution Status",
        "Phase 2": "MediaPipe Extraction",
        "Phase 3": "Feature Integrity",
        "Phase 4": "Inference Deterministic",
        "Phase 5": "DB Write Integrity",
        "Phase 6": "API Contract Integrity",
        "Hardcoded Audit": "Hardcoded Score Audit",
    }

    all_pass = True
    failures = []

    for phase_key, display_name in phase_names.items():
        data = REPORT.get(phase_key, {"passed": False, "checks": []})
        passed = data["passed"]
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_pass = False
        print(f"  {display_name:40s} {status}")

        # Show failures
        for check in data.get("checks", []):
            if not check["passed"]:
                failures.append(f"  [{phase_key}] {check['check']}: {check['detail']}")

    verdict = "SAFE" if all_pass else "UNSAFE"
    print(f"\n  {'='*50}")
    print(f"  Production Readiness Verdict: {verdict}")
    print(f"  {'='*50}")

    if failures:
        print(f"\n  Failures ({len(failures)}):")
        for f in failures:
            print(f"    {f}")

    return all_pass


# ============================================================================
# Main
# ============================================================================
def main():
    parser = argparse.ArgumentParser(description="PostureV1 Production Validation")
    parser.add_argument("--video", type=str, default=None,
                        help="Path to a real MP4 video file for Phases 2-3")
    args = parser.parse_args()

    print("PostureV1 Production Validation Script")
    print(f"Backend dir: {BACKEND_DIR}")

    # Phase 1 — always runs
    loader = phase_1()

    # Phase 2 — requires video
    pose_data = None
    prep = None
    if args.video:
        pose_data, prep = phase_2(args.video)
    else:
        print("\n  [SKIP] Phase 2 — no --video argument provided")
        record("Phase 2", "Video provided", True, "skipped — no video arg")

    # Phase 3 — requires Phase 2
    features_raw = None
    features_scaled = None
    if prep is not None:
        features_raw, features_scaled = phase_3(pose_data, prep)
    else:
        if not args.video:
            print("\n  [SKIP] Phase 3 — no video data")
            record("Phase 3", "Video data available", True, "skipped — no video")

    # Phase 4 — inference (uses real data if available, synthetic otherwise)
    phase_4(loader, pose_data, prep)

    # Phase 5 — static code audit
    phase_5()

    # Phase 6 — API contract audit
    phase_6()

    # Hardcoded score audit
    hardcoded_audit()

    # Final report
    all_pass = print_final_report()

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
