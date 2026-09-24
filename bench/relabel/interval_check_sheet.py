#!/usr/bin/env python3
"""Gate 0 sheet: are Fitness-AQA's knees-forward intervals frame-accurate enough to be ground truth?

50 train-split clips with at least one labelled interval, seed 42, no test clips. The sheet SHOWS the
dataset's interval (this task is not blind -- it checks the label, it does not create one) and the
annotator writes the start and end they observe. Pre-registered pass (PREREGISTRATION.md, Gate 0):
median |observed - labelled| <= 0.30 s at both boundaries. Do this AFTER the severity sheet.

    python3 bench/relabel/interval_check_sheet.py   # -> bench/results/relabel/interval_check_sheet.csv
"""
import csv, json, os, random, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
DATASET = Path(os.environ.get("FORMIQ_DATASET_DIR", os.path.expanduser("~/Desktop/Squat More/Labeled_Dataset")))
N, SEED = 50, 42

kf = json.load(open(DATASET / "Labels" / "error_knees_forward.json"))
split = {r["video"]: r["split"] for r in json.load(open(R / "bench/results/content_level_splits.json"))["videos"] if r["split"]}
test = set((R / "bench/results/retrain/test_clip_names.txt").read_text().split()) | {v for v, s in split.items() if s == "test"}
pool = sorted(v for v, ivs in kf.items() if ivs and split.get(v) == "train" and v not in test and (DATASET / "videos" / f"{v}.mp4").exists())
random.Random(SEED).shuffle(pool); chosen = sorted(pool[:N])
out = R / "bench/results/relabel/interval_check_sheet.csv"
with open(out, "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["video", "video_path", "labelled_start_s", "labelled_end_s", "observed_start_s", "observed_end_s", "verdict_accurate_yes_no", "notes"])
    w.writerow(["_header", "", "", "", "", "", "", "annotator=<name>; started=<date>; finished=<date>; task=interval boundary check (do after the severity sheet)"])
    for v in chosen:
        for s, e in kf[v]:
            w.writerow([v, str(DATASET / "videos" / f"{v}.mp4"), f"{s:.2f}", f"{e:.2f}", "", "", "", ""])
print(f"wrote {out}: {len(chosen)} clips, {sum(len(kf[v]) for v in chosen)} intervals (pool {len(pool)} train clips with an interval, seed {SEED})")
