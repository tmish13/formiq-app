#!/usr/bin/env python3
"""
Evaluate PostureV1 model on all in_domain_accuracy fixtures.

Loads fixtures from in_domain_accuracy/manifest.json, runs inference,
computes aggregate metrics (P/R/F1/F0.5) treating posture_fault as positive class.

Outputs:
  - Console table summary
  - JSON report at backend/scripts/output/posture_v1_fixture_eval.json

Usage:
    cd backend && python scripts/eval_posture_v1_fixtures.py
"""

import gzip
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np

# Ensure backend is on sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.ml.posture_v1.loader import PostureV1TorchLoader, DEFAULT_FAULT_THRESHOLD
from app.ml.posture_v1.preprocess import preprocess_pose_data
from app.ml.posture_v1.features_151d import compute_151d_features, EXPECTED_DIM

FIXTURE_DIR = BACKEND_DIR / "tests" / "fixtures" / "pose_data" / "in_domain_accuracy"
OUTPUT_DIR = BACKEND_DIR / "scripts" / "output"


def load_fixture(directory: Path, name: str) -> list:
    path = directory / f"{name}.json.gz"
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def compute_metrics(tp: int, fp: int, fn: int, tn: int) -> dict:
    """Compute P/R/F1/F0.5/accuracy from confusion matrix counts."""
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    f05 = (1.25 * precision * recall) / (0.25 * precision + recall) if (0.25 * precision + recall) > 0 else 0.0
    accuracy = (tp + tn) / (tp + fp + fn + tn) if (tp + fp + fn + tn) > 0 else 0.0
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "f0.5": round(f05, 4),
        "accuracy": round(accuracy, 4),
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
    }


def main():
    # Load manifest
    manifest_path = FIXTURE_DIR / "manifest.json"
    if not manifest_path.exists():
        print(f"ERROR: manifest not found at {manifest_path}")
        sys.exit(1)

    with open(manifest_path) as f:
        manifest = json.load(f)

    print(f"Loaded {len(manifest)} fixtures from {FIXTURE_DIR}")

    # Check model
    artifacts_dir = BACKEND_DIR / "app" / "ml" / "posture_v1" / "artifacts"
    model_path = artifacts_dir / "posture_v1.pt"
    if not model_path.exists():
        print(f"ERROR: posture_v1.pt not found at {model_path}")
        sys.exit(1)

    # Initialize loader
    settings = MagicMock()
    settings.USE_POSTURE_V1 = True
    loader = PostureV1TorchLoader(settings)

    threshold = loader._fault_threshold if hasattr(loader, '_fault_threshold') else DEFAULT_FAULT_THRESHOLD

    # Run inference on all fixtures
    results = []
    for name, meta in manifest.items():
        fixture_path = FIXTURE_DIR / f"{name}.json.gz"
        if not fixture_path.exists():
            print(f"  SKIP: {name} — fixture file not found")
            continue

        pose_data = load_fixture(FIXTURE_DIR, name)
        result = loader.predict_posture(pose_data)

        entry = {
            "name": name,
            "label": meta["label"],
            "frames": meta["frames"],
            "prob_fault": result["prob_fault"],
            "decision": result["decision"],
            "confidence": result["confidence"],
            "quality_ok": result["quality_ok"],
            "quality_flags": result.get("quality_flags", []),
            "sequence_length": result["preprocessing"]["sequence_length"],
        }
        results.append(entry)

    # Compute confusion matrix (posture_fault = positive class)
    # "positive" = posture_fault label, "predicted positive" = decision == "fault"
    tp = fp = fn = tn = 0
    n_uncertain = 0
    good_probs = []
    fault_probs = []
    depth_probs = []

    for r in results:
        label = r["label"]
        decision = r["decision"]
        prob = r["prob_fault"]

        if label == "good_form":
            good_probs.append(prob)
        elif label == "posture_fault":
            fault_probs.append(prob)
        elif label == "depth_fault":
            depth_probs.append(prob)

        if decision == "uncertain":
            n_uncertain += 1
            continue

        is_positive = label == "posture_fault"
        pred_positive = decision == "fault"

        if is_positive and pred_positive:
            tp += 1
        elif not is_positive and pred_positive:
            fp += 1
        elif is_positive and not pred_positive:
            fn += 1
        else:
            tn += 1

    metrics = compute_metrics(tp, fp, fn, tn)
    metrics["n_uncertain"] = n_uncertain
    metrics["threshold"] = threshold

    # Percentage-based metrics
    pct_fault_correct = (
        sum(1 for p in fault_probs if p >= threshold) / len(fault_probs) * 100
        if fault_probs else 0.0
    )
    pct_good_correct = (
        sum(1 for p in good_probs if p < threshold) / len(good_probs) * 100
        if good_probs else 0.0
    )
    pct_depth_as_fault = (
        sum(1 for p in depth_probs if p >= threshold) / len(depth_probs) * 100
        if depth_probs else 0.0
    )

    # Print table
    print()
    print("=" * 85)
    print("POSTURE V1 FIXTURE EVALUATION")
    print("=" * 85)
    print(f"{'Name':<40s} {'Label':<18s} {'Prob':>6s} {'Decision':<12s} {'Conf':>5s}")
    print("-" * 85)
    for r in results:
        print(
            f"{r['name']:<40s} {r['label']:<18s} {r['prob_fault']:>6.3f} "
            f"{r['decision']:<12s} {r['confidence']:>5.3f}"
        )
    print("-" * 85)

    # Group summaries
    print()
    if good_probs:
        print(f"  good_form     ({len(good_probs):>2d}): mean_prob={np.mean(good_probs):.4f}  "
              f"correct={pct_good_correct:.0f}% ({sum(1 for p in good_probs if p < threshold)}/{len(good_probs)})")
    if fault_probs:
        print(f"  posture_fault ({len(fault_probs):>2d}): mean_prob={np.mean(fault_probs):.4f}  "
              f"correct={pct_fault_correct:.0f}% ({sum(1 for p in fault_probs if p >= threshold)}/{len(fault_probs)})")
    if depth_probs:
        print(f"  depth_fault   ({len(depth_probs):>2d}): mean_prob={np.mean(depth_probs):.4f}  "
              f"as_fault={pct_depth_as_fault:.0f}% ({sum(1 for p in depth_probs if p >= threshold)}/{len(depth_probs)})")

    # Metrics
    print()
    print(f"  Threshold:   {threshold}")
    print(f"  Precision:   {metrics['precision']:.4f}")
    print(f"  Recall:      {metrics['recall']:.4f}")
    print(f"  F1:          {metrics['f1']:.4f}")
    print(f"  F0.5:        {metrics['f0.5']:.4f}")
    print(f"  Accuracy:    {metrics['accuracy']:.4f}")
    print(f"  Uncertain:   {n_uncertain}")
    print(f"  TP={tp} FP={fp} FN={fn} TN={tn}")
    print("=" * 85)

    # Save JSON report
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report = {
        "threshold": threshold,
        "metrics": metrics,
        "group_summary": {
            "good_form": {
                "count": len(good_probs),
                "mean_prob": round(float(np.mean(good_probs)), 4) if good_probs else None,
                "pct_correct": round(pct_good_correct, 1),
            },
            "posture_fault": {
                "count": len(fault_probs),
                "mean_prob": round(float(np.mean(fault_probs)), 4) if fault_probs else None,
                "pct_correct": round(pct_fault_correct, 1),
            },
            "depth_fault": {
                "count": len(depth_probs),
                "mean_prob": round(float(np.mean(depth_probs)), 4) if depth_probs else None,
                "pct_as_fault": round(pct_depth_as_fault, 1),
            },
        },
        "per_fixture": results,
    }

    output_path = OUTPUT_DIR / "posture_v1_fixture_eval.json"
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport saved to {output_path}")


if __name__ == "__main__":
    main()
