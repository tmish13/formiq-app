#!/usr/bin/env python3
"""Knee valgus: state the predicate, then check its polarity BEFORE fitting anything.

THE PREDICATE
-------------
Valgus is the knee collapsing toward the body midline relative to the foot. So
measure both against the midline rather than against each other:

    M        = hip-midpoint x           (the body midline in the image)
    inward_s = (|ankle_x - M| - |knee_x - M|) / S      for side s

Positive means the knee is CLOSER to the midline than the ankle, i.e. valgus.
Negative means the knee tracks outside the foot.

Why midline-relative and not the literal `knee_x - ankle_x`: the sign of
`knee_x - ankle_x` flips between the left and right leg, and flips again if the
subject faces the other way. Measuring each joint's distance from the midline is
polarity-unambiguous by construction, for either leg, facing either direction.
It still reduces to a knee-x-versus-ankle-x comparison, just an orientation-safe
one.

Normalised by the standing torso length S -- the same scale reference the depth
rule used -- and side-gated by visibility, for the same reason: a side view
occludes one leg, and requiring both discards the informative clips.

THE POLARITY CHECK
------------------
Within-video, self-controlled: for each labelled clip, compare the predicate on
frames INSIDE a human-marked valgus interval against frames OUTSIDE it, in the
same clip, same subject, same camera. That removes every between-video confound
in one step, which eyeballing 50 frames cannot.

If `inward` is higher inside the marked intervals, the predicate and the label
agree and the sign convention above is right. If it is lower, the convention is
inverted. If there is no difference, the label is not recoverable from this
geometry -- the same outcome depth produced, and better to learn it now.

NO CONSTANTS ARE FITTED HERE. Train + validation only; test is not opened.

    python bench/valgus_polarity.py
"""
from __future__ import annotations

import gzip
import json
import statistics as st
import sys
from collections import Counter, defaultdict
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
OUT = REPO / "bench" / "results" / "valgus_polarity.json"


def inward_at(frame, S, min_vis):
    """The predicate for one frame: mean over usable sides, or None."""
    from app.rules.kinematics import SIDES, X, usable_sides

    sides = usable_sides(frame, min_vis)
    if not sides or not S:
        return None
    hips = [frame[SIDES[s]["hip"]][X] for s in ("L", "R")
            if np.isfinite(frame[SIDES[s]["hip"]][X])]
    if not hips:
        return None
    M = float(np.mean(hips))
    vals = []
    for s in sides:
        idx = SIDES[s]
        kx, ax = frame[idx["knee"]][X], frame[idx["ankle"]][X]
        if not (np.isfinite(kx) and np.isfinite(ax)):
            continue
        vals.append((abs(ax - M) - abs(kx - M)) / S)
    return float(np.mean(vals)) if vals else None


def main():
    from app.rules import load_params
    from app.rules.kinematics import scale_reference, to_array
    from app.rules.view import estimate_view

    p = load_params()
    inward_labels = json.loads((LABELS / "error_knees_inward.json").read_text())

    sp = json.loads(SPLITS.read_text())
    split_of = {}
    for split in ("train", "validation"):          # test not opened
        for r in sp["splits"][split]["video_data"]:
            split_of[r["video_name"]] = split

    rows = []
    skipped = Counter()
    for f in sorted(KP_DIR.glob("*.json.gz")):
        name = f.name[:-8]
        if name not in split_of:
            skipped["not_train_or_val"] += 1
            continue
        ivs = inward_labels.get(name)
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

        vin, vout = [], []
        for t in range(kp.shape[0]):
            v = inward_at(kp[t], S, p["min_visibility"])
            if v is None:
                continue
            (vin if marked[t] else vout).append(v)

        allv = vin + vout
        rows.append({
            "video": name, "split": split_of[name], "view": view.kind,
            "positive": bool(ivs),
            "n_in": len(vin), "n_out": len(vout),
            "inward_in": st.median(vin) if vin else None,
            "inward_out": st.median(vout) if vout else None,
            # Whole-clip statistics, for the BETWEEN-video comparison. Comparing
            # a max taken inside a ~40-frame interval against a max over a
            # ~100-frame clip is a comparison of sample sizes, not of subjects:
            # the larger sample wins on any max. Both sides must be whole-clip.
            "inward_clip_max": max(allv) if allv else None,
            "inward_clip_median": st.median(allv) if allv else None,
        })

    pos = [r for r in rows if r["positive"] and r["n_in"] >= 3 and r["n_out"] >= 3]
    neg = [r for r in rows if not r["positive"] and r["n_out"] >= 3]

    print(f"clips: {len(rows)}  ({len(pos)} labelled positive with both in/out "
          f"frames, {len(neg)} labelled negative)   skipped: {dict(skipped)}")
    print("  TEST NOT OPENED -- train + validation only")
    print()

    # ---- 1. within-video, self-controlled ----------------------------------
    print("=" * 78)
    print("1. WITHIN-VIDEO: predicate inside vs outside the marked interval")
    print("=" * 78)
    print("   Same clip, same subject, same camera. Positive delta => the")
    print("   predicate agrees with the label and the sign convention is right.")
    print()
    if pos:
        deltas = [r["inward_in"] - r["inward_out"] for r in pos]
        higher = sum(1 for d in deltas if d > 0)
        print(f"   n clips                : {len(pos)}")
        print(f"   median delta (in-out)  : {st.median(deltas):+.4f} torso-lengths")
        print(f"   mean delta             : {st.mean(deltas):+.4f}")
        print(f"   clips with delta > 0   : {higher}/{len(deltas)} ({higher/len(deltas):.1%})")
        print()
        if higher / len(deltas) > 0.60:
            print("   => POLARITY CONFIRMED: inward is higher inside marked intervals.")
        elif higher / len(deltas) < 0.40:
            print("   => POLARITY INVERTED: flip the sign of the predicate.")
        else:
            print("   => NO AGREEMENT: the predicate does not track the label.")
            print("      Same outcome as depth. Do not fit constants to this.")

    # ---- 2. by view --------------------------------------------------------
    print()
    print("=" * 78)
    print("2. BY VIEW -- valgus is a frontal-plane fault")
    print("=" * 78)
    for v in ("front", "oblique", "side"):
        sub = [r for r in pos if r["view"] == v]
        if len(sub) < 3:
            print(f"   {v:8s} n={len(sub)} (too few)")
            continue
        deltas = [r["inward_in"] - r["inward_out"] for r in sub]
        higher = sum(1 for d in deltas if d > 0)
        print(f"   {v:8s} n={len(sub):3d}  median delta {st.median(deltas):+.4f}  "
              f"agree {higher}/{len(sub)} ({higher/len(sub):.0%})")

    # ---- 3. between-video cross-tab ---------------------------------------
    print()
    print("=" * 78)
    print("3. BETWEEN-VIDEO: positive vs negative clips")
    print("=" * 78)
    if pos and neg:
        from app.eval.metrics import auroc
        print("   Like-for-like: whole-clip statistics on BOTH sides.")
        for stat in ("inward_clip_max", "inward_clip_median"):
            pv = [r[stat] for r in pos if r[stat] is not None]
            nv = [r[stat] for r in neg if r[stat] is not None]
            if not pv or not nv:
                continue
            y = [0] * len(nv) + [1] * len(pv)
            sc = list(nv) + list(pv)
            a = auroc(y, sc)
            print(f"   {stat:20s} positive n={len(pv):3d} median {st.median(pv):+.4f} | "
                  f"negative n={len(nv):3d} median {st.median(nv):+.4f} | AUROC {a:.3f}")
        print()
        print("   0.5 = indistinguishable. This is the number that says whether a")
        print("   video-level valgus rule is possible at all.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"rows": rows, "skipped": dict(skipped),
                               "test_opened": False}, indent=2))
    print()
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
