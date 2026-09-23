#!/usr/bin/env python3
"""Does this corpus contain a depth contrast at all -- and if not, what separates the classes?

Two questions, one run:

  1. Knee-flexion distribution by class. If good_form / depth_fault / posture_fault
     overlap, there is no depth contrast in the corpus and no rule can find one.
  2. If some OTHER axis separates them, the label means something other than its
     name, and that something is worth knowing before picking the next target.

Separability is reported as AUROC between good_form and depth_fault on each axis.
0.5 is indistinguishable; anything far from 0.5 in either direction is signal
(below 0.5 means the axis runs backwards relative to the label's name).

TEST IS NOT OPENED. The knee-valgus work uses the same split structure, so
looking at test for a depth question would contaminate the next target too.
Train + validation only.

    python bench/corpus_axes.py
"""
from __future__ import annotations

import gzip
import json
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "backend"))

import numpy as np

KP_DIR = REPO / "bench" / "cache" / "keypoints_live"
SPLITS = (
    Path.home() / "FORMIQ Form Analysis Model" / "data" / "squat_processed"
    / "user_level_multilabel_splits.json"
)
OUT = REPO / "bench" / "results" / "corpus_axes.json"

CLASSES = ("good_form", "depth_fault", "posture_fault")


def main():
    from app.eval.metrics import auroc
    from app.rules import load_params
    from app.rules.kinematics import (
        SIDES, X, Y, scale_reference, side_knee_angle, side_hip_angle,
        side_hip_knee_delta, to_array, usable_sides,
    )
    from app.rules.segmentation import find_bottom

    p = load_params()
    sp = json.loads(SPLITS.read_text())

    meta = {}
    for split in ("train", "validation"):          # test deliberately excluded
        for r in sp["splits"][split]["video_data"]:
            cls = (r.get("enhanced_labels", {}).get("video_level", {}) or {}).get(
                "class_label")
            if cls in CLASSES:
                meta[r["video_name"]] = (split, cls)

    axes = defaultdict(lambda: defaultdict(list))
    n_used = 0
    for name, (split, cls) in sorted(meta.items()):
        f = KP_DIR / f"{name}.json.gz"
        if not f.exists():
            continue
        with gzip.open(f, "rt") as fh:
            d = json.load(fh)
        kp = to_array(d["frames"])
        S = scale_reference(kp, p["min_visibility"], p["standing_quantile"],
                            p["min_usable_frames_for_scale"], p["min_standing_frames"])
        if not S:
            continue
        w = find_bottom(kp, float(d.get("source_fps") or 0.0), p["min_visibility"],
                        p["smooth_seconds"], p["baseline_quantile"],
                        p["bottom_band_frac"], p["max_window_seconds"],
                        p["min_window_frames"], p["fallback_fps"],
                        scale_ref=S, min_descent_ratio=p["min_descent_ratio"])
        if not w:
            continue
        n_used += 1

        knees, hips, deltas, valgus, trunk = [], [], [], [], []
        for t in range(w.start, w.end + 1):
            for s in usable_sides(kp[t], p["min_visibility"]):
                a = side_knee_angle(kp[t], s)
                if a is not None:
                    knees.append(a)
                a = side_hip_angle(kp[t], s)
                if a is not None:
                    hips.append(a)
                v = side_hip_knee_delta(kp[t], s, S)
                if v is not None:
                    deltas.append(v)
                # knee travel inside/outside the ankle, torso-normalised
                idx = SIDES[s]
                kn, an = kp[t][idx["knee"]], kp[t][idx["ankle"]]
                if np.isfinite(kn[X]) and np.isfinite(an[X]):
                    valgus.append(abs(kn[X] - an[X]) / S)
            # trunk lean: hip->shoulder vector away from vertical
            sides = usable_sides(kp[t], p["min_visibility"])
            if sides:
                hx = np.mean([kp[t][SIDES[s]["hip"]][X] for s in sides])
                hy = np.mean([kp[t][SIDES[s]["hip"]][Y] for s in sides])
                sx = np.mean([kp[t][SIDES[s]["shoulder"]][X] for s in sides])
                sy = np.mean([kp[t][SIDES[s]["shoulder"]][Y] for s in sides])
                dx, dy = sx - hx, sy - hy
                if abs(dy) > 1e-9:
                    trunk.append(abs(np.degrees(np.arctan2(dx, -dy))))

        if knees:
            axes["knee_flexion_min"][cls].append(min(knees))
            axes["knee_flexion_median"][cls].append(st.median(knees))
        if hips:
            axes["hip_flexion_min"][cls].append(min(hips))
        if deltas:
            axes["hip_knee_delta_max"][cls].append(max(deltas))
        if valgus:
            axes["knee_ankle_x_max"][cls].append(max(valgus))
        if trunk:
            axes["trunk_lean_max_deg"][cls].append(max(trunk))
        axes["hip_drop_ratio"][cls].append(
            (w.hip_y_at_bottom - w.baseline_hip_y) / S)
        axes["clip_frames"][cls].append(float(kp.shape[0]))
        axes["bottom_window_frames"][cls].append(float(w.n_frames))
        axes["scale_ref"][cls].append(S)

    print(f"train + validation, {n_used} clips with a usable bottom "
          f"(TEST NOT OPENED)")
    print()

    # ---- 1. knee flexion: is there a depth contrast at all? ----------------
    print("=" * 78)
    print("1. KNEE FLEXION AT THE BOTTOM -- is there a depth contrast?")
    print("=" * 78)
    print(f"  {'class':14s} {'n':>4s} {'p10':>7s} {'p25':>7s} {'median':>7s} "
          f"{'p75':>7s} {'p90':>7s}")
    for cls in CLASSES:
        v = sorted(axes["knee_flexion_min"][cls])
        if not v:
            continue
        q = lambda f: v[min(len(v) - 1, int(len(v) * f))]
        print(f"  {cls:14s} {len(v):4d} {q(.10):7.1f} {q(.25):7.1f} "
              f"{st.median(v):7.1f} {q(.75):7.1f} {q(.90):7.1f}")
    print()
    print("  parallel is ~90-100 deg; 180 is a straight leg; rock bottom ~40-60")

    # ---- 2. what DOES separate the classes? --------------------------------
    print()
    print("=" * 78)
    print("2. SEPARABILITY, good_form vs depth_fault, per axis")
    print("=" * 78)
    print("  AUROC 0.5 = indistinguishable. <0.5 means the axis runs BACKWARDS")
    print("  relative to what the label's name implies.")
    print()
    results = {}
    rows = []
    for axis in sorted(axes):
        g = axes[axis]["good_form"]
        f_ = axes[axis]["depth_fault"]
        if len(g) < 20 or len(f_) < 20:
            continue
        y = [0] * len(g) + [1] * len(f_)
        s = list(g) + list(f_)
        a = auroc(y, s)
        rows.append((abs(a - 0.5), axis, a, st.median(g), st.median(f_), len(g), len(f_)))
        results[axis] = {"auroc_depthfault_vs_goodform": a,
                         "median_good_form": st.median(g),
                         "median_depth_fault": st.median(f_),
                         "n_good_form": len(g), "n_depth_fault": len(f_)}
    rows.sort(reverse=True)
    print(f"  {'axis':24s} {'AUROC':>7s} {'|dev|':>6s} {'good_form':>10s} "
          f"{'depth_fault':>12s}")
    for dev, axis, a, mg, mf, ng, nf in rows:
        flag = "  <- separates" if dev >= 0.10 else ""
        print(f"  {axis:24s} {a:7.3f} {dev:6.3f} {mg:10.3f} {mf:12.3f}{flag}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(
        {"n_clips": n_used, "splits": ["train", "validation"],
         "test_opened": False, "axes": results,
         "knee_flexion_by_class": {
             c: sorted(axes["knee_flexion_min"][c]) for c in CLASSES}},
        indent=2))
    print()
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
