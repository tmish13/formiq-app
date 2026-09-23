"""Turning several checkers' outputs into one answer, auditably.

`combiner.py` is pure and has no I/O. `types.py` is the wire shape between a
checker and both the combiner and the `checker_decisions` table.
"""
from app.services.decisions.combiner import (
    COMBINER_VERSION,
    CombinedResult,
    combine,
)
from app.services.decisions.types import CheckerOutcome

__all__ = ["combine", "CombinedResult", "COMBINER_VERSION", "CheckerOutcome"]
