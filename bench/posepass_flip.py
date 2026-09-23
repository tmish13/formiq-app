#!/usr/bin/env python3
"""The pose pass moves 1 in 7 verdicts. The aggregate does not show it.

Same model, same threshold, same videos, byte-identical source footage. The
only thing that differs is WHICH MediaPipe run produced the keypoints:

  * DATASET pass -- the keypoints shipped with the corpus, the ones every
    pinned v1 number was computed on.
  * LIVE pass    -- `_extract_pose_from_video` inside the worker container,
    complexity 2, fresh tracker per video. What a real upload gets.

The population metrics barely move and their paired CIs span zero, so an F1
comparison says "no measurable difference". That conclusion is correct about
the population and useless about a user, because the per-video probabilities
move a great deal and the movements cancel.

This script exists to state the per-item number next to the aggregate one, and
to answer the obvious follow-up: are the flips just threshold jitter? A verdict
that flips because its probability sat at 0.524 is noise anyone would expect.
One that flips because its probability moved 0.6 is not. Section 4 separates
them.

Pure offline join of two stored score files -- no torch, no container, no DB.

    python bench/posepass_flip.py
"""
from __future__ import annotations

import json
import statistics as st
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "backend"))

import numpy as np

# Dataset-keypoint scores, frozen 2026-09-19. n=224.
PINNED = REPO / "bench" / "results" / "2026-09-19-v1-test-per-video-scores.json"
# Live-keypoint scores, written by bench/depth_rule_eval.py --split test --final.
LIVE = REPO / "bench" / "results" / "depth_rule_eval_test.json"
OUT = REPO / "bench" / "results" / "posepass_flip.json"

# PostureV1 predicts POSTURE fault. Getting this wrong scores the model
# against a label it was never trained on and silently produces a
# below-chance AUROC that looks like a finding.
POSITIVE_CLASS = "posture_fault"
N_BOOT = 2000
SEED = 0


def paired_bootstrap(rows, fn, n=N_BOOT, seed=SEED):
    """CI on the DELTA, resampling videos once and scoring both arms on it.

    Resampling each arm independently would compare two different video sets
    and inflate the interval with between-video variance that the pairing is
    there to remove.
    """
    rng = np.random.default_rng(seed)
    N = len(rows)
    idx_all = np.arange(N)
    out = []
    for _ in range(n):
        idx = rng.integers(0, N, N)
        sub = [rows[i] for i in idx]
        out.append(fn(sub, "live") - fn(sub, "pinned"))
    point = fn([rows[i] for i in idx_all], "live") - fn([rows[i] for i in idx_all], "pinned")
    return point, float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


def main():
    from app.eval.metrics import auroc, counts, precision_recall_f1, trivial_floor

    pin = json.loads(PINNED.read_text())
    thr = float(pin["threshold"])
    pinned_prob = {r["video"]: r["prob_fault"] for r in pin["rows"]}
    pinned_cls = {r["video"]: r["class"] for r in pin["rows"]}

    live_raw = json.loads(LIVE.read_text())
    live_prob = {r["video"]: r["pv1_prob"] for r in live_raw["rows"]
                 if r.get("pv1_prob") is not None}

    shared = sorted(set(pinned_prob) & set(live_prob))
    rows = [{
        "video": v,
        "class": pinned_cls[v],
        "y": 1 if pinned_cls[v] == POSITIVE_CLASS else 0,
        "pinned": float(pinned_prob[v]),
        "live": float(live_prob[v]),
    } for v in shared]
    for r in rows:
        r["delta"] = r["live"] - r["pinned"]
        r["pred_pinned"] = int(r["pinned"] >= thr)
        r["pred_live"] = int(r["live"] >= thr)
        r["flipped"] = r["pred_pinned"] != r["pred_live"]
        # How far the DATASET-pass probability sat from the threshold. A flip
        # from just inside the margin is threshold jitter; a flip from well
        # outside it is the pose pass changing the model's mind.
        r["margin_pinned"] = abs(r["pinned"] - thr)

    print(f"shared videos {len(rows)}  (pinned {len(pinned_prob)}, live {len(live_prob)})")
    print(f"threshold {thr}   positive class {POSITIVE_CLASS}")
    print()

    def f1_of(sub, arm):
        return precision_recall_f1(counts([r["y"] for r in sub],
                                          [int(r[arm] >= thr) for r in sub]))[2]

    def auroc_of(sub, arm):
        return auroc([r["y"] for r in sub], [r[arm] for r in sub])

    print("=" * 78)
    print("1. AGGREGATE -- paired on the same videos")
    print("=" * 78)
    agg = {}
    for arm in ("pinned", "live"):
        c = counts([r["y"] for r in rows], [int(r[arm] >= thr) for r in rows])
        p, rc, f = precision_recall_f1(c)
        a = auroc_of(rows, arm)
        agg[arm] = {"precision": p, "recall": rc, "f1": f, "auroc": a,
                    "tp": c.tp, "fp": c.fp, "tn": c.tn, "fn": c.fn}
        print(f"   {arm:7s}  F1 {f:.4f}  AUROC {a:.4f}  P {p:.4f}  R {rc:.4f}"
              f"   (tp {c.tp} fp {c.fp} tn {c.tn} fn {c.fn})")
    floor = trivial_floor([r["y"] for r in rows])
    print(f"   trivial floor F1 {floor['all_positive_f1']:.4f}  "
          f"prevalence {floor['prevalence']:.4f}")
    print()

    deltas = {}
    for name, fn in (("f1", f1_of), ("auroc", auroc_of)):
        pt, lo, hi = paired_bootstrap(rows, fn)
        deltas[name] = {"delta": pt, "ci95": [lo, hi], "includes_zero": lo <= 0 <= hi}
        flag = "INCLUDES ZERO" if lo <= 0 <= hi else "excludes zero"
        print(f"   delta {name:6s} {pt:+.4f}   95% CI [{lo:+.4f}, {hi:+.4f}]   {flag}")
    print()
    print("   Paired bootstrap, 2000 resamples, seed 0, same videos in both arms.")

    print()
    print("=" * 78)
    print("2. PER-VIDEO -- what the aggregate hides")
    print("=" * 78)
    ad = sorted(abs(r["delta"]) for r in rows)
    q = lambda p: float(np.percentile(ad, p))
    print(f"   |prob delta|  median {st.median(ad):.4f}   p75 {q(75):.4f}   "
          f"p90 {q(90):.4f}   p95 {q(95):.4f}   max {max(ad):.4f}")
    flips = [r for r in rows if r["flipped"]]
    print(f"   verdicts flipped   {len(flips)}/{len(rows)} = {len(flips)/len(rows):.1%}")
    up = [r for r in flips if r["pred_live"] == 1]
    dn = [r for r in flips if r["pred_live"] == 0]
    print(f"     negative -> positive {len(up)}     positive -> negative {len(dn)}")
    better = sum(1 for r in flips if r["pred_live"] == r["y"])
    print(f"     flipped TOWARD the label {better}/{len(flips)}, "
          f"AWAY {len(flips)-better}/{len(flips)}")
    print()
    print("   The flips nearly cancel, which is exactly why the aggregate is flat.")

    print()
    print("=" * 78)
    print("3. FLIPS BY CLASS")
    print("=" * 78)
    for cls in sorted({r["class"] for r in rows}):
        sub = [r for r in rows if r["class"] == cls]
        fl = [r for r in sub if r["flipped"]]
        md = st.median([abs(r["delta"]) for r in sub])
        print(f"   {cls:14s} n={len(sub):3d}  flipped {len(fl):2d} "
              f"({len(fl)/len(sub):5.1%})  median |delta| {md:.4f}")

    print()
    print("=" * 78)
    print("4. ARE THE FLIPS JUST THRESHOLD JITTER?")
    print("=" * 78)
    print("   Margin = |dataset-pass probability - threshold|. A flip from")
    print("   inside a narrow margin is expected; one from outside it is not.")
    print()
    for band in (0.02, 0.05, 0.10):
        inside = [r for r in flips if r["margin_pinned"] <= band]
        print(f"   flips with margin <= {band:.2f}: {len(inside):2d}/{len(flips)} "
              f"({len(inside)/len(flips):.0%})")
    far = sorted(flips, key=lambda r: -r["margin_pinned"])[:5]
    print()
    print("   Five flips furthest from the threshold:")
    for r in far:
        print(f"     {r['video']:12s} {r['class']:14s} "
              f"{r['pinned']:.3f} -> {r['live']:.3f}  "
              f"(delta {r['delta']:+.3f}, margin {r['margin_pinned']:.3f})")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "threshold": thr, "n": len(rows), "aggregate": agg, "deltas": deltas,
        "flip_count": len(flips), "flip_rate": len(flips) / len(rows),
        "abs_delta": {"median": st.median(ad), "p75": q(75), "p90": q(90),
                      "p95": q(95), "max": max(ad)},
        "trivial_floor": floor, "rows": rows,
    }, indent=2))
    print()
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
