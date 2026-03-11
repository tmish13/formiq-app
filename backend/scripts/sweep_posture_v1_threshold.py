#!/usr/bin/env python3
"""
Threshold sweep for PostureV1 model on in-domain fixtures.

Runs inference on all in-domain fixtures and evaluates classification
metrics at thresholds from 0.2 to 0.8.

Reports Precision, Recall, F0.5 at each threshold.
F0.5 weights precision over recall (better for production where
false positives — incorrectly flagging good form — are costly).

Usage:
    cd backend && python scripts/sweep_posture_v1_threshold.py
"""

import gzip
import json
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

import numpy as np
from unittest.mock import MagicMock
from app.ml.posture_v1.loader import PostureV1TorchLoader, DEFAULT_FAULT_THRESHOLD

IN_DOMAIN_DIR = backend_dir / "tests" / "fixtures" / "pose_data" / "in_domain_accuracy"


def _load_manifest() -> dict:
    with open(IN_DOMAIN_DIR / "manifest.json", "r") as f:
        return json.load(f)


def _load_fixture(name: str) -> list:
    with gzip.open(IN_DOMAIN_DIR / f"{name}.json.gz", "rt") as f:
        return json.load(f)


def _is_positive(label: str) -> bool:
    """Positive = posture_fault (what the model is trained to detect)."""
    return label == "posture_fault"


def fbeta_score(precision: float, recall: float, beta: float = 0.5) -> float:
    """Compute F-beta score. beta < 1 weights precision more."""
    if precision + recall == 0:
        return 0.0
    beta_sq = beta ** 2
    return (1 + beta_sq) * (precision * recall) / (beta_sq * precision + recall)


def main():
    print("=" * 70)
    print("PostureV1 Threshold Sweep (In-Domain Fixtures)")
    print("=" * 70)

    settings = MagicMock()
    settings.USE_POSTURE_V1 = True
    loader = PostureV1TorchLoader(settings)

    if not loader.is_available():
        print("ERROR: PostureV1 model not available")
        sys.exit(1)

    manifest = _load_manifest()

    # Collect prob_fault and ground truth for each fixture
    samples = []
    print("\n--- Fixture Inference ---")
    for name, meta in manifest.items():
        pose_data = _load_fixture(name)
        result = loader.predict_posture(pose_data)
        prob = result["prob_fault"]
        label = meta["label"]
        decision = result["decision"]
        is_pos = _is_positive(label)

        # Note: gate-blocked fixtures get prob=0.5 decision=uncertain
        # We still include them in sweep — gate overrides threshold anyway
        samples.append({
            "name": name,
            "label": label,
            "is_positive": is_pos,
            "prob_fault": prob,
            "decision": decision,
            "gated": decision == "uncertain" and "gate" in str(result.get("reason", "")),
        })
        marker = "POS" if is_pos else "NEG"
        print(f"  {name:35s} [{marker}] label={label:20s} prob={prob:.6f} decision={decision}")

    n_pos = sum(1 for s in samples if s["is_positive"])
    n_neg = sum(1 for s in samples if not s["is_positive"])
    print(f"\n  Total: {len(samples)} fixtures ({n_pos} positive=posture_fault, {n_neg} negative)")

    # Also show depth_fault and good_form separately
    depth_faults = [s for s in samples if s["label"] == "depth_fault"]
    if depth_faults:
        print(f"  Note: {len(depth_faults)} depth_fault fixtures treated as NEGATIVE (model is posture-specific)")

    # Sweep
    thresholds = np.arange(0.20, 0.81, 0.05)
    print(f"\n{'Threshold':>10s} {'TP':>4s} {'FP':>4s} {'TN':>4s} {'FN':>4s} {'Prec':>7s} {'Recall':>7s} {'F0.5':>7s} {'Acc':>7s}")
    print("-" * 70)

    best_f05 = -1
    best_threshold = DEFAULT_FAULT_THRESHOLD
    results = []

    for threshold in thresholds:
        tp = fp = tn = fn = 0
        for s in samples:
            predicted_fault = s["prob_fault"] >= threshold
            if s["is_positive"] and predicted_fault:
                tp += 1
            elif s["is_positive"] and not predicted_fault:
                fn += 1
            elif not s["is_positive"] and predicted_fault:
                fp += 1
            else:
                tn += 1

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f05 = fbeta_score(precision, recall, beta=0.5)
        accuracy = (tp + tn) / len(samples) if samples else 0.0

        marker = " <-- default" if abs(threshold - DEFAULT_FAULT_THRESHOLD) < 0.01 else ""
        if f05 > best_f05:
            best_f05 = f05
            best_threshold = threshold

        print(f"  {threshold:>7.3f}   {tp:>4d} {fp:>4d} {tn:>4d} {fn:>4d} {precision:>7.3f} {recall:>7.3f} {f05:>7.3f} {accuracy:>7.3f}{marker}")

        results.append({
            "threshold": round(float(threshold), 3),
            "tp": tp, "fp": fp, "tn": tn, "fn": fn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f05": round(f05, 4),
            "accuracy": round(accuracy, 4),
        })

    print("-" * 70)
    print(f"\n  Current default threshold: {DEFAULT_FAULT_THRESHOLD}")
    print(f"  Best F0.5 threshold:      {best_threshold:.3f} (F0.5={best_f05:.4f})")

    if abs(best_threshold - DEFAULT_FAULT_THRESHOLD) > 0.05:
        print(f"\n  NOTE: Best threshold differs from default by {abs(best_threshold - DEFAULT_FAULT_THRESHOLD):.3f}")
        print(f"  Consider setting POSTURE_V1_THRESHOLD={best_threshold:.3f}")
    else:
        print(f"\n  Default threshold is near-optimal. No change recommended.")

    print("\n  IMPORTANT: These metrics are on {n} fixtures only.".format(n=len(samples)))
    print("  Do NOT change production threshold based solely on this sweep.")
    print("  Use a larger validation set before adjusting.")

    # Save results
    output_dir = backend_dir / "scripts" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "posture_v1_threshold_sweep.json"
    with open(output_path, "w") as f:
        json.dump({
            "samples": samples,
            "sweep_results": results,
            "default_threshold": DEFAULT_FAULT_THRESHOLD,
            "best_f05_threshold": round(float(best_threshold), 3),
            "best_f05": round(best_f05, 4),
        }, f, indent=2)
    print(f"\n  Results saved to: {output_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
