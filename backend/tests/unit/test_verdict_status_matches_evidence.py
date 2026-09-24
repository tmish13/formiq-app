"""The API's verdict_status block must match the committed acceptance-bar verdict (no drift)."""
import json
from pathlib import Path

import pytest

from app.ml.posture_v1.status import LOCALISATION_STATUS, POSTURE_VERDICT_STATUS

pytestmark = pytest.mark.unit


def _verdict():
    for cand in (Path(__file__).resolve().parents[3] / "bench/results/acceptance_bar_verdict.json",
                 Path("/repo/bench/results/acceptance_bar_verdict.json")):
        if cand.exists():
            return json.loads(cand.read_text())
    pytest.skip("bench/results not present in this layout")


def test_status_block_is_honest_about_the_bar():
    v = _verdict()
    assert POSTURE_VERDICT_STATUS["tier1_statistical"] == bool(v["tier1_incumbent"])
    assert POSTURE_VERDICT_STATUS["meets_acceptance_bar"] is False
    assert POSTURE_VERDICT_STATUS["test_n"] == v["n_test"]
    inc = next(r for r in v["rows"] if r["criterion"] == "separation" and r["model"] == "incumbent")
    assert f"{POSTURE_VERDICT_STATUS['auroc']:.4f}" in inc["value"]
    assert POSTURE_VERDICT_STATUS["presentation"] == "experimental"


def test_localisation_status_states_its_validation_limit():
    assert "polarity only" in LOCALISATION_STATUS["validated"]
    assert "not a verdict" in LOCALISATION_STATUS["presentation"]
