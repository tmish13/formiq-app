#!/usr/bin/env python3
"""Does `find_bottom` land where the human looked?

This validates the MECHANISM, separately from the verdict, and it matters more
than it first appears. Under the corrected formulation the negative class -- the
bottoms of good_form clips -- does not exist until `find_bottom` produces it. If
segmentation is wrong, the rule is not merely measuring at a slightly wrong
frame; it is fitted against a negative class it invented.

Ground truth that nothing in the repo has used: `video_data[i]["enhanced_labels"]
["temporal_faults"]["depth_frames"]` is populated for all 469 depth_fault videos
as timestamps in seconds. They are frame indices / 30 exactly (verified:
1.2666... * 30 == 38.0), and they mark the instants a human judged the depth
fault -- which are the bottom of the rep.

Three measures, because they answer different questions:

  containment  what fraction of the marked frames fall inside the detected
               window. Low means we are measuring the wrong part of the rep.
  offset       |detected bottom - median marked frame|, in frames. The bias.
  IoU          overlap of [start, end] with [min(marked), max(marked)]. Whether
               the window is the right SIZE, not just in the right place.

Train split only -- the test split is extracted but not opened.

    python bench/validate_segmentation.py --split train
"""
from __future__ import annotations

import argparse
import gzip
import json
import statistics as st
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "backend"))

KP_DIR = REPO / "bench" / "cache" / "keypoints_live"
SPLITS = (
    Path.home() / "FORMIQ Form Analysis Model" / "data" / "squat_processed"
    / "user_level_multilabel_splits.json"
)
OUT = REPO / "bench" / "results" / "segmentation_validation.json"

DEPTH_FRAMES_FPS = 30.0   # depth_frames are frame_index / 30, verified exactly


def load_marked() -> Dict[str, Tuple[str, List[int]]]:
    sp = json.loads(SPLITS.read_text())
    out = {}
    for split in ("train", "validation", "test"):
        for r in sp["splits"][split]["video_data"]:
            tf = (r.get("enhanced_labels", {}).get("temporal_faults", {}) or {})
            times = tf.get("depth_frames") or []
            if times:
                out[r["video_name"]] = (
                    split, sorted({int(round(t * DEPTH_FRAMES_FPS)) for t in times}))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="train")
    args = ap.parse_args()
    assert args.split != "test", "the test split is extracted but not opened"

    from app.rules import load_params
    from app.rules.kinematics import scale_reference, to_array
    from app.rules.segmentation import find_bottom

    params = load_params()
    marked = load_marked()

    rows, skipped = [], Counter()
    for name, (split, frames_marked) in sorted(marked.items()):
        if split != args.split:
            continue
        p = KP_DIR / f"{name}.json.gz"
        if not p.exists():
            skipped["not_extracted"] += 1
            continue
        with gzip.open(p, "rt") as fh:
            d = json.load(fh)
        kp = to_array(d["frames"])
        S = scale_reference(
            kp, params["min_visibility"], params["standing_quantile"],
            params["min_usable_frames_for_scale"], params["min_standing_frames"])
        if S is None:
            skipped["bad_scale"] += 1
            continue
        w = find_bottom(
            kp, float(d.get("source_fps") or 0.0), params["min_visibility"],
            params["smooth_seconds"], params["baseline_quantile"],
            params["bottom_band_frac"], params["max_window_seconds"],
            params["min_window_frames"], params["fallback_fps"],
            scale_ref=S, min_descent_ratio=params["min_descent_ratio"],
        )
        if w is None:
            skipped["no_bottom"] += 1
            continue

        inside = [f for f in frames_marked if w.start <= f <= w.end]
        containment = len(inside) / len(frames_marked)
        offset = abs(w.index - int(st.median(frames_marked)))

        lo_m, hi_m = min(frames_marked), max(frames_marked)
        inter = max(0, min(w.end, hi_m) - max(w.start, lo_m) + 1)
        union = max(w.end, hi_m) - min(w.start, lo_m) + 1
        iou = inter / union if union else 0.0

        rows.append({"video": name, "n_marked": len(frames_marked),
                     "marked_span": [lo_m, hi_m], "window": [w.start, w.end],
                     "bottom": w.index, "containment": containment,
                     "offset_frames": offset, "iou": iou,
                     "n_frames": kp.shape[0]})

    if not rows:
        print(f"no extracted depth_fault videos in split={args.split} yet "
              f"(skipped: {dict(skipped)})")
        return

    print(f"split={args.split}  validated {len(rows)} depth_fault videos "
          f"(skipped: {dict(skipped)})")
    print()

    def dist(key, fmt="{:.3f}"):
        v = sorted(r[key] for r in rows)
        return (f"median={fmt.format(st.median(v))}  mean={fmt.format(st.mean(v))}  "
                f"p10={fmt.format(v[int(len(v) * 0.1)])}  "
                f"p90={fmt.format(v[int(len(v) * 0.9)])}")

    print("=" * 74)
    print("CONTAINMENT -- fraction of human-marked frames inside the window")
    print("=" * 74)
    print("  " + dist("containment"))
    for thr in (1.0, 0.5, 0.0):
        n = sum(1 for r in rows if r["containment"] > thr - 1e-9)
        label = "all marked frames" if thr == 1.0 else (
            "at least half" if thr == 0.5 else "at least one")
        print(f"  {label:20s} {n:4d}/{len(rows)}  ({n / len(rows):.1%})")

    print()
    print("=" * 74)
    print("OFFSET -- |detected bottom - median marked frame|, in frames")
    print("=" * 74)
    print("  " + dist("offset_frames", "{:.1f}"))
    for k in (0, 2, 5, 10):
        n = sum(1 for r in rows if r["offset_frames"] <= k)
        print(f"  within {k:2d} frames ({k / 30:.2f}s): {n:4d}/{len(rows)}  "
              f"({n / len(rows):.1%})")

    print()
    print("=" * 74)
    print("IoU -- detected window vs the span of marked frames")
    print("=" * 74)
    print("  " + dist("iou"))

    worst = sorted(rows, key=lambda r: r["containment"])[:5]
    if worst and worst[0]["containment"] < 1.0:
        print()
        print("  worst containment:")
        for r in worst:
            print(f"    {r['video']:10s} marked {r['marked_span']} "
                  f"window {r['window']} bottom {r['bottom']} "
                  f"containment {r['containment']:.2f}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(
        {"split": args.split, "n": len(rows), "skipped": dict(skipped),
         "params_id": params["params_id"], "rows": rows}, indent=2))
    print()
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
