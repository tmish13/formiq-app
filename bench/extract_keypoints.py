#!/usr/bin/env python3
"""Extract keypoints with the LIVE serving path, to be the calibration set.

Not a preprocessing convenience -- the point. The Stage 0b gate measured a
+0.0108 torso-length systematic bias between the dataset's pose pass and the
container's MediaPipe, with all six verdict disagreements running the same
direction (bench/results/2026-09-22-keypoint-provenance.md). Calibrating on
dataset keypoints would bake that bias into serving. Extracting with the live
path makes the transfer error zero by construction, and demotes the dataset
keypoints to a cross-check.

Four guarantees, each of which has cost someone a night before:

  1. CHECKPOINT PER VIDEO. Each result is written as it finishes and existing
     outputs are skipped on restart. A crash three hours in costs one video.
  2. EXTRACTION CONTRACT in the manifest -- MediaPipe version, complexity,
     static_image_mode, confidence thresholds, source fps, and the
     fresh-tracker-per-video guarantee. Same discipline as spec_hash: if this
     pass ever needs reproducing, the header is how.
  3. FRESH TRACKER PER VIDEO, inherited from _extract_pose_from_video, which
     calls reset_pose_tracker(). Without it the tracker carries state across
     videos and the same bytes score differently by predecessor (Phase 1, G-31).
  4. TEST SPLIT IS EXTRACTED BUT NOT OPENED. Extraction is not fitting, but the
     calibration script keeps `assert split != "test"` so the separation holds
     mechanically rather than by intention.

Run in-container:

    docker run --rm -m 6g --network deployment_default \
      -v $PWD/backend:/app -v $PWD:/repo \
      -v "$HOME/Desktop/Squat More/Labeled_Dataset/videos:/videos:ro" \
      -v "$HOME/FORMIQ Form Analysis Model/data/squat_processed:/splits:ro" \
      -e POSTGRES_SERVER=db -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres \
      -e POSTGRES_DB=formiq -e SECRET_KEY=dev-only-insecure-secret-key-32chars-minimum \
      -e REDIS_HOST=redis -e REDIS_PORT=6379 -w /app deployment-worker:latest \
      python /repo/bench/extract_keypoints.py --pass 1 --workers 4
"""
from __future__ import annotations

import argparse
import asyncio
import gzip
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, "/app")

VIDEOS = Path("/videos")
SPLITS = Path("/splits/user_level_multilabel_splits.json")
OUT_DIR = Path("/repo/bench/cache/keypoints_live")
MANIFEST = OUT_DIR / "_manifest.json"

CLASSES = ("good_form", "depth_fault", "posture_fault")

# Pass 1: the FULL test split, so the headline lands on the same n=244 as the
# pinned v1 numbers and the depth rule can be compared to PostureV1 on one
# footing. Plus a real fit set and enough validation for honest model selection.
PASS1 = {"test": None, "train": 400, "validation": 100}   # None = all
# Pass 2 extends train toward the full 1,047 of interest, only if pass 1's
# number is worth publishing.
PASS2 = {"test": None, "train": None, "validation": None}

_AI = None
_SETTINGS = None


# ------------------------------------------------------------------ workers --
def _init_worker():
    """One AIService per process. MediaPipe is not safe to share across a fork,
    and this mirrors the prefork pool the worker already uses."""
    global _AI, _SETTINGS
    from app.core.config import get_settings
    from app.services.ai_service import AIService

    _SETTINGS = get_settings()
    _AI = AIService(app_settings=_SETTINGS)


def _extract_one(name: str) -> dict:
    """Extract one video. Returns a small status record; writes the payload."""
    out = OUT_DIR / f"{name}.json.gz"
    if out.exists():                       # guarantee 1: resume is free
        return {"video": name, "status": "skipped"}

    from app.tasks.analysis_tasks import _extract_pose_from_video

    src = VIDEOS / f"{name}.mp4"
    if not src.exists():
        return {"video": name, "status": "missing_video"}

    t0 = time.time()
    try:
        pose, fps = asyncio.run(
            _extract_pose_from_video(str(src), _AI, _SETTINGS)
        )[0::2]
    except Exception as e:                  # one bad video must not stop the run
        return {"video": name, "status": "error", "error": f"{type(e).__name__}: {e}"}

    valid = sum(1 for f in pose if f)
    payload = {
        "video": name,
        "source_fps": fps,
        "n_frames": len(pose),
        "n_valid": valid,
        "complexity": _AI._pose_complexity_used,
        "complexity_fallback": _AI._pose_complexity_fallback,
        # frames[i] is the landmark list for frame i, or null when undetected.
        "frames": pose,
    }
    tmp = out.with_suffix(".tmp")
    with gzip.open(tmp, "wt") as fh:        # atomic: never leave a half file
        json.dump(payload, fh)
    tmp.replace(out)

    return {"video": name, "status": "ok", "n_frames": len(pose),
            "n_valid": valid, "fps": fps, "sec": round(time.time() - t0, 1)}


# ---------------------------------------------------------------- selection --
def select(pass_spec: dict) -> tuple:
    """Deterministic stratified selection. Sorted, no RNG -- reproducible.

    Also records every split member that CANNOT be extracted, with its source and
    reason. One pose pass means no mixing dataset keypoints back in to pad the
    count, so the excluded set has to be visible rather than silently dropped.
    """
    sp = json.loads(SPLITS.read_text())
    picked, summary, excluded = [], {}, {}
    for split, budget in pass_spec.items():
        by_class = {c: [] for c in CLASSES}
        miss = []
        for r in sp["splits"][split]["video_data"]:
            name = r["video_name"]
            cls = (r.get("enhanced_labels", {}).get("video_level", {}) or {}).get("class_label")
            if (VIDEOS / f"{name}.mp4").exists():
                if cls in by_class:
                    by_class[cls].append(name)
                continue
            declared = r.get("video_path", "")
            miss.append({
                "video": name,
                "class": cls,
                "source_dataset": r.get("source_dataset"),
                "declared_path": declared,
                "declared_path_exists": bool(declared) and Path(declared).exists(),
                "has_dataset_keypoints": bool(r.get("keypoints_path"))
                                          and Path(r["keypoints_path"]).exists(),
                "reason": "no .mp4 under /videos; not re-extractable with the live path",
            })
        counts = {}
        for c in CLASSES:
            take = sorted(by_class[c]) if budget is None \
                else sorted(by_class[c])[: budget // len(CLASSES)]
            picked += take
            counts[c] = len(take)
        summary[split] = counts
        if miss:
            excluded[split] = miss
    return picked, summary, excluded


def contract(ai, settings) -> dict:
    """Guarantee 2 -- everything needed to reproduce this extraction.

    Delegates to app.core.pose_pass so that this corpus and a production
    verdict are identified by the SAME function. If the two drifted, a stored
    `pose_pass_id` could not be compared against the pass a rule was
    calibrated on, which is the only reason the id exists.
    """
    from app.core.pose_pass import extraction_contract, pose_pass_id
    c = extraction_contract(ai_service=ai, settings=settings)
    return {"pose_pass_id": pose_pass_id(c), **c}


# -------------------------------------------------------------------- main --
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pass", dest="pass_no", type=int, choices=(1, 2), default=1)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--limit", type=int, default=None, help="smoke-test a few videos")
    ap.add_argument("--min-free-gb", type=float, default=40.0)
    ap.add_argument("--skip-disk-check", action="store_true")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Disk gate. A wedged daemon three hours into a four-hour run costs the night.
    stat = os.statvfs(str(OUT_DIR))
    free_gb = stat.f_bavail * stat.f_frsize / 1e9
    print(f"free space at output: {free_gb:.1f} GB (required {args.min_free_gb})")
    if free_gb < args.min_free_gb and not args.skip_disk_check:
        print("REFUSING TO START -- clear disk first, or pass --skip-disk-check "
              "for a small smoke run.")
        sys.exit(2)

    spec = PASS1 if args.pass_no == 1 else PASS2
    names, summary, excluded = select(spec)
    if args.limit:
        names = names[:args.limit]
    todo = [n for n in names if not (OUT_DIR / f"{n}.json.gz").exists()]

    print(f"pass {args.pass_no}: {len(names)} selected, {len(todo)} to extract, "
          f"{len(names) - len(todo)} already present")
    for split, counts in summary.items():
        print(f"  {split:11s} {counts}  (total {sum(counts.values())})")
    for split, miss in excluded.items():
        from collections import Counter
        by_src = Counter(m["source_dataset"] for m in miss)
        print(f"  {split:11s} EXCLUDED {len(miss)}: {dict(by_src)}")

    if not todo:
        print("nothing to do")
        return

    from multiprocessing import Pool

    t0 = time.time()
    done = ok = err = 0
    results = []
    with Pool(processes=args.workers, initializer=_init_worker) as pool:
        for rec in pool.imap_unordered(_extract_one, todo, chunksize=1):
            done += 1
            results.append(rec)
            if rec["status"] == "ok":
                ok += 1
            elif rec["status"] != "skipped":
                err += 1
                print(f"  !! {rec['video']}: {rec.get('error', rec['status'])}")
            if done % 20 == 0 or done == len(todo):
                el = time.time() - t0
                rate = done / el if el else 0
                eta = (len(todo) - done) / rate if rate else 0
                print(f"  {done}/{len(todo)}  ok={ok} err={err}  "
                      f"{rate * 60:.1f} vid/min  ETA {eta / 60:.0f} min")

    # Manifest last, so a partial run never claims to be complete.
    _init_worker()
    man = {
        "pass": args.pass_no,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "selection": summary,
        "n_selected": len(names),
        "excluded": excluded,
        "excluded_counts": {k: len(v) for k, v in excluded.items()},
        "exclusion_policy": "ONE POSE PASS. Split members without a re-extractable "
                            ".mp4 are excluded rather than back-filled from dataset "
                            "keypoints -- the Stage 0b gate measured 80% raw verdict "
                            "agreement between passes, so mixing provenance would put "
                            "a different pose pass into the headline.",
        "n_extracted_this_run": ok,
        "n_errors": err,
        "extraction_contract": contract(_AI, _SETTINGS),
        "splits_file": str(SPLITS),
        "output_dir": str(OUT_DIR),
        "format": "one gzipped JSON per video: "
                  "{video, source_fps, n_frames, n_valid, complexity, frames[]}",
    }
    MANIFEST.write_text(json.dumps(man, indent=2))

    el = time.time() - t0
    print()
    print(f"extracted {ok}, errors {err}, in {el / 60:.1f} min")
    print(f"manifest: {MANIFEST}")
    total = sum(f.stat().st_size for f in OUT_DIR.glob("*.json.gz"))
    print(f"on disk: {len(list(OUT_DIR.glob('*.json.gz')))} files, {total / 1e9:.2f} GB")


if __name__ == "__main__":
    main()
