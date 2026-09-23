"""Deterministic rules layer.

A verdict from here is a pure function of (keypoints, params): no model, no RNG,
no clock, no I/O. The criterion is definitional -- parallel is the femur reaching
horizontal -- and only the measurement correction is fitted from data.

See app/rules/depth.py for why the threshold is not fitted, and
bench/results/2026-09-22-label-polarity.md for what the labels actually mean.
"""
from app.rules.depth import evaluate_depth
from app.rules.spec import (
    RULES_SPEC_VERSION,
    build_manifest,
    load_params,
    rules_spec_hash,
)
from app.rules.types import AT_DEPTH, SHALLOW, UNCERTAIN, DepthVerdict

__all__ = [
    "evaluate_depth",
    "load_params",
    "rules_spec_hash",
    "build_manifest",
    "RULES_SPEC_VERSION",
    "DepthVerdict",
    "SHALLOW",
    "AT_DEPTH",
    "UNCERTAIN",
]
