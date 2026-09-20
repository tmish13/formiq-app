#!/usr/bin/env python3
"""Post-fix counterpart to bench/mediapipe_state_leak_test.py.

Phase 0's script called ai.detect_pose() in its own loop, which bypasses the
per-video reset. This one drives the live extraction path
(app.tasks.analysis_tasks._extract_pose_from_video), which is where
AIService.reset_pose_tracker() is called, and prints the same four rows so the
before/after tables line up.

  docker run --rm --network deployment_default \
    -v $PWD/backend:/app -v "$HOME/Desktop/Squat More/Labeled_Dataset/videos:/videos:ro" \
    -v $PWD:/repo -w /app deployment-worker:latest python /repo/bench/tracker_reset_verify.py
"""
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, "/app")
VID = Path("/videos")
TARGET, OTHERS = "33387_1", ["33348_2", "36049_2"]


def main():
    from app.core.config import get_settings
    from app.services.ai_service import AIService
    from app.ml.posture_v1.loader import PostureV1TorchLoader
    from app.tasks.analysis_tasks import _extract_pose_from_video

    s = get_settings()
    loader = PostureV1TorchLoader(s)
    loader._ensure_loaded()

    def run(ai, vid):
        pose, _n, _fps = asyncio.run(
            _extract_pose_from_video(str(VID / f"{vid}.mp4"), ai, s)
        )
        return float(loader.predict_posture(pose)["prob_fault"])

    out = {"target": TARGET, "path": "_extract_pose_from_video", "rows": []}

    cold1 = run(AIService(app_settings=s), TARGET)
    cold2 = run(AIService(app_settings=s), TARGET)
    print(f"cold tracker, run 1            : {cold1:.6f}")
    print(f"cold tracker, run 2            : {cold2:.6f}   "
          f"(deterministic when cold: {abs(cold1 - cold2) < 1e-9})")
    out["cold_run_1"] = cold1
    out["cold_run_2"] = cold2

    for prev in OTHERS:
        ai = AIService(app_settings=s)
        run(ai, prev)
        warm = run(ai, TARGET)
        print(f"same video after {prev:9s}      : {warm:.6f}   shift vs cold {warm - cold1:+.6f}")
        out["rows"].append({"after": prev, "prob_fault": warm, "shift": warm - cold1})

    ai = AIService(app_settings=s)
    run(ai, TARGET)
    itself = run(ai, TARGET)
    print(f"same video after ITSELF        : {itself:.6f}   shift vs cold {itself - cold1:+.6f}")
    out["rows"].append({"after": "itself", "prob_fault": itself, "shift": itself - cold1})

    shifts = [abs(r["shift"]) for r in out["rows"]]
    out["max_abs_shift"] = max(shifts)
    print(f"\nmax |shift| vs cold            : {max(shifts):.6f}")
    dest = Path(os.getenv("BENCH_OUT", "/repo/bench/results/tracker_reset_verify.json"))
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2))
    print(f"wrote {dest}")


if __name__ == "__main__":
    main()
