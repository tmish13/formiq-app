"""Several checkers in, one answer out. Pure: no I/O, no clock, no RNG.

THE RULE THAT MATTERS: AN UNFITTED CHECKER IS ADVISORY
------------------------------------------------------
An advisory checker contributes EVIDENCE and never the VERDICT. Its outcome is
recorded in full, appears in `advisory` and in `evidence`, and is excluded from
both the per-target verdict and the overall score.

This is not caution for its own sake. Every rule this repo has built so far is
unfitted, and each one was measured and refuted at the video level:

  * depth          -- no axis separates the classes (best AUROC 0.578 of ten)
  * knee valgus    -- real signal, ~5% front view, 4 positive examples
  * knees forward  -- 80.2% within-video, 0.572 between, floor F1 0.812

They are carried because the *path* is worth proving and the measurements are
worth showing, not because their answers are trustworthy. If an advisory
outcome could set a verdict, the audit table would be full of rows that look
exactly like calibrated ones, and the distinction would survive only in a
results file.

THE OTHER RULES
---------------
* An abstention, an error or a skip never contributes and never sets a verdict.
  Each is recorded in `exclusions` with the reason, so "we did not answer"
  is distinguishable from "no checker ran".
* Targets never merge. A depth verdict and a posture verdict are separate
  answers about separate things, and averaging them would invent a claim no
  checker made.
* Weights are renormalised over survivors, structurally mirroring
  `compute_weighted_overall` in app/services/scoring/squat_score_engine.py --
  same pattern, different domain, its OWN constants. COMPONENT_WEIGHTS is about
  posture sub-components, not about checkers, and sharing it would couple two
  things that only look alike.
* No contributors at all is a COMPLETED analysis with `score=None` and every
  target uncertain -- not a failure. That preserves today's behaviour for an
  uncertain PostureV1 result, which is the common case, not an edge case.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from app.services.decisions.types import (
    EXCLUDED_ABSTAINED,
    EXCLUDED_ADVISORY,
    EXCLUDED_ERROR,
    EXCLUDED_NO_SCORE,
    EXCLUDED_SKIPPED,
    ERROR,
    SKIPPED,
    UNCERTAIN,
    CheckerOutcome,
)

COMBINER_VERSION = "combiner_v1"

_EPS = 1e-9


@dataclass(frozen=True)
class CombinedResult:
    """The combined answer, plus everything needed to explain it."""
    combiner_version: str
    score: Optional[float]
    verdicts: Dict[str, str]                      # target -> decision
    contributors: List[str]                       # "checker:target"
    advisory: List[str]
    exclusions: List[Dict[str, str]]              # {checker, target, reason}
    weights_used: Dict[str, float]                # renormalised, sums to 1
    evidence: List[Dict[str, Any]]                # every outcome, in order

    @property
    def has_verdict(self) -> bool:
        return any(v != UNCERTAIN for v in self.verdicts.values())

    def to_finalize_payload(self) -> Dict[str, Any]:
        """Only the keys we actually have values for.

        Absence and explicit None mean different things downstream: absent
        leaves the column alone, present writes it. Emitting `depth_score: None`
        unconditionally is how a real depth verdict would get erased by a run
        in which the depth checker merely abstained.
        """
        payload: Dict[str, Any] = {}
        if self.score is not None:
            payload["score"] = self.score
        if self.verdicts:
            payload["verdicts"] = dict(self.verdicts)
        return payload


def _excluded(o: CheckerOutcome, reason: str) -> Dict[str, str]:
    return {"checker": o.checker_name, "target": o.target, "reason": reason}


def combine(outcomes: Sequence[CheckerOutcome]) -> CombinedResult:
    """Fold checker outcomes into one result. Order-stable, side-effect free."""
    verdicts: Dict[str, str] = {}
    contributors: List[str] = []
    advisory: List[str] = []
    exclusions: List[Dict[str, str]] = []
    evidence: List[Dict[str, Any]] = []
    scoring: List[CheckerOutcome] = []

    for o in outcomes:
        evidence.append(o.as_dict())
        key = f"{o.checker_name}:{o.target}"

        # Every target a checker looked at is reported, even when the answer is
        # "we do not know" -- silence and uncertainty are different claims.
        verdicts.setdefault(o.target, UNCERTAIN)

        if o.decision == ERROR or o.error:
            exclusions.append(_excluded(o, EXCLUDED_ERROR))
            continue
        if o.decision == SKIPPED:
            exclusions.append(_excluded(o, EXCLUDED_SKIPPED))
            continue
        if o.abstained or o.decision == UNCERTAIN:
            exclusions.append(_excluded(o, EXCLUDED_ABSTAINED))
            continue

        if not o.is_authoritative:
            # The load-bearing branch. It answered, and its answer is evidence.
            advisory.append(key)
            exclusions.append(_excluded(o, EXCLUDED_ADVISORY))
            continue

        verdicts[o.target] = o.decision
        contributors.append(key)
        if o.score is None:
            exclusions.append(_excluded(o, EXCLUDED_NO_SCORE))
        else:
            scoring.append(o)

    total = sum(max(0.0, o.weight) for o in scoring)
    if total <= _EPS:
        return CombinedResult(
            combiner_version=COMBINER_VERSION,
            score=None,
            verdicts=verdicts,
            contributors=contributors,
            advisory=advisory,
            exclusions=exclusions,
            weights_used={},
            evidence=evidence,
        )

    weights_used = {f"{o.checker_name}:{o.target}": max(0.0, o.weight) / total
                    for o in scoring}
    score = sum(weights_used[f"{o.checker_name}:{o.target}"] * float(o.score)
                for o in scoring)

    return CombinedResult(
        combiner_version=COMBINER_VERSION,
        score=round(float(score), 6),
        verdicts=verdicts,
        contributors=contributors,
        advisory=advisory,
        exclusions=exclusions,
        weights_used={k: round(v, 6) for k, v in weights_used.items()},
        evidence=evidence,
    )
