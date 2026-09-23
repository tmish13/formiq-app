"""Every field a rule verdict carries must reach the stored decision.

This exists because one did not. `score` was omitted from the depth checker's
inline outcome construction, `CheckerOutcome.score` defaults to None, and every
stored depth decision had a NULL score while the identical offline computation
produced a real one. Nothing raised: the field exists on the verdict, on the
outcome and as a column. It simply was not connected.

Only comparing stored decisions against the offline computation caught it --
the argument for running that comparison at scale rather than on eight videos.
"""
import pytest

from app.rules.spec import load_knees_forward_params, load_params
from app.rules.types import UNCERTAIN, DepthVerdict, RuleVerdict
from app.services.decisions.adapters import (
    VERDICT_CARRIED_FIELDS,
    depth_outcome,
    knees_forward_outcome,
)

pytestmark = pytest.mark.unit

_IND = [{"name": "I2_hip_knee_delta", "value": 0.12, "confidence": 0.9}]


def _depth(**over):
    base = dict(verdict="AT_DEPTH", abstain_reason=None, score=0.089498,
                confidence=0.77, coverage=0.83, scale_ref=0.31,
                view={"kind": "oblique"}, bottom={"index": 42},
                indicators=_IND, rules_spec_version="v", rules_spec_hash="h",
                params_id="depth_v1_provisional")
    base.update(over)
    return DepthVerdict(**base)


def _kf(**over):
    base = dict(target="knees_forward", decision="OBSERVED", abstain_reason=None,
                score=0.1919, confidence=0.81, coverage=0.81, scale_ref=0.31,
                view={"kind": "oblique"}, bottom={"index": 42}, indicators=_IND,
                rules_spec_version="v", rules_spec_hash="h",
                params_id="knees_forward_v0_unfitted", fitted=False,
                threshold=0.05)
    base.update(over)
    return RuleVerdict(**base)


class TestDepth:
    def test_the_score_reaches_the_stored_decision(self):
        """The bug. Every stored depth decision had score NULL."""
        assert depth_outcome(_depth(), load_params()).score == 0.089498

    def test_the_verdict_field_is_renamed_correctly(self):
        """DepthVerdict calls it `verdict`; every other rule calls it
        `decision`. That asymmetry is how `score` went missing."""
        assert depth_outcome(_depth(), load_params()).decision == "AT_DEPTH"

    def test_the_definitional_threshold_is_recorded(self):
        """Parallel IS the femur reaching horizontal, so the threshold is 0 and
        was never fitted. Recording it makes that visible in the audit row."""
        assert depth_outcome(_depth(), load_params()).threshold == 0.0

    def test_it_is_unfitted_and_advisory(self):
        o = depth_outcome(_depth(), load_params())
        assert o.fitted is False and o.advisory is True
        assert o.is_authoritative is False

    def test_an_abstention_carries_its_reason(self):
        o = depth_outcome(_depth(verdict=UNCERTAIN, abstain_reason="near_parallel",
                                 score=None, confidence=None), load_params())
        assert o.abstained is True and o.abstain_reason == "near_parallel"

    def test_the_evidence_survives(self):
        o = depth_outcome(_depth(), load_params())
        assert o.indicators == _IND
        assert o.quality["scale_ref"] == 0.31
        assert o.quality["view"] == {"kind": "oblique"}


class TestKneesForward:
    def test_the_score_reaches_the_stored_decision(self):
        assert knees_forward_outcome(_kf()).score == 0.1919

    def test_fitted_comes_off_the_verdict(self):
        """RuleVerdict carries `fitted` precisely so a caller cannot lose it."""
        assert knees_forward_outcome(_kf()).fitted is False
        assert knees_forward_outcome(_kf(fitted=True)).fitted is True

    def test_the_hand_set_cut_is_recorded_as_the_threshold(self):
        assert knees_forward_outcome(_kf()).threshold == 0.05


class TestTheMappingIsTotal:
    """The class-closing test: a field added to a verdict and forgotten in the
    adapter is a failure here, not a NULL column discovered months later."""

    @pytest.mark.parametrize("field", VERDICT_CARRIED_FIELDS)
    def test_depth_carries_every_field(self, field):
        v, o = _depth(), depth_outcome(_depth(), load_params())
        src = getattr(v, "verdict" if field == "decision" else field, None)
        assert getattr(o, field) == src, (
            f"depth_outcome drops `{field}`: verdict has {src!r}, outcome has "
            f"{getattr(o, field)!r}")

    @pytest.mark.parametrize("field", VERDICT_CARRIED_FIELDS)
    def test_knees_forward_carries_every_field(self, field):
        v, o = _kf(), knees_forward_outcome(_kf())
        assert getattr(o, field) == getattr(v, field), (
            f"knees_forward_outcome drops `{field}`")

    def test_no_carried_field_is_silently_none(self):
        """A default of None is what let `score` vanish. If a verdict has a
        value, the outcome must too."""
        for o, v in ((depth_outcome(_depth(), load_params()), _depth()),
                     (knees_forward_outcome(_kf()), _kf())):
            for f in VERDICT_CARRIED_FIELDS:
                src = getattr(v, "verdict" if f == "decision" and
                              hasattr(v, "verdict") else f, None)
                if src is not None:
                    assert getattr(o, f) is not None, f"{f} became None"


def test_the_real_params_load_and_are_unfitted():
    assert load_params()["fitted"] is False
    assert load_knees_forward_params()["fitted"] is False


class TestKeypointDigest:
    """The digest makes the determinism claim a query instead of a re-run.

    It is also the mechanism that would have caught the missing `score`
    automatically: with a digest stored, comparing two decisions on identical
    inputs is a join, not a hand-written script over eight videos.
    """

    @staticmethod
    def _frames(y=0.5):
        lm = [{"x": 0.5, "y": y, "z": 0.0, "visibility": 1.0} for _ in range(33)]
        return [lm, lm]

    def test_identical_input_gives_an_identical_digest(self):
        from app.services.decisions.adapters import keypoint_digest
        assert keypoint_digest(self._frames()) == keypoint_digest(self._frames())

    def test_different_input_gives_a_different_digest(self):
        from app.services.decisions.adapters import keypoint_digest
        assert keypoint_digest(self._frames(0.5)) != keypoint_digest(self._frames(0.6))

    def test_noise_below_the_stored_resolution_does_not_change_it(self):
        """Rounded to the 6dp the pipeline stores. Otherwise two verdicts that
        are identical as recorded would look like different inputs."""
        from app.services.decisions.adapters import keypoint_digest
        a = self._frames(0.5)
        b = [[{**lm, "y": 0.5 + 1e-12} for lm in f] for f in a]
        assert keypoint_digest(a) == keypoint_digest(b)

    def test_empty_input_is_none_not_a_hash_of_nothing(self):
        from app.services.decisions.adapters import keypoint_digest
        assert keypoint_digest([]) is None
        assert keypoint_digest(None) is None

    def test_it_never_raises(self):
        """An audit field must not break the analysis that produced it."""
        from app.services.decisions.adapters import keypoint_digest
        assert keypoint_digest([["not-a-dict"], [None]]) is not None or True

    def test_the_digest_reaches_both_outcomes(self):
        from app.services.decisions.adapters import (
            depth_outcome, keypoint_digest, knees_forward_outcome)
        d = keypoint_digest(self._frames())
        assert depth_outcome(_depth(), load_params(), inputs_digest=d).inputs_digest == d
        assert knees_forward_outcome(_kf(), inputs_digest=d).inputs_digest == d
