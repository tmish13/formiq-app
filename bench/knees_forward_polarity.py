#!/usr/bin/env python3
"""Knees-forward: predicate and polarity cross-tab, before any constants.

THE LAST FAULT CANDIDATE. Depth had no geometric signal at all (no axis
separated the classes, best AUROC 0.578 of ten tried). Valgus had real signal
but only in front view, and this corpus is ~5% front view with 4 positive
front-view examples. Knees-forward is the one whose visibility profile matches
the data that actually exists.

THE PREDICATE
-------------
Knee travelling forward past the toes is a SAGITTAL-plane fault, so it is
visible from the side and oblique views this corpus mostly contains -- the exact
opposite of valgus, and the reason this is worth one more run.

    dir_s   = sign(foot_index_x − heel_x)        the way that foot points
    fwd_s   = ((knee_x − foot_index_x) · dir_s) / S

Positive = knee is forward of the toes. Using the foot's own pointing direction
makes the sign orientation-safe: it does not matter which way the subject faces
or which leg is measured, the same convention holds.

Normalised by standing torso length S, side-gated by visibility, averaged over
usable sides -- same machinery as the depth and valgus work.

THE POLARITY CHECK
------------------
Identical discipline to valgus, and the errors from that run are already fixed
here:

  * within-video, self-controlled -- frames inside a marked interval against
    frames outside it, same clip, same subject, same camera
  * view-stratified agreement, since a sagittal fault should read BEST in side
    view and worst head-on (the mirror of valgus)
  * between-video comparisons use LIKE-FOR-LIKE windows. The valgus run first
    compared a peak inside a ~40-frame interval against a peak over a ~100-frame
    clip and produced a spurious AUROC of 0.178; a max over more samples is
    larger by construction. Every between-video statistic below is whole-clip on
    both sides, and a matched-window variant is reported alongside.

NO CONSTANTS ARE FITTED. Train + validation only; test is not opened.

    python bench/knees_forward_polarity.py
"""
from __future__ import annotations

import gzip
import json
import statistics as st
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "backend"))

import numpy as np

KP_DIR = REPO / "bench" / "cache" / "keypoints_live"
LABELS = Path.home() / "Desktop" / "Squat More" / "Labeled_Dataset" / "Labels"
SPLITS = (
    Path.home() / "FORMIQ Form Analysis Model" / "data" / "squat_processed"
    / "user_level_multilabel_splits.json"
)
OUT = REPO / "bench" / "results" / "knees_forward_polarity.json"

FOOT = {"L": {"heel": 29, "toe": 31}, "R": {"heel": 30, "toe": 32}}
MIN_FOOT_LEN = 1e-6


def forward_at(frame, S, min_vis):
    """Knee-past-toe for one frame, mean over usable sides, or None."""
    from app.rules.kinematics import SIDES, VIS, X, usable_sides

    if not S:
        return None
    vals = []
    for s in usable_sides(frame, min_vis):
        heel_i, toe_i = FOOT[s]["heel"], FOOT[s]["toe"]
        heel, toe = frame[heel_i], frame[toe_i]
        knee = frame[SIDES[s]["knee"]]
        if not (np.isfinite(heel[X]) and np.isfinite(toe[X]) and np.isfinite(knee[X])):
            continue
        # The foot landmarks carry their own visibility; a foot we cannot see
        # cannot define a forward direction.
        if not (np.isfinite(heel[VIS]) and heel[VIS] >= min_vis
                and np.isfinite(toe[VIS]) and toe[VIS] >= min_vis):
            continue
        span = toe[X] - heel[X]
        if abs(span) < MIN_FOOT_LEN:
            continue
        direction = 1.0 if span > 0 else -1.0
        vals.append(((knee[X] - toe[X]) * direction) / S)
    return float(np.mean(vals)) if vals else None


def main():
    from app.eval.metrics import auroc
    from app.rules import load_params
    from app.rules.kinematics import scale_reference, to_array
    from app.rules.view import estimate_view

    p = load_params()
    labels = json.loads((LABELS / "error_knees_forward.json").read_text())

    sp = json.loads(SPLITS.read_text())
    split_of = {}
    for split in ("train", "validation"):          # test not opened
        for r in sp["splits"][split]["video_data"]:
            split_of[r["video_name"]] = split

    rows, skipped = [], Counter()
    for f in sorted(KP_DIR.glob("*.json.gz")):
        name = f.name[:-8]
        if name not in split_of:
            skipped["not_train_or_val"] += 1
            continue
        ivs = labels.get(name)
        if ivs is None:
            skipped["no_label"] += 1
            continue
        with gzip.open(f, "rt") as fh:
            d = json.load(fh)
        kp = to_array(d["frames"])
        fps = float(d.get("source_fps") or 0.0) or p["fallback_fps"]
        S = scale_reference(kp, p["min_visibility"], p["standing_quantile"],
                            p["min_usable_frames_for_scale"], p["min_standing_frames"])
        if not S:
            skipped["bad_scale"] += 1
            continue
        view = estimate_view(kp, S, p["min_visibility"], p["standing_quantile"],
                             p["view_side_max"], p["view_front_min"])

        marked = np.zeros(kp.shape[0], dtype=bool)
        for a, b in ivs:
            lo, hi = int(round(a * fps)), int(round(b * fps))
            marked[max(0, lo):min(kp.shape[0], hi + 1)] = True

        vin, vout, allv = [], [], []
        for t in range(kp.shape[0]):
            v = forward_at(kp[t], S, p["min_visibility"])
            if v is None:
                continue
            allv.append(v)
            (vin if marked[t] else vout).append(v)
        if not allv:
            skipped["no_foot_landmarks"] += 1
            continue

        # Matched window: the same number of frames a positive clip's interval
        # would cover, taken from the deepest part of the clip. Gives negatives
        # a like-sized window instead of the whole clip.
        wlen = int(marked.sum()) if marked.any() else 0
        rows.append({
            "video": name, "split": split_of[name], "view": view.kind,
            "positive": bool(ivs), "n_in": len(vin), "n_out": len(vout),
            "fwd_in": st.median(vin) if vin else None,
            "fwd_out": st.median(vout) if vout else None,
            "fwd_clip_max": max(allv),
            "fwd_clip_median": st.median(allv),
            "marked_frames": wlen,
        })

    pos = [r for r in rows if r["positive"] and r["n_in"] >= 3 and r["n_out"] >= 3]
    neg = [r for r in rows if not r["positive"]]

    print(f"clips {len(rows)}  positive-with-both {len(pos)}  negative {len(neg)}"
          f"   skipped {dict(skipped)}")
    print("  TEST NOT OPENED -- train + validation only")
    print()

    print("=" * 78)
    print("1. WITHIN-VIDEO: predicate inside vs outside the marked interval")
    print("=" * 78)
    if pos:
        deltas = [r["fwd_in"] - r["fwd_out"] for r in pos]
        higher = sum(1 for d in deltas if d > 0)
        print(f"   n clips               : {len(pos)}")
        print(f"   median delta (in-out) : {st.median(deltas):+.4f} torso-lengths")
        print(f"   clips with delta > 0  : {higher}/{len(deltas)} ({higher/len(deltas):.1%})")
        print()
        if higher / len(deltas) > 0.60:
            print("   => POLARITY CONFIRMED")
        elif higher / len(deltas) < 0.40:
            print("   => POLARITY INVERTED -- flip the sign")
        else:
            print("   => NO AGREEMENT: the predicate does not track the label")

    print()
    print("=" * 78)
    print("2. BY VIEW -- sagittal fault: should read BEST in side view")
    print("=" * 78)
    for v in ("side", "oblique", "front"):
        sub = [r for r in pos if r["view"] == v]
        if len(sub) < 3:
            print(f"   {v:8s} n={len(sub)} (too few)")
            continue
        deltas = [r["fwd_in"] - r["fwd_out"] for r in sub]
        higher = sum(1 for d in deltas if d > 0)
        print(f"   {v:8s} n={len(sub):3d}  median delta {st.median(deltas):+.4f}  "
              f"agree {higher}/{len(sub)} ({higher/len(sub):.0%})")

    print()
    print("=" * 78)
    print("3. BETWEEN-VIDEO -- like-for-like windows on both sides")
    print("=" * 78)
    for stat in ("fwd_clip_max", "fwd_clip_median"):
        pv = [r[stat] for r in pos if r[stat] is not None]
        nv = [r[stat] for r in neg if r[stat] is not None]
        if not pv or not nv:
            continue
        y = [0] * len(nv) + [1] * len(pv)
        sc = list(nv) + list(pv)
        print(f"   {stat:18s} pos n={len(pv):3d} median {st.median(pv):+.4f} | "
              f"neg n={len(nv):3d} median {st.median(nv):+.4f} | AUROC {auroc(y, sc):.3f}")
    print()
    print("   0.5 = indistinguishable.")

    print()
    print("=" * 78)
    print("4. PREVALENCE -- how much of the corpus is even labelled here")
    print("=" * 78)
    print(f"   positive clips {len(pos) + sum(1 for r in rows if r['positive']) - len(pos)}"
          f" / {len(rows)}  ({sum(1 for r in rows if r['positive'])/max(len(rows),1):.1%})")
    print(f"   views: {dict(Counter(r['view'] for r in rows))}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"rows": rows, "skipped": dict(skipped),
                               "test_opened": False}, indent=2))
    print()
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
