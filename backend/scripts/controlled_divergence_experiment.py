#!/usr/bin/env python3
"""
Controlled Divergence Experiment
=================================
Isolates whether MediaPipe config is the root cause of prob_fault divergence.

Experiment A: Extract keypoints with ML-repo settings (complexity=2, native res)
              → feed into backend PostureV1 loader
              → compare prob_fault to ML repo's 0.9065

Experiment B: Extract keypoints with backend settings (complexity=1, native res)
              → feed into backend PostureV1 loader
              → compare prob_fault (isolates complexity effect)

If A matches ML repo → MediaPipe complexity is root cause.
If A still differs → preprocessing/feature mismatch exists.
"""

import os
import sys
import time
import json
from pathlib import Path

import numpy as np
import cv2

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

VIDEO_PATH = os.path.join(os.environ.get("FORMIQ_ML_DIR", os.path.expanduser("~/FORMIQ Form Analysis Model")), "tmp_infer/OpQio9X5rBs_trimmed.mp4")
ML_REPO_PROB_FAULT = 0.9065
ML_REPO_SEQ_LEN = 259


def extract_keypoints(video_path: str, model_complexity: int, label: str):
    """Extract MediaPipe keypoints at native resolution."""
    import mediapipe as mp

    cap = cv2.VideoCapture(video_path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"\n  [{label}] Video: {total} frames, {fps:.1f} FPS, {w}x{h}")
    print(f"  [{label}] MediaPipe: model_complexity={model_complexity}, native resolution")

    mp_pose = mp.solutions.pose
    pose = mp_pose.Pose(
        static_image_mode=False,
        model_complexity=model_complexity,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )

    pose_data = []
    detected = 0
    missing = 0

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
                    "x": lm.x, "y": lm.y, "z": lm.z,
                    "visibility": lm.visibility,
                })
            pose_data.append(landmarks)
            detected += 1
        else:
            pose_data.append(None)
            missing += 1

    cap.release()
    pose.close()

    ratio = missing / len(pose_data) if pose_data else 1.0
    print(f"  [{label}] Extracted: {len(pose_data)} frames, {detected} detected, {missing} missing ({ratio:.1%})")
    return pose_data


def run_backend_inference(pose_data, label: str):
    """Run through backend PostureV1 loader."""
    from app.core.config import get_settings
    from app.ml.posture_v1.loader import PostureV1TorchLoader

    loader = PostureV1TorchLoader(get_settings())
    t0 = time.monotonic()
    result = loader.predict_posture(pose_data)
    elapsed = (time.monotonic() - t0) * 1000

    prep = result.get("preprocessing", {})
    print(f"\n  [{label}] Backend inference result:")
    print(f"    prob_fault:      {result['prob_fault']}")
    print(f"    decision:        {result['decision']}")
    print(f"    confidence:      {result['confidence']}")
    print(f"    threshold:       {result['threshold']}")
    print(f"    quality_ok:      {result['quality_ok']}")
    print(f"    quality_flags:   {result['quality_flags']}")
    print(f"    sequence_length: {prep.get('sequence_length')}")
    print(f"    original_frames: {prep.get('original_frames')}")
    print(f"    valid_frames:    {prep.get('valid_frames')}")
    print(f"    frames_padded:   {prep.get('frames_padded')}")
    print(f"    latency:         {elapsed:.1f}ms")

    return result


def main():
    print("=" * 70)
    print("  CONTROLLED DIVERGENCE EXPERIMENT")
    print("=" * 70)
    print(f"\n  ML Repo reference: prob_fault={ML_REPO_PROB_FAULT}, seq_len={ML_REPO_SEQ_LEN}")

    # ── Experiment A: ML-repo settings (complexity=2) ──
    print("\n" + "─" * 70)
    print("  EXPERIMENT A: model_complexity=2 (ML repo match)")
    print("─" * 70)
    pose_data_c2 = extract_keypoints(VIDEO_PATH, model_complexity=2, label="A")
    result_a = run_backend_inference(pose_data_c2, label="A")

    # ── Experiment B: Backend default settings (complexity=1) ──
    print("\n" + "─" * 70)
    print("  EXPERIMENT B: model_complexity=1 (backend default)")
    print("─" * 70)
    pose_data_c1 = extract_keypoints(VIDEO_PATH, model_complexity=1, label="B")
    result_b = run_backend_inference(pose_data_c1, label="B")

    # ── Analysis ──
    print("\n" + "=" * 70)
    print("  COMPARISON")
    print("=" * 70)

    prob_a = result_a["prob_fault"]
    prob_b = result_b["prob_fault"]
    seq_a = result_a["preprocessing"]["sequence_length"]
    seq_b = result_b["preprocessing"]["sequence_length"]

    detected_a = sum(1 for f in pose_data_c2 if f is not None)
    detected_b = sum(1 for f in pose_data_c1 if f is not None)

    print(f"\n  {'':30s} {'ML Repo':>12s} {'Exp A (c=2)':>12s} {'Exp B (c=1)':>12s}")
    print(f"  {'─'*30} {'─'*12} {'─'*12} {'─'*12}")
    print(f"  {'model_complexity':30s} {'2':>12s} {'2':>12s} {'1':>12s}")
    print(f"  {'frames_detected':30s} {'~258':>12s} {detected_a:>12d} {detected_b:>12d}")
    print(f"  {'sequence_length':30s} {ML_REPO_SEQ_LEN:>12d} {seq_a:>12d} {seq_b:>12d}")
    print(f"  {'prob_fault':30s} {ML_REPO_PROB_FAULT:>12.4f} {prob_a:>12.6f} {prob_b:>12.6f}")
    print(f"  {'decision':30s} {'FAULT':>12s} {result_a['decision']:>12s} {result_b['decision']:>12s}")

    delta_a = abs(prob_a - ML_REPO_PROB_FAULT)
    delta_b = abs(prob_b - ML_REPO_PROB_FAULT)
    delta_ab = abs(prob_a - prob_b)

    print(f"\n  Delta A vs ML repo:  {delta_a:.4f}")
    print(f"  Delta B vs ML repo:  {delta_b:.4f}")
    print(f"  Delta A vs B:        {delta_ab:.4f}")

    print(f"\n  {'─'*70}")
    if delta_a < 0.02:
        print("  CONCLUSION: Experiment A matches ML repo (delta < 0.02)")
        print("  → MediaPipe model_complexity=1 (backend default) is the ROOT CAUSE")
        print("  → Fix: Set AI_MODEL_COMPLEXITY=2 in backend config")
    elif delta_a < 0.10:
        print("  CONCLUSION: Experiment A is close to ML repo (delta < 0.10)")
        print("  → MediaPipe complexity is PRIMARY cause, minor residual from MediaPipe non-determinism")
        if delta_ab > 0.05:
            print(f"  → complexity alone accounts for {delta_ab:.4f} of divergence")
    else:
        print("  CONCLUSION: Experiment A still diverges (delta >= 0.10)")
        print("  → Additional preprocessing or feature computation mismatch exists")
        print("  → Further investigation needed in feature extraction path")

    print(f"  {'─'*70}")


if __name__ == "__main__":
    main()
