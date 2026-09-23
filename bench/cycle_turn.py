#!/usr/bin/env python3
"""One complete turn of the evaluation cycle, on stored decisions only.

THE POINT OF THIS SCRIPT IS THAT IT RUNS NO INFERENCE.

Gate 1 pushed 300 videos through the live pipeline and `checker_decisions`
recorded each one's `prob`. A threshold is applied to that probability, so
changing the threshold and re-measuring is a QUERY -- seconds -- not another
26 minutes of pose extraction and model loading. That is what the audit trail
buys, and until now nothing had demonstrated it.

THE TURN
--------
  1. gap analysis on train+validation: where do the errors concentrate?
  2. choose a threshold on VALIDATION ONLY
  3. apply it to TEST ONCE, against the incumbent 0.525
  4. paired bootstrap on the delta -- same videos, two thresholds, so the
     comparison is of thresholds and not of samples

DISCIPLINE
----------
Test is read once, at step 3, and the script refuses to let the sweep see it.
The incumbent and the candidate are scored on the SAME test videos. Every
number is reported against the trivial floor, because at 34% prevalence an
F1 that beats nothing still looks respectable.

HONESTY ABOUT n
---------------
41 validation and 51 test videos. That is thin for selecting a threshold and
the confidence intervals will say so. This is a demonstration that the cycle
CLOSES, with real numbers, not a claim that the chosen threshold is good.

    python bench/cycle_turn.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Tuple

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "backend"))

COMPOSE = REPO / "backend" / "deployment" / "docker-compose.yml"
SPLITS = REPO / "bench" / "results" / "content_level_splits.json"
OUT = REPO / "bench" / "results" / "cycle_turn.json"

INCUMBENT = 0.525
POSITIVE_TARGET = "posture_fault"


def _psql(sql: str) -> str:
    return subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE), "exec", "-T", "db",
         "psql", "-U", "postgres", "-d", "formiq", "-tAF|", "-c", sql],
        capture_output=True, text=True).stdout


def _load() -> Tuple[Dict[str, List[dict]], Counter]:
    from app.eval.labels import resolve_all

    built = json.loads(SPLITS.read_text())
    split_of = {r["content_hash"]: r["split"] for r in built["videos"]
                if r["content_hash"] and r["split"]}

    probs: Dict[str, float] = {}
    for ln in _psql("SELECT content_hash, prob FROM checker_decisions "
                    "WHERE checker_name='posture_v1' AND prob IS NOT NULL;"
                    ).strip().splitlines():
        p = ln.split("|")
        if len(p) == 2:
            probs[p[0]] = float(p[1])

    class _Row:
        __slots__ = ("content_hash", "target", "value", "usable", "source",
                     "source_ref", "trust", "labeled_at")

    labels = []
    for ln in _psql(
            "SELECT content_hash, target, value, usable, source, source_ref, "
            f"trust FROM labels WHERE target='{POSITIVE_TARGET}';"
    ).strip().splitlines():
        p = ln.split("|")
        if len(p) != 7:
            continue
        r = _Row()
        (r.content_hash, r.target, r.value, r.usable, r.source, r.source_ref,
         r.trust) = (p[0], p[1], (None if p[2] == "" else int(p[2])),
                     p[3] == "t", p[4], p[5], float(p[6] or 0))
        r.labeled_at = None
        labels.append(r)

    resolved = resolve_all(labels, POSITIVE_TARGET)

    by_split: Dict[str, List[dict]] = {"train": [], "validation": [], "test": []}
    skipped = Counter()
    for h, prob in probs.items():
        s = split_of.get(h)
        if s is None:
            skipped["not_in_content_split"] += 1
            continue
        lab = resolved.get(h)
        if lab is None or not lab.usable or lab.value is None:
            skipped["no_usable_label"] += 1
            continue
        if lab.disputed:
            skipped["disputed_label"] += 1
            continue
        by_split[s].append({"hash": h, "prob": prob, "y": int(lab.value)})
    return by_split, skipped


def _score(rows: List[dict], thr: float) -> dict:
    from app.eval.metrics import counts, precision_recall_f1, trivial_floor
    y = [r["y"] for r in rows]
    pred = [int(r["prob"] >= thr) for r in rows]
    c = counts(y, pred)
    p, rc, f = precision_recall_f1(c)
    fl = trivial_floor(y)
    return {"threshold": thr, "n": len(rows), "precision": p, "recall": rc,
            "f1": f, "accuracy": (c.tp + c.tn) / c.n if c.n else 0.0,
            "counts": c.as_dict(), "floor_f1": fl["all_positive_f1"],
            "majority_acc": fl["majority_class_accuracy"],
            "prevalence": fl["prevalence"]}


def main() -> int:
    import numpy as np
    from app.eval.metrics import counts, precision_recall_f1

    by_split, skipped = _load()
    n = {k: len(v) for k, v in by_split.items()}
    print("CYCLE TURN -- no inference is run; every probability is already stored")
    print("=" * 74)
    print(f"  usable decisions by split: {n}    skipped: {dict(skipped)}")
    if n["validation"] < 10 or n["test"] < 10:
        print("  too few decisions to turn the cycle; run bench/select_eval_batch.py "
              "and the Gate 1 batch first")
        return 1

    # ---- 1. gap analysis, train + validation only ---------------------------
    dev = by_split["train"] + by_split["validation"]
    base = _score(dev, INCUMBENT)
    print()
    print("1. GAP ANALYSIS  (train + validation, test untouched)")
    print("-" * 74)
    print(f"   n={base['n']}  prevalence {base['prevalence']:.3f}")
    print(f"   at the incumbent {INCUMBENT}: P {base['precision']:.4f}  "
          f"R {base['recall']:.4f}  F1 {base['f1']:.4f}  acc {base['accuracy']:.4f}")
    print(f"   counts {base['counts']}")
    print(f"   floor F1 {base['floor_f1']:.4f}   majority-class acc "
          f"{base['majority_acc']:.4f}")
    verdict = ("BELOW" if base["accuracy"] < base["majority_acc"] else "above")
    print(f"   -> accuracy is {verdict} the majority-class baseline")
    fp, fn = base["counts"]["fp"], base["counts"]["fn"]
    print(f"   -> the error is asymmetric: {fp} false positives vs {fn} false "
          f"negatives")
    print(f"      the model over-flags, so the lever is a HIGHER threshold")

    # ---- 2. sweep on validation ONLY ----------------------------------------
    val = by_split["validation"]
    grid = [round(x, 3) for x in np.arange(0.30, 0.96, 0.01)]
    swept = [_score(val, t) for t in grid]
    best_f1 = max(swept, key=lambda r: (r["f1"], r["threshold"]))
    # A precision-constrained alternative: the product only helps if a flag is
    # usually right, and 0.45 precision is not that.
    p_ok = [r for r in swept if r["precision"] >= 0.60 and r["counts"]["tp"] > 0]
    best_p = max(p_ok, key=lambda r: (r["f1"], r["threshold"])) if p_ok else None

    print()
    print("2. THRESHOLD SWEEP  (VALIDATION ONLY -- test is not read here)")
    print("-" * 74)
    print(f"   n={len(val)}  prevalence {swept[0]['prevalence']:.3f}")
    inc_val = _score(val, INCUMBENT)
    print(f"   incumbent {INCUMBENT}: F1 {inc_val['f1']:.4f}  "
          f"P {inc_val['precision']:.4f}  R {inc_val['recall']:.4f}")
    print(f"   best F1   {best_f1['threshold']}: F1 {best_f1['f1']:.4f}  "
          f"P {best_f1['precision']:.4f}  R {best_f1['recall']:.4f}")
    if best_p:
        print(f"   best F1 at P>=0.60  {best_p['threshold']}: "
              f"F1 {best_p['f1']:.4f}  P {best_p['precision']:.4f}  "
              f"R {best_p['recall']:.4f}")
    chosen = best_f1["threshold"]
    print(f"   -> CHOSEN: {chosen}  (selected on validation, n={len(val)} -- thin)")

    # ---- 3. test, once ------------------------------------------------------
    test = by_split["test"]
    inc_test = _score(test, INCUMBENT)
    new_test = _score(test, chosen)
    print()
    print("3. TEST  (read once, both thresholds on the SAME videos)")
    print("-" * 74)
    print(f"   n={len(test)}  prevalence {inc_test['prevalence']:.3f}  "
          f"floor F1 {inc_test['floor_f1']:.4f}  "
          f"majority acc {inc_test['majority_acc']:.4f}")
    for name, r in (("incumbent", inc_test), ("chosen  ", new_test)):
        print(f"   {name} {r['threshold']:<5}  F1 {r['f1']:.4f}  "
              f"P {r['precision']:.4f}  R {r['recall']:.4f}  "
              f"acc {r['accuracy']:.4f}  {r['counts']}")
    d_f1 = new_test["f1"] - inc_test["f1"]

    # ---- 4. paired bootstrap on the delta ------------------------------------
    rng = np.random.default_rng(0)
    y = np.array([r["y"] for r in test])
    pr = np.array([r["prob"] for r in test])
    deltas = []
    for _ in range(2000):
        idx = rng.integers(0, len(y), len(y))
        a = precision_recall_f1(counts(y[idx], (pr[idx] >= chosen).astype(int)))[2]
        b = precision_recall_f1(counts(y[idx], (pr[idx] >= INCUMBENT).astype(int)))[2]
        deltas.append(a - b)
    lo, hi = float(np.percentile(deltas, 2.5)), float(np.percentile(deltas, 97.5))
    spans = lo <= 0 <= hi
    print()
    print(f"   delta F1 {d_f1:+.4f}   95% CI [{lo:+.4f}, {hi:+.4f}]   "
          f"{'INCLUDES ZERO' if spans else 'excludes zero'}")
    print("   (paired: videos resampled once, both thresholds scored on the same draw)")

    print()
    print("4. WHAT THIS TURN COST")
    print("-" * 74)
    print("   inference runs: 0.  Every probability was already in")
    print("   checker_decisions from the Gate 1 batch. The same turn without a")
    print("   decision trail costs a re-run of the whole corpus -- ~26 minutes")
    print("   here, and it would have produced DIFFERENT keypoints (G-39: two")
    print("   MediaPipe passes moved 14.9% of verdicts), so the comparison")
    print("   would not have been of thresholds at all.")

    OUT.write_text(json.dumps({
        "incumbent": INCUMBENT, "chosen": chosen,
        "n": n, "skipped": dict(skipped),
        "gap_analysis_dev": base,
        "sweep_validation": swept,
        "test_incumbent": inc_test, "test_chosen": new_test,
        "delta_f1": d_f1, "delta_f1_ci95": [lo, hi],
        "ci_includes_zero": spans,
        "inference_runs": 0,
    }, indent=2))
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
