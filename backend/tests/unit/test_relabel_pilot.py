"""The relabelling pilot's pure parts: sheet -> label rows, and the agreement gate."""
import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit
BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND / "scripts"))
import import_pilot_labels as ipl  # noqa: E402


def _agreement():
    for cand in (BACKEND.parent / "bench/relabel/agreement.py", Path("/repo/bench/relabel/agreement.py")):
        if cand.exists():
            spec = importlib.util.spec_from_file_location("agreement", cand); m = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(m); return m
    pytest.skip("bench/ not present in this layout")


SEL = {"v1": {"content_hash": "h1", "split": "test"}, "v2": {"content_hash": "h2", "split": "test"},
       "v3": {"content_hash": "h3", "split": "train"}}


def test_sheet_rows_become_severity_and_v2_rows():
    sheet = [{"video": "_header", "notes": "annotator=A"},
             {"video": "v1", "severity_0_to_3": "3", "usable_yes_no": "yes", "notes": "oblique"},
             {"video": "v2", "severity_0_to_3": "1", "usable_yes_no": "yes", "notes": ""},
             {"video": "v3", "severity_0_to_3": "", "usable_yes_no": "no", "notes": "front"},
             {"video": "v9", "severity_0_to_3": "2", "usable_yes_no": "yes"},
             {"video": "v1", "severity_0_to_3": "7", "usable_yes_no": "yes"}]
    rows, skipped = ipl.rows_from_sheet(sheet, "A", SEL, labeled_at=datetime(2026, 9, 24, tzinfo=timezone.utc))
    by = {(r["content_hash"], r["target"]): r for r in rows}
    assert by[("h1", "posture_severity")]["value"] == 3 and by[("h1", "posture_fault_v2")]["value"] == 1
    assert by[("h2", "posture_severity")]["value"] == 1 and by[("h2", "posture_fault_v2")]["value"] == 0
    assert by[("h3", "*")]["usable"] is False and by[("h3", "*")]["value"] is None
    assert all(r["source"] == "expert" and r["trust"] == 1.0 and r["source_ref"] == "pilot:A" for r in rows)
    assert skipped == {"header": 1, "ungraded": 0, "not_in_selection": 1, "bad_severity": 1}


def test_constants_match_the_label_store():
    try:
        from app.models.labels import SOURCE_EXPERT, SOURCE_TRUST, TARGET_ALL
    except Exception:
        pytest.skip("app package not importable here")
    assert (SOURCE_EXPERT, SOURCE_TRUST[SOURCE_EXPERT], TARGET_ALL) == (ipl.SOURCE_EXPERT, ipl.TRUST_EXPERT, ipl.TARGET_ALL)


def test_weighted_kappa_is_one_on_perfect_agreement_and_near_zero_on_independence():
    ag = _agreement()
    assert ag.weighted_kappa([0, 1, 2, 3, 2, 1], [0, 1, 2, 3, 2, 1]) == pytest.approx(1.0)
    import random
    rng = random.Random(0); a = [rng.randrange(4) for _ in range(4000)]; b = [rng.randrange(4) for _ in range(4000)]
    assert abs(ag.weighted_kappa(a, b)) < 0.05


def test_summary_uses_only_clips_both_marked_usable():
    ag = _agreement()
    A = {"v1": (2, True), "v2": (0, True), "v3": (3, False)}
    B = {"v1": (2, True), "v2": (1, True), "v3": (3, True)}
    s = ag.summarize(A, B)
    assert s["n_both_usable"] == 2 and s["unusable_A"] == 1 and s["unusable_B"] == 0
    assert s["agreement_on_severity_ge_2"] == 1.0
