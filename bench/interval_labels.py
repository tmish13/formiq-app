#!/usr/bin/env python3
"""Fitness-AQA's temporal fault intervals as frame-level ground truth (2026-09-24).

The dataset's labels are per-video INTERVAL lists in seconds (`Labels/error_knees_forward.json`,
`error_knees_inward.json`: [[start, end], ...], empty = no error). The corpus flag the model was
trained on is `len(intervals) > 0` (ML_AUDIT §2.3). The intervals themselves were never used. Two
questions, answered on TRAIN + VALIDATION clips only (the test split is excluded by name; no test read):

  1. Localisation timing: when the shipped knees-forward rule says OBSERVED at `peak_time_sec`, does
     that time fall inside a labelled knees-forward interval (±tol)?
  2. A graded label without annotators: does PostureV1's stored probability separate videos better
     against interval-DERIVED degree labels (fraction of the clip in error, longest interval) than
     against presence?

    docker run --rm -v $PWD/backend:/app -v $PWD:/repo \
      -v "$HOME/Desktop/Squat More/Labeled_Dataset/Labels:/labels:ro" -v <export.csv>:/tmp/kf_export.csv:ro \
      -e SECRET_KEY=dev-only-insecure-secret-key-32chars-minimum -w /app deployment-worker:latest \
      python /repo/bench/interval_labels.py --export /tmp/kf_export.csv --labels /labels \
      --cache /repo/bench/cache/keypoints_live --splits /repo/bench/results/content_level_splits.json \
      --test-names /repo/bench/results/retrain/test_clip_names.txt

The export is one row per content hash from form_checks.results (rules_shadow.knees_forward and
posture_v1.prob_fault), serving pose pass only; see bench/results/2026-09-24-interval-labels.md.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import sys
from pathlib import Path

import numpy as np

for p in ("/app", str(Path(__file__).resolve().parents[1] / "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)
from app.eval.metrics import auroc, bootstrap_ci, trivial_floor  # noqa: E402


def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * ((p * (1 - p) + z * z / (4 * n)) / n) ** 0.5
    return ((c - h) / d, (c + h) / d)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--export", type=Path, required=True); ap.add_argument("--labels", type=Path, required=True)
    ap.add_argument("--cache", type=Path, required=True); ap.add_argument("--splits", type=Path, required=True)
    ap.add_argument("--test-names", type=Path, required=True); ap.add_argument("--tol", type=float, default=0.25)
    a = ap.parse_args()

    kf = json.load(open(a.labels / "error_knees_forward.json")); ki = json.load(open(a.labels / "error_knees_inward.json"))
    test = set(a.test_names.read_text().split())
    split = {r["video"]: r["split"] for r in json.load(open(a.splits))["videos"] if r["split"]}
    test |= {v for v, s in split.items() if s == "test"}
    rows = [r for r in csv.DictReader(open(a.export)) if r["filename"].endswith(".mp4")]
    rows = [dict(r, name=r["filename"][:-4]) for r in rows]
    n_all = len(rows); rows = [r for r in rows if r["name"] not in test]; rows = [r for r in rows if r["name"] in kf]
    print(f"judged videos: {n_all}; after excluding the test split by name and videos without Fitness-AQA labels: {len(rows)}")
    by_split = {s: sum(1 for r in rows if split.get(r['name']) == s) for s in ("train", "validation")}
    print(f"of which in our content-level train: {by_split['train']}, validation: {by_split['validation']}, unassigned/withheld: {len(rows) - sum(by_split.values())}")

    # clip durations from the serving cache (fps + frame count)
    dur = {}
    for r in rows:
        f = a.cache / f"{r['name']}.json.gz"
        if f.exists():
            d = json.load(gzip.open(f, "rt")); fps = float(d.get("source_fps") or 30.0); n = len(d.get("frames") or [])
            if fps and n:
                dur[r["name"]] = n / fps

    # ---- 1. localisation timing vs intervals
    print("\n## 1. Knees-forward rule timing vs the labelled intervals (train+validation)")
    obs = [r for r in rows if r["kf_decision"] == "OBSERVED" and r["kf_peak_s"]]
    with_int = [r for r in obs if kf[r["name"]]]
    hits = 0; dists = []
    for r in with_int:
        t = float(r["kf_peak_s"]); ivs = kf[r["name"]]
        inside = any(s - a.tol <= t <= e + a.tol for s, e in ivs); hits += inside
        dists.append(min(abs(t - (s + e) / 2) for s, e in ivs))
    lo, hi = wilson(hits, len(with_int))
    print(f"OBSERVED with a peak time: {len(obs)}; of those with >=1 labelled interval: {len(with_int)}")
    print(f"peak inside a labelled interval (±{a.tol}s): {hits}/{len(with_int)} = {hits/max(len(with_int),1):.3f}  95% Wilson [{lo:.3f}, {hi:.3f}]")
    if dists:
        d = np.asarray(dists); print(f"|peak - nearest interval midpoint| s: median {np.median(d):.2f}, p75 {np.percentile(d,75):.2f}, p90 {np.percentile(d,90):.2f}")
    # chance level: if the peak were placed uniformly at random in the clip, how often would it land inside an interval?
    cov = [min(1.0, sum(e - s + 2 * a.tol for s, e in kf[r["name"]]) / dur[r["name"]]) for r in with_int if r["name"] in dur]
    if cov:
        print(f"chance level (interval coverage of the clip, ±tol, mean over the same videos): {np.mean(cov):.3f}  (n={len(cov)})")
    no_int_obs = sum(1 for r in obs if not kf[r["name"]]); no_int = sum(1 for r in rows if not kf[r["name"]])
    yes_int = sum(1 for r in rows if kf[r["name"]]); yes_int_obs = len(with_int)
    print(f"video level: P(OBSERVED | interval) = {yes_int_obs}/{yes_int} = {yes_int_obs/max(yes_int,1):.3f};  P(OBSERVED | no interval) = {no_int_obs}/{no_int} = {no_int_obs/max(no_int,1):.3f}")
    byview = {}
    for r in with_int:
        t = float(r["kf_peak_s"]); inside = any(s - a.tol <= t <= e + a.tol for s, e in kf[r["name"]])
        k = r["view_kind"] or "unknown"; byview.setdefault(k, [0, 0]); byview[k][0] += inside; byview[k][1] += 1
    print("by view:", {k: f"{h}/{n}={h/n:.2f}" for k, (h, n) in sorted(byview.items())})

    # ---- 2. interval-derived degree labels vs PostureV1's probability
    print("\n## 2. PostureV1 stored probability vs interval-derived labels (validation split; train shown as in-sample)")
    def frac(name):
        return min(1.0, sum(e - s for s, e in kf[name]) / dur[name]) if name in dur and dur[name] > 0 else None
    def longest(name):
        return max((e - s for s, e in kf[name]), default=0.0)
    defs = {
        "presence: any knees_forward interval": lambda n: int(bool(kf[n])),
        "presence: forward OR inward interval (the corpus posture flag)": lambda n: int(bool(kf[n]) or bool(ki.get(n))),
        "degree: fraction of clip in error >= 0.5": lambda n: (None if frac(n) is None else int(frac(n) >= 0.5)),
        "degree: fraction of clip in error >= 0.35": lambda n: (None if frac(n) is None else int(frac(n) >= 0.35)),
        "degree: longest interval >= 1.5 s": lambda n: int(longest(n) >= 1.5),
        "degree: longest interval >= 2.0 s": lambda n: int(longest(n) >= 2.0),
        "degree: total error time >= 2.0 s": lambda n: int(sum(e - s for s, e in kf[n]) >= 2.0),
    }
    for split_name in ("validation", "train"):
        sub = [r for r in rows if split.get(r["name"]) == split_name and r["pv1_prob"]]
        print(f"\n### {split_name} (n judged = {len(sub)})" + ("  -- IN-SAMPLE for the incumbent" if split_name == "train" else ""))
        print("| label definition | n | prevalence | AUROC [95% CI] | all-positive F1 floor |"); print("|---|---|---|---|---|")
        for label, fn in defs.items():
            pairs = [(fn(r["name"]), float(r["pv1_prob"])) for r in sub]; pairs = [(y, p) for y, p in pairs if y is not None]
            if len(pairs) < 20: print(f"| {label} | {len(pairs)} | — | too few | — |"); continue
            y = np.asarray([p[0] for p in pairs]); p = np.asarray([p[1] for p in pairs])
            if y.min() == y.max(): print(f"| {label} | {len(y)} | {y.mean():.3f} | single class | — |"); continue
            lo, hi = bootstrap_ci(y, p, 0.525, metric="auroc", n=2000, seed=0); fl = trivial_floor(y)
            floor = fl.get("f1_all_positive", fl.get("all_positive_f1", next(iter(fl.values()))))
            print(f"| {label} | {len(y)} | {y.mean():.3f} | {auroc(y, p):.4f} [{lo:.4f}, {hi:.4f}] | {float(floor):.3f} |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
