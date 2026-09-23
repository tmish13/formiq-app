"""Reading labels back, and resolving the sources that disagree.

The `labels` table deliberately keeps every source's answer rather than
collapsing them at import (see app/models/labels.py). That makes reading a
decision: this module is where it is made, once, instead of in each caller.

THE RESOLUTION RULE
-------------------
Highest `trust` wins; ties broken by `labeled_at`, then by `source_ref` so the
result is deterministic with no clock and no dict ordering. An `usable=False`
row for target `*` vetoes every target for that video -- "this clip is
unusable" is a statement about the clip, not about one question asked of it.

Trust is a number and not a hierarchy on purpose. A dataset label the corpus
shipped (0.6) loses to a hand review (1.0) and beats the subject's own
correction (0.4) -- which is the most reliable source about INTENT and the
least about form.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

__all__ = [
    "ResolvedLabel", "resolve", "resolve_all", "to_binary_arrays",
    "TARGET_ALL",
]

TARGET_ALL = "*"


@dataclass(frozen=True)
class ResolvedLabel:
    content_hash: str
    target: str
    value: Optional[int]
    usable: bool
    source: Optional[str]
    source_ref: Optional[str]
    trust: Optional[float]
    #: Every source that answered this target, so a disagreement is visible
    #: rather than silently resolved. The corpus's two dataset fields disagree
    #: on 600 of 1,625 videos; a reader that cannot see that will not ask why.
    contenders: Tuple[Tuple[str, str, Optional[int]], ...] = ()
    #: Trust of each contender, positionally aligned with `contenders`.
    contender_trust: Tuple[float, ...] = ()

    @property
    def disputed(self) -> bool:
        """Do the sources at the WINNING trust tier disagree?

        Not "do any two sources disagree". A lower-trust source contradicting a
        higher-trust one is a resolved question, not an open one, and treating
        it as open was badly wrong here: `category` is the folder a clip was
        collected into and `multilabel_targets` is the class it was assigned.
        They disagree on nearly every `depth_fault` video, because depth_fault
        is precisely the class that was REASSIGNED from other folders (293 from
        posture_faults, 128 from good_form).

        Counting those as disputes excluded **374 of 418 depth_fault videos
        (89.5%)** from evaluation while dropping only 5.7% of posture_fault --
        a filter that looks class-neutral and is not. It collapsed depth
        prevalence from ~32% to 3.1% and made the depth evaluation meaningless
        for a reason that had nothing to do with the rule.
        """
        if not self.contenders:
            return False
        trusts = self.contender_trust or tuple(
            self.trust or 0.0 for _ in self.contenders)
        top = max(trusts)
        vals = {v for (_, _, v), t in zip(self.contenders, trusts)
                if v is not None and t >= top}
        return len(vals) > 1


def _key(row: Any) -> Tuple[float, float, str]:
    """Sort key: trust desc, then labeled_at desc, then source_ref asc.

    All three terms ascend, so the reversals are done numerically. An earlier
    version inverted the timestamp by prefixing its ISO string with "-", which
    does not reverse lexical order at all and silently preferred the OLDER
    label.

    An undated row sorts to 0.0 and therefore last among equal-trust rows: a
    row that says when it was written is more specific than one that does not.

    The final term is what makes this deterministic. Without it, two sources at
    equal trust with no timestamp resolve by whatever order the query returned
    -- stable until the day it is not.
    """
    trust = float(getattr(row, "trust", 0.0) or 0.0)
    at = getattr(row, "labeled_at", None)
    when = 0.0
    if at is not None:
        try:
            when = -at.timestamp()
        except (AttributeError, ValueError, OSError):
            when = 0.0
    return (-trust, when, str(getattr(row, "source_ref", "") or ""))


def resolve(rows: Iterable[Any], target: str) -> Optional[ResolvedLabel]:
    """One answer for one (video, target), or None if nothing addressed it."""
    rows = list(rows)
    if not rows:
        return None
    content_hash = str(rows[0].content_hash)

    # A `*` veto is about the clip, so it outranks any per-target answer.
    for r in rows:
        if r.target == TARGET_ALL and not r.usable:
            return ResolvedLabel(
                content_hash=content_hash, target=target, value=None,
                usable=False, source=r.source, source_ref=r.source_ref,
                trust=float(r.trust or 0.0),
                contenders=((r.source, r.source_ref, None),),
            )

    candidates = [r for r in rows if r.target == target and r.usable]
    if not candidates:
        return None
    candidates.sort(key=_key)
    best = candidates[0]
    return ResolvedLabel(
        content_hash=content_hash, target=target, value=best.value,
        usable=True, source=best.source, source_ref=best.source_ref,
        trust=float(best.trust or 0.0),
        contenders=tuple((c.source, c.source_ref, c.value) for c in candidates),
        contender_trust=tuple(float(c.trust or 0.0) for c in candidates),
    )


def resolve_all(rows: Iterable[Any], target: str) -> Dict[str, ResolvedLabel]:
    """Group by content_hash and resolve each. Videos with no answer are absent."""
    by_hash: Dict[str, List[Any]] = {}
    for r in rows:
        by_hash.setdefault(str(r.content_hash), []).append(r)
    out: Dict[str, ResolvedLabel] = {}
    for h, group in by_hash.items():
        res = resolve(group, target)
        if res is not None:
            out[h] = res
    return out


def to_binary_arrays(
    resolved: Dict[str, ResolvedLabel],
    predictions: Dict[str, Any],
    positive_value: Any = 1,
) -> Tuple[List[int], List[Any], List[str]]:
    """Align labels and predictions into (y_true, y_pred, hashes).

    Only videos that BOTH have a usable label and were predicted on are
    returned, and the hash list comes back so a caller can say which ones. An
    evaluation that quietly drops the disagreements is how a coverage problem
    becomes an accuracy claim.
    """
    y: List[int] = []
    p: List[Any] = []
    hashes: List[str] = []
    for h in sorted(resolved):
        lab = resolved[h]
        if not lab.usable or lab.value is None or h not in predictions:
            continue
        y.append(int(lab.value))
        p.append(predictions[h])
        hashes.append(h)
    return y, p, hashes
