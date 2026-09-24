"""Build the PostureV1 training arrays from the SERVING pose pass (Track B5, dataset side).

Same inputs and cleaning as bench/retrain/build_dataset.py, plus the keypoint sequences the CNN-LSTM
needs:

  --splits     bench/results/content_level_splits.json  (content-level, dedup map applied first)
  --ml-splits  backend/ml_training/data/user_level_multilabel_splits.json  (raw + collapsed labels)
  --cache      bench/cache/keypoints_live  (<video>.json.gz written by bench/extract_keypoints.py;
               _manifest.json carries the pose_pass_id)
  --target     posture_collapsed (the incumbent's own task: collapsed class == posture_fault)
               or posture_fault (the raw multi-label bit)

Writes <out>/{train,validation,test}.npz with K [N,300,33,3] float32 (preprocess_pose_data output,
zero-padded), X [N,151] float64 (compute_151d_features, UNSCALED -- the trainer fits the scaler on
train only), y [N] int8, L [N] int32 sequence lengths, names and hashes; and <out>/manifest.json.
The test split is written so that a --final read is possible; train.py refuses to open it otherwise.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

for p in ("/app", str(Path(__file__).resolve().parents[2])):
    if p not in sys.path:
        sys.path.insert(0, p)

TARGETS = ("posture_collapsed", "posture_fault")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--splits", type=Path, required=True)
    ap.add_argument("--ml-splits", type=Path, required=True)
    ap.add_argument("--cache", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--target", choices=TARGETS, default="posture_collapsed")
    ap.add_argument("--limit", type=int, default=None, help="first N assigned videos (smoke runs)")
    args = ap.parse_args()

    from app.ml.posture_v1.features_151d import compute_151d_features
    from app.ml.posture_v1.preprocess import preprocess_pose_data

    cl = json.loads(args.splits.read_text())
    assigned = {r["video"]: r for r in cl["videos"] if r["split"]}
    ml = json.loads(args.ml_splits.read_text())
    raw, collapsed = {}, {}
    for s in ("train", "validation", "test"):
        for vd in ml["splits"][s]["video_data"]:
            raw[vd["video_name"]] = (vd.get("enhanced_labels") or {}).get("original_multi_label") or {}
            collapsed[vd["video_name"]] = ((vd.get("enhanced_labels") or {}).get("video_level") or {}).get("class_label")
    cache_manifest = json.loads((args.cache / "_manifest.json").read_text())
    pose_pass_id = cache_manifest.get("extraction_contract", {}).get("pose_pass_id")

    rows = {s: [] for s in ("train", "validation", "test")}
    skipped: Counter = Counter()
    names = sorted(assigned)
    if args.limit:
        names = names[: args.limit]
    for name in names:
        r = assigned[name]
        f = args.cache / f"{name}.json.gz"
        if not f.exists():
            skipped["no_cached_keypoints"] += 1; continue
        if name not in raw:
            skipped["no_raw_labels"] += 1; continue
        with gzip.open(f, "rt") as fh:
            d = json.load(fh)
        try:
            pre = preprocess_pose_data(d["frames"])
        except Exception as e:  # noqa: BLE001 -- recorded, not hidden
            skipped[f"preprocess_error:{type(e).__name__}"] += 1; continue
        if pre.sequence_length < 10:
            skipped["too_short"] += 1; continue
        try:
            x = compute_151d_features(pre.keypoints, apply_scaler=False,
                                      sequence_length=pre.sequence_length).astype(np.float64)
        except Exception as e:  # noqa: BLE001
            skipped[f"feature_error:{type(e).__name__}"] += 1; continue
        if args.target == "posture_collapsed":
            y = int(collapsed.get(name) == "posture_fault")
        else:
            y = int(bool(raw[name].get("posture_fault")))
        rows[r["split"]].append({"video": name, "hash": r["content_hash"], "y": y,
                                 "K": pre.keypoints.astype(np.float32), "X": x,
                                 "L": int(pre.sequence_length)})

    args.out.mkdir(parents=True, exist_ok=True)
    manifest = {"target": args.target, "pose_pass_id": pose_pass_id, "cache": str(args.cache),
                "splits_file": str(args.splits), "splits_sha256": sha256_file(args.splits),
                "ml_splits_file": str(args.ml_splits), "ml_splits_sha256": sha256_file(args.ml_splits),
                "cleaning": "preprocess_pose_data (first 300, zero-pad); features unscaled",
                "feature_spec": "features_151d truth_spec_151d_v1", "skipped": dict(skipped),
                "n": {}, "prevalence": {}}
    for s, rs in rows.items():
        if not rs:
            manifest["n"][s] = 0; continue
        np.savez_compressed(args.out / f"{s}.npz",
                            K=np.stack([r["K"] for r in rs]), X=np.stack([r["X"] for r in rs]),
                            y=np.asarray([r["y"] for r in rs], np.int8),
                            L=np.asarray([r["L"] for r in rs], np.int32),
                            names=np.asarray([r["video"] for r in rs]), hashes=np.asarray([r["hash"] for r in rs]))
        manifest["n"][s] = len(rs)
        manifest["prevalence"][s] = round(float(np.mean([r["y"] for r in rs])), 4)
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps({k: manifest[k] for k in ("target", "pose_pass_id", "n", "prevalence", "skipped")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
