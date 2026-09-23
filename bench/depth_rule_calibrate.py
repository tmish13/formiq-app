#!/usr/bin/env python3
"""Calibrate the depth rule's MEASUREMENT. Never its criterion.

    AT_DEPTH  <=>  (hip_y - knee_y)/S + offset(view) >= 0

A NECESSARY ADMISSION, UP FRONT
-------------------------------
Fitting `offset` is algebraically identical to fitting a threshold:
`score + offset >= 0` is the same rule as `score >= -offset`. Calling it a
measurement correction does not, by itself, make it one.

So the distinction is not mechanism -- it is MAGNITUDE, and it has to be reported
rather than asserted:

  * The class separation between good_form bottoms and depth_fault bottoms is
    roughly 0.32 torso-lengths (measured in the Stage 0 probe).
  * An offset that is a few percent of that is plausibly what it claims to be:
    MediaPipe's landmark 23/24 is not the anatomical hip crease, 25/26 is not the
    top of the knee, and the camera foreshortens the femur off-axis.
  * An offset approaching that separation is NOT a correction. It is a fitted
    threshold wearing a correction's name, and the honest conclusion would be
    that the definitional criterion does not match this annotator -- which is a
    finding, not a failure.

This script therefore reports the ZERO-PARAMETER definitional result FIRST, and
the fitted offset second with its magnitude stated as a fraction of the class
separation. Whoever reads it can decide which story the number supports.

Usage:
    python bench/depth_rule_calibrate.py --split train
    python bench/depth_rule_calibrate.py --split train --smoke   # partial data ok
"""
from __future__ import annotations

import argparse
import gzip
import json
import statistics as st
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "backend"))

KP_DIR = REPO / "bench" / "cache" / "keypoints_live"
SPLITS = (
    Path.home() / "FORMIQ Form Analysis Model" / "data" / "squat_processed"
    / "user_level_multilabel_splits.json"
)
OUT = REPO / "bench" / "results" / "depth_rule_calibration.json"

# The two classes the definitional criterion is judged on. posture_fault videos
# are depth-negatives under the disjoint-label scheme but were classified by
# their PRIMARY fault, so some are certainly also shallow -- reported separately
# as a noisy negative, never folded into the clean contrast.
POSITIVE_CLASS = "depth_fault"      # bottoms that were too shallow
NEGATIVE_CLASS = "good_form"        # bottoms that were deep enough
NOISY_NEGATIVE = "posture_fault"


def load_split_map() -> Dict[str, Tuple[str, str]]:
    sp = json.loads(SPLITS.read_text())
    out: Dict[str, Tuple[str, str]] = {}
    for split in ("train", "validation", "test"):
        for r in sp["splits"][split]["video_data"]:
            cls = (r.get("enhanced_labels", {}).get("video_level", {}) or {}).get(
                "class_label")
            if cls:
                out[r["video_name"]] = (split, cls)
    return out


def load_keypoints(name: str) -> Optional[Tuple[list, float]]:
    p = KP_DIR / f"{name}.json.gz"
    if not p.exists():
        return None
    with gzip.open(p, "rt") as fh:
        d = json.load(fh)
    return d["frames"], float(d.get("source_fps") or 0.0)


def evaluate_split(split: str, params: dict, split_map: Dict[str, Tuple[str, str]]):
    """Run the rule over every extracted video in `split`."""
    from app.rules import evaluate_depth

    rows = []
    for name, (sp, cls) in sorted(split_map.items()):
        if sp != split:
            continue
        kp = load_keypoints(name)
        if kp is None:
            continue
        frames, fps = kp
        v = evaluate_depth(frames, fps, params)
        rows.append({
            "video": name, "class": cls, "verdict": v.verdict,
            "abstain_reason": v.abstain_reason, "score": v.score,
            "coverage": v.coverage, "view": (v.view or {}).get("kind"),
            "n_bottom": (v.bottom or {}).get("n_frames"),
        })
    return rows


def _prf(tp, fp, fn):
    p = tp / (tp + fp) if (tp + fp) else 0.0
    r = tp / (tp + fn) if (tp + fn) else 0.0
    f = 2 * p * r / (p + r) if (p + r) else 0.0
    return p, r, f


def score_at_offset(rows, offset: float, deadband: float) -> Dict:
    """Apply an offset to already-computed scores and re-derive the verdicts.

    The rule is a sign test, so shifting the score and re-thresholding at 0 is
    exactly what `offset_by_view` does inside `evaluate_depth` -- no need to
    re-run the whole pipeline per candidate.
    """
    tp = fp = fn = tn = 0
    abstained = 0
    considered = 0
    for r in rows:
        if r["class"] not in (POSITIVE_CLASS, NEGATIVE_CLASS):
            continue
        considered += 1
        if r["score"] is None:
            abstained += 1
            continue
        s = r["score"] + offset
        if abs(s) < deadband:
            abstained += 1
            continue
        called_shallow = s <= -deadband
        is_shallow = r["class"] == POSITIVE_CLASS
        if called_shallow and is_shallow:
            tp += 1
        elif called_shallow and not is_shallow:
            fp += 1
        elif not called_shallow and is_shallow:
            fn += 1
        else:
            tn += 1
    p, rec, f1 = _prf(tp, fp, fn)
    n_called = tp + fp + tn + fn
    # Precision on AT_DEPTH is the P_target class: of the bottoms we call deep
    # enough, how many were.
    p_at_depth = tn / (tn + fn) if (tn + fn) else 0.0
    return {
        "offset": offset, "deadband": deadband,
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "precision_shallow": p, "recall_shallow": rec, "f1_shallow": f1,
        "precision_at_depth": p_at_depth,
        "coverage": n_called / considered if considered else 0.0,
        "n_considered": considered, "n_called": n_called, "n_abstained": abstained,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="train")
    ap.add_argument("--smoke", action="store_true",
                    help="allow a partially-extracted cache")
    ap.add_argument("--deadband", type=float, default=None)
    args = ap.parse_args()

    # The test split is extracted but NOT opened. Extraction is not fitting, but
    # the separation holds mechanically rather than by good intentions.
    assert args.split != "test", (
        "refusing to calibrate on the test split -- use bench/depth_rule_eval.py "
        "--final for the one look you get")

    from app.rules import load_params
    params = load_params()
    deadband = args.deadband if args.deadband is not None else params["deadband"]

    # evaluate_depth() already folds params["offset_by_view"] into the score it
    # returns. Sweeping an offset on top of that would double-apply it and every
    # number below would be quietly wrong. Calibration must start from the raw
    # definitional measurement.
    nonzero = {k: v for k, v in params["offset_by_view"].items() if v != 0.0}
    assert not nonzero, (
        f"params already carry fitted offsets {nonzero}; calibrate from a "
        "zero-offset params file or the sweep double-counts them")

    split_map = load_split_map()
    rows = evaluate_split(args.split, params, split_map)
    if not rows:
        print("no extracted videos for this split yet")
        return

    n_expected = sum(1 for _, (sp, _c) in split_map.items() if sp == args.split)
    print(f"split={args.split}  evaluated {len(rows)} of {n_expected} "
          f"{'(SMOKE: partial cache)' if args.smoke else ''}")
    print()

    # ---- what the rule does at all, before any fitting -----------------------
    print("=" * 74)
    print("VERDICT DISTRIBUTION  (offset = 0, i.e. PURELY DEFINITIONAL)")
    print("=" * 74)
    by_class = defaultdict(Counter)
    for r in rows:
        by_class[r["class"]][r["verdict"]] += 1
    for cls in sorted(by_class):
        c = by_class[cls]
        n = sum(c.values())
        print(f"  {cls:14s} n={n:4d}  " +
              "  ".join(f"{k}={v}" for k, v in sorted(c.items())))
    print()
    reasons = Counter(r["abstain_reason"] for r in rows if r["abstain_reason"])
    if reasons:
        print("  abstain reasons:", dict(reasons))
    views = Counter(r["view"] for r in rows if r["view"])
    print("  views:", dict(views))
    print()

    # ---- score distributions by class ---------------------------------------
    print("=" * 74)
    print("SCORE = (hip_y - knee_y)/S at the bottom, by class")
    print("=" * 74)
    stats = {}
    for cls in (NEGATIVE_CLASS, POSITIVE_CLASS, NOISY_NEGATIVE):
        vals = [r["score"] for r in rows if r["class"] == cls and r["score"] is not None]
        if not vals:
            continue
        stats[cls] = {"n": len(vals), "mean": st.mean(vals),
                      "median": st.median(vals),
                      "sd": st.pstdev(vals) if len(vals) > 1 else 0.0}
        print(f"  {cls:14s} n={len(vals):4d}  mean={st.mean(vals):+.4f}  "
              f"median={st.median(vals):+.4f}  sd={stats[cls]['sd']:.4f}")
    sep = None
    if NEGATIVE_CLASS in stats and POSITIVE_CLASS in stats:
        sep = stats[POSITIVE_CLASS]["mean"] - stats[NEGATIVE_CLASS]["mean"]
        print()
        print(f"  class separation (shallow - deep): {sep:+.4f} torso-lengths")
        print( "  NOTE: shallow bottoms should have the SMALLER score (hip higher)")

    # ---- the zero-parameter result ------------------------------------------
    print()
    print("=" * 74)
    print("RESULT A -- DEFINITIONAL, ZERO FITTED PARAMETERS  (offset = 0)")
    print("=" * 74)
    base = score_at_offset(rows, 0.0, deadband)
    for k in ("tp", "fp", "tn", "fn"):
        print(f"  {k}={base[k]}", end="")
    print()
    print(f"  precision(SHALLOW)  {base['precision_shallow']:.4f}")
    print(f"  recall(SHALLOW)     {base['recall_shallow']:.4f}")
    print(f"  F1(SHALLOW)         {base['f1_shallow']:.4f}")
    print(f"  precision(AT_DEPTH) {base['precision_at_depth']:.4f}   <- P_target class")
    print(f"  coverage            {base['coverage']:.1%}  "
          f"({base['n_called']}/{base['n_considered']}, {base['n_abstained']} abstained)")

    # ---- the fitted offset, with its magnitude in context -------------------
    print()
    print("=" * 74)
    print("RESULT B -- FITTED OFFSET, and whether it is a correction or a threshold")
    print("=" * 74)
    grid = [round(-0.30 + i * 0.005, 4) for i in range(121)]
    sweep = [score_at_offset(rows, o, deadband) for o in grid]
    best = max(sweep, key=lambda d: d["f1_shallow"])
    print(f"  best offset by F1(SHALLOW): {best['offset']:+.4f}  "
          f"F1={best['f1_shallow']:.4f}  precision(AT_DEPTH)={best['precision_at_depth']:.4f}  "
          f"coverage={best['coverage']:.1%}")
    if sep:
        frac = abs(best["offset"]) / abs(sep)
        print()
        print(f"  |offset| / |class separation| = {frac:.1%}")
        if frac < 0.15:
            print("  => SMALL relative to the separation. Consistent with a genuine")
            print("     measurement correction (landmark placement, foreshortening).")
        else:
            print("  => LARGE relative to the separation. This is not a correction --")
            print("     it is a fitted threshold, and the definitional criterion does")
            print("     NOT match this annotator. Report it as that.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "split": args.split, "smoke": args.smoke, "n_evaluated": len(rows),
        "n_expected": n_expected, "deadband": deadband,
        "params_id": params["params_id"],
        "verdicts_by_class": {k: dict(v) for k, v in by_class.items()},
        "score_stats": stats, "class_separation": sep,
        "result_definitional": base, "result_fitted": best,
        "offset_sweep": sweep, "rows": rows,
    }, indent=2))
    print()
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
