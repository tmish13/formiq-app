#!/usr/bin/env python3
"""Select the pilot clips and write the two blind annotation sheets (PREREGISTRATION.md).

    python bench/relabel/select_pilot.py [--train-n 300] [--seed 42]

Writes bench/results/relabel/pilot_selection.csv (the record: video, hash, split, current labels,
path) and annotation_sheet_A.csv / annotation_sheet_B.csv (video, path, empty grade columns; no
labels; shuffled differently per annotator so order effects differ between them).
"""
import argparse, csv, json, os, random
from collections import Counter, defaultdict
from pathlib import Path

R = Path(__file__).resolve().parents[2]
VID = Path(os.getenv("VID_DIR", os.path.expanduser("~/Desktop/Squat More/Labeled_Dataset/videos")))
ML = Path(os.getenv("ML_SPLITS", os.path.expanduser("~/FORMIQ Form Analysis Model/data/squat_processed/user_level_multilabel_splits.json")))
SHEET_COLS = ["video", "video_path", "severity_0_to_3", "usable_yes_no", "knees_forward_at_s", "notes"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train-n", type=int, default=300); ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=Path, default=R / "bench/results/relabel")
    a = ap.parse_args(); a.out.mkdir(parents=True, exist_ok=True)
    cl = json.loads((R / "bench/results/content_level_splits.json").read_text())
    cache = {p.name[:-8] for p in (R / "bench/cache/keypoints_live").glob("*.json.gz")}
    cls, bit = {}, {}
    for sp in ("train", "validation", "test"):
        for vd in json.loads(ML.read_text())["splits"][sp]["video_data"]:
            el = vd.get("enhanced_labels") or {}
            cls[vd["video_name"]] = (el.get("video_level") or {}).get("class_label")
            bit[vd["video_name"]] = int(bool((el.get("original_multi_label") or {}).get("posture_fault")))
    rows = [r for r in cl["videos"] if r["split"] and r["content_hash"] and r["video"] in cache and (VID / f"{r['video']}.mp4").exists()]
    test = sorted((r for r in rows if r["split"] == "test"), key=lambda r: r["video"])
    train_pool = defaultdict(list)
    for r in rows:
        if r["split"] == "train": train_pool[cls.get(r["video"], "?")].append(r)
    rng = random.Random(a.seed)
    total = sum(len(v) for v in train_pool.values())
    train = []
    for c, pool in sorted(train_pool.items()):
        k = round(a.train_n * len(pool) / total); rng.shuffle(pool); train += pool[:k]
    sel = [dict(video=r["video"], content_hash=r["content_hash"], split=r["split"], current_class=cls.get(r["video"]),
                current_posture_bit=bit.get(r["video"]), video_path=str(VID / f"{r['video']}.mp4")) for r in test + train]
    with (a.out / "pilot_selection.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(sel[0].keys())); w.writeheader(); w.writerows(sel)
    for tag, seed in (("A", a.seed + 1), ("B", a.seed + 2)):
        order = list(sel); random.Random(seed).shuffle(order)
        with (a.out / f"annotation_sheet_{tag}.csv").open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=SHEET_COLS); w.writeheader()
            w.writerow({"video": "_header", "video_path": "", "severity_0_to_3": "", "usable_yes_no": "",
                        "knees_forward_at_s": "", "notes": "annotator=<name>; started=<date>; finished=<date>"})
            for r in order: w.writerow({"video": r["video"], "video_path": r["video_path"], "severity_0_to_3": "",
                                        "usable_yes_no": "", "knees_forward_at_s": "", "notes": ""})
    print(f"selected {len(test)} test + {len(train)} train = {len(sel)} clips; train by class {dict(Counter(r['current_class'] for r in sel if r['split']=='train'))}")
    print(f"wrote {a.out}/pilot_selection.csv and annotation_sheet_A.csv / _B.csv")


if __name__ == "__main__":
    main()
