"""Frozen result types for the deterministic rules layer.

Everything here is immutable and JSON-serialisable: these objects end up in the
`checker_decisions.indicators` column as the evidence behind a verdict, and an
audit row that can be mutated after the fact is not an audit row.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# Verdicts. SHALLOW / AT_DEPTH are calls; UNCERTAIN is a refusal to call, and is
# never silently coerced into either by anything downstream.
SHALLOW = "SHALLOW"
AT_DEPTH = "AT_DEPTH"
UNCERTAIN = "UNCERTAIN"

# Reasons for refusing. Each is actionable: it tells the user (or us) what was
# wrong with the input rather than just "we don't know".
ABSTAIN_NO_FRAMES = "no_usable_frames"
ABSTAIN_BAD_SCALE = "bad_scale_reference"
ABSTAIN_NO_BOTTOM = "no_bottom_found"
ABSTAIN_LOW_COVERAGE = "low_coverage"
ABSTAIN_NEAR_PARALLEL = "near_parallel"


@dataclass(frozen=True)
class IndicatorResult:
    name: str
    value: Optional[float]          # raw, in its own units
    confidence: float               # 0..1, from visibility and view suitability
    usable: bool
    detail: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ViewEstimate:
    kind: str                       # "side" | "oblique" | "front"
    shoulder_ratio: Optional[float]  # ||L_sho - R_sho|| / scale_ref
    confidence: float               # 0..1

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BottomWindow:
    """One rep per clip -- confirmed across the corpus, so one bottom.

    See bench/results/2026-09-22-depth-label-inventory.md: clips are median 3.5s,
    marked depth frames span median 7 frames (0.23s), and bar trajectories show a
    single descent-and-return.
    """
    index: int                      # the bottom frame
    start: int                      # inclusive
    end: int                        # inclusive
    n_frames: int
    hip_y_at_bottom: float
    baseline_hip_y: float

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DepthVerdict:
    verdict: str                    # SHALLOW | AT_DEPTH | UNCERTAIN
    abstain_reason: Optional[str]
    score: Optional[float]          # corrected (hip_y - knee_y)/S at the bottom
    confidence: Optional[float]
    coverage: float                 # sum(w*c) / sum(w)
    scale_ref: Optional[float]
    view: Optional[Dict[str, Any]]
    bottom: Optional[Dict[str, Any]]
    indicators: List[Dict[str, Any]]
    rules_spec_version: str
    rules_spec_hash: str
    params_id: str

    @property
    def abstained(self) -> bool:
        return self.verdict == UNCERTAIN

    def as_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["abstained"] = self.abstained
        return d
