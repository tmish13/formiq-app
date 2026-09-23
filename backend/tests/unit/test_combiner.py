"""The combiner's rules, one test each.

The first group is the one that matters: every rule this repo has built is
unfitted and was measured and refuted at the video level. If an advisory
outcome could set a verdict, the audit table would fill with rows
indistinguishable from calibrated ones.
"""
import pytest

from app.services.decisions import COMBINER_VERSION, CheckerOutcome, combine
from app.services.decisions.types import (
    EXCLUDED_ABSTAINED,
    EXCLUDED_ADVISORY,
    EXCLUDED_ERROR,
    EXCLUDED_SKIPPED,
    UNCERTAIN,
)


def _out(**kw):
    base = dict(checker_name="c", target="depth", decision="AT_DEPTH",
                fitted=True, advisory=False, score=80.0, weight=1.0)
    base.update(kw)
    return CheckerOutcome(**base)


def _reasons(result, checker):
    return [e["reason"] for e in result.exclusions if e["checker"] == checker]


# ------------------------------------------------- advisory is evidence only --

def test_an_advisory_checker_does_not_set_the_verdict():
    r = combine([_out(checker_name="kf", fitted=False, advisory=True,
                      decision="OBSERVED")])
    assert r.verdicts["depth"] == UNCERTAIN
    assert r.advisory == ["kf:depth"]
    assert r.contributors == []
    assert _reasons(r, "kf") == [EXCLUDED_ADVISORY]


def test_an_advisory_checker_does_not_move_the_score():
    with_advisory = combine([
        _out(checker_name="auth", score=60.0),
        _out(checker_name="adv", fitted=False, advisory=True, score=0.0),
    ])
    alone = combine([_out(checker_name="auth", score=60.0)])
    assert with_advisory.score == alone.score == 60.0


def test_an_advisory_checker_is_still_recorded_in_full():
    """Excluded from the verdict, not from the record. The evidence is the
    reason the checker is carried at all."""
    r = combine([_out(checker_name="kf", fitted=False, advisory=True,
                      decision="OBSERVED", score=42.0,
                      indicators=[{"name": "K1", "value": 0.12}])])
    assert len(r.evidence) == 1
    ev = r.evidence[0]
    assert ev["decision"] == "OBSERVED"
    assert ev["indicators"] == [{"name": "K1", "value": 0.12}]
    assert ev["is_answer"] is True
    assert ev["is_authoritative"] is False


def test_unfitted_is_advisory_even_if_someone_clears_the_flag():
    """Two independent conditions, both required. Flipping `advisory` alone on
    an unfitted checker must not promote it."""
    r = combine([_out(checker_name="kf", fitted=False, advisory=False)])
    assert r.verdicts["depth"] == UNCERTAIN
    assert _reasons(r, "kf") == [EXCLUDED_ADVISORY]


def test_a_fitted_checker_may_be_advisory_while_shadowed():
    r = combine([_out(checker_name="shadowed", fitted=True, advisory=True)])
    assert r.verdicts["depth"] == UNCERTAIN
    assert r.advisory == ["shadowed:depth"]


# ------------------------------------------------------- non-answers --

@pytest.mark.parametrize("kw,reason", [
    (dict(abstained=True, decision=UNCERTAIN, abstain_reason="low_coverage"),
     EXCLUDED_ABSTAINED),
    (dict(decision="ERROR", error="boom"), EXCLUDED_ERROR),
    (dict(decision="SKIPPED"), EXCLUDED_SKIPPED),
])
def test_non_answers_never_contribute(kw, reason):
    r = combine([_out(checker_name="x", **kw)])
    assert r.verdicts["depth"] == UNCERTAIN
    assert r.score is None
    assert _reasons(r, "x") == [reason]


def test_an_errored_checker_is_excluded_even_with_a_decision_attached():
    """`error` set alongside a plausible decision is the dangerous shape: a
    checker that threw halfway and left a stale value behind."""
    r = combine([_out(checker_name="x", decision="AT_DEPTH", error="boom")])
    assert r.verdicts["depth"] == UNCERTAIN
    assert _reasons(r, "x") == [EXCLUDED_ERROR]


def test_an_abstention_is_distinguishable_from_no_checker_at_all():
    abstained = combine([_out(checker_name="x", abstained=True,
                              decision=UNCERTAIN)])
    nothing = combine([])
    assert abstained.verdicts == {"depth": UNCERTAIN}
    assert nothing.verdicts == {}
    assert abstained.exclusions and not nothing.exclusions


# ------------------------------------------------------------ targets --

def test_targets_never_merge():
    r = combine([
        _out(checker_name="a", target="depth", decision="AT_DEPTH"),
        _out(checker_name="b", target="posture", decision="FAULT"),
    ])
    assert r.verdicts == {"depth": "AT_DEPTH", "posture": "FAULT"}


def test_a_target_is_reported_even_when_only_abstentions_touched_it():
    r = combine([
        _out(checker_name="a", target="depth", decision="AT_DEPTH"),
        _out(checker_name="b", target="knees_forward", abstained=True,
             decision=UNCERTAIN),
    ])
    assert r.verdicts["knees_forward"] == UNCERTAIN


# ------------------------------------------------------------- scoring --

def test_weights_are_renormalised_over_survivors():
    r = combine([
        _out(checker_name="a", target="t1", score=100.0, weight=3.0),
        _out(checker_name="b", target="t2", score=0.0, weight=1.0),
    ])
    assert r.score == pytest.approx(75.0)
    assert sum(r.weights_used.values()) == pytest.approx(1.0)


def test_an_excluded_checker_does_not_dilute_the_score():
    """The bug this prevents: treating an abstention as a zero."""
    r = combine([
        _out(checker_name="a", score=80.0, weight=1.0),
        _out(checker_name="b", target="t2", abstained=True, decision=UNCERTAIN,
             score=0.0, weight=9.0),
    ])
    assert r.score == pytest.approx(80.0)


def test_an_authoritative_checker_without_a_score_still_sets_its_verdict():
    r = combine([_out(checker_name="a", score=None)])
    assert r.verdicts["depth"] == "AT_DEPTH"
    assert r.score is None
    assert "a:depth" in r.contributors


def test_no_contributors_is_a_completed_analysis_not_a_failure():
    r = combine([_out(checker_name="a", abstained=True, decision=UNCERTAIN)])
    assert r.score is None
    assert r.has_verdict is False
    assert r.weights_used == {}


# ----------------------------------------------------- finalize payload --

def test_payload_omits_keys_it_has_no_value_for():
    """Absent means 'leave the column alone'. Emitting an unconditional None is
    how an abstaining run would erase a real verdict from an earlier one."""
    assert "score" not in combine([]).to_finalize_payload()
    assert "verdicts" not in combine([]).to_finalize_payload()


def test_payload_carries_the_score_when_there_is_one():
    p = combine([_out(score=55.0)]).to_finalize_payload()
    assert p["score"] == pytest.approx(55.0)


# ----------------------------------------------------------- mechanics --

def test_evidence_order_follows_input_order():
    names = ["a", "b", "c"]
    r = combine([_out(checker_name=n) for n in names])
    assert [e["checker_name"] for e in r.evidence] == names


def test_combine_is_pure():
    outs = [_out(checker_name="a"), _out(checker_name="b", target="t2")]
    snapshot = [o.as_dict() for o in outs]
    first, second = combine(outs), combine(outs)
    assert first == second
    assert [o.as_dict() for o in outs] == snapshot


def test_version_is_stamped():
    assert combine([]).combiner_version == COMBINER_VERSION == "combiner_v1"


def test_as_row_keys_match_the_checker_decisions_columns():
    """The wire shape and the table must not drift apart."""
    from app.models.audit import CheckerDecision
    cols = set(CheckerDecision.__table__.c.keys())
    assert set(_out().as_row()) <= cols
