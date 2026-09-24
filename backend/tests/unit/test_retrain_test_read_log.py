"""The retrain's test split is read once per artifact, and every read is logged.

bench/retrain/train.py --final appends one line per (arm, learner) to
bench/results/retrain/TEST_READ_LOG.jsonl and refuses a second read unless it is
forced with a written reason. This test makes that contract a CI fact rather than
a script's good intention: a key that appears more than once without a forced
reason fails the build.

Skips when the results directory is not present (the worker image mounts only
backend/), and passes trivially before the first read (no log yet).
"""
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def _log_path() -> Path:
    backend = Path(__file__).resolve().parents[2]
    for cand in (backend.parent / "bench" / "results" / "retrain" / "TEST_READ_LOG.jsonl",
                 Path("/repo/bench/results/retrain/TEST_READ_LOG.jsonl")):
        if cand.parent.parent.is_dir():          # bench/results exists in this layout
            return cand
    pytest.skip("bench/results not present in this layout")


def _reads():
    log = _log_path()
    if not log.exists():
        return []
    return [json.loads(l) for l in log.read_text().splitlines() if l.strip()]


def test_each_artifact_reads_test_at_most_once_unless_forced_with_a_reason():
    seen = {}
    for r in _reads():
        key = r["key"]
        if key in seen:
            assert r.get("forced") and (r.get("reason") or "").strip(), (
                f"{key}: a second test read that was neither forced nor explained -- "
                f"the split has been read twice for the same artifact")
        seen.setdefault(key, r)


def test_every_logged_read_names_its_n_and_time():
    for r in _reads():
        assert r.get("n") and r.get("read_at"), r
