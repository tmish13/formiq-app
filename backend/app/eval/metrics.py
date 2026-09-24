"""One implementation of the evaluation metrics, replacing four.

Before this module the same confusion-matrix arithmetic existed in four places
(`bench/eval_v1_test_split.py`, `scripts/eval_posture_v1_fixtures.py`,
`scripts/e2e_posture_v1_smoke.py`, `bench/ablate_face_block.py`), the bootstrap
CI existed in exactly one, and nothing was unit-tested against a hand-computed
case.

Two properties this module must hold, and both are pinned by tests:

1.  **Bit-exact replay of the published v1 numbers.** `bootstrap_ci` reproduces
    `bench/eval_v1_test_split.py:bootstrap_f1` exactly -- same
    `default_rng(seed)`, same single `rng.integers(0, N, N)` draw per iteration,
    same `np.percentile` interpolation. Change the RNG call order and the
    published CI stops reproducing, which is the signal that a refactor broke
    something.

2.  **Abstention is never free.** An abstaining checker that declines the hard
    cases looks like a precision triumph unless coverage is reported beside it.
    `coverage_metrics` therefore always returns BOTH the covered-only view and
    the abstain-as-negative view; callers do not get to pick one.

No hard scipy/sklearn dependency -- sklearn appears in this repo only inside a
try/except, so `auroc` is implemented directly with tie-corrected ranks.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Sequence, Tuple

import numpy as np

__all__ = [
    "Counts",
    "counts",
    "precision_recall_f1",
    "f_beta",
    "auroc",
    "bootstrap_ci",
    "trivial_floor",
    "coverage_metrics",
    "summarize",
]


@dataclass(frozen=True)
class Counts:
    tp: int
    fp: int
    tn: int
    fn: int

    @property
    def n(self) -> int:
        return self.tp + self.fp + self.tn + self.fn

    def as_dict(self) -> Dict[str, int]:
        return {"tp": self.tp, "fp": self.fp, "tn": self.tn, "fn": self.fn}


def counts(y_true: Sequence[int], y_pred: Sequence[int]) -> Counts:
    y = np.asarray(y_true).astype(int)
    p = np.asarray(y_pred).astype(int)
    if y.shape != p.shape:
        raise ValueError(f"shape mismatch: y_true {y.shape} vs y_pred {p.shape}")
    return Counts(
        tp=int(((p == 1) & (y == 1)).sum()),
        fp=int(((p == 1) & (y == 0)).sum()),
        tn=int(((p == 0) & (y == 0)).sum()),
        fn=int(((p == 0) & (y == 1)).sum()),
    )


def precision_recall_f1(c: Counts) -> Tuple[float, float, float]:
    """Zero-denominator cases return 0.0, matching the original implementation.

    That convention matters for the bootstrap: a resample can contain no
    predicted positives, and returning 0.0 rather than nan keeps the percentile
    well-defined.
    """
    p = c.tp / (c.tp + c.fp) if (c.tp + c.fp) else 0.0
    r = c.tp / (c.tp + c.fn) if (c.tp + c.fn) else 0.0
    f = 2 * p * r / (p + r) if (p + r) else 0.0
    return p, r, f


def f_beta(c: Counts, beta: float = 1.0) -> float:
    p, r, _ = precision_recall_f1(c)
    b2 = beta * beta
    return ((1 + b2) * p * r / (b2 * p + r)) if (b2 * p + r) else 0.0


def auroc(y_true: Sequence[int], y_score: Sequence[float]) -> float:
    """Tie-corrected rank AUC, equal to sklearn's roc_auc_score.

    AUC = (sum of positive ranks - n_pos(n_pos+1)/2) / (n_pos * n_neg),
    with tied scores sharing their average rank. Returns nan when one class is
    absent, which is what an undefined AUC should look like.
    """
    y = np.asarray(y_true).astype(int)
    s = np.asarray(y_score, dtype=np.float64)
    n_pos = int((y == 1).sum())
    n_neg = int((y == 0).sum())
    if n_pos == 0 or n_neg == 0:
        return float("nan")

    order = np.argsort(s, kind="mergesort")   # stable, so ties resolve reproducibly
    ranks = np.empty(len(s), dtype=np.float64)
    ranks[order] = np.arange(1, len(s) + 1, dtype=np.float64)

    # average rank within each tied group
    s_sorted = s[order]
    i = 0
    while i < len(s_sorted):
        j = i
        while j + 1 < len(s_sorted) and s_sorted[j + 1] == s_sorted[i]:
            j += 1
        if j > i:
            ranks[order[i : j + 1]] = (i + 1 + j + 1) / 2.0
        i = j + 1

    return float((ranks[y == 1].sum() - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg))


def bootstrap_ci(
    y_true: Sequence[int],
    y_score: Sequence[float],
    threshold: float,
    metric: str = "f1",
    n: int = 2000,
    seed: int = 0,
) -> Tuple[float, float]:
    """Percentile bootstrap CI over resampled items.

    Reproduces `bench/eval_v1_test_split.py:bootstrap_f1` exactly. The RNG call
    order is load-bearing: one `rng.integers(0, N, N)` per iteration and nothing
    else draws from `rng`. Adding a draw, vectorising the loop, or reordering
    changes the sequence and the published CI stops reproducing.
    """
    y = np.asarray(y_true).astype(int)
    s = np.asarray(y_score, dtype=np.float64)
    rng = np.random.default_rng(seed)
    N = len(y)
    out = []
    for _ in range(n):
        idx = rng.integers(0, N, N)
        c = counts(y[idx], (s[idx] >= threshold).astype(int))
        if metric == "f1":
            out.append(precision_recall_f1(c)[2])
        elif metric == "precision":
            out.append(precision_recall_f1(c)[0])
        elif metric == "recall":
            out.append(precision_recall_f1(c)[1])
        elif metric == "auroc":
            # threshold-free; `threshold` is ignored. Same single draw per iteration,
            # so the f1/precision/recall sequences are untouched.
            out.append(auroc(y[idx], s[idx]))
        else:
            raise ValueError(f"unsupported metric: {metric}")
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


def trivial_floor(y_true: Sequence[int]) -> Dict[str, float]:
    """What a classifier that thinks about nothing achieves.

    At high prevalence the all-positive F1 is large, and a model can beat chance
    while being useless. Quoting F1 without this number is how that gets missed.
    """
    y = np.asarray(y_true).astype(int)
    n = len(y)
    if n == 0:
        return {"prevalence": float("nan"), "all_positive_f1": float("nan"),
                "majority_class_accuracy": float("nan")}
    prev = float(y.mean())
    c_all_pos = counts(y, np.ones_like(y))
    return {
        "prevalence": prev,
        "all_positive_f1": precision_recall_f1(c_all_pos)[2],
        "majority_class_accuracy": max(prev, 1.0 - prev),
    }


def coverage_metrics(
    y_true: Sequence[int],
    decisions: Sequence[Any],
    abstain_value: Any = "uncertain",
    positive_value: Any = 1,
) -> Dict[str, Any]:
    """Metrics for a checker that is allowed to decline.

    Returns BOTH views, always:

      covered_only        -- P/R/F1 among the items it actually called. This is
                             the quality of its answers.
      abstain_as_negative -- P/R/F1 with every abstention scored as a negative.
                             This is what a user experiences, because an
                             unanswered video is an unflagged video.

    Reporting only the first makes a checker that abstains on everything hard
    look excellent; reporting only the second hides that its answers are good.
    """
    y = np.asarray(y_true).astype(int)
    d = np.asarray(decisions, dtype=object)
    if y.shape != d.shape:
        raise ValueError(f"shape mismatch: y_true {y.shape} vs decisions {d.shape}")

    covered = d != abstain_value
    n = len(y)
    n_cov = int(covered.sum())

    if n_cov:
        pred_cov = (d[covered] == positive_value).astype(int)
        c_cov = counts(y[covered], pred_cov)
        p, r, f = precision_recall_f1(c_cov)
        covered_only = {"n": n_cov, "counts": c_cov.as_dict(),
                        "precision": p, "recall": r, "f1": f}
    else:
        covered_only = {"n": 0, "counts": None,
                        "precision": None, "recall": None, "f1": None}

    pred_all = np.where(covered, d == positive_value, False).astype(int)
    c_all = counts(y, pred_all)
    p2, r2, f2 = precision_recall_f1(c_all)

    return {
        "n": n,
        "n_covered": n_cov,
        "n_abstained": n - n_cov,
        "coverage": (n_cov / n) if n else float("nan"),
        "covered_only": covered_only,
        "abstain_as_negative": {"counts": c_all.as_dict(),
                                "precision": p2, "recall": r2, "f1": f2},
    }


def summarize(
    y_true: Sequence[int],
    y_score: Optional[Sequence[float]] = None,
    threshold: Optional[float] = None,
    y_pred: Optional[Sequence[int]] = None,
    decisions: Optional[Sequence[Any]] = None,
    abstain_value: Any = "uncertain",
    bootstrap: bool = True,
    n_boot: int = 2000,
    seed: int = 0,
    label: str = "",
) -> Dict[str, Any]:
    """The one dict every report prints.

    Give it scores + a threshold, or hard predictions, or decisions that may
    abstain. Coverage appears whenever `decisions` is supplied, and the trivial
    floor appears always -- it is not optional.
    """
    y = np.asarray(y_true).astype(int)
    out: Dict[str, Any] = {"label": label, "n": int(len(y)),
                           "floor": trivial_floor(y)}

    if decisions is not None:
        out["coverage_metrics"] = coverage_metrics(
            y, decisions, abstain_value=abstain_value)

    if y_score is not None:
        s = np.asarray(y_score, dtype=np.float64)
        out["auroc"] = auroc(y, s)
        if threshold is not None:
            out["threshold"] = float(threshold)
            c = counts(y, (s >= threshold).astype(int))
            p, r, f = precision_recall_f1(c)
            out.update({"counts": c.as_dict(), "precision": p, "recall": r, "f1": f,
                        "accuracy": (c.tp + c.tn) / c.n if c.n else float("nan")})
            if bootstrap:
                lo, hi = bootstrap_ci(y, s, threshold, "f1", n_boot, seed)
                out["f1_ci95"] = [lo, hi]
                out["bootstrap"] = {"n": n_boot, "seed": seed, "method": "percentile"}
    elif y_pred is not None:
        c = counts(y, y_pred)
        p, r, f = precision_recall_f1(c)
        out.update({"counts": c.as_dict(), "precision": p, "recall": r, "f1": f,
                    "accuracy": (c.tp + c.tn) / c.n if c.n else float("nan")})

    return out
