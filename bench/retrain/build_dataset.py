#!/usr/bin/env python3
"""Build the controlled-retrain dataset: one cleaning path, three feature arms, four heads.

WHAT IS FIXED, AND WHY
----------------------
  splits    content_level_splits.json (leakage-free by hash AND user; conflicts and
            Penn withheld by construction -- Penn mp4s live outside the corpus dir).
  keypoints bench/cache/keypoints_live -- the SERVING pose pass, pp1_f9850424580ae186,
            recorded in the manifest. Not the unrecorded training pass (ML_AUDIT §3.1).
  cleaning  app.ml.posture_v1.preprocess.preprocess_pose_data -- trim, interpolate,
            drop visibility -- then the zero-pad tail is REMOVED so tempo features see
            real frames only. One path for all arms so the arms differ in features alone.
  targets   enhanced_labels.original_multi_label, the pre-collapse flags (ML_AUDIT §2.4):
            posture, stability, depth as independent heads, plus any_fault = OR.

THE THREE ARMS
--------------
  A  v2 body-only, camera-invariant (app/ml/posture_v2/features.py; spec_hash recorded)
  B  the incumbent's 64-D temporal-angle block alone (151-D slots 87..150)
  C  the incumbent's full 151-D (87 face + 64 temporal), unscaled
Same videos, same targets, same cleaning; the face block's contribution is C - B and the
v2 design's is A - B. Scalers are fitted per arm on TRAIN only, inside training.

Test features are built here so that the final evaluation is a single read; no test
label is examined by this script beyond the counts needed for the trivial floor.
"""
from __future__ import annotations
import argparse, gzip, json, sys, hashlib
from pathlib import Path
from collections import Counter
import numpy as np

# In-container the service repo is mounted at /app; on the host it is <repo>/backend.
for p in ("/app", str(Path.home() / "formiq-app-3" / "backend")):
    if p not in sys.path: sys.path.insert(0, p)

HEADS = ("posture_fault", "stability_fault", "depth_fault", "any_fault", "posture_collapsed")
ARMS = ("A_v2_body", "B_temporal64", "C_incumbent151")

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--splits", type=Path, required=True)          # content_level_splits.json
    ap.add_argument("--ml-splits", type=Path, required=True)       # user_level_multilabel_splits.json (for original_multi_label)
    ap.add_argument("--cache", type=Path, required=True)           # keypoints_live dir
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--reports", type=Path, default=None, help="also copy the manifest here (committed)")
    args = ap.parse_args()

    from app.ml.posture_v1.preprocess import preprocess_pose_data
    from app.ml.posture_v1.features_151d import compute_151d_features
    from app.ml.posture_v2.features import compute_features as v2_features, spec_hash as v2_spec_hash, get_feature_names as v2_names

    cl = json.loads(args.splits.read_text())
    assigned = {r["video"]: r for r in cl["videos"] if r["split"]}
    ml = json.loads(args.ml_splits.read_text())
    raw = {}; collapsed = {}
    for s in ("train", "validation", "test"):
        for vd in ml["splits"][s]["video_data"]:
            raw[vd["video_name"]] = (vd.get("enhanced_labels") or {}).get("original_multi_label") or {}
            collapsed[vd["video_name"]] = ((vd.get("enhanced_labels") or {}).get("video_level") or {}).get("class_label")
    cache_manifest = json.loads((args.cache / "_manifest.json").read_text())
    pose_pass_id = cache_manifest.get("extraction_contract", {}).get("pose_pass_id")

    rows = {s: [] for s in ("train", "validation", "test")}
    skipped = Counter()
    for name, r in sorted(assigned.items()):
        f = args.cache / f"{name}.json.gz"
        if not f.exists(): skipped["no_cached_keypoints"] += 1; continue
        if name not in raw: skipped["no_raw_labels"] += 1; continue
        with gzip.open(f, "rt") as fh: d = json.load(fh)
        fps = float(d.get("source_fps") or 0.0) or 30.0
        try:
            pre = preprocess_pose_data(d["frames"])
        except Exception as e:
            skipped[f"preprocess_error:{type(e).__name__}"] += 1; continue
        if pre.sequence_length < 10: skipped["too_short"] += 1; continue
        kp_clean = pre.keypoints[: pre.sequence_length]            # padding removed
        try:
            c151 = compute_151d_features(pre.keypoints, apply_scaler=False,
                                         sequence_length=pre.sequence_length).astype(np.float64)
            a_vals, a_names = v2_features(kp_clean, source_fps=fps)
        except Exception as e:
            skipped[f"feature_error:{type(e).__name__}"] += 1; continue
        lab = raw[name]
        y = [int(bool(lab.get("posture_fault"))), int(bool(lab.get("stability_fault"))),
             int(bool(lab.get("depth_fault")))]
        y.append(int(any(y)))
        # 5th column: the corpus's COLLAPSED single-class label -- the incumbent's own task
        # (PREREGISTRATION amendment 2). Same video, second label definition.
        y.append(int(collapsed.get(name) == "posture_fault"))
        rows[r["split"]].append({"video": name, "hash": r["content_hash"], "y": y,
                                 "A": np.asarray(a_vals, np.float64), "B": c151[87:151], "C": c151,
                                 "n_frames": int(pre.sequence_length), "fps": fps})

    args.out.mkdir(parents=True, exist_ok=True)
    manifest = {"pose_pass_id": pose_pass_id, "spec_hash_A": v2_spec_hash(),
                "feature_names_A": v2_names(), "feature_names_B": "features_151d slots 87..150",
                "feature_names_C": "features_151d slots 0..150", "heads": list(HEADS),
                "splits_file": str(args.splits), "cleaning": "preprocess_pose_data, pad removed",
                "skipped": dict(skipped), "n": {}, "prevalence": {}}
    for s, rs in rows.items():
        if not rs: continue
        Y = np.array([x["y"] for x in rs], dtype=np.int64)
        for arm in ARMS:
            key = arm[0]
            X = np.stack([x[key] for x in rs])
            np.savez_compressed(args.out / f"{arm}_{s}.npz", X=X, y=Y,
                                video=np.array([x["video"] for x in rs]), hash=np.array([x["hash"] for x in rs]),
                                n_frames=np.array([x["n_frames"] for x in rs]))
        manifest["n"][s] = len(rs)
        manifest["prevalence"][s] = {h: round(float(Y[:, i].mean()), 4) for i, h in enumerate(HEADS)}
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    if args.reports:
        args.reports.mkdir(parents=True, exist_ok=True)
        (args.reports / "dataset_manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"pose_pass_id {pose_pass_id}   spec_hash_A {v2_spec_hash()[:16]}   skipped {dict(skipped)}")
    for s in ("train", "validation", "test"):
        if s in manifest["n"]:
            print(f"  {s:11s} n={manifest['n'][s]:4d}  prevalence {manifest['prevalence'][s]}")
    dims = {arm: int(np.load(args.out / f"{arm}_train.npz")["X"].shape[1]) for arm in ARMS}
    print(f"  dims {dims}")
    print(f"wrote {args.out}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
