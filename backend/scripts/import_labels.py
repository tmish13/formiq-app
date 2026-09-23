#!/usr/bin/env python3
"""Import human labels into `labels`, keyed on content_hash. Idempotent.

WHAT GETS IMPORTED, AND WHY IT IS THREE SOURCES AND NOT ONE
-----------------------------------------------------------
The splits file carries TWO label fields that disagree, and the disagreement is
not a bug -- they are answers to different questions:

  `multilabel_targets` / `enhanced_labels.video_level.class_label`
      the ASSIGNED class used for training. These two agree perfectly:
      0 disagreements over all 1,625 videos.

  `category`
      the SOURCE FOLDER the clip was collected into
      (good_form / posture_faults / stability_faults).

They disagree semantically on **600 of 1,625 videos (36.9%)**:

      posture_faults folder -> depth_fault      293
      stability_faults      -> posture_fault    131
      good_form folder      -> depth_fault      128
      stability_faults      -> depth_fault       48

`stability_fault` is not one of the three classes, so all 179 stability clips
were reassigned. And 128 clips the collectors filed under GOOD FORM carry the
`depth_fault` label -- which is worth holding next to the Phase 2 finding that
no geometric axis separates depth in this corpus. A label applied to clips
somebody else called good form is a reassignment, not an observation.

Importing only the winner would erase that. Both go in, under different
`source_ref`s, and the unique key keeps both. Resolution is the reader's job,
which is the only place that can know what it is resolving for.

HASHING
-------
Every row is keyed on the sha256 of the video file, via app/core/hashing.py --
the same function and chunk size the upload path uses. If those diverged the
labels would join to nothing, and that looks exactly like "no labels imported
yet". Where the .mp4 is missing the clip is SKIPPED and counted, never given a
made-up key.

    python backend/scripts/import_labels.py --dry-run
    python backend/scripts/import_labels.py
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

REPO = BACKEND.parent
SPLITS = (Path.home() / "FORMIQ Form Analysis Model" / "data" / "squat_processed"
          / "user_level_multilabel_splits.json")
OVERRIDE = BACKEND / "test_videos" / "labels_override.json"
OVERRIDE_VIDEO_ROOT = BACKEND / "test_videos"

CLASSES = ("good_form", "posture_fault", "depth_fault")
REF_TARGETS = "user_level_multilabel_splits.json#multilabel_targets"
REF_CATEGORY = "user_level_multilabel_splits.json#category"


def _ref(prefix: str, video_name: str) -> str:
    """Qualify the source ref with the video NAME, not just the file.

    105 of the 1,487 corpus files are byte-identical duplicates filed under
    different names, 80 of them with conflicting labels -- the same footage
    called good_form under one name and a fault under another
    (bench/results/2026-09-23-corpus-duplicates.md). Those collide on
    (content_hash, target, source, source_ref) unless the name is in the ref.

    Qualifying keeps BOTH rows, which is the schema working as designed:
    app/eval/labels.py surfaces them as contenders and marks the label
    `disputed`. Deduping at import would pick a winner silently and erase the
    strongest evidence in the corpus about its own label quality.

    The prefix is preserved so `LIKE 'user_level_...#multilabel_targets%'`
    still selects the whole source.
    """
    return f"{prefix}@{video_name}"[:255]
REF_OVERRIDE = "test_videos/labels_override.json"

#: `category` values -> the class vocabulary. `stability_faults` has no class of
#: its own in the three-class scheme; it maps to None and is recorded as an
#: unusable row for `*` rather than being forced into a class it does not have.
CATEGORY_TO_CLASS = {
    "good_form": "good_form",
    "posture_faults": "posture_fault",
    "stability_faults": None,
}


def _resolve_video(vd: dict, name: str, video_root: Optional[Path]) -> Optional[Path]:
    """The recorded path, else <video_root>/<name>.mp4.

    `video_path` in the splits file is an absolute path on the machine that
    built it, so it does not resolve inside a container. The fallback keeps the
    importer runnable in both places WITHOUT inventing a key when neither
    exists.
    """
    path = Path(vd.get("video_path") or "")
    if path.exists():
        return path
    if video_root is not None:
        cand = video_root / f"{name}.mp4"
        if cand.exists():
            return cand
    return None


def _rows_from_splits(limit: Optional[int],
                      video_root: Optional[Path] = None,
                      splits_path: Optional[Path] = None) -> tuple:
    from app.core.hashing import sha256_file
    from app.models.labels import SOURCE_DATASET, SOURCE_TRUST, TARGET_ALL

    data = json.loads((splits_path or SPLITS).read_text())
    rows: List[dict] = []
    skipped: Counter = Counter()
    seen = 0

    for split in ("train", "validation", "test"):
        s = data["splits"][split]
        for vd, tgt, name, uid in zip(s["video_data"], s["multilabel_targets"],
                                      s["video_names"], s["user_ids"]):
            if limit is not None and seen >= limit:
                break
            seen += 1
            path = _resolve_video(vd, name, video_root)
            if path is None:
                # No made-up keys. A row whose content_hash was invented joins
                # to the wrong video or to nothing, and both are worse than an
                # absent row that is counted.
                skipped["video_file_missing"] += 1
                continue
            digest = sha256_file(path)
            common = dict(content_hash=digest, video_name=name,
                          subject_id=str(uid), split=split,
                          source=SOURCE_DATASET,
                          trust=SOURCE_TRUST[SOURCE_DATASET])
            # A FOLDER IS NOT A JUDGEMENT. `category` records where a clip was
            # collected; `multilabel_targets` records the class it was assigned.
            # Importing both at equal trust made every reassignment look like a
            # disagreement, and since depth_fault is almost entirely
            # reassignments, it disqualified 89.5% of that class from
            # evaluation. Provenance gets its own, lower trust.
            category_trust = round(SOURCE_TRUST[SOURCE_DATASET] / 2, 3)

            # 1. the assigned class, one row per target so the evaluation join
            #    is `WHERE target = ?` rather than an index lookup into a list.
            for i, cls in enumerate(CLASSES):
                rows.append({**common, "target": cls, "value": int(tgt[i]),
                             "usable": True,
                             "source_ref": _ref(REF_TARGETS, name)})

            # 2. the source folder, kept as its own statement.
            cat = vd.get("category")
            mapped = CATEGORY_TO_CLASS.get(cat, None)
            if mapped is not None:
                for cls in CLASSES:
                    rows.append({**common, "target": cls,
                                 "value": int(cls == mapped), "usable": True,
                                 "trust": category_trust,
                                 "source_ref": _ref(REF_CATEGORY, name),
                                 "notes": f"collected under category={cat!r} "
                                          "(provenance, not a judgement)"})
            else:
                rows.append({**common, "target": TARGET_ALL, "value": None,
                             "usable": True, "trust": category_trust,
                             "source_ref": _ref(REF_CATEGORY, name),
                             "notes": (f"collected under category={cat!r}, which "
                                       "has no class in the three-class scheme")})
    return rows, skipped


def _rows_from_override() -> tuple:
    """`labels_override.json` -- a hand review of the smoke-test fixtures."""
    from app.core.hashing import sha256_file
    from app.models.labels import SOURCE_EXPERT, SOURCE_TRUST, TARGET_ALL

    rows: List[dict] = []
    skipped: Counter = Counter()
    if not OVERRIDE.exists():
        skipped["override_file_missing"] += 1
        return rows, skipped

    raw = json.loads(OVERRIDE.read_text())
    reviewer = raw.get("_reviewed_by")
    by_name = {p.name: p for p in OVERRIDE_VIDEO_ROOT.rglob("*.mp4")}

    for fname, label in raw.items():
        # 10 of the 24 entries are `_`-prefixed prose, not labels.
        if fname.startswith("_"):
            skipped["comment_key"] += 1
            continue
        path = by_name.get(fname)
        if path is None:
            skipped["video_file_missing"] += 1
            continue
        digest = sha256_file(path)
        common = dict(content_hash=digest, video_name=fname, subject_id=None,
                      split=None, source=SOURCE_EXPERT,
                      source_ref=REF_OVERRIDE,
                      trust=SOURCE_TRUST[SOURCE_EXPERT], labeled_by=reviewer)

        if label == "messy":
            # A real statement -- "unusable for every target" -- and different
            # from having no row at all.
            rows.append({**common, "target": TARGET_ALL, "value": None,
                         "usable": False, "notes": "labels_override: messy"})
            continue
        # "fault" is an accepted alias for posture_fault per the file's own
        # _comment; other_fault is a class this scheme does not carry.
        mapped = {"fault": "posture_fault", "posture_fault": "posture_fault",
                  "good_form": "good_form"}.get(label)
        if mapped is None:
            rows.append({**common, "target": TARGET_ALL, "value": None,
                         "usable": False,
                         "notes": f"labels_override: {label!r} has no class here"})
            continue
        for cls in CLASSES:
            rows.append({**common, "target": cls, "value": int(cls == mapped),
                         "usable": True, "notes": f"labels_override: {label!r}"})
    return rows, skipped


async def _upsert(rows: List[dict], dry_run: bool) -> Dict[str, int]:
    """Insert or update on (content_hash, target, source, source_ref)."""
    import uuid

    import sqlalchemy as sa

    from app.core.database import get_async_session_for_celery
    from app.models.labels import Label

    stats = Counter()
    async with get_async_session_for_celery() as session:
        existing = {
            (r.content_hash, r.target, r.source, r.source_ref): r
            for r in (await session.execute(sa.select(Label))).scalars().all()
        }
        for row in rows:
            key = (row["content_hash"], row["target"], row["source"],
                   row["source_ref"])
            prior = existing.get(key)
            if prior is None:
                stats["insert"] += 1
                if not dry_run:
                    session.add(Label(id=uuid.uuid4(), **row))
                    await session.flush()   # see recorder.py: sentinel batching
            elif (prior.value != row.get("value")
                  or prior.usable != row.get("usable", True)):
                stats["update"] += 1
                if not dry_run:
                    for k, v in row.items():
                        setattr(prior, k, v)
            else:
                stats["unchanged"] += 1
        if not dry_run:
            await session.commit()
    return stats


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="print what would change and write nothing")
    ap.add_argument("--limit", type=int, default=None,
                    help="only the first N corpus videos (smoke test)")
    ap.add_argument("--skip-corpus", action="store_true")
    ap.add_argument("--splits", type=Path, default=None,
                    help="user_level_multilabel_splits.json, when not at the "
                         "default host location")
    ap.add_argument("--video-root", type=Path, default=None,
                    help="directory of <video_name>.mp4, when the absolute "
                         "paths recorded in the splits file do not resolve here")
    args = ap.parse_args()

    rows: List[dict] = []
    skipped: Counter = Counter()
    if not args.skip_corpus:
        splits_path = args.splits or SPLITS
        if not splits_path.exists():
            print(f"splits file not found: {splits_path}", file=sys.stderr)
            return 1
        r, s = _rows_from_splits(args.limit, args.video_root, splits_path)
        rows += r
        skipped += s
    r, s = _rows_from_override()
    rows += r
    skipped += s

    # The shape check exists because writing a video FILENAME into a
    # content_hash column produces a table that joins to nothing, silently.
    from app.core.hashing import is_content_hash
    bad = [r for r in rows if not is_content_hash(r["content_hash"])]
    if bad:
        print(f"ABORT: {len(bad)} row(s) have a malformed content_hash, "
              f"e.g. {bad[0]['content_hash']!r}", file=sys.stderr)
        return 1

    seen_keys = Counter((r["content_hash"], r["target"], r["source"],
                         r["source_ref"]) for r in rows)
    collisions = [k for k, n in seen_keys.items() if n > 1]
    if collisions:
        # Reaching here means two rows claim the same key WITHIN one run, which
        # the database would reject anyway -- better to say which, here, than to
        # read it out of an IntegrityError traceback.
        print(f"ABORT: {len(collisions)} duplicate key(s) in this run, "
              f"e.g. {collisions[0]}", file=sys.stderr)
        return 1

    by_ref = Counter(r["source_ref"].split("@", 1)[0] for r in rows)
    print(f"{'DRY RUN -- ' if args.dry_run else ''}prepared {len(rows)} label rows")
    for ref, n in by_ref.most_common():
        print(f"   {ref:52s} {n:6d}")
    print(f"   distinct videos: {len({r['content_hash'] for r in rows})}")
    if skipped:
        print(f"   skipped: {dict(skipped)}")

    stats = asyncio.run(_upsert(rows, args.dry_run))
    print()
    print(f"   insert {stats['insert']}   update {stats['update']}   "
          f"unchanged {stats['unchanged']}")
    if args.dry_run:
        print("   (nothing written)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
