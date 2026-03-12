#!/usr/bin/env python3
"""
Distribution drift report for PostureV1 model.

Loads all in-domain fixtures and runs the full pipeline:
  preprocess -> features_151d -> scaler transform -> inference

For each fixture, reports:
  - sequence_length, missing_frame_ratio
  - per-angle invalid frame percentages
  - scaled feature outlier counts (|z|>3, |z|>6)
  - top 10 outlier features by |z|
  - probability output, decision, confidence

Also computes aggregate stats:
  - mean/std of each feature pre-scale and post-scale
  - comparison to scaler.mean_ / scaler.scale_

Outputs:
  - Readable report to stdout
  - JSON report to scripts/output/posture_v1_distribution_report.json

Usage:
    cd backend && python scripts/debug_posture_v1_distribution.py
"""

import gzip
import json
import sys
from pathlib import Path

# Ensure backend is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

import numpy as np
from app.core.config import Settings
from app.ml.posture_v1.preprocess import preprocess_pose_data
from app.ml.posture_v1.features_151d import (
    compute_151d_features,
    compute_angle_validity,
    compute_outlier_counts,
    FEATURE_NAMES,
    EXPECTED_DIM,
)
from app.ml.posture_v1.loader import PostureV1TorchLoader


# ---------------------------------------------------------------------------
# Fixture loading
# ---------------------------------------------------------------------------

IN_DOMAIN_DIR = backend_dir / "tests" / "fixtures" / "pose_data" / "in_domain_accuracy"


def _load_manifest() -> dict:
    manifest_path = IN_DOMAIN_DIR / "manifest.json"
    with open(manifest_path, "r") as f:
        return json.load(f)


def _load_fixture(name: str) -> list:
    path = IN_DOMAIN_DIR / f"{name}.json.gz"
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Per-fixture analysis
# ---------------------------------------------------------------------------

def analyze_fixture(
    name: str,
    meta: dict,
    loader: PostureV1TorchLoader,
) -> dict:
    """Run full pipeline on one fixture, return detailed report dict."""
    pose_data = _load_fixture(name)

    # Preprocess
    prep = preprocess_pose_data(pose_data)
    kp = prep.keypoints
    T = prep.sequence_length

    # Missing frame ratio
    if prep.original_frame_count > 0:
        missing_ratio = 1.0 - prep.valid_frame_count / prep.original_frame_count
    else:
        missing_ratio = 1.0

    # Angle validity
    angle_validity = compute_angle_validity(kp)
    angle_invalid_pct = {
        k: round((1.0 - v) * 100, 1) for k, v in angle_validity.items()
    }

    # Features: raw and scaled
    raw_features = compute_151d_features(kp, apply_scaler=False)
    scaled_features = compute_151d_features(kp, apply_scaler=True)

    # Outlier counts
    outliers = compute_outlier_counts(scaled_features)
    n_z3 = outliers["count_z3"]
    n_z6 = outliers["count_z6"]

    # Top 10 outliers by |z|
    abs_z = np.abs(scaled_features)
    top10_idx = np.argsort(abs_z)[-10:][::-1]
    top10 = []
    for idx in top10_idx:
        top10.append({
            "index": int(idx),
            "name": FEATURE_NAMES[idx],
            "raw_value": round(float(raw_features[idx]), 6),
            "z_value": round(float(scaled_features[idx]), 4),
        })

    # Full inference
    result = loader.predict_posture(pose_data)

    return {
        "name": name,
        "label": meta["label"],
        "source": meta.get("source", "unknown"),
        "sequence_length": T,
        "original_frames": prep.original_frame_count,
        "valid_frames": prep.valid_frame_count,
        "missing_frame_ratio": round(missing_ratio, 4),
        "angle_invalid_pct": angle_invalid_pct,
        "angle_validity_raw": {k: round(v, 4) for k, v in angle_validity.items()},
        "count_outliers_z3": n_z3,
        "count_outliers_z6": n_z6,
        "top10_outlier_features": top10,
        "prob_fault": result["prob_fault"],
        "decision": result["decision"],
        "confidence": result["confidence"],
        "quality_flags": result["quality_flags"],
        "quality_ok": result["quality_ok"],
        "raw_features_summary": {
            "min": round(float(raw_features.min()), 6),
            "max": round(float(raw_features.max()), 6),
            "mean": round(float(raw_features.mean()), 6),
        },
        "scaled_features_summary": {
            "min": round(float(scaled_features.min()), 4),
            "max": round(float(scaled_features.max()), 4),
            "mean": round(float(scaled_features.mean()), 4),
        },
    }


# ---------------------------------------------------------------------------
# Aggregate analysis
# ---------------------------------------------------------------------------

def aggregate_analysis(
    fixture_reports: list,
    loader: PostureV1TorchLoader,
) -> dict:
    """Compute aggregate feature stats across all fixtures + compare to scaler."""
    all_raw = []
    all_scaled = []

    for report in fixture_reports:
        name = report["name"]
        pose_data = _load_fixture(name)
        prep = preprocess_pose_data(pose_data)
        raw = compute_151d_features(prep.keypoints, apply_scaler=False)
        scaled = compute_151d_features(prep.keypoints, apply_scaler=True)
        all_raw.append(raw)
        all_scaled.append(scaled)

    raw_matrix = np.array(all_raw)      # [N, 151]
    scaled_matrix = np.array(all_scaled)  # [N, 151]

    # Per-feature stats across fixtures
    raw_mean = raw_matrix.mean(axis=0)
    raw_std = raw_matrix.std(axis=0)
    scaled_mean = scaled_matrix.mean(axis=0)
    scaled_std = scaled_matrix.std(axis=0)

    # Compare to scaler expectations
    scaler_mean, scaler_scale = loader.get_scaler_params()
    if scaler_mean is not None:
        # avg |z-score| of our fixture means vs scaler means
        deviation = np.abs(raw_mean - scaler_mean) / np.maximum(scaler_scale, 1e-8)
        avg_abs_z = float(deviation.mean())
        max_abs_z = float(deviation.max())
        worst_feature_idx = int(deviation.argmax())
    else:
        avg_abs_z = None
        max_abs_z = None
        worst_feature_idx = None

    return {
        "n_fixtures": len(fixture_reports),
        "raw_feature_stats": {
            "global_mean": round(float(raw_mean.mean()), 6),
            "global_std": round(float(raw_std.mean()), 6),
        },
        "scaled_feature_stats": {
            "global_mean": round(float(scaled_mean.mean()), 4),
            "global_std": round(float(scaled_std.mean()), 4),
        },
        "scaler_drift": {
            "avg_abs_z_deviation": round(avg_abs_z, 4) if avg_abs_z is not None else None,
            "max_abs_z_deviation": round(max_abs_z, 4) if max_abs_z is not None else None,
            "worst_feature": {
                "index": worst_feature_idx,
                "name": FEATURE_NAMES[worst_feature_idx] if worst_feature_idx is not None else None,
                "z_deviation": round(float(deviation[worst_feature_idx]), 4) if worst_feature_idx is not None else None,
            } if worst_feature_idx is not None else None,
        },
    }


# ---------------------------------------------------------------------------
# Report printing
# ---------------------------------------------------------------------------

def print_report(fixture_reports: list, agg: dict):
    """Print human-readable report to stdout."""
    print("=" * 90)
    print("POSTURE V1 DISTRIBUTION DRIFT REPORT")
    print("=" * 90)

    for r in fixture_reports:
        print(f"\n--- {r['name']} ({r['label']}) ---")
        print(f"  source: {r['source']}")
        print(f"  sequence_length: {r['sequence_length']}")
        print(f"  missing_frame_ratio: {r['missing_frame_ratio']:.2%}")
        print(f"  angle invalid %: {r['angle_invalid_pct']}")
        print(f"  outliers |z|>3: {r['count_outliers_z3']}  |z|>6: {r['count_outliers_z6']}")
        print(f"  prob_fault: {r['prob_fault']:.6f}  decision: {r['decision']}  confidence: {r['confidence']:.4f}")
        print(f"  quality_flags: {r['quality_flags']}")
        print(f"  raw range: [{r['raw_features_summary']['min']:.4f}, {r['raw_features_summary']['max']:.4f}]")
        print(f"  scaled range: [{r['scaled_features_summary']['min']:.4f}, {r['scaled_features_summary']['max']:.4f}]")
        print(f"  top 10 outlier features:")
        for f in r["top10_outlier_features"]:
            print(f"    [{f['index']:3d}] {f['name']:40s} raw={f['raw_value']:>10.4f}  z={f['z_value']:>8.4f}")

    print(f"\n{'=' * 90}")
    print("AGGREGATE STATISTICS")
    print(f"{'=' * 90}")
    print(f"  fixtures analyzed: {agg['n_fixtures']}")
    print(f"  raw features:   mean={agg['raw_feature_stats']['global_mean']:.4f}  std={agg['raw_feature_stats']['global_std']:.4f}")
    print(f"  scaled features: mean={agg['scaled_feature_stats']['global_mean']:.4f}  std={agg['scaled_feature_stats']['global_std']:.4f}")

    drift = agg["scaler_drift"]
    if drift["avg_abs_z_deviation"] is not None:
        print(f"\n  SCALER DRIFT:")
        print(f"    avg |z| deviation of fixture means from scaler means: {drift['avg_abs_z_deviation']:.4f}")
        print(f"    max |z| deviation: {drift['max_abs_z_deviation']:.4f}")
        if drift["worst_feature"]:
            wf = drift["worst_feature"]
            print(f"    worst feature: [{wf['index']}] {wf['name']} (z={wf['z_deviation']:.4f})")
    else:
        print(f"\n  SCALER: not loaded, cannot compute drift")

    print(f"\n{'=' * 90}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Loading model and fixtures...")
    settings = Settings()
    loader = PostureV1TorchLoader(settings)

    if not loader.is_available():
        print("ERROR: PostureV1 model not available. Place artifacts in posture_v1/artifacts/")
        sys.exit(1)

    manifest = _load_manifest()
    if not manifest:
        print("ERROR: No in-domain manifest found at", IN_DOMAIN_DIR / "manifest.json")
        sys.exit(1)

    # Analyze each fixture
    fixture_reports = []
    for name, meta in manifest.items():
        report = analyze_fixture(name, meta, loader)
        fixture_reports.append(report)

    # Aggregate
    agg = aggregate_analysis(fixture_reports, loader)

    # Print
    print_report(fixture_reports, agg)

    # Save JSON
    output_dir = backend_dir / "scripts" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "posture_v1_distribution_report.json"

    full_report = {
        "fixtures": fixture_reports,
        "aggregate": agg,
    }
    with open(output_path, "w") as f:
        json.dump(full_report, f, indent=2, default=str)

    print(f"\nJSON report saved to: {output_path}")


if __name__ == "__main__":
    main()
