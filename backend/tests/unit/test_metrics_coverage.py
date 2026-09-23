"""Hand-computed cases, and the semantics of a checker that may abstain.

`test_metrics_parity.py` proves the module reproduces the published v1 numbers.
This proves the arithmetic is right in the first place, against cases worked out
by hand rather than against another implementation.

The coverage tests carry the most weight. The depth rule is allowed to decline,
and a checker that abstains on everything hard looks excellent if you report
only the calls it made. `coverage_metrics` returns both views precisely so that
cannot happen by accident.
"""
from __future__ import annotations

import numpy as np
import pytest

from app.eval.metrics import (
    auroc,
    counts,
    coverage_metrics,
    f_beta,
    precision_recall_f1,
    summarize,
    trivial_floor,
)

pytestmark = pytest.mark.unit


class TestConfusionArithmetic:
    def test_hand_computed_counts(self):
        y = [1, 1, 1, 0, 0, 0]
        p = [1, 1, 0, 1, 0, 0]
        c = counts(y, p)
        assert (c.tp, c.fp, c.tn, c.fn) == (2, 1, 2, 1)
        assert c.n == 6

    def test_hand_computed_prf(self):
        c = counts([1, 1, 1, 0, 0, 0], [1, 1, 0, 1, 0, 0])
        p, r, f = precision_recall_f1(c)
        assert p == pytest.approx(2 / 3)          # 2 of 3 predicted positives
        assert r == pytest.approx(2 / 3)          # 2 of 3 actual positives
        assert f == pytest.approx(2 / 3)

    def test_zero_denominators_return_zero_not_nan(self):
        """Load-bearing for the bootstrap: a resample can predict no positives,
        and a nan would poison the percentile."""
        c = counts([1, 1, 0], [0, 0, 0])          # nothing predicted positive
        p, r, f = precision_recall_f1(c)
        assert (p, r, f) == (0.0, 0.0, 0.0)
        assert not any(np.isnan(v) for v in (p, r, f))

    def test_perfect_and_inverted(self):
        y = [1, 0, 1, 0]
        assert precision_recall_f1(counts(y, y))[2] == 1.0
        assert precision_recall_f1(counts(y, [1 - v for v in y]))[2] == 0.0

    def test_f_beta_beta_gt_1_weights_recall_and_so_punishes_low_recall(self):
        """precision 1.0, recall 1/3 -- so leaning on recall must score LOWER.

        F_beta = (1+b^2)pr / (b^2 p + r):
            b=2.0 -> 5/13   ~ 0.385   (recall weighted 4x, and recall is the weak one)
            b=1.0 -> 0.5
            b=0.5 -> 5/7    ~ 0.714   (precision weighted, and precision is perfect)
        """
        c = counts([1, 1, 1, 0], [1, 0, 0, 0])
        assert f_beta(c, 1.0) == pytest.approx(0.5)
        assert f_beta(c, 2.0) == pytest.approx(5 / 13)
        assert f_beta(c, 0.5) == pytest.approx(5 / 7)
        assert f_beta(c, 2.0) < f_beta(c, 1.0) < f_beta(c, 0.5)

    def test_f_beta_beta_gt_1_rewards_high_recall(self):
        """The mirror case, so the direction is pinned from both sides."""
        c = counts([1, 1, 1, 0], [1, 1, 1, 1])    # recall 1.0, precision 0.75
        assert f_beta(c, 2.0) > f_beta(c, 1.0) > f_beta(c, 0.5)

    def test_shape_mismatch_raises(self):
        with pytest.raises(ValueError, match="shape mismatch"):
            counts([1, 0, 1], [1, 0])


class TestAuroc:
    def test_perfect_separation_is_one(self):
        assert auroc([0, 0, 1, 1], [0.1, 0.2, 0.8, 0.9]) == pytest.approx(1.0)

    def test_inverted_is_zero(self):
        assert auroc([0, 0, 1, 1], [0.9, 0.8, 0.2, 0.1]) == pytest.approx(0.0)

    def test_all_ties_is_one_half(self):
        """Every score identical means no ranking information at all."""
        assert auroc([0, 1, 0, 1], [0.5, 0.5, 0.5, 0.5]) == pytest.approx(0.5)

    def test_partial_ties_use_average_rank(self):
        # scores: neg .1, tie .5 (one neg one pos), pos .9
        # positive ranks: tie->2.5, .9->4  => (6.5 - 3) / (2*2) = 0.875
        assert auroc([0, 0, 1, 1], [0.1, 0.5, 0.5, 0.9]) == pytest.approx(0.875)

    def test_single_class_is_nan(self):
        assert np.isnan(auroc([1, 1, 1], [0.1, 0.5, 0.9]))
        assert np.isnan(auroc([0, 0, 0], [0.1, 0.5, 0.9]))


class TestTrivialFloor:
    def test_all_positive_f1_at_known_prevalence(self):
        """F1 of predicting everything positive is 2p/(1+p)."""
        y = [1] * 30 + [0] * 70                   # prevalence 0.30
        fl = trivial_floor(y)
        assert fl["prevalence"] == pytest.approx(0.30)
        assert fl["all_positive_f1"] == pytest.approx(2 * 0.30 / 1.30)
        assert fl["majority_class_accuracy"] == pytest.approx(0.70)

    def test_high_prevalence_floor_is_brutal(self):
        """At 80% prevalence a useless classifier scores F1 0.889."""
        fl = trivial_floor([1] * 80 + [0] * 20)
        assert fl["all_positive_f1"] == pytest.approx(2 * 0.8 / 1.8, abs=1e-6)
        assert fl["all_positive_f1"] > 0.88


class TestCoverage:
    def test_abstentions_are_excluded_from_covered_only(self):
        y = [1, 1, 0, 0]
        d = [1, "uncertain", 0, "uncertain"]
        m = coverage_metrics(y, d)
        assert m["n"] == 4 and m["n_covered"] == 2 and m["n_abstained"] == 2
        assert m["coverage"] == pytest.approx(0.5)
        # among the two it called: one TP, one TN -> perfect
        assert m["covered_only"]["f1"] == pytest.approx(1.0)

    def test_abstain_as_negative_costs_recall(self):
        """The user's view: an unanswered video is an unflagged video."""
        y = [1, 1, 0, 0]
        d = [1, "uncertain", 0, "uncertain"]
        m = coverage_metrics(y, d)
        an = m["abstain_as_negative"]
        assert an["precision"] == pytest.approx(1.0)
        assert an["recall"] == pytest.approx(0.5)     # the abstained positive is missed
        assert an["f1"] < m["covered_only"]["f1"]

    def test_the_cherry_picking_case_is_visible(self):
        """A checker that answers only the easy 20% looks perfect covered-only.

        This is the exact failure mode the dual report exists to expose: 1.0 F1
        on 20% coverage, and 0.33 F1 once the declines are counted.
        """
        y = [1] * 5 + [0] * 5
        d = ["uncertain"] * 4 + [1] + ["uncertain"] * 4 + [0]
        m = coverage_metrics(y, d)
        assert m["coverage"] == pytest.approx(0.2)
        assert m["covered_only"]["f1"] == pytest.approx(1.0)
        assert m["abstain_as_negative"]["f1"] == pytest.approx(2 * 1 / (2 * 1 + 0 + 4))

    def test_total_abstention_reports_none_not_zero(self):
        """Nothing was measured; that is not the same as measuring zero."""
        m = coverage_metrics([1, 0, 1], ["uncertain"] * 3)
        assert m["coverage"] == 0.0
        assert m["n_covered"] == 0
        assert m["covered_only"]["f1"] is None
        assert m["covered_only"]["counts"] is None

    def test_full_coverage_makes_both_views_identical(self):
        y = [1, 1, 0, 0]
        d = [1, 0, 1, 0]
        m = coverage_metrics(y, d)
        assert m["coverage"] == 1.0
        assert m["covered_only"]["f1"] == m["abstain_as_negative"]["f1"]

    def test_custom_abstain_and_positive_values(self):
        m = coverage_metrics(
            [1, 1, 0], ["SHALLOW", "UNCERTAIN", "AT_DEPTH"],
            abstain_value="UNCERTAIN", positive_value="SHALLOW")
        assert m["n_covered"] == 2
        assert m["covered_only"]["f1"] == pytest.approx(1.0)

    def test_shape_mismatch_raises(self):
        with pytest.raises(ValueError, match="shape mismatch"):
            coverage_metrics([1, 0, 1], [1, 0])


class TestSummarize:
    def test_floor_is_always_present(self):
        for kwargs in ({"y_score": [0.1, 0.9, 0.2, 0.8], "threshold": 0.5},
                       {"y_pred": [0, 1, 0, 1]},
                       {"decisions": [0, 1, "uncertain", 1]}):
            res = summarize([0, 1, 0, 1], bootstrap=False, **kwargs)
            assert "floor" in res, f"floor missing for {list(kwargs)}"

    def test_coverage_appears_only_with_decisions(self):
        assert "coverage_metrics" not in summarize(
            [0, 1], y_score=[0.1, 0.9], threshold=0.5, bootstrap=False)
        assert "coverage_metrics" in summarize([0, 1], decisions=[0, 1])

    def test_bootstrap_can_be_switched_off(self):
        res = summarize([0, 1, 0, 1], y_score=[0.1, 0.9, 0.2, 0.8],
                        threshold=0.5, bootstrap=False)
        assert "f1_ci95" not in res
