# Labelling worklist — every video to label, and the file to check the model against

Two files, made 2026-09-24. Grading itself still happens in the task sheets the importers read.

## `LABELLING_WORKLIST.csv` — what to label, in order

| task | rows | where to write | who |
|---|---|---|---|
| `1_severity` | 496 clips (196 test + 300 train) | `annotation_sheet_A.csv` (annotator A, column `order_A`) and `annotation_sheet_B.csv` (annotator B, `order_B`) | both annotators, independently, **blind** |
| `2_boundary_check` | 50 clips, 53 labelled intervals | `interval_check_sheet.csv` | one annotator, after task 1 |
| `3_pair_adjudication` | 80 byte-identical pairs | `conflicting_pairs_sheet.csv` | one annotator, last |

Columns: `video`, `video_path` (the `.mp4` to open), `split` (which of our content-level splits the
clip sits in — informational; it must not change how a clip is graded), `fill_in` (the sheet and
columns to complete), `shown_to_annotator` (what the sheet already displays: nothing for task 1, the
dataset's labelled interval for task 2, the two conflicting classes for task 3). Protocol:
`docs/ml/LABELLING_PROTOCOL.md`; gates: `bench/relabel/PREREGISTRATION.md`.

## `model_outputs_for_review.csv` — how the model did on each clip it has judged

972 judged videos, **test split withheld** (168 rows), one row per video: the dataset's knees-forward
and knees-inward intervals in seconds, the corpus class the model was trained on, PostureV1's
probability and its yes/no at 0.525, the knees-forward rule's decision and peak time, whether that
peak falls inside a labelled interval (± 0.25 s), the view, and the paths to the video and its frame
images. `python3 bench/where_is_the_fault.py <video> --ours` prints the same for one clip with the
frame paths of the interval's start, middle and end.

**Do not open this file before you have finished grading if you are one of the two annotators**: it
shows the model's verdicts and the dataset's labels, and the severity task is pre-registered as blind.

Validation-split read from this file (n = 190, not in-sample, not test), PostureV1 at 0.525 against
"any fault interval": TP 89, FP 22, FN 37, TN 42 → precision 0.802, recall 0.706, accuracy 0.689 against
an all-yes accuracy of 0.663. The rule fired on 91 of 190 clips; of the 64 fired clips with a labelled
interval, the peak was inside it in 46.
