"""What a checker hands to the combiner, and to the audit table.

One shape, two consumers, deliberately: if the combiner saw a richer object
than the database row, the stored evidence would be a lossy summary of what the
decision was actually made from, and the audit trail would quietly stop being
an audit trail.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

# Non-answers. None of these may set a verdict or contribute to a score; all of
# them are recorded.
UNCERTAIN = "UNCERTAIN"
ERROR = "ERROR"
SKIPPED = "SKIPPED"
NON_ANSWERS = (UNCERTAIN, ERROR, SKIPPED)

# Why a checker's answer did not count.
EXCLUDED_ABSTAINED = "abstained"
EXCLUDED_ERROR = "error"
EXCLUDED_SKIPPED = "skipped"
EXCLUDED_ADVISORY = "advisory_unfitted"
EXCLUDED_NO_SCORE = "no_score"


@dataclass(frozen=True)
class CheckerOutcome:
    """One checker's answer about one target.

    `fitted` and `advisory` are separate on purpose. `fitted` is a fact about
    the constants. `advisory` is a policy decision about what may be done with
    them. They coincide today -- nothing unfitted is authoritative -- but a
    fitted checker can still be advisory while it is being shadowed, and
    collapsing the two would make that state unexpressible.
    """
    checker_name: str
    target: str
    decision: str
    checker_kind: str = "rule"          # rule | model | heuristic
    checker_version: Optional[str] = None
    fitted: bool = False
    advisory: bool = True
    abstained: bool = False
    abstain_reason: Optional[str] = None
    score: Optional[float] = None       # 0..100, the product's scale
    prob: Optional[float] = None
    confidence: Optional[float] = None
    coverage: Optional[float] = None
    threshold: Optional[float] = None
    weight: float = 1.0
    indicators: Optional[List[Dict[str, Any]]] = None
    quality: Optional[Dict[str, Any]] = None
    inputs_digest: Optional[str] = None
    latency_ms: Optional[float] = None
    error: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_answer(self) -> bool:
        """A real call: not an abstention, an error or a skip."""
        return not self.abstained and self.decision not in NON_ANSWERS

    @property
    def is_authoritative(self) -> bool:
        """May this outcome set a verdict?

        Unfitted means the constants were never selected against data, so the
        checker's output is a description rather than a judgement. An unfitted
        checker that could set a verdict would be indistinguishable downstream
        from a calibrated one, which is the specific confusion this exists to
        prevent.
        """
        return self.is_answer and self.fitted and not self.advisory

    def as_row(self) -> Dict[str, Any]:
        """The `checker_decisions` column set. Keys map 1:1 to columns."""
        return {
            "checker_name": self.checker_name,
            "checker_kind": self.checker_kind,
            "checker_version": self.checker_version,
            "fitted": bool(self.fitted),
            "advisory": bool(self.advisory),
            "target": self.target,
            "decision": self.decision,
            "abstained": bool(self.abstained),
            "abstain_reason": self.abstain_reason,
            "score": self.score,
            "prob": self.prob,
            "confidence": self.confidence,
            "coverage": self.coverage,
            "threshold": self.threshold,
            "indicators": self.indicators,
            "quality": self.quality,
            "inputs_digest": self.inputs_digest,
            "latency_ms": self.latency_ms,
            "error": self.error,
        }

    def as_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["is_answer"] = self.is_answer
        d["is_authoritative"] = self.is_authoritative
        return d
