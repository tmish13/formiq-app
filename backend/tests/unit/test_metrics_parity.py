"""The published v1 numbers must replay through app.eval.metrics exactly.

Four implementations of this arithmetic existed before `app/eval/metrics.py`,
none unit-tested, and nothing anywhere asserted the headline numbers. A silent
change to the bootstrap's RNG call order, or to the zero-denominator convention
in `precision_recall_f1`, would have moved every reported figure with no test
failing.

`bench/results/2026-09-19-v1-test-per-video-scores.json` stores the per-video
probabilities from that run, so this replays them offline: no model load, no
DB, no container, deterministic.

The CI is the sharp test. `bootstrap_ci` draws one `rng.integers(0, N, N)` per
iteration from `default_rng(0)` and nothing else touches the stream. Vectorise
the loop, add a draw, or reorder, and [0.5291, 0.6872] stops reproducing.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from app.eval.metrics import (
    auroc,
    bootstrap_ci,
    counts,
    precision_recall_f1,
    summarize,
    trivial_floor,
)

pytestmark = pytest.mark.unit

SCORES = (
    Path(__file__).resolve().parents[2]
    / ".." / "bench" / "results" / "2026-09-19-v1-test-per-video-scores.json"
).resolve()

# Frozen at bench/results/2026-09-19-v1-held-out-evaluation.md. Changing any of
# these means the published number changed; that is a decision, not a test fix.
PINNED = {
    "n": 224,
    "positives": 86,
    "threshold": 0.525,
    "f1": 0.6131,
    "f1_ci95": (0.5291, 0.6872),
    "precision": 0.5398,
    "recall": 0.7093,
    "accuracy": 0.65625,
    "auroc": 0.7184,
    "prevalence": 0.3839,
    "trivial_floor_f1": 0.5548,
    "tp": 61, "fp": 52, "tn": 86, "fn": 25,
}
TOL = 5e-5


@pytest.fixture(scope="module")
def v1():
    if not SCORES.exists():
        pytest.skip(f"stored v1 scores not found at {SCORES}")
    d = json.loads(SCORES.read_text())
    rows = d["rows"]
    # The v1 eval scored the POSTURE label (multilabel index 1).
    y = np.array([1 if r["class"] == "posture_fault" else 0 for r in rows])
    s = np.array([r["prob_fault"] for r in rows], dtype=np.float64)
    return y, s, float(d["threshold"])


def test_replayed_dataset_matches_the_published_shape(v1):
    y, s, thr = v1
    assert len(y) == PINNED["n"]
    assert int(y.sum()) == PINNED["positives"]
    assert thr == PINNED["threshold"]


def test_confusion_counts_reproduce(v1):
    y, s, thr = v1
    c = counts(y, (s >= thr).astype(int))
    assert (c.tp, c.fp, c.tn, c.fn) == (
        PINNED["tp"], PINNED["fp"], PINNED["tn"], PINNED["fn"])


def test_precision_recall_f1_reproduce(v1):
    y, s, thr = v1
    p, r, f = precision_recall_f1(counts(y, (s >= thr).astype(int)))
    assert p == pytest.approx(PINNED["precision"], abs=TOL)
    assert r == pytest.approx(PINNED["recall"], abs=TOL)
    assert f == pytest.approx(PINNED["f1"], abs=TOL)


def test_auroc_reproduces_without_sklearn(v1):
    """Our tie-corrected rank AUC must equal what sklearn produced."""
    y, s, _ = v1
    assert auroc(y, s) == pytest.approx(PINNED["auroc"], abs=TOL)


def test_auroc_agrees_with_sklearn_when_available(v1):
    y, s, _ = v1
    sk = pytest.importorskip("sklearn.metrics")
    assert auroc(y, s) == pytest.approx(sk.roc_auc_score(y, s), abs=1e-9)


def test_bootstrap_ci_reproduces_bit_for_bit(v1):
    """The sharp one: guards the RNG call order."""
    y, s, thr = v1
    lo, hi = bootstrap_ci(y, s, thr, metric="f1", n=2000, seed=0)
    assert lo == pytest.approx(PINNED["f1_ci95"][0], abs=TOL), (
        "bootstrap lower bound drifted -- the RNG draw sequence changed")
    assert hi == pytest.approx(PINNED["f1_ci95"][1], abs=TOL), (
        "bootstrap upper bound drifted -- the RNG draw sequence changed")


def test_bootstrap_is_deterministic_across_calls(v1):
    y, s, thr = v1
    assert bootstrap_ci(y, s, thr, n=200, seed=7) == bootstrap_ci(y, s, thr, n=200, seed=7)


def test_trivial_floor_reproduces(v1):
    """The floor is the number that makes F1 0.6131 interpretable."""
    y, _, _ = v1
    fl = trivial_floor(y)
    assert fl["prevalence"] == pytest.approx(PINNED["prevalence"], abs=TOL)
    assert fl["all_positive_f1"] == pytest.approx(PINNED["trivial_floor_f1"], abs=TOL)


def test_v1_beats_its_floor_but_the_ci_does_not_exclude_it(v1):
    """States the honest reading of the published result.

    F1 0.6131 is above the 0.5548 all-positive floor, but the 95% CI reaches
    down to 0.5291 -- below it. This test exists so that reading survives.
    """
    y, s, thr = v1
    res = summarize(y, y_score=s, threshold=thr)
    assert res["f1"] > res["floor"]["all_positive_f1"]
    assert res["f1_ci95"][0] < res["floor"]["all_positive_f1"]


def test_summarize_always_reports_the_floor(v1):
    y, s, thr = v1
    res = summarize(y, y_score=s, threshold=thr, bootstrap=False)
    assert "floor" in res and res["floor"]["all_positive_f1"] is not None
