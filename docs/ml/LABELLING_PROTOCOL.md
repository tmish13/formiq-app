# Labelling protocol — graded knee-travel severity for squats (pilot)

**Purpose.** The corpus's `posture_fault` label is a presence judgement on a behaviour that is
near-universal in a squat (the knees travel forward), and it separates videos at AUROC 0.57
(ML_AUDIT §10 cause 1). Every modelling intervention on that label has failed to move the honest
number (G-49). This protocol replaces presence with **degree**, on a pilot first, with two gates
(`bench/relabel/PREREGISTRATION.md`) that decide whether the full corpus is relabelled.

**Who.** Two annotators, working independently, blind to the corpus label, each other, and the
model's verdict. The sheets (`bench/results/relabel/annotation_sheet_A.csv`, `_B.csv`) contain the
video name and path only.

## What to score

One number per video, **the worst rep** if the clip has several: how far the knees travel forward
of the toes at the deepest point, seen from the camera's angle.

| severity | meaning | anchor |
|---|---|---|
| **0** | knees stay over the mid-foot or behind the toe line through the whole descent | no forward travel visible |
| **1** | mild: knees pass the toe line by roughly a shoe's width or less, heels down | what most people would call a normal squat |
| **2** | clear: knees travel well past the toes (more than a shoe's width) **or** the heels rise to allow it | a coach would mention it |
| **3** | severe: knees far past the toes with the torso pitching forward or the heels well off the floor | a coach would stop the set |

`posture_fault_v2` is defined as **severity ≥ 2**. The 0/1 boundary and the 2/3 boundary matter
for agreement (κ is weighted); the 1/2 boundary is the one that becomes the label.

## View handling

- **Side view** (hip, knee and ankle all visible in profile): score normally.
- **Oblique** (≈ 30–60°): score; note `oblique` in the notes column. Knee travel is foreshortened;
  when unsure between two grades, take the lower one.
- **Front view**: knee travel is not observable. Mark `usable = no`, note `front`. Do not guess.
- Camera moves, subject leaves frame, or the descent is cut: `usable = no`, note why.

## Other faults

Score **only** knee travel. A rounded back, a shallow squat or a knee cave is not a reason to raise
the severity. If you notice one, put it in the notes column as a single word (`round`, `shallow`,
`cave`); it is not scored in this pilot.

## Optional: where

`knees_forward_at_s`: the clip time (seconds, one decimal) at which the knees are furthest forward.
Leave blank if unsure. This feeds the localisation claim, not the label.

## The 80 conflicting duplicate pairs

`bench/results/relabel/conflicting_pairs_sheet.csv` lists 80 byte-identical video pairs filed under
two different classes (G-44). For each pair, watch the file once and write **one** class in
`adjudicated_class` — `good_form`, `posture_fault` or `depth_fault` — or `unusable`. This is a
separate, shorter task; do it after the severity sheet so its classes do not anchor your grades.

## The interval boundary check (one annotator, 50 clips, after the severity sheet)

`bench/results/relabel/interval_check_sheet.csv` lists 50 train clips with the dataset's own
knees-forward interval (`labelled_start_s`, `labelled_end_s`). Watch the clip, write the second at
which the knees first pass the toe line (`observed_start_s`) and the second at which they come back
behind it or the rep ends (`observed_end_s`), one decimal, and `yes`/`no` in `verdict_accurate_yes_no`
for whether the labelled interval is the right one. Notes as single words. This checks whether the
dataset's intervals can serve as frame-level ground truth (pre-registration, Gate 0); it changes no
label.

## Rules

1. Watch each clip at least twice; pause at the deepest point.
2. Do not go back and change earlier grades after seeing later clips (drift is measured, not hidden).
3. Do not discuss clips with the other annotator until both sheets are submitted.
4. Record the date you started and finished in the sheet's header row.
