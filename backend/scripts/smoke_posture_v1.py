#!/usr/bin/env python3
"""
Smoke test for PostureV1 model inference pipeline.

Can run with synthetic data (default) or a real pose fixture file.

Usage:
    cd backend && python scripts/smoke_posture_v1.py
    cd backend && python scripts/smoke_posture_v1.py --pose-fixture tests/fixtures/pose_data/45959_1_posture_fault.json.gz
"""

import argparse
import gzip
import json
import sys
import time
from pathlib import Path

# Ensure backend is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.config import Settings
from app.ml.posture_v1.loader import PostureV1TorchLoader


def _make_landmark(x: float = 0.5, y: float = 0.5, z: float = 0.0) -> dict:
    return {"x": x, "y": y, "z": z, "visibility": 0.95}


def _make_frame(offset: float = 0.0) -> list:
    return [_make_landmark(x=0.3 + offset * 0.001, y=0.5 + i * 0.01)
            for i in range(33)]


def _make_pose_data(n_frames: int) -> list:
    return [_make_frame(offset=float(i)) for i in range(n_frames)]


def _load_fixture(path: str) -> list:
    """Load pose fixture — supports .json.gz and .json."""
    p = Path(path)
    if p.suffix == ".gz":
        with gzip.open(p, "rt", encoding="utf-8") as f:
            return json.load(f)
    else:
        with open(p, "r") as f:
            return json.load(f)


def _health_check(loader: PostureV1TorchLoader) -> bool:
    """Verify artifacts exist, model loads, scaler loads."""
    print("\n--- Health Check ---")
    artifacts_dir = loader._artifacts_dir
    model_path = artifacts_dir / "posture_v1.pt"
    scaler_path = artifacts_dir / "posture_v1_scaler.joblib"
    manifest_path = artifacts_dir / "posture_v1_manifest.json"

    checks = {
        "artifacts_dir exists": artifacts_dir.exists(),
        "posture_v1.pt exists": model_path.exists(),
        "posture_v1_scaler.joblib exists": scaler_path.exists(),
        "posture_v1_manifest.json exists": manifest_path.exists(),
    }

    for check, ok in checks.items():
        status = "OK" if ok else "MISSING"
        print(f"  [{status}] {check}")

    # Try loading
    meta = loader.get_metadata()
    model_ok = meta["model_available"]
    print(f"  [{'OK' if model_ok else 'FAIL'}] Model loads successfully")
    print(f"  Version: {meta['model_version']}")
    print(f"  Threshold: {meta['threshold']}")
    print(f"  Feature dim: {meta['feature_dim']}")

    # Check scaler
    mean, scale = loader.get_scaler_params()
    scaler_ok = mean is not None
    print(f"  [{'OK' if scaler_ok else 'FAIL'}] Scaler loads (mean shape={mean.shape if mean is not None else 'N/A'})")

    all_ok = all(checks.values()) and model_ok
    return all_ok


def _run_inference(loader: PostureV1TorchLoader, pose_data: list, label: str = ""):
    """Run inference and print detailed results."""
    n_frames = len(pose_data)
    n_none = sum(1 for f in pose_data if f is None)
    label_str = f" [{label}]" if label else ""

    print(f"\n--- {n_frames} frames{label_str} (missing: {n_none}) ---")

    t0 = time.monotonic()
    result = loader.predict_posture(pose_data)
    elapsed = (time.monotonic() - t0) * 1000

    print(f"  prob_fault:  {result['prob_fault']:.4f}")
    print(f"  decision:    {result['decision']}")
    print(f"  confidence:  {result['confidence']:.4f}")
    print(f"  quality_ok:  {result['quality_ok']}")
    print(f"  quality_flags: {result['quality_flags']}")
    print(f"  latency:     {elapsed:.1f}ms (total) / {result['latency_ms']:.1f}ms (internal)")

    prep = result["preprocessing"]
    print(f"  preprocessing:")
    print(f"    original_frames:    {prep['original_frames']}")
    print(f"    valid_frames:       {prep['valid_frames']}")
    print(f"    sequence_length:    {prep['sequence_length']}")
    print(f"    frames_interpolated: {prep['frames_interpolated']}")
    print(f"    frames_padded:      {prep['frames_padded']}")
    print(f"    frames_truncated:   {prep['frames_truncated']}")
    if prep['original_frames'] > 0:
        missing_pct = (1.0 - prep['valid_frames'] / prep['original_frames']) * 100
        print(f"    missing_frame_pct:  {missing_pct:.1f}%")

    if "reason" in result:
        print(f"  reason:      {result['reason']}")

    return result


def main():
    parser = argparse.ArgumentParser(description="PostureV1 Smoke Test")
    parser.add_argument(
        "--pose-fixture",
        type=str,
        default=None,
        help="Path to a pose fixture file (.json or .json.gz) to use instead of synthetic data",
    )
    parser.add_argument(
        "--no-synthetic",
        action="store_true",
        help="Skip synthetic data tests (only run fixture if provided)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("PostureV1 Smoke Test")
    print("=" * 60)

    settings = Settings()
    loader = PostureV1TorchLoader(settings)

    # Health check
    healthy = _health_check(loader)
    if not healthy:
        print("\nWARNING: Health check found issues. Continuing anyway...")

    if not loader.is_available():
        print("\nERROR: Model not available. Place posture_v1.pt in artifacts/")
        sys.exit(1)

    # Run on fixture if provided
    if args.pose_fixture:
        print(f"\n--- Loading fixture: {args.pose_fixture} ---")
        pose_data = _load_fixture(args.pose_fixture)
        fixture_name = Path(args.pose_fixture).stem.replace(".json", "")
        _run_inference(loader, pose_data, label=fixture_name)

    # Run on synthetic data (unless --no-synthetic)
    if not args.no_synthetic:
        for n_frames in [50, 200, 300]:
            pose_data = _make_pose_data(n_frames)
            _run_inference(loader, pose_data, label=f"synthetic-{n_frames}")

    print("\n" + "=" * 60)
    print("SMOKE TEST PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
