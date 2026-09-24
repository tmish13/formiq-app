#!/usr/bin/env python3
"""The same video file appears under multiple names, in multiple splits, with
different labels.

Found by accident: the `labels` table's unique key
(content_hash, target, source, source_ref) refused an insert during the first
full import. Two different `video_name`s hashed to identical bytes.

WHY THE EARLIER "ZERO LEAKAGE" CHECK DID NOT CATCH THIS
-------------------------------------------------------
The splits are user-level and were verified leakage-free BY USER ID: 1,625
videos, 1,625 users, no user in two splits. That check is correct and it is not
sufficient. It assumes each user's footage is distinct. When byte-identical
files are filed under two different user ids, the split is clean by the
identifier and dirty by the content -- which is exactly the failure a content
hash exists to detect and a user id cannot.

Hashing is the same function the upload path uses (app/core/hashing.py), so
these are the same keys `form_checks`, `analysis_runs` and `labels` join on.

    docker run --rm -v $PWD/backend:/app \
      -v "${FORMIQ_ML_DIR:-$HOME/FORMIQ Form Analysis Model}/data/squat_processed:/splits:ro" \
      -v "$HOME/Desktop/Squat More/Labeled_Dataset/videos:/videos:ro" \
      -e SECRET_KEY=dev-only-insecure-secret-key-32chars-minimum -w /app \
      deployment-beat:latest python /repo/bench/corpus_duplicates.py
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

for cand in ("/app", str(Path(__file__).resolve().parent.parent / "backend")):
    if cand not in sys.path:
        sys.path.insert(0, cand)

CLASSES = ("good_form", "posture_fault", "depth_fault")


def main() -> int:
    from app.core.hashing import sha256_file

    ap = argparse.ArgumentParser()
    ap.add_argument("--splits", type=Path,
                    default=Path("/splits/user_level_multilabel_splits.json"))
    ap.add_argument("--video-root", type=Path, default=Path("/videos"))
    ap.add_argument("--out", type=Path,
                    default=Path("/repo/bench/results/corpus_duplicates.json"))
    args = ap.parse_args()

    sp = json.loads(args.splits.read_text())
    by_hash = defaultdict(list)
    missing = 0
    for split in ("train", "validation", "test"):
        s = sp["splits"][split]
        for vd, tgt, name, uid in zip(s["video_data"], s["multilabel_targets"],
                                      s["video_names"], s["user_ids"]):
            p = Path(vd.get("video_path") or "")
            if not p.exists():
                p = args.video_root / f"{name}.mp4"
            if not p.exists():
                missing += 1
                continue
            cls = CLASSES[list(tgt).index(1)] if sum(tgt) == 1 else "MULTI"
            by_hash[sha256_file(p)].append(
                {"video": name, "split": split, "user": str(uid), "class": cls})

    n_hashed = sum(len(v) for v in by_hash.values())
    dups = {h: v for h, v in by_hash.items() if len(v) > 1}
    cross_split = {h: v for h, v in dups.items() if len({x["split"] for x in v}) > 1}
    cross_user = {h: v for h, v in dups.items() if len({x["user"] for x in v}) > 1}
    cross_class = {h: v for h, v in dups.items() if len({x["class"] for x in v}) > 1}

    print(f"videos hashed          : {n_hashed}   (files missing {missing})")
    print(f"distinct content       : {len(by_hash)}")
    print(f"hashes with >1 name    : {len(dups)}")
    print(f"extra copies           : {sum(len(v) - 1 for v in dups.values())}"
          f"  ({sum(len(v) - 1 for v in dups.values()) / n_hashed:.1%} of the corpus)")
    print()
    print(f"spanning DIFFERENT SPLITS : {len(cross_split)}   <-- train/test leakage")
    print(f"spanning different users  : {len(cross_user)}")
    print(f"with CONFLICTING labels   : {len(cross_class)}   <-- same bytes, two answers")
    print()
    print("group sizes:", dict(Counter(len(v) for v in dups.values())))

    # Which label pairs conflict, and how often. If one pairing dominates it is
    # a systematic annotation boundary, not scattered noise.
    pair_counts = Counter()
    for v in cross_class.values():
        pair_counts[tuple(sorted({x["class"] for x in v}))] += 1
    print()
    print("conflicting label pairs:")
    for pair, n in pair_counts.most_common():
        print(f"   {' vs '.join(pair):34s} {n:4d}")

    for title, d in (("CROSS-SPLIT", cross_split), ("CONFLICTING", cross_class)):
        if d:
            print()
            print(f"--- {title} examples ---")
            for h, v in list(d.items())[:5]:
                print(f"   {h[:12]} " + "  ".join(
                    f"{x['video']}/{x['split']}/u{x['user']}/{x['class']}" for x in v))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({
        "n_hashed": n_hashed, "files_missing": missing,
        "distinct_content": len(by_hash), "duplicate_hashes": len(dups),
        "extra_copies": sum(len(v) - 1 for v in dups.values()),
        "cross_split": len(cross_split), "cross_user": len(cross_user),
        "conflicting_labels": len(cross_class),
        "conflicting_pairs": {" vs ".join(k): v for k, v in pair_counts.items()},
        "groups": dups,
    }, indent=2))
    print()
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
