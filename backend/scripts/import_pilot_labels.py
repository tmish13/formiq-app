#!/usr/bin/env python3
"""Import an annotator's pilot sheet into the label store as expert rows.

    python scripts/import_pilot_labels.py --sheet /repo/bench/results/relabel/annotation_sheet_A.csv \
        --annotator A --selection /repo/bench/results/relabel/pilot_selection.csv [--dry-run]

Each graded, usable clip becomes two rows keyed on its content hash:
    target posture_severity  value 0..3
    target posture_fault_v2  value int(severity >= 2)
A clip marked unusable becomes the store's "unusable for every target" row (target "*").
source = expert, source_ref = pilot:<annotator>, trust 1.0 -- so the existing resolver prefers
these over the corpus label, and two annotators who disagree at the 1/2 boundary make the clip
`disputed` (excluded from Gate 2) rather than silently picking one.

The mapping is a pure function (rows_from_sheet) so it is unit-tested without a database; the
upsert reuses scripts/import_labels._upsert.
"""
import argparse, asyncio, csv, sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

# Mirrors app.models.labels (SOURCE_EXPERT, SOURCE_TRUST[expert], TARGET_ALL); asserted equal in the
# unit test when the app package is importable, so drift shows up there and not in the store.
SOURCE_EXPERT = "expert"
TRUST_EXPERT = 1.0
TARGET_ALL = "*"
TARGET_SEVERITY = "posture_severity"
TARGET_V2 = "posture_fault_v2"
V2_THRESHOLD = 2


def read_selection(path: Path) -> Dict[str, dict]:
    return {r["video"]: r for r in csv.DictReader(open(path, newline=""))}


def rows_from_sheet(sheet_rows: List[dict], annotator: str, selection: Dict[str, dict],
                    labeled_at: datetime | None = None) -> tuple:
    labeled_at = labeled_at or datetime.now(timezone.utc)
    rows, skipped = [], {"header": 0, "ungraded": 0, "not_in_selection": 0, "bad_severity": 0}
    for r in sheet_rows:
        v = (r.get("video") or "").strip()
        if not v or v.startswith("_"):
            skipped["header"] += 1; continue
        sel = selection.get(v)
        if sel is None:
            skipped["not_in_selection"] += 1; continue
        common = dict(content_hash=sel["content_hash"], video_name=v, subject_id=None, split=sel.get("split"),
                      source=SOURCE_EXPERT, source_ref=f"pilot:{annotator}", trust=TRUST_EXPERT,
                      labeled_by=annotator, labeled_at=labeled_at, notes=(r.get("notes") or "").strip() or None)
        usable = (r.get("usable_yes_no") or "").strip().lower()
        sev = (r.get("severity_0_to_3") or "").strip()
        if usable in ("no", "n", "0", "false"):
            rows.append({**common, "target": TARGET_ALL, "value": None, "usable": False}); continue
        if not sev:
            skipped["ungraded"] += 1; continue
        if not sev.isdigit() or not 0 <= int(sev) <= 3:
            skipped["bad_severity"] += 1; continue
        s = int(sev)
        rows.append({**common, "target": TARGET_SEVERITY, "value": s, "usable": True})
        rows.append({**common, "target": TARGET_V2, "value": int(s >= V2_THRESHOLD), "usable": True})
    return rows, skipped


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", type=Path, required=True); ap.add_argument("--annotator", required=True)
    ap.add_argument("--selection", type=Path, required=True); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from app.models.labels import SOURCE_EXPERT as _SE, SOURCE_TRUST as _ST, TARGET_ALL as _TA
    assert (_SE, _ST[_SE], _TA) == (SOURCE_EXPERT, TRUST_EXPERT, TARGET_ALL), "constants drifted from app.models.labels"
    from scripts.import_labels import _upsert
    rows, skipped = rows_from_sheet(list(csv.DictReader(open(a.sheet, newline=""))), a.annotator, read_selection(a.selection))
    print(f"{len(rows)} rows from {a.sheet.name} (annotator {a.annotator}); skipped {skipped}")
    stats = asyncio.run(_upsert(rows, a.dry_run))
    print("upsert:", dict(stats), "(dry run)" if a.dry_run else "")
    return 0


if __name__ == "__main__":
    sys.exit(main())
