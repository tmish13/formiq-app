#!/usr/bin/env python3
"""
Convert ML-repo keypoint JSONs into app-format compressed fixtures.

Reads test-split videos from the ML repo's user_level_multilabel_splits.json,
converts keypoint data to app format, and saves as gzipped JSON fixtures.

ML repo format:
    [{"frame_index": N, "landmarks": [{x, y, z, visibility}, ...]}, ...]

App format (preprocess_pose_data input):
    List[List[Dict]]  — just the landmarks list per frame, no wrapper.

Output: gzipped JSON files + manifest.json in
    backend/tests/fixtures/pose_data/in_domain_accuracy/

Usage:
    cd backend && python scripts/convert_ml_fixtures.py
"""

import gzip
import json
import os
import sys
from pathlib import Path
# The notebook codebase that produced PostureV1 (backend/ml_training/README.md); override with FORMIQ_ML_DIR.
FORMIQ_ML_DIR = Path(os.environ.get("FORMIQ_ML_DIR", str(Path.home() / "FORMIQ Form Analysis Model")))

BACKEND_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BACKEND_DIR / "tests" / "fixtures" / "pose_data" / "in_domain_accuracy"

# Keypoint source directories
SQUAT_MORE_DIR = Path.home() / "Desktop" / "Squat More" / "Labeled_Dataset" / "processed_videos" / "keypoints"
PENN_ACTION_DIR = FORMIQ_ML_DIR / "data" / "squat_processed" / "keypoints"
SPLITS_PATH = FORMIQ_ML_DIR / "data" / "squat_processed" / "user_level_multilabel_splits.json"

# User-verified label corrections (override training labels)
LABEL_OVERRIDES = {
    "50852_1": "posture_fault",  # Training says good_form, actually posture_fault
    "47534_1": "good_form",      # Training says posture_fault, actually good_form
}

# How many of each class to include
TARGET_GOOD = 25
TARGET_FAULT = 25


def find_keypoint_file(video_name: str) -> str | None:
    """Find keypoint file in Squat More or Penn Action directories."""
    squat_path = SQUAT_MORE_DIR / f"{video_name}_keypoints.json"
    if squat_path.exists():
        return str(squat_path)
    penn_path = PENN_ACTION_DIR / f"{video_name}_keypoints.json"
    if penn_path.exists():
        return str(penn_path)
    return None


def convert_ml_keypoints(source_path: str) -> list:
    """
    Read ML-repo keypoint JSON and convert to app format.

    ML format: [{"frame_index": N, "landmarks": [...]}, ...]
    App format: [landmarks_list_per_frame, ...]  (List[Optional[List[Dict]]])
    """
    with open(source_path, "r") as f:
        ml_data = json.load(f)

    ml_data.sort(key=lambda x: x["frame_index"])

    app_data = []
    for frame in ml_data:
        landmarks = frame["landmarks"]
        if not landmarks or len(landmarks) < 33:
            app_data.append(None)
        else:
            app_data.append(landmarks)
    return app_data


def main():
    # Load test split
    if not SPLITS_PATH.exists():
        print(f"ERROR: splits file not found at {SPLITS_PATH}")
        sys.exit(1)

    with open(SPLITS_PATH) as f:
        splits = json.load(f)

    test = splits["splits"]["test"]
    vnames = test["video_names"]
    clabels = test["class_labels"]

    print(f"Test split: {len(vnames)} videos")

    # Categorize by label (applying overrides)
    good_candidates = []
    fault_candidates = []
    for vid, label in zip(vnames, clabels):
        effective_label = LABEL_OVERRIDES.get(vid, label)
        src = find_keypoint_file(vid)
        if src is None:
            continue
        if effective_label == "good_form":
            good_candidates.append((vid, src, effective_label))
        elif effective_label == "posture_fault":
            fault_candidates.append((vid, src, effective_label))
        # Skip depth_fault for now — focus on posture_fault vs good_form

    print(f"Available with keypoints: good_form={len(good_candidates)}, posture_fault={len(fault_candidates)}")

    # Select up to TARGET each
    selected_good = good_candidates[:TARGET_GOOD]
    selected_fault = fault_candidates[:TARGET_FAULT]
    all_selected = selected_good + selected_fault

    print(f"Selected: {len(selected_good)} good_form + {len(selected_fault)} posture_fault = {len(all_selected)}")

    # Convert and write
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {}

    for vid, src, label in all_selected:
        output_name = f"{vid}_{label}"
        app_data = convert_ml_keypoints(src)
        n_frames = len(app_data)
        n_none = sum(1 for f in app_data if f is None)

        out_path = OUTPUT_DIR / f"{output_name}.json.gz"
        raw_json = json.dumps(app_data, separators=(",", ":"))
        with gzip.open(out_path, "wt", encoding="utf-8") as f:
            f.write(raw_json)

        gz_size = out_path.stat().st_size
        source_type = "penn_action" if "FORMIQ" in src else "squat_more"
        status = f"{n_frames} frames, {gz_size/1024:.0f}KB"
        if n_none > 0:
            status += f" ({n_none} gaps)"
        print(f"  {output_name}: {status}")

        manifest[output_name] = {
            "video_id": vid,
            "label": label,
            "frames": n_frames,
            "source": source_type,
        }

    # Write manifest
    manifest_path = OUTPUT_DIR / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"\nManifest written to {manifest_path}")
    print(f"Total fixtures: {len(manifest)}")

    # Summary
    from collections import Counter
    label_counts = Counter(m["label"] for m in manifest.values())
    for label, count in sorted(label_counts.items()):
        print(f"  {label}: {count}")


if __name__ == "__main__":
    main()
