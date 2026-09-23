"""depth_score must not carry anything that is not a depth verdict.

It carried `movement_quality['consistency']` -- how steady the movement was --
under a column named for depth. Nothing depth-related fed it, and the word
"femur" appears nowhere in this repo. That is worse than NULL: a NULL is a
missing answer, a number is a wrong one.
"""
import ast
from pathlib import Path

import pytest

TASKS = Path(__file__).resolve().parents[2] / "app" / "tasks" / "analysis_tasks.py"
CONFIG = Path(__file__).resolve().parents[2] / "app" / "core" / "config.py"

pytestmark = pytest.mark.unit


def _assignments_to(attr: str, src: str):
    """Every `<anything>.<attr> = ...` in the module, with line numbers."""
    tree = ast.parse(src)
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AugAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        for t in targets:
            if isinstance(t, ast.Attribute) and t.attr == attr:
                out.append(node.lineno)
    return out


def test_nothing_writes_depth_score_on_the_live_path():
    """The whole point. When a fitted depth checker exists this test changes
    deliberately, with the fit in the same commit."""
    lines = _assignments_to("depth_score", TASKS.read_text())
    assert not lines, (
        "analysis_tasks.py assigns to depth_score at line(s) "
        f"{lines}. It stays NULL until a FITTED depth checker exists; the "
        "unfitted parallel rule records into results['rules_shadow'] instead."
    )


def test_consistency_is_still_recorded_somewhere_honest():
    """Removing the wrong home for a number must not lose the number."""
    src = TASKS.read_text()
    assert '"movement_quality"' in src and '"consistency"' in src


def test_the_orphan_depth_threshold_is_gone():
    """`EXERCISE_CONFIGS['squat']['depth_threshold'] = 0.7` had zero readers.
    An unused threshold reads as a tuned constant to anyone auditing this."""
    from app.core.config import settings
    assert "depth_threshold" not in settings.EXERCISE_CONFIGS["squat"]
    # Only in the comment that records why it went, never as a live key. A raw
    # substring check would forbid explaining the removal.
    live = [ln for ln in CONFIG.read_text().splitlines()
            if "depth_threshold" in ln and not ln.lstrip().startswith("#")]
    assert not live, live


def test_the_shipped_depth_rule_is_unfitted():
    """If this ever flips, the two tests above need revisiting in the same
    change rather than being discovered later."""
    from app.rules import load_params
    assert load_params()["fitted"] is False
