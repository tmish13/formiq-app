#!/usr/bin/env python3
"""Score the depth rule and PostureV1 on the SAME videos, one pose pass.

Two things this exists to prevent:

1.  Comparing the depth rule to a number from a different report computed on a
    different n with a different pose pass. PostureV1 is re-scored here, on the
    same live-extracted keypoints, so any delta is attributable.

2.  Quoting one label view. `depth_fault` and `posture_fault` are DISJOINT
    classes (every multilabel row sums to exactly 1), so the posture_fault videos
    are forced depth-negatives even though many are certainly shallow. Both views
    are always reported:
      (a) all classes        -- deployment reality, pessimistic
      (b) good_form vs depth_fault -- the clean depth contrast

The pinned dataset-keypoint numbers (F1 0.6131 / AUROC 0.7184 on n=224) are
printed alongside rather than replaced. The delta between those and PostureV1
re-scored here is the POSE-PASS contribution to the train/serve gap, which is
worth stating on its own.

Run in-container (PostureV1 needs torch):

    docker run --rm -m 6g --network deployment_default \
      -v $PWD/backend:/app -v $PWD:/repo \
      -v "$HOME/FORMIQ Form Analysis Model/data/squat_processed:/splits:ro" \
      -e POSTGRES_SERVER=db -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres \
      -e POSTGRES_DB=formiq -e SECRET_KEY=dev-only-insecure-secret-key-32chars-minimum \
      -e REDIS_HOST=redis -e REDIS_PORT=6379 -w /app deployment-worker:latest \
      python /repo/bench/depth_rule_eval.py --split validation
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, "/app")

KP_DIR = REPO / "bench" / "cache" / "keypoints_live"
if not KP_DIR.exists():
    KP_DIR = Path("/repo/bench/cache/keypoints_live")
SPLITS_CANDIDATES = [
    Path("/splits/user_level_multilabel_splits.json"),
    Path.home() / "FORMIQ Form Analysis Model" / "data" / "squat_processed"
    / "user_level_multilabel_splits.json",
]

POSITIVE_CLASS = "depth_fault"
NEGATIVE_CLASS = "good_form"
NOISY_NEGATIVE = "posture_fault"

# Frozen at bench/results/2026-09-19-v1-held-out-evaluation.md, on DATASET
# keypoints and n=224. Printed for contrast, never as this run's result.
PINNED_V1 = {"n": 224, "f1": 0.6131, "ci95": (0.5291, 0.6872), "auroc": 0.7184,
             "threshold": 0.525, "floor_f1": 0.5548, "prevalence": 0.3839}


def splits_path() -> Path:
    for p in SPLITS_CANDIDATES:
        if p.exists():
            return p
    raise SystemExit("splits file not found")


def load_split_map() -> Dict[str, Tuple[str, str, List[int]]]:
    sp = json.loads(splits_path().read_text())
    out = {}
    for split in ("train", "validation", "test"):
        s = sp["splits"][split]
        for r, tgt in zip(s["video_data"], s["multilabel_targets"]):
            cls = (r.get("enhanced_labels", {}).get("video_level", {}) or {}).get(
                "class_label")
            if cls:
                out[r["video_name"]] = (split, cls, list(tgt))
    return out


def load_keypoints(name: str):
    p = KP_DIR / f"{name}.json.gz"
    if not p.exists():
        return None
    with gzip.open(p, "rt") as fh:
        d = json.load(fh)
    return d["frames"], float(d.get("source_fps") or 0.0)


def score_posture_v1(frames) -> Optional[float]:
    """prob_fault from PostureV1 on the same keypoints. None when it cannot run."""
    from app.ml.posture_v1.loader import PostureV1TorchLoader
    global _LOADER
    try:
        _LOADER
    except NameError:
        from app.core.config import get_settings
        _LOADER = PostureV1TorchLoader(get_settings())
        _LOADER._ensure_loaded()
    try:
        return float(_LOADER.predict_posture(frames)["prob_fault"])
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="validation")
    ap.add_argument("--final", action="store_true",
                    help="required to touch the test split; you get one look")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    if args.split == "test" and not args.final:
        raise SystemExit(
            "refusing to open the test split without --final. Selection and "
            "tuning happen on train/validation; test is looked at once.")

    from app.eval.metrics import summarize
    from app.rules import load_params, evaluate_depth
    from app.rules.types import AT_DEPTH, SHALLOW, UNCERTAIN

    params = load_params()
    split_map = load_split_map()

    rows = []
    for name, (sp, cls, tgt) in sorted(split_map.items()):
        if sp != args.split:
            continue
        kp = load_keypoints(name)
        if kp is None:
            continue
        frames, fps = kp
        v = evaluate_depth(frames, fps, params)
        rows.append({
            "video": name, "class": cls,
            "y_depth": int(tgt[2]), "y_posture": int(tgt[1]),
            "rule_verdict": v.verdict, "rule_score": v.score,
            "rule_coverage": v.coverage, "view": (v.view or {}).get("kind"),
            "abstain_reason": v.abstain_reason,
            "pv1_prob": score_posture_v1(frames),
        })

    if not rows:
        raise SystemExit(f"no extracted videos for split={args.split}")

    print(f"split={args.split}  n={len(rows)}  params={params['params_id']} "
          f"fitted={params['fitted']}")
    print()

    # ---------------------------------------------------------------- depth --
    for view_name, keep in (
        ("(a) ALL CLASSES -- deployment reality", lambda r: True),
        ("(b) good_form vs depth_fault -- clean depth contrast",
         lambda r: r["class"] in (NEGATIVE_CLASS, POSITIVE_CLASS)),
    ):
        sub = [r for r in rows if keep(r)]
        if not sub:
            continue
        y = [r["y_depth"] for r in sub]
        dec = [1 if r["rule_verdict"] == SHALLOW
               else ("uncertain" if r["rule_verdict"] == UNCERTAIN else 0)
               for r in sub]
        res = summarize(y, decisions=dec, abstain_value="uncertain",
                        label=f"depth_rule {view_name}")
        cm = res["coverage_metrics"]
        print("=" * 74)
        print(f"DEPTH RULE  {view_name}   n={len(sub)}")
        print("=" * 74)
        print(f"  prevalence(shallow) {res['floor']['prevalence']:.3f}   "
              f"trivial floor F1 {res['floor']['all_positive_f1']:.4f}")
        print(f"  coverage            {cm['coverage']:.1%}  "
              f"({cm['n_covered']}/{cm['n']}, {cm['n_abstained']} abstained)")
        co = cm["covered_only"]
        if co["f1"] is not None:
            # P_target is precision on AT_DEPTH: of the bottoms called deep
            # enough, how many were. That is the NEGATIVE class here.
            c = co["counts"]
            p_at_depth = c["tn"] / (c["tn"] + c["fn"]) if (c["tn"] + c["fn"]) else 0.0
            print(f"  covered-only        P(shallow)={co['precision']:.4f} "
                  f"R={co['recall']:.4f} F1={co['f1']:.4f}")
            print(f"                      P(AT_DEPTH)={p_at_depth:.4f}   "
                  f"<- P_target 0.85 {'MET' if p_at_depth >= 0.85 else 'NOT MET'}")
        an = cm["abstain_as_negative"]
        print(f"  abstain-as-negative P={an['precision']:.4f} R={an['recall']:.4f} "
              f"F1={an['f1']:.4f}")
        print()

    print("  abstain reasons:", dict(Counter(
        r["abstain_reason"] for r in rows if r["abstain_reason"])))
    print("  views:", dict(Counter(r["view"] for r in rows if r["view"])))
    print()

    # ------------------------------------------------------------ PostureV1 --
    pv1 = [r for r in rows if r["pv1_prob"] is not None]
    if pv1:
        y = [r["y_posture"] for r in pv1]
        s = [r["pv1_prob"] for r in pv1]
        res = summarize(y, y_score=s, threshold=PINNED_V1["threshold"],
                        label="posture_v1 re-scored")
        print("=" * 74)
        print(f"POSTURE_V1 re-scored on THESE keypoints   n={len(pv1)}")
        print("=" * 74)
        print(f"  F1 {res['f1']:.4f}  CI95 [{res['f1_ci95'][0]:.4f}, "
              f"{res['f1_ci95'][1]:.4f}]  AUROC {res['auroc']:.4f}")
        print(f"  precision {res['precision']:.4f}  recall {res['recall']:.4f}  "
              f"floor {res['floor']['all_positive_f1']:.4f}")
        print()
        print("  PINNED (dataset keypoints, n=224, NOT replaced):")
        print(f"    F1 {PINNED_V1['f1']:.4f}  CI95 [{PINNED_V1['ci95'][0]:.4f}, "
              f"{PINNED_V1['ci95'][1]:.4f}]  AUROC {PINNED_V1['auroc']:.4f}")
        print()
        print(f"  delta F1    {res['f1'] - PINNED_V1['f1']:+.4f}")
        print(f"  delta AUROC {res['auroc'] - PINNED_V1['auroc']:+.4f}")
        print("  => the POSE-PASS contribution to the train/serve gap, on its own.")
        print("     (n differs: this split vs the pinned 224, so read as indicative")
        print("      unless split == test.)")

    out = Path(args.out) if args.out else (
        REPO / "bench" / "results" / f"depth_rule_eval_{args.split}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(
        {"split": args.split, "n": len(rows), "params_id": params["params_id"],
         "fitted": params["fitted"], "pinned_v1": PINNED_V1, "rows": rows},
        indent=2))
    print()
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
