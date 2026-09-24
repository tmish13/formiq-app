#!/usr/bin/env python3
"""The 80 byte-identical pairs filed under two classes (G-44), as one adjudication sheet.

    python bench/relabel/conflicting_pairs_sheet.py
"""
import csv, json, os
from pathlib import Path

R = Path(__file__).resolve().parents[2]
VID = Path(os.getenv("VID_DIR", os.path.expanduser("~/Desktop/Squat More/Labeled_Dataset/videos")))


def main():
    d = json.loads((R / "bench/results/corpus_duplicates.json").read_text())
    out = R / "bench/results/relabel/conflicting_pairs_sheet.csv"; out.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with out.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["content_hash", "video_a", "class_a", "video_b", "class_b", "video_path", "adjudicated_class", "notes"])
        for h, members in d["groups"].items():
            classes = {m["class"] for m in members}
            if len(classes) < 2: continue
            a, b = members[0], members[1]
            path = next((VID / f"{m['video']}.mp4" for m in members if (VID / f"{m['video']}.mp4").exists()), "")
            w.writerow([h, a["video"], a["class"], b["video"], b["class"], str(path), "", ""]); n += 1
    print(f"{n} conflicting pairs -> {out}")


if __name__ == "__main__":
    main()
