#!/usr/bin/env python3
"""
One-video diff: why does the eval CSV say prob_fault=0.0001 when serving says ~0.33?

Target: backend/test_videos/good/T6ad8Et3C5Q_good_rep_1.mp4
  eval CSV : prob_fault 0.0001, confidence 1.000, frames 89, orig_frames 90, complexity 2
  serving  : prob_fault 0.3347, confidence 0.331, sequence_length 90, complexity 2

The "frames" column is the lead. This script reports what the container actually
produces at each stage, then sweeps sequence_length to see whether that single
knob can move prob_fault across the observed range, and diffs the feature vector
to name which features are responsible.

Bench only. No serving changes.
    docker compose -f backend/deployment/docker-compose.yml exec -T app \
        python - < bench/one_video_diff.py
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "/app")

VIDEO = Path("/app/test_videos/good/T6ad8Et3C5Q_good_rep_1.mp4")
EVAL_PROB = 0.0001
EVAL_FRAMES = 89
SERVING_PROB = 0.3347


def main():
    import cv2
    from app.core.config import get_settings
    from app.services.ai_service import AIService
    from app.ml.posture_v1.loader import PostureV1TorchLoader
    from app.ml.posture_v1.preprocess import preprocess_pose_data
    from app.ml.posture_v1.features_151d import compute_151d_features, get_feature_names

    settings = get_settings()
    ai = AIService(app_settings=settings)
    print(f"AIService complexity={ai._pose_complexity_used} fallback={ai._pose_complexity_fallback}")

    # ---- Stage 1: decode + pose ------------------------------------------
    cap = cv2.VideoCapture(str(VIDEO))
    fps = cap.get(cv2.CAP_PROP_FPS)
    pose_data, valid, read = [], 0, 0
    while cap.isOpened() and read < 300:
        ok, frame = cap.read()
        if not ok:
            break
        lm, _conf = ai.detect_pose(frame)
        pose_data.append(lm if lm else None)
        valid += 1 if lm else 0
        read += 1
    cap.release()
    print(f"decode: fps={fps:.2f} frames_read={read} valid_detections={valid} "
          f"(eval CSV recorded frames={EVAL_FRAMES}, orig_frames=90)")

    # ---- Stage 2: preprocess ---------------------------------------------
    pre = preprocess_pose_data(pose_data)
    print(f"preprocess: sequence_length={pre.sequence_length} "
          f"keypoints={pre.keypoints.shape} flags={pre.quality_flags}")

    loader = PostureV1TorchLoader(settings)
    loader._ensure_loaded()
    mean, std = (np.asarray(a, dtype=np.float64) for a in loader.get_scaler_params())
    names = get_feature_names()

    def run(seq_len):
        raw = compute_151d_features(
            pre.keypoints, apply_scaler=False, sequence_length=seq_len
        ).astype(np.float64)
        scaled = ((raw - mean) / std).astype(np.float32)
        prob = float(loader._run_inference(pre.keypoints, scaled, seq_len))
        return prob, raw

    # ---- Stage 3: does sequence_length alone explain it? -----------------
    print(f"\nsequence_length sweep (threshold={loader._fault_threshold}):")
    probs = {}
    for sl in [60, 66, 80, 85, 88, 89, 90, 100, 120, 150, 200, 300]:
        if sl > pre.keypoints.shape[0]:
            continue
        p, _ = run(sl)
        probs[sl] = p
        mark = ""
        if sl == EVAL_FRAMES:
            mark = f"   <- eval CSV frame count (eval prob was {EVAL_PROB})"
        if sl == pre.sequence_length:
            mark += "   <- what serving used"
        print(f"  seq_len={sl:3d}  prob_fault={p:.6f}{mark}")

    lo, hi = min(probs.values()), max(probs.values())
    print(f"\nrange across all sequence_lengths: [{lo:.6f}, {hi:.6f}]")
    print(f"eval CSV value {EVAL_PROB} is {'INSIDE' if lo <= EVAL_PROB <= hi else 'OUTSIDE'} that range")
    if not (lo <= EVAL_PROB <= hi):
        print("  => sequence_length alone CANNOT explain the difference.")

    # ---- Stage 4: feature diff, 89 vs 90 ---------------------------------
    p89, r89 = run(89)
    p90, r90 = run(90)
    print(f"\n89 vs 90 frames: prob {p89:.6f} vs {p90:.6f}  (delta {p90-p89:+.6f})")
    d = np.abs(r90 - r89)
    denom = np.maximum(np.abs(r89), 1e-9)
    rel = d / denom
    order = np.argsort(-d)[:15]
    print("\ntop 15 features by absolute change (89 -> 90):")
    print(f"  {'idx':>4} {'feature':44s} {'v@89':>12} {'v@90':>12} {'abs':>10} {'rel':>8}")
    for i in order:
        print(f"  {i:4d} {names[i]:44s} {r89[i]:12.4f} {r90[i]:12.4f} {d[i]:10.4f} {rel[i]:7.2%}")
    changed = int((d > 1e-9).sum())
    print(f"\nfeatures changed: {changed}/151   "
          f"static[0:87]={int((d[:87] > 1e-9).sum())}  temporal[87:151]={int((d[87:] > 1e-9).sum())}")

    print("\n===JSON===")
    print(json.dumps({
        "video": VIDEO.name,
        "complexity": ai._pose_complexity_used,
        "fallback": ai._pose_complexity_fallback,
        "fps": fps, "frames_read": read, "valid_detections": valid,
        "preprocess_sequence_length": pre.sequence_length,
        "quality_flags": list(pre.quality_flags),
        "eval_csv": {"prob_fault": EVAL_PROB, "frames": EVAL_FRAMES, "orig_frames": 90},
        "serving_reference_prob": SERVING_PROB,
        "seq_len_sweep": probs,
        "prob_range": [lo, hi],
        "eval_explained_by_seq_len": bool(lo <= EVAL_PROB <= hi),
        "features_changed_89_vs_90": changed,
    }))


if __name__ == "__main__":
    main()
