#!/usr/bin/env python3
"""
Ablation: how much of PostureV1's signal comes from the face-landmark block?

Context
-------
PostureV1 consumes 151 features. Verified against the training source
(export_posture_v1.py::extract_rep_features_87d) and pinned by
backend/tests/unit/test_train_serve_parity.py:

    [0:33]    joint{0..10}_{x,y,z}_mean    MediaPipe 0-10 = nose, eyes, ears, mouth
    [33:66]   joint{0..10}_{x,y,z}_std     same face joints
    [66:87]   joint{0..6}_{x,y,z}_range    nose + both eyes
    [87:147]  4 angles x 15 stats          squat biomechanics
    [147:151] 4 derived                    squat biomechanics

MediaPipe body landmarks start at index 11, so features 0-86 (87 of 151, 57%)
are raw, unnormalised FACE coordinates and contain zero body joints.

Question: does that block carry signal, or is it camera-framing noise that
leaves the scaler's training distribution whenever the camera moves?

Method
------
Ablate by FREEZING a feature block at the scaler's training mean, so the value
after standardisation is exactly 0.0 -- the neutral point of the training
distribution. (Zeroing the RAW value would instead push it to -mean/scale, which
is far out of distribution and would measure the wrong thing.)

Arms:
  baseline        no ablation
  face_mean_std   freeze [0:66]    (the block the manifest previously misdescribed)
  face_all        freeze [0:87]    (the entire face block)
  temporal        freeze [87:151]  (CONTROL - the squat biomechanics)

If `face_all` barely moves F1 while `temporal` collapses it, the face block is
close to dead weight. If `face_all` collapses F1, the model genuinely depends on
face framing and is fragile to camera changes. Either result is informative.

This script is BENCH ONLY. It does not touch the serving path.

Run (inside the app container, which has torch + the artifacts):
    docker compose -f backend/deployment/docker-compose.yml exec -T app \
        python - < bench/ablate_face_block.py
"""
import gzip
import json
import sys
from pathlib import Path

import numpy as np

APP = Path("/app")
FIXTURES = APP / "tests" / "fixtures" / "pose_data" / "in_domain_accuracy"
POSITIVE_LABEL = "posture_fault"   # "fault" is the positive class

sys.path.insert(0, str(APP))

from app.core.config import get_settings                      # noqa: E402
from app.ml.posture_v1.loader import PostureV1TorchLoader      # noqa: E402
from app.ml.posture_v1.preprocess import preprocess_pose_data  # noqa: E402
from app.ml.posture_v1.features_151d import compute_151d_features  # noqa: E402

ARMS = {
    "baseline":      None,
    "face_mean_std": (0, 66),
    "face_all":      (0, 87),
    "temporal":      (87, 151),
    "all_features":  (0, 151),
}


def metrics(rows, arm):
    """rows: list of (label, prob_fault). Positive class = fault."""
    tp = fp = tn = fn = 0
    for label, prob in rows:
        pred_fault = prob >= THRESHOLD
        is_fault = label == POSITIVE_LABEL
        if pred_fault and is_fault:
            tp += 1
        elif pred_fault and not is_fault:
            fp += 1
        elif not pred_fault and is_fault:
            fn += 1
        else:
            tn += 1
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    acc = (tp + tn) / len(rows) if rows else 0.0
    probs = np.array([p for _, p in rows])
    return {
        "arm": arm, "n": len(rows),
        "TP": tp, "FP": fp, "TN": tn, "FN": fn,
        "precision": round(prec, 4), "recall": round(rec, 4),
        "f1": round(f1, 4), "accuracy": round(acc, 4),
        "prob_mean": round(float(probs.mean()), 4),
        "prob_std": round(float(probs.std()), 4),
    }


def main():
    global THRESHOLD
    settings = get_settings()
    loader = PostureV1TorchLoader(settings)
    loader._ensure_loaded()
    THRESHOLD = loader._fault_threshold
    scaler_mean, scaler_std = loader.get_scaler_params()
    scaler_mean = np.asarray(scaler_mean, dtype=np.float64)
    scaler_std = np.asarray(scaler_std, dtype=np.float64)

    manifest = json.loads((FIXTURES / "manifest.json").read_text())
    print(f"threshold={THRESHOLD}  fixtures={len(manifest)}  "
          f"positive_class={POSITIVE_LABEL!r}", flush=True)

    # --- Pass 1: preprocess + raw features once per fixture (expensive part) ---
    prepared = []
    for name, meta in sorted(manifest.items()):
        path = FIXTURES / f"{name}.json.gz"
        if not path.exists():
            print(f"  SKIP {name}: fixture file missing", flush=True)
            continue
        pose = json.loads(gzip.open(path, "rt").read())
        pre = preprocess_pose_data(pose)
        if pre.sequence_length == 0:
            print(f"  SKIP {name}: 0 valid frames", flush=True)
            continue
        raw = compute_151d_features(
            pre.keypoints, apply_scaler=False, sequence_length=pre.sequence_length,
        ).astype(np.float64)
        prepared.append((name, meta["label"], pre.keypoints, pre.sequence_length, raw))
    print(f"prepared {len(prepared)} fixtures\n", flush=True)

    # --- Pass 2: one forward pass per (arm, fixture) ---
    results, per_sample = {}, {}
    for arm, span in ARMS.items():
        rows = []
        detail = []
        for name, label, kp, seq_len, raw in prepared:
            feats = raw.copy()
            if span is not None:
                lo, hi = span
                # Freeze at the training mean -> exactly 0.0 after standardisation.
                feats[lo:hi] = scaler_mean[lo:hi]
            scaled = ((feats - scaler_mean) / scaler_std).astype(np.float32)
            prob = float(loader._run_inference(kp, scaled, seq_len))
            rows.append((label, prob))
            detail.append({"fixture": name, "label": label, "prob_fault": round(prob, 6)})
        results[arm] = metrics(rows, arm)
        per_sample[arm] = detail
        r = results[arm]
        print(f"{arm:14s} F1={r['f1']:.4f}  P={r['precision']:.4f}  R={r['recall']:.4f}  "
              f"acc={r['accuracy']:.4f}  TP={r['TP']} FP={r['FP']} TN={r['TN']} FN={r['FN']}  "
              f"prob_mean={r['prob_mean']:.4f}", flush=True)

    base = results["baseline"]
    print("\ndelta vs baseline (F1):")
    for arm, r in results.items():
        if arm == "baseline":
            continue
        print(f"  {arm:14s} {r['f1'] - base['f1']:+.4f}")

    out = {
        "threshold": THRESHOLD,
        "n_fixtures": len(prepared),
        "positive_class": POSITIVE_LABEL,
        "ablation_method": "freeze block at scaler training mean (== 0.0 after standardisation)",
        "blocks": {k: v for k, v in ARMS.items()},
        "results": results,
        "per_sample": per_sample,
    }
    print("\n===JSON===")
    print(json.dumps(out))


if __name__ == "__main__":
    main()
