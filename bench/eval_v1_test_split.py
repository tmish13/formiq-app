#!/usr/bin/env python3
"""
v1 on the recovered held-out TEST split, with a bootstrap CI and a trivial floor.

Replaces the n=50 ablation baseline (F1 0.769), which used hand-picked balanced
fixtures and is NOT comparable to the manifest's 0.724 (244 videos at natural
prevalence, different F1 floor, +/-0.07 noise at n=50).

Coverage caveat, reported prominently: only 224 of the 244 test videos have
keypoints available. The missing 20 are exactly the Penn Action clips in the
split; the 224 present are all Fitness-AQA. So this is a
"224/244, Fitness-AQA only" number, never "the test F1".

Bench only.
    docker compose -f backend/deployment/docker-compose.yml exec -T app \
        python - < bench/eval_v1_test_split.py
"""
import json
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "/app")

SPLITS = Path("/splits/user_level_multilabel_splits.json")
KP_DIR = Path("/keypoints")
POSTURE_IDX = 1  # class_names = [good_form, posture_fault, depth_fault]


def prf(tp, fp, fn):
    p = tp / (tp + fp) if (tp + fp) else 0.0
    r = tp / (tp + fn) if (tp + fn) else 0.0
    f = 2 * p * r / (p + r) if (p + r) else 0.0
    return p, r, f


def counts(y, pred):
    tp = int(((pred == 1) & (y == 1)).sum()); fp = int(((pred == 1) & (y == 0)).sum())
    tn = int(((pred == 0) & (y == 0)).sum()); fn = int(((pred == 0) & (y == 1)).sum())
    return tp, fp, tn, fn


def bootstrap_f1(y, prob, thr, n=2000, seed=0):
    rng = np.random.default_rng(seed)
    N = len(y); out = []
    for _ in range(n):
        idx = rng.integers(0, N, N)
        yy, pp = y[idx], (prob[idx] >= thr).astype(int)
        tp, fp, tn, fn = counts(yy, pp)
        out.append(prf(tp, fp, fn)[2])
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


def main():
    from app.core.config import get_settings
    from app.ml.posture_v1.loader import PostureV1TorchLoader
    from app.ml.posture_v1.preprocess import preprocess_pose_data
    from app.ml.posture_v1.features_151d import compute_151d_features

    d = json.loads(SPLITS.read_text())
    test = d["splits"]["test"]
    names, targets = test["video_names"], test["multilabel_targets"]

    settings = get_settings()
    loader = PostureV1TorchLoader(settings); loader._ensure_loaded()
    thr = loader._fault_threshold
    mean, std = (np.asarray(a, dtype=np.float64) for a in loader.get_scaler_params())

    ys, probs, used, missing = [], [], [], []
    for vn, tgt in zip(names, targets):
        f = KP_DIR / f"{vn}_keypoints.json"
        if not f.exists():
            missing.append((vn, int(tgt[POSTURE_IDX]))); continue
        frames = json.loads(f.read_text())
        pose = [fr.get("landmarks") for fr in frames]
        pre = preprocess_pose_data(pose)
        if pre.sequence_length == 0:
            missing.append((vn, int(tgt[POSTURE_IDX]))); continue
        raw = compute_151d_features(pre.keypoints, apply_scaler=False,
                                    sequence_length=pre.sequence_length).astype(np.float64)
        scaled = ((raw - mean) / std).astype(np.float32)
        probs.append(float(loader._run_inference(pre.keypoints, scaled, pre.sequence_length)))
        ys.append(int(tgt[POSTURE_IDX])); used.append(vn)

    y = np.array(ys); prob = np.array(probs)
    pred = (prob >= thr).astype(int)
    tp, fp, tn, fn = counts(y, pred)
    p, r, f1 = prf(tp, fp, fn)
    lo, hi = bootstrap_f1(y, prob, thr)

    prev = float(y.mean())
    tp0, fp0, _, fn0 = counts(y, np.ones_like(y))
    _, _, f1_all = prf(tp0, fp0, fn0)

    try:
        from sklearn.metrics import roc_auc_score
        auroc = float(roc_auc_score(y, prob))
    except Exception:
        auroc = float("nan")

    print(f"evaluated {len(y)}/244 test videos   (missing {len(missing)})")
    print(f"prevalence (posture_fault): {y.sum()}/{len(y)} = {prev:.3f}")
    print(f"threshold: {thr}")
    print()
    print(f"  F1        {f1:.4f}   95% CI [{lo:.4f}, {hi:.4f}]  (bootstrap, 2000x)")
    print(f"  precision {p:.4f}")
    print(f"  recall    {r:.4f}")
    print(f"  accuracy  {(tp+tn)/len(y):.4f}")
    print(f"  AUROC     {auroc:.4f}")
    print(f"  TP={tp} FP={fp} TN={tn} FN={fn}")
    print()
    print(f"  trivial floor (always-predict-fault): F1 {f1_all:.4f}")
    print(f"  manifest recorded test F1 (244, all)  : 0.7237")
    print()
    mis_pos = sum(1 for _, l in missing if l == 1)
    print(f"missing {len(missing)}: posture_fault={mis_pos}, not_fault={len(missing)-mis_pos}")
    print(f"  ids: {[m[0] for m in missing][:25]}")

    print("\n===JSON===")
    print(json.dumps({
        "n_evaluated": len(y), "n_total": 244, "n_missing": len(missing),
        "missing_ids": [m[0] for m in missing],
        "missing_label_mix": {"posture_fault": mis_pos, "not_fault": len(missing) - mis_pos},
        "prevalence": prev, "threshold": thr,
        "f1": f1, "f1_ci95": [lo, hi], "precision": p, "recall": r,
        "accuracy": (tp + tn) / len(y), "auroc": auroc,
        "TP": tp, "FP": fp, "TN": tn, "FN": fn,
        "trivial_floor_f1": f1_all,
        "manifest_test_f1": 0.7237,
        "per_video": [
            {"video": v, "y": int(yy), "prob_fault": round(float(pp), 6)}
            for v, yy, pp in zip(used, y, prob)
        ],
    }))


if __name__ == "__main__":
    main()
