# EVAL — the two PostureV1 numbers, and the one that replaced them

G-07: an offline F1 of 0.7237 (the shipped manifest's binary task) sat next to an end-to-end F1 of
0.182 on the first live run, and the live run's reports were untracked. Both are stated here, with
their populations, and both are superseded by the clean held-out measurement.

| number | population | what it is | caveat |
|---|---|---|---|
| F1 **0.7237** | the notebook's test split, ~162 videos, dataset keypoints | the shipped manifest's binary posture task | measured before G-44 was found: ~10 % of that population has a byte-identical twin in train; an upper bound (`app/eval/provenance.py`) |
| F1 **0.182**, recall 0.111, precision 0.5 (strict labels: F1 0.143) | 24 fixture videos, 18 scorable, live pipeline, 2026-02-18 (`scripts/output/posture_v1_combined_report.json`) | the first end-to-end run: MediaPipe live pass, the serving gates, threshold 0.525 | n = 18; 5 of the 8 false negatives were suspected Penn Action mislabels; the report's own diagnosis was domain shift + gate behaviour + label noise |
| AUROC **0.7057 [0.6246, 0.7808]**, F1 **0.6036 [0.5135, 0.6854]** vs floor 0.5865 | 188 content-level test videos, de-duplicated, serving pose pass, stored decisions | **the number to quote** (`bench/results/2026-09-23-gate1b-full-corpus.md`) | clean; at the all-positive floor; 15 % of verdicts flip between pose passes |

The gap between the first two was real and had three parts, all since measured: the train/serve pose
pass (G-39, 14.9 % verdict flips), contamination of the offline split (G-44), and a label that is a
degree judgement (ML_AUDIT §10). The third number is what the model does; the other two are history.
