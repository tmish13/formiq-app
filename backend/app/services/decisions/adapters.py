"""Turning a rule verdict into a CheckerOutcome, in one testable place.

WHY THIS IS A MODULE AND NOT AN INLINE LITERAL
-----------------------------------------------
It was an inline literal in `analysis_tasks.py`, and the depth checker's
`score` was left out of it. `CheckerOutcome.score` defaults to None, so every
stored depth decision had a NULL score while the identical offline computation
produced a real one. Nothing raised: the field exists on the verdict, exists on
the outcome, exists as a column, and simply was not connected.

That is the same bug class as the phantom `summary` / `error_details` columns
(G-37) -- a value that goes nowhere, silently -- and the guard added to
`BaseService.update_async` does not catch it, because nothing was misspelled.
Only comparing the stored decision against the offline one caught it.

So the mapping lives here, and `tests/unit/test_decision_adapters.py` asserts
that every field the verdict carries reaches the outcome. A field added to a
verdict and forgotten here is a test failure rather than a NULL column.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from app.services.decisions.types import CheckerOutcome

__all__ = ["depth_outcome", "knees_forward_outcome", "keypoint_digest",
           "VERDICT_CARRIED_FIELDS"]

#: Fields a rule verdict carries that MUST reach the stored decision. Checked
#: by the unit test rather than trusted.
VERDICT_CARRIED_FIELDS = (
    "decision", "abstained", "abstain_reason", "score", "confidence",
    "coverage", "indicators",
)

DEPTH_CHECKER = "depth_parallel_v0"
KNEES_FORWARD_CHECKER = "knees_forward_v0"


def keypoint_digest(pose_data: Any) -> Optional[str]:
    """sha256 of the exact keypoint array a checker saw.

    This is what makes the determinism claim auditable after the fact instead
    of asserted: the same digest through the same checker version must give the
    same decision, and that is a query rather than a re-run.

    It is also the check that would have caught the missing `score` field
    automatically. That bug was found by hand-comparing eight stored decisions
    against the offline computation; with a digest recorded, the comparison is
    a join.

    Rounded to 6dp before hashing, matching the resolution the pipeline stores
    (loader.py:604) -- otherwise float noise below the recorded precision would
    make two identical stored verdicts look like different inputs.
    """
    import hashlib
    import json

    if not pose_data:
        return None
    try:
        norm = [
            None if not frame else [
                None if not isinstance(lm, dict) else [
                    round(float(lm.get(k, 0.0) or 0.0), 6)
                    for k in ("x", "y", "z", "visibility")
                ]
                for lm in frame
            ]
            for frame in pose_data
        ]
        blob = json.dumps(norm, separators=(",", ":"), sort_keys=True)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()
    except Exception:
        # An audit field must never break the analysis that produced it.
        return None


def _quality(verdict: Any) -> Dict[str, Any]:
    return {"scale_ref": verdict.scale_ref, "view": verdict.view,
            "bottom": verdict.bottom}


def depth_outcome(verdict: Any, params: Dict[str, Any],
                  latency_ms: Optional[float] = None,
                  inputs_digest: Optional[str] = None) -> CheckerOutcome:
    """`DepthVerdict` -> stored decision.

    `DepthVerdict` names its call `verdict`, not `decision`; the other rules use
    `decision`. That asymmetry is exactly how `score` went missing, so it is
    handled here once rather than at each call site.

    `threshold` is 0.0 by definition -- parallel IS the femur reaching
    horizontal, and the threshold was never fitted (see app/rules/depth.py).
    Recording it makes the definitional criterion visible in the audit row
    instead of implicit.
    """
    return CheckerOutcome(
        checker_name=DEPTH_CHECKER,
        checker_kind="rule",
        checker_version=verdict.params_id,
        target="depth",
        decision=verdict.verdict,
        fitted=bool(params.get("fitted")),
        advisory=True,
        abstained=verdict.abstained,
        abstain_reason=verdict.abstain_reason,
        score=verdict.score,
        confidence=verdict.confidence,
        coverage=verdict.coverage,
        threshold=0.0,
        indicators=verdict.indicators,
        quality=_quality(verdict),
        inputs_digest=inputs_digest,
        latency_ms=latency_ms,
    )


def knees_forward_outcome(verdict: Any,
                          latency_ms: Optional[float] = None,
                          inputs_digest: Optional[str] = None) -> CheckerOutcome:
    """`RuleVerdict` -> stored decision. `fitted` comes off the verdict, which
    carries it precisely so a caller cannot lose track of it."""
    return CheckerOutcome(
        checker_name=KNEES_FORWARD_CHECKER,
        checker_kind="rule",
        checker_version=verdict.params_id,
        target=verdict.target,
        decision=verdict.decision,
        fitted=bool(verdict.fitted),
        advisory=True,
        abstained=verdict.abstained,
        abstain_reason=verdict.abstain_reason,
        score=verdict.score,
        confidence=verdict.confidence,
        coverage=verdict.coverage,
        threshold=verdict.threshold,
        indicators=verdict.indicators,
        quality=_quality(verdict),
        inputs_digest=inputs_digest,
        latency_ms=latency_ms,
    )
