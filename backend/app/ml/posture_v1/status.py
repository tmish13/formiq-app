"""What the shipped posture verdict is allowed to claim (docs/ml/ACCEPTANCE_BAR.md §A3).

The API carries this block on every /ml-analysis response so the UI cannot present the posture
score as more than it is. The values are the measured state on the date given; the unit test
asserts they match bench/results/acceptance_bar_verdict.json when that file is present, so this
cannot drift from the evidence silently.
"""
POSTURE_VERDICT_STATUS = {
    "meets_acceptance_bar": False,
    "tier1_statistical": False,
    "tier2_product": False,
    "measured": "2026-09-24",
    "test_n": 196,
    "auroc": 0.7306,
    "auroc_ci95": [0.6616, 0.7995],
    "bar": "docs/ml/ACCEPTANCE_BAR.md",
    "presentation": "experimental",
    "note": ("The posture score separates faults from good form at AUROC 0.73 [0.66, 0.80] on a clean "
             "held-out set and flips on 15% of clips between two pose passes. Below the acceptance bar: "
             "shown as experimental, not as a verdict."),
}

LOCALISATION_STATUS = {
    "validated": "polarity only (80.2% within-video agreement, n=268); between-video AUROC 0.572",
    "presentation": "measured localisation, not a verdict about the squat overall",
}
