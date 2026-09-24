#!/usr/bin/env python3
"""Where is the fault in this video? Every source of "where" the repo has, for one clip.

    python3 bench/where_is_the_fault.py 45823_6            # dataset intervals -> seconds, frames, frame images
    python3 bench/where_is_the_fault.py 48563_1 --ours      # plus what our knees-forward rule stored (asks the compose DB)

Sources, in order of authority:
  1. Fitness-AQA labels: Labels/error_knees_forward.json and error_knees_inward.json map a video to
     [[start_s, end_s], ...]. Seconds x fps = frame index. This is the ground truth for WHEN.
  2. The frame images: processed_videos/frames/<video>/frame_%06d.jpg -- open the start, middle and
     end frames of an interval and you are looking at the fault.
  3. Per-frame depth labels: Shallow_Squat_Error_Dataset/labels_shallow_depth.json, key <video>_<frame>.
  4. Ours (--ours): the knees-forward rule's stored output for the latest completed run of that video
     (form_checks.results.rules_shadow.knees_forward: decision, peak_time_sec, peak_frame, the bottom
     window). The app shows the same numbers at GET /api/v1/form-checks/<id>/ml-analysis under
     `localisation.knees_forward`.
Env: FORMIQ_DATASET_DIR (default ~/Desktop/Squat More/Labeled_Dataset), FORMIQ_KEYPOINT_CACHE
(default bench/cache/keypoints_live, for fps when ffprobe is absent).
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DATASET = Path(os.environ.get("FORMIQ_DATASET_DIR", os.path.expanduser("~/Desktop/Squat More/Labeled_Dataset")))
CACHE = Path(os.environ.get("FORMIQ_KEYPOINT_CACHE", REPO / "bench" / "cache" / "keypoints_live"))


def fps_and_frames(video: str):
    mp4 = DATASET / "videos" / f"{video}.mp4"
    if shutil.which("ffprobe") and mp4.exists():
        out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate,nb_frames",
                              "-of", "csv=p=0", str(mp4)], capture_output=True, text=True).stdout.strip()
        if out:
            rate, n = (out.split(",") + ["", ""])[:2]; num, _, den = rate.partition("/")
            try:
                return float(num) / float(den or 1), int(n) if n.isdigit() else None, "ffprobe"
            except ValueError:
                pass
    f = CACHE / f"{video}.json.gz"
    if f.exists():
        d = json.load(gzip.open(f, "rt")); return float(d.get("source_fps") or 30.0), len(d.get("frames") or []), "serving cache"
    return 30.0, None, "assumed 30"


def ours(video: str):
    sql = (f"select f.id, f.results->'rules_shadow'->'knees_forward'->>'decision', "
           f"f.results->'rules_shadow'->'knees_forward'->'indicators'->0->'detail'->>'peak_time_sec', "
           f"f.results->'rules_shadow'->'knees_forward'->'indicators'->0->'detail'->>'peak_frame', "
           f"f.results->'rules_shadow'->'knees_forward'->'bottom'->>'start', f.results->'rules_shadow'->'knees_forward'->'bottom'->>'end', "
           f"f.results->'rules_shadow'->'knees_forward'->'view'->>'kind', f.results->'posture_v1'->>'prob_fault' "
           f"from form_checks f join videos v on v.id=f.video_id where v.filename='{video}.mp4' and f.status='COMPLETED' "
           f"and f.results->'rules_shadow'->'knees_forward' is not null order by f.updated_at desc limit 1;")
    try:
        out = subprocess.run(["docker", "exec", "formiq_db", "psql", "-U", "postgres", "-d", "formiq", "-tAc", sql],
                             capture_output=True, text=True, timeout=30).stdout.strip()
    except Exception as e:  # noqa: BLE001
        return f"(could not query the compose DB: {e})"
    if not out:
        return "(this video has not been judged by the running stack)"
    fid, decision, peak_s, peak_f, b0, b1, view, prob = (out.split("|") + [""] * 8)[:8]
    return (f"form_check {fid}: knees_forward {decision} at {peak_s or '?'} s (frame {peak_f or '?'}), bottom window frames {b0}-{b1}, view {view}; "
            f"PostureV1 prob_fault {prob}\n    -> GET /api/v1/form-checks/{fid}/ml-analysis  (localisation.knees_forward.peak_time_sec)")


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("video"); ap.add_argument("--ours", action="store_true"); a = ap.parse_args()
    v = a.video[:-4] if a.video.endswith(".mp4") else a.video
    fps, n, src = fps_and_frames(v)
    print(f"{v}: fps {fps:g} ({src})" + (f", {n} frames = {n / fps:.2f} s" if n else ""))
    frames_dir = DATASET / "processed_videos" / "frames" / v
    for fault, fname in (("knees_forward", "error_knees_forward.json"), ("knees_inward", "error_knees_inward.json")):
        lab = json.load(open(DATASET / "Labels" / fname))
        if v not in lab:
            print(f"  {fault}: video not in the label file"); continue
        ivs = lab[v]
        if not ivs:
            print(f"  {fault}: no error labelled"); continue
        for s, e in ivs:
            f0, f1 = int(round(s * fps)), int(round(e * fps)); mid = (f0 + f1) // 2
            print(f"  {fault}: {s:.2f}-{e:.2f} s  = frames {f0}-{f1} ({f1 - f0 + 1} frames)")
            if frames_dir.exists():
                for tag, fi in (("start", f0), ("middle", mid), ("end", f1)):
                    p = frames_dir / f"frame_{fi:06d}.jpg"; print(f"      {tag:6s} {p}" + ("" if p.exists() else "  (missing)"))
            else:
                print(f"      (no extracted frames at {frames_dir}; open the .mp4 at {s:.2f} s)")
    depth = json.load(open(DATASET / "Shallow_Squat_Error_Dataset" / "labels_shallow_depth.json"))
    dframes = sorted(int(k.rsplit("_", 1)[1]) for k, val in depth.items() if k.rsplit("_", 1)[0] == v and val == 1)
    print(f"  shallow depth: {len(dframes)} frames labelled 1" + (f" ({dframes[0]}-{dframes[-1]})" if dframes else ""))
    if a.ours:
        print("  ours:", ours(v))
    return 0


if __name__ == "__main__":
    sys.exit(main())
