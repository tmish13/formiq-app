#!/usr/bin/env python3
"""Stage 0 GATE — what does `1` mean in labels_shallow_depth.json?

The filename says "shallow depth error", which reads as `1 = shallow = fault`.
A 600-frame probe on the train split says the opposite: label-1 frames have the
hip *closer to / below* knee level and a *smaller* knee angle, both of which mean
DEEPER (|Cohen d| = 1.29 each, y increases downward in image coords).

Getting this backwards produces a rule that is inverted and still scores well, so
nothing is fitted until it is resolved. Three independent routes, no model, no
Docker:

  A. Direct overlap with `depth_frames` — the decisive one. `depth_frames` in the
     splits file marks the frames where a human saw the depth fault. If those same
     frame indices carry label 1, then 1 = fault. If 0, then 0 = fault.
  B. Cross-tab — per-video rate of label-1 frames, grouped by video-level class.
     If 1 = fault, depth_fault videos should carry a higher rate than good_form.
  C. Geometry — restate the indicator means per class, on the full labelled set
     rather than the 600-frame sample.

Route A is the arbiter; B and C must agree with it or the disagreement is the
finding.

Usage:
    python bench/label_polarity_probe.py [--crops-out DIR]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics as st
from collections import Counter, defaultdict
from pathlib import Path

DATASET = Path.home() / "Desktop" / "Squat More" / "Labeled_Dataset"
SPLITS = (
    Path.home()
    / "FORMIQ Form Analysis Model"
    / "data"
    / "squat_processed"
    / "user_level_multilabel_splits.json"
)
FRAME_LABELS = DATASET / "Shallow_Squat_Error_Dataset" / "labels_shallow_depth.json"
CROPS = DATASET / "Shallow_Squat_Error_Dataset" / "crops_unaligned"
KP_DIR = DATASET / "processed_videos" / "keypoints"

# depth_frames are stored as frame_index / 30 (verified: 1.2666... * 30 == 38.0)
DEPTH_FRAMES_FPS = 30.0

# Landmarks we need for the geometry route.
CORE = (11, 12, 23, 24, 25, 26, 27, 28)
MIN_VIS = 0.4


# ---------------------------------------------------------------- geometry --
def _angle(a, b, c):
    """Interior angle at b, in degrees. None when degenerate."""
    v1 = (a["x"] - b["x"], a["y"] - b["y"])
    v2 = (c["x"] - b["x"], c["y"] - b["y"])
    n1 = math.hypot(*v1)
    n2 = math.hypot(*v2)
    if n1 < 1e-9 or n2 < 1e-9:
        return None
    cos = max(-1.0, min(1.0, (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2)))
    return math.degrees(math.acos(cos))


def indicators(landmarks):
    """(hip_knee_delta_norm, knee_flexion_deg) or None when unusable.

    y increases downward, so a LARGER hip-knee delta and a SMALLER knee angle
    both mean deeper.
    """
    if len(landmarks) < 33:
        return None
    if any(landmarks[i].get("visibility", 1.0) < MIN_VIS for i in CORE):
        return None
    hip_y = (landmarks[23]["y"] + landmarks[24]["y"]) / 2
    sho_y = (landmarks[11]["y"] + landmarks[12]["y"]) / 2
    hip_x = (landmarks[23]["x"] + landmarks[24]["x"]) / 2
    sho_x = (landmarks[11]["x"] + landmarks[12]["x"]) / 2
    torso = math.hypot(hip_x - sho_x, hip_y - sho_y)
    if torso < 1e-6:
        return None
    knee_y = (landmarks[25]["y"] + landmarks[26]["y"]) / 2
    delta = (hip_y - knee_y) / torso
    sides = [
        a
        for a in (
            _angle(landmarks[23], landmarks[25], landmarks[27]),
            _angle(landmarks[24], landmarks[26], landmarks[28]),
        )
        if a is not None
    ]
    if not sides:
        return None
    return delta, st.mean(sides)


# -------------------------------------------------------------------- data --
def load():
    frame_labels = json.loads(FRAME_LABELS.read_text())
    splits = json.loads(SPLITS.read_text())

    video_class, depth_frames, split_of = {}, {}, {}
    for split in ("train", "validation", "test"):
        s = splits["splits"][split]
        for rec in s["video_data"]:
            name = rec["video_name"]
            split_of[name] = split
            el = rec.get("enhanced_labels") or {}
            video_class[name] = (el.get("video_level") or {}).get("class_label")
            tf = el.get("temporal_faults") or {}
            depth_frames[name] = tf.get("depth_frames") or []
    return frame_labels, video_class, depth_frames, split_of


def parse_key(key):
    vid, frame = key.rsplit("_", 1)
    return vid, int(frame)


# ------------------------------------------------------------------ routes --
def route_a(frame_labels, depth_frames):
    """Decisive: do human-marked fault frames carry label 1 or label 0?"""
    hits = Counter()
    per_video = []
    for vid, times in depth_frames.items():
        if not times:
            continue
        marked = {int(round(t * DEPTH_FRAMES_FPS)) for t in times}
        labelled = {
            f: v for k, v in frame_labels.items()
            for vv, f in [parse_key(k)] if vv == vid
        }
        if not labelled:
            continue
        overlap = marked & set(labelled)
        if not overlap:
            continue
        ones = sum(labelled[f] for f in overlap)
        hits["frames_matched"] += len(overlap)
        hits["label_1"] += ones
        hits["label_0"] += len(overlap) - ones
        per_video.append((vid, len(overlap), ones))
    return hits, per_video


def route_b(frame_labels, video_class):
    """Per-video rate of label-1 frames, grouped by video-level class."""
    by_video = defaultdict(list)
    for k, v in frame_labels.items():
        vid, _ = parse_key(k)
        by_video[vid].append(v)
    by_class = defaultdict(list)
    for vid, vals in by_video.items():
        cls = video_class.get(vid)
        if cls:
            by_class[cls].append(sum(vals) / len(vals))
    return by_class, by_video


def route_c(frame_labels, split_of):
    """Indicator means per label, on every labelled TRAIN frame (not a sample)."""
    rows = []
    cache = {}
    skipped = Counter()
    for k, y in frame_labels.items():
        vid, fi = parse_key(k)
        if split_of.get(vid) != "train":
            skipped["not_train"] += 1
            continue
        if vid not in cache:
            p = KP_DIR / f"{vid}_keypoints.json"
            if not p.exists():
                skipped["no_keypoints"] += 1
                cache[vid] = None
            else:
                cache[vid] = json.loads(p.read_text())
        frames = cache[vid]
        if frames is None or fi >= len(frames):
            skipped["frame_oob"] += 1
            continue
        ind = indicators(frames[fi]["landmarks"])
        if ind is None:
            skipped["unusable"] += 1
            continue
        rows.append((y, ind[0], ind[1]))
    return rows, skipped


def cohen_d(a, b):
    if len(a) < 2 or len(b) < 2:
        return float("nan")
    pooled = math.sqrt((st.pstdev(a) ** 2 + st.pstdev(b) ** 2) / 2) or 1e-9
    return (st.mean(a) - st.mean(b)) / pooled


# -------------------------------------------------------------------- main --
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--crops-out", default=None,
                    help="copy 10 sample crops (5 per class) here for eyeballing")
    args = ap.parse_args()

    frame_labels, video_class, depth_frames, split_of = load()
    print(f"frame labels        : {len(frame_labels)}")
    print(f"videos with labels  : {len({parse_key(k)[0] for k in frame_labels})}")
    print()

    # ---- Route A -----------------------------------------------------------
    print("=" * 72)
    print("ROUTE A — overlap with human-marked depth_frames  [DECISIVE]")
    print("=" * 72)
    hits, per_video = route_a(frame_labels, depth_frames)
    if not hits["frames_matched"]:
        print("  NO OVERLAP — depth_frames and labelled frames are disjoint.")
        print("  Route A cannot arbitrate; fall back to B and C.")
    else:
        n = hits["frames_matched"]
        p1 = hits["label_1"] / n
        print(f"  videos with overlap     : {len(per_video)}")
        print(f"  frames matched          : {n}")
        print(f"  ...carrying label 1     : {hits['label_1']} ({p1:.1%})")
        print(f"  ...carrying label 0     : {hits['label_0']} ({1 - p1:.1%})")
        print()
        base = sum(frame_labels.values()) / len(frame_labels)
        print(f"  base rate of label 1    : {base:.1%}")
        print(f"  lift on fault frames    : {p1 - base:+.1%}")
        print()
        if p1 > base + 0.10:
            print("  => label 1 is ENRICHED on human-marked fault frames")
            print("     READING: 1 = shallow / depth fault")
        elif p1 < base - 0.10:
            print("  => label 1 is DEPLETED on human-marked fault frames")
            print("     READING: 0 = shallow / depth fault, 1 = at depth")
        else:
            print("  => no clear enrichment either way; Route A is inconclusive")

    # ---- Route B -----------------------------------------------------------
    print()
    print("=" * 72)
    print("ROUTE B — per-video rate of label-1 frames, by video class")
    print("=" * 72)
    by_class, by_video = route_b(frame_labels, video_class)
    for cls in ("good_form", "posture_fault", "depth_fault"):
        vals = by_class.get(cls, [])
        if vals:
            print(f"  {cls:14s} n={len(vals):4d} videos   "
                  f"mean rate of label-1 frames = {st.mean(vals):.3f}")
    gf, df = by_class.get("good_form", []), by_class.get("depth_fault", [])
    if gf and df:
        print()
        print(f"  depth_fault − good_form = {st.mean(df) - st.mean(gf):+.3f}")
        if st.mean(df) > st.mean(gf):
            print("     READING: 1 = shallow / depth fault  (agrees with A if A said the same)")
        else:
            print("     READING: 0 = shallow / depth fault, 1 = at depth")

    mixed = sum(1 for v in by_video.values() if 0 < sum(v) < len(v))
    print()
    print(f"  videos with MIXED labels: {mixed}/{len(by_video)} "
          f"({mixed / len(by_video):.0%}) — high means genuine per-frame judgement,")
    print( "    low means a video-level label copied down onto frames")

    # ---- Route C -----------------------------------------------------------
    print()
    print("=" * 72)
    print("ROUTE C — geometry on ALL labelled train frames")
    print("=" * 72)
    rows, skipped = route_c(frame_labels, split_of)
    print(f"  usable frames: {len(rows)}   skipped: {dict(skipped)}")
    if rows:
        print(f"  label counts : {Counter(r[0] for r in rows)}")
        print()
        for name, idx, deeper in (
            ("(hip_y-knee_y)/torso", 1, "larger"),
            ("knee flexion (deg)", 2, "smaller"),
        ):
            a = [r[idx] for r in rows if r[0] == 1]
            b = [r[idx] for r in rows if r[0] == 0]
            if not a or not b:
                continue
            print(f"  {name:22s} label1={st.mean(a):8.3f}  label0={st.mean(b):8.3f}  "
                  f"d={cohen_d(a, b):+.2f}   (deeper = {deeper})")
        d_delta = cohen_d([r[1] for r in rows if r[0] == 1],
                          [r[1] for r in rows if r[0] == 0])
        print()
        if d_delta > 0:
            print("  => label 1 frames are geometrically DEEPER")
            print("     READING: 1 = at depth, 0 = shallow / depth fault")
        else:
            print("  => label 1 frames are geometrically SHALLOWER")
            print("     READING: 1 = shallow / depth fault")

    # ---- crops for eyeballing ---------------------------------------------
    if args.crops_out:
        out = Path(args.crops_out)
        out.mkdir(parents=True, exist_ok=True)
        import shutil
        picked = Counter()
        for k in sorted(frame_labels):
            y = frame_labels[k]
            if picked[y] >= 5:
                continue
            src = CROPS / f"{k}.jpg"
            if src.exists():
                shutil.copy(src, out / f"label{y}_{k}.jpg")
                picked[y] += 1
        print()
        print(f"copied {sum(picked.values())} crops to {out} "
              f"(label0={picked[0]}, label1={picked[1]})")


if __name__ == "__main__":
    main()
