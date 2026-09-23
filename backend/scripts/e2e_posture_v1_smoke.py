#!/usr/bin/env python3
"""
E2E smoke test for the PostureV1 pipeline.

Exercises the full path: login -> upload -> poll -> resolve -> ML analysis.
Requires running services: postgres, redis, celery worker, uvicorn.

Usage (single video):
    python scripts/e2e_posture_v1_smoke.py --video /path/to/squat.mp4
    python scripts/e2e_posture_v1_smoke.py --video /path/to/squat.mp4 --threshold-mode strict
    python scripts/e2e_posture_v1_smoke.py --video /path/to/squat.mp4 --posture-v1-mode shadow

Usage (batch):
    python scripts/e2e_posture_v1_smoke.py --video-dir /path/to/videos/
    python scripts/e2e_posture_v1_smoke.py --video-dir /path/to/videos/ --max 5
    python scripts/e2e_posture_v1_smoke.py --video-dir /path/to/videos/ --exercise-type deadlift
    python scripts/e2e_posture_v1_smoke.py --video-dir test_videos/fault/ --labels-override test_videos/labels_override.json --metrics-scope posture_only

Environment variables:
    TEST_USER_EMAIL     - Login email (required)
    TEST_USER_PASSWORD  - Login password (required)
"""

import argparse
import glob
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "output"

VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".avi", ".mkv"}

# Map exercise types to exercise_name sent to API
EXERCISE_NAME_MAP = {
    "squat": "Low Bar Squat",
    "deadlift": "Deadlift",
    "bench_press": "Bench Press",
    "overhead_press": "Overhead Press",
    "barbell_row": "Barbell Row",
    "lunge": "Lunge",
}

# Label sets used by metrics computation and review queue builder.
# "fault" is the legacy generic label; "posture_fault" is the explicit in-scope label.
_POSTURE_FAULT_LABELS: frozenset = frozenset({"fault", "posture_fault"})
_OTHER_FAULT_LABELS: frozenset = frozenset({"other_fault"})
_GOOD_FORM_LABELS: frozenset = frozenset({"good_form"})


def fail(msg: str):
    print(f"\nFAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def authenticate(api: str, email: str, password: str) -> dict:
    """Authenticate and return headers with Bearer token."""
    auth_resp = requests.post(f"{api}/api/v1/auth/login", data={"username": email, "password": password})
    if auth_resp.status_code != 200:
        fail(f"Login failed ({auth_resp.status_code}): {auth_resp.text}")
    token = auth_resp.json().get("access_token")
    if not token:
        fail("No access_token in login response")
    return {"Authorization": f"Bearer {token}"}


def process_single_video(
    api: str,
    headers: dict,
    video_path: str,
    exercise_name: str,
    threshold_mode: str | None,
    posture_v1_mode: str | None,
    timeout: int,
    verbose: bool = True,
) -> dict:
    """
    Run full E2E pipeline for a single video. Returns a result dict.

    Result dict keys:
        filename, exercise_type, status, form_check_id, video_id,
        decision, prob_fault, confidence, posture_score,
        missing_ratio, frames_detected, original_frames, model_complexity,
        pose_complexity_fallback, latency_ms, elapsed_s, error
    """
    filename = os.path.basename(video_path)
    result = {
        "filename": filename,
        "exercise_type": exercise_name,
        "status": None,
        "form_check_id": None,
        "video_id": None,
        "decision": None,
        "prob_fault": None,
        "confidence": None,
        "posture_score": None,
        "missing_ratio": None,
        "frames_detected": None,
        "original_frames": None,
        "sequence_length": None,
        "duration_sec": None,
        "fps": None,
        "quality_flags": [],
        "model_complexity": None,
        "pose_complexity_fallback": None,
        "latency_ms": None,
        "elapsed_s": None,
        "error": None,
    }

    try:
        # Upload
        if verbose:
            print(f"\n  Uploading {filename} ({os.path.getsize(video_path) / 1024 / 1024:.1f} MB)...")
        with open(video_path, "rb") as f:
            files = {"video_upload": (filename, f)}
            params = {"exercise_name": exercise_name}
            if threshold_mode:
                params["threshold_mode"] = threshold_mode
            if posture_v1_mode:
                params["posture_v1_mode"] = posture_v1_mode

            upload_resp = requests.post(
                f"{api}/api/v1/form-checks/submit",
                headers=headers,
                files=files,
                params=params,
                timeout=60,
            )

        if upload_resp.status_code not in (200, 201, 202):
            result["error"] = f"Upload failed ({upload_resp.status_code})"
            result["status"] = "UPLOAD_FAILED"
            return result

        fc_data = upload_resp.json()
        result["form_check_id"] = fc_data.get("id")
        result["video_id"] = fc_data.get("video_id")

        # Poll for completion
        start = time.time()
        final_status = None
        poll_data = {}
        while time.time() - start < timeout:
            poll_resp = requests.get(
                f"{api}/api/v1/form-checks/{result['form_check_id']}", headers=headers
            )
            if poll_resp.status_code != 200:
                time.sleep(3)
                continue

            poll_data = poll_resp.json()
            final_status = poll_data.get("status", "").upper()
            if final_status in ("COMPLETED", "FAILED"):
                break
            time.sleep(3)
        else:
            result["error"] = f"Timed out after {timeout}s"
            result["status"] = "TIMEOUT"
            result["elapsed_s"] = round(time.time() - start, 1)
            return result

        result["elapsed_s"] = round(time.time() - start, 1)
        result["status"] = final_status

        if final_status == "FAILED":
            result["error"] = "Processing ended with FAILED status"
            return result

        # Fetch ML analysis
        ml_resp = requests.get(
            f"{api}/api/v1/form-checks/{result['form_check_id']}/ml-analysis",
            headers=headers,
        )
        if ml_resp.status_code != 200:
            result["error"] = f"ML analysis fetch failed ({ml_resp.status_code})"
            return result

        ml_data = ml_resp.json()

        # Extract PostureV1 results
        is_shadow = posture_v1_mode == "shadow"
        pv1_key = "posture_v1_shadow" if is_shadow else "posture_v1"
        pv1 = ml_data.get(pv1_key, {})

        if pv1.get("status") == "not_supported":
            result["decision"] = "not_supported"
            return result

        result["decision"] = pv1.get("decision")
        result["prob_fault"] = pv1.get("prob_fault")
        result["confidence"] = pv1.get("confidence")
        result["latency_ms"] = pv1.get("latency_ms")

        preprocessing = pv1.get("preprocessing", {})
        result["missing_ratio"] = preprocessing.get("missing_ratio")
        result["frames_detected"] = preprocessing.get(
            "valid_frame_count", preprocessing.get("sequence_length")
        )
        result["original_frames"] = preprocessing.get("original_frames")
        result["sequence_length"] = preprocessing.get("sequence_length")
        result["duration_sec"] = preprocessing.get("duration_sec")
        result["fps"] = preprocessing.get("fps")
        result["model_complexity"] = preprocessing.get("model_complexity")
        result["pose_complexity_fallback"] = preprocessing.get("pose_complexity_fallback")
        quality = pv1.get("quality", {})
        result["quality_flags"] = quality.get("quality_flags") or []

        if not is_shadow:
            ms = ml_data.get("ml_scores", {})
            result["posture_score"] = ms.get("posture_score")

    except Exception as exc:
        result["error"] = str(exc)
        result["status"] = "ERROR"

    return result


def format_summary_line(r: dict) -> str:
    """Format a single result as a one-line summary."""
    parts = [
        f"{r['filename']:40s}",
        f"{r['exercise_type']:20s}",
        f"{str(r.get('decision') or '?'):12s}",
        f"p={r['prob_fault']:.4f}" if r.get("prob_fault") is not None else "p=?      ",
        f"c={r['confidence']:.3f}" if r.get("confidence") is not None else "c=?    ",
        f"mr={r['missing_ratio']:.3f}" if r.get("missing_ratio") is not None else "mr=?    ",
        f"{r.get('frames_detected', '?')}/{r.get('original_frames', '?')}",
        f"cx={r.get('model_complexity', '?')}",
        f"fb={r.get('pose_complexity_fallback', '?')}",
    ]
    if r.get("error"):
        parts.append(f"ERR: {r['error'][:40]}")
    return " | ".join(parts)


def run_single_mode(args):
    """Original single-video smoke test with full validation output."""
    api = args.api_base.rstrip("/")
    video_path = args.video

    email = os.environ.get("TEST_USER_EMAIL")
    password = os.environ.get("TEST_USER_PASSWORD")
    if not email or not password:
        fail("Set TEST_USER_EMAIL and TEST_USER_PASSWORD environment variables")

    if not os.path.isfile(video_path):
        fail(f"Video file not found: {video_path}")

    # Check API connectivity
    try:
        r = requests.get(f"{api}/health", timeout=5)
        r.raise_for_status()
    except Exception as e:
        fail(f"API not reachable at {api}/health: {e}")

    print(f"API: {api}")
    print(f"Video: {video_path} ({os.path.getsize(video_path) / 1024 / 1024:.1f} MB)")

    # --- Step 1: Authenticate ---
    print("\n[1/6] Authenticating...")
    headers = authenticate(api, email, password)
    print(f"  Authenticated as {email}")

    # --- Step 2: Upload video ---
    print("\n[2/6] Uploading video...")
    exercise_name = EXERCISE_NAME_MAP.get(args.exercise_type, "Low Bar Squat")
    with open(video_path, "rb") as f:
        files = {"video_upload": (os.path.basename(video_path), f)}
        params = {"exercise_name": exercise_name}
        if args.threshold_mode:
            params["threshold_mode"] = args.threshold_mode
        if args.posture_v1_mode:
            params["posture_v1_mode"] = args.posture_v1_mode

        upload_resp = requests.post(
            f"{api}/api/v1/form-checks/submit",
            headers=headers,
            files=files,
            params=params,
            timeout=60,
        )

    if upload_resp.status_code not in (200, 201, 202):
        fail(f"Upload failed ({upload_resp.status_code}): {upload_resp.text}")

    fc_data = upload_resp.json()
    form_check_id = fc_data.get("id")
    video_id = fc_data.get("video_id")
    print(f"  FormCheck ID: {form_check_id}")
    print(f"  Video ID:     {video_id}")
    print(f"  Status:       {fc_data.get('status')}")

    # --- Step 3: Poll for completion ---
    print(f"\n[3/6] Polling for completion (timeout {args.timeout}s)...")
    start = time.time()
    final_status = None
    while time.time() - start < args.timeout:
        poll_resp = requests.get(f"{api}/api/v1/form-checks/{form_check_id}", headers=headers)
        if poll_resp.status_code != 200:
            print(f"  Poll error ({poll_resp.status_code}), retrying...")
            time.sleep(3)
            continue

        poll_data = poll_resp.json()
        final_status = poll_data.get("status", "").upper()
        elapsed = time.time() - start
        print(f"  {elapsed:.0f}s - status: {final_status}")

        if final_status in ("COMPLETED", "FAILED"):
            break
        time.sleep(3)
    else:
        fail(f"Timed out after {args.timeout}s (last status: {final_status})")

    if final_status == "FAILED":
        fail(f"Processing ended with FAILED status: {json.dumps(poll_data, indent=2)}")

    print(f"  Completed in {time.time() - start:.1f}s")

    # --- Step 4: Fetch ML analysis ---
    print(f"\n[4/6] Fetching ML analysis for FormCheck {form_check_id}...")
    ml_resp = requests.get(f"{api}/api/v1/form-checks/{form_check_id}/ml-analysis", headers=headers)
    if ml_resp.status_code != 200:
        fail(f"ML analysis fetch failed ({ml_resp.status_code}): {ml_resp.text}")

    ml_data = ml_resp.json()

    # --- Step 5: Validate results ---
    print("\n[5/6] Validating results...")

    # Check for shadow mode results
    is_shadow = args.posture_v1_mode == "shadow"
    if is_shadow:
        pv1_shadow = ml_data.get("posture_v1_shadow")
        if not pv1_shadow:
            fail("Shadow mode: posture_v1_shadow key missing from ML analysis")
        pv1 = pv1_shadow
        print("  Shadow mode: posture_v1_shadow present")
        # In shadow mode, posture_score should be None (not written)
        ml_scores = ml_data.get("ml_scores", {})
        if ml_scores.get("posture_score") is not None:
            print(f"  WARNING: posture_score is {ml_scores['posture_score']} in shadow mode (expected None)")
    else:
        pv1 = ml_data.get("posture_v1", {})
        if not pv1:
            fail("posture_v1 key missing from ML analysis")

    decision = pv1.get("decision")
    confidence = pv1.get("confidence")
    prob_fault = pv1.get("prob_fault")
    named_scores = pv1.get("named_scores", {})

    assert decision in ("good_form", "fault", "uncertain"), f"Invalid decision: {decision}"
    assert confidence is not None and 0.0 <= confidence <= 1.0, f"Invalid confidence: {confidence}"
    assert prob_fault is not None and 0.0 <= prob_fault <= 1.0, f"Invalid prob_fault: {prob_fault}"

    if decision != "uncertain" and not named_scores:
        print("  WARNING: decision is definitive but named_scores is empty")

    # Verify model_complexity in preprocessing metadata
    preprocessing = pv1.get("preprocessing", {})
    model_complexity = preprocessing.get("model_complexity")
    pose_complexity_fallback = preprocessing.get("pose_complexity_fallback")
    if model_complexity is not None:
        assert model_complexity == 2, f"Expected model_complexity=2, got {model_complexity}"
        print(f"  model_complexity: {model_complexity} (verified)")
    else:
        print("  WARNING: model_complexity not found in preprocessing metadata")
    if pose_complexity_fallback is not None:
        assert pose_complexity_fallback is False, f"Unexpected fallback: {pose_complexity_fallback}"
        print(f"  pose_complexity_fallback: {pose_complexity_fallback}")

    frames_detected = preprocessing.get("valid_frame_count", preprocessing.get("sequence_length", "?"))
    print(f"  frames_detected: {frames_detected}")

    print(f"  decision:    {decision}")
    print(f"  prob_fault:  {prob_fault:.4f}")
    print(f"  confidence:  {confidence:.3f}")
    print(f"  named_scores: {json.dumps(named_scores, indent=4) if named_scores else '{}'}")

    # --- Step 6: Report ---
    print("\n[6/6] Summary")
    print("=" * 50)
    print(f"  FormCheck ID:   {form_check_id}")
    print(f"  Decision:       {decision}")
    print(f"  Prob(fault):    {prob_fault:.4f}")
    print(f"  Confidence:     {confidence:.3f}")
    print(f"  Complexity:     {model_complexity or '?'}")
    print(f"  Frames:         {frames_detected}")
    if not is_shadow:
        ms = ml_data.get("ml_scores", {})
        print(f"  Posture Score:  {ms.get('posture_score')}")
    else:
        print(f"  Mode:           SHADOW (scores not applied)")
    print(f"  Latency:        {pv1.get('latency_ms', '?')}ms")
    print("=" * 50)
    print("\nPASS")


def _infer_folder_label(video_dir: str) -> str:
    """Infer default true label from folder name convention."""
    vd = video_dir.lower()
    if "good" in vd:
        return "good_form"
    if "fault" in vd:
        return "fault"
    if "messy" in vd:
        return "messy"
    return "unknown"


def _compute_metrics(results: list, threshold: float = 0.525, scope: str = "all") -> dict:
    """
    Compute confusion matrix and classification metrics from batch results.

    scope="all" (default): scores good_form vs fault/posture_fault/other_fault.
    scope="posture_only": scores good_form vs fault/posture_fault ONLY.
        Videos labeled "other_fault" (stability, depth) are excluded so they
        don't penalise PostureV1's recall on out-of-scope fault types.

    Videos labeled "messy" or "unknown" are always excluded.
    Videos with decision="uncertain" are counted as abstentions.

    Returns a dict with: scope, TP, FP, TN, FN, uncertain_fault, uncertain_good,
    precision, recall, f1, accuracy, uncertain_rate, borderline_count,
    scorable_n, and per-error details.
    """
    THRESHOLD_MARGIN = 0.05
    all_fault_labels = _POSTURE_FAULT_LABELS | _OTHER_FAULT_LABELS

    if scope == "posture_only":
        # Exclude other_fault (e.g. stability/depth) — PostureV1 doesn't handle them
        in_scope_fault = _POSTURE_FAULT_LABELS
        scorable = [
            r for r in results
            if r.get("label_used") in (_GOOD_FORM_LABELS | _POSTURE_FAULT_LABELS)
        ]
    else:
        # "all": include other_fault as a fault class
        in_scope_fault = all_fault_labels
        scorable = [
            r for r in results
            if r.get("label_used") in (_GOOD_FORM_LABELS | all_fault_labels)
        ]

    TP = FP = TN = FN = unc_fault = unc_good = borderline = 0
    errors = []

    for r in scorable:
        label = r["label_used"]
        pred = r.get("decision") or "unknown"
        prob = r.get("prob_fault")

        if prob is not None and abs(prob - threshold) < THRESHOLD_MARGIN:
            borderline += 1

        if pred == "uncertain":
            if label in in_scope_fault:
                unc_fault += 1
            else:
                unc_good += 1
            continue

        if label in in_scope_fault:
            if pred == "fault":
                TP += 1
            else:
                FN += 1
                errors.append({**r, "_error_type": "FN"})
        else:  # good_form
            if pred == "good_form":
                TN += 1
            else:
                FP += 1
                errors.append({**r, "_error_type": "FP"})

    # The counting loop above encodes this script's scope and abstention
    # POLICY; the arithmetic below comes from app.eval.metrics, which is the
    # single implementation. Four scripts each had their own copy, with
    # different zero-denominator conventions.
    from app.eval.metrics import Counts, coverage_metrics, precision_recall_f1, trivial_floor

    n = len(scorable)
    decided = TP + FP + TN + FN
    c = Counts(tp=TP, fp=FP, tn=TN, fn=FN)
    prec, rec, f1 = precision_recall_f1(c)
    acc = (TP + TN) / decided if decided else 0.0
    unc_rate = (unc_fault + unc_good) / n if n else 0.0

    # These numbers were the COVERED-ONLY view and were reported alone, which
    # flatters a checker that declines whenever it is unsure: the videos it
    # refused simply vanished from the denominator. An unanswered video is an
    # unflagged video, so the abstain-as-negative view is what a user actually
    # experiences. Both are reported now, always, plus the floor.
    _y, _dec = [], []
    for r in scorable:
        _y.append(1 if r["label_used"] in in_scope_fault else 0)
        _pred = r.get("decision") or "unknown"
        _dec.append("uncertain" if _pred == "uncertain"
                    else (1 if _pred == "fault" else 0))
    _cov = coverage_metrics(_y, _dec, abstain_value="uncertain") if _y else None
    _floor = trivial_floor(_y) if _y else None

    return {
        "scope": scope,
        "coverage_view": _cov,
        "trivial_floor": _floor,
        "scorable_n": n,
        "TP": TP, "FP": FP, "TN": TN, "FN": FN,
        "uncertain_fault": unc_fault, "uncertain_good": unc_good,
        "precision": round(prec, 3),
        "recall": round(rec, 3),
        "f1": round(f1, 3),
        "accuracy": round(acc, 3),
        "uncertain_rate": round(unc_rate, 3),
        "borderline_count": borderline,
        "errors": errors,
    }


def _build_review_queue(
    results: list,
    threshold: float = 0.525,
    video_dir: str = "",
) -> list:
    """
    Build a prioritized list of videos that warrant human visual review.

    Priority 1 — High-confidence FP:
        prob_fault >= 0.70, labeled good_form, decision=fault.
        Likely a model error or unusual filming angle; confirm and add to training data.

    Priority 2 — High-confidence FN:
        prob_fault <= 0.30, labeled posture_fault/fault, decision=good_form.
        Likely a dataset label error or an edge case the model misses.

    Priority 3 — Borderline:
        abs(prob_fault - threshold) < 0.05.
        Model is near-coin-flip; worth a quick watch to confirm label.

    Each entry contains: priority, reason, filename, folder_label, label_used,
    decision, prob_fault, confidence, missing_ratio, duration_sec, flags,
    abs_path, suggested_action.

    Returns entries sorted by priority (asc) then confidence (desc).
    """
    HCONF_FP_THRESH = 0.70
    HCONF_FN_THRESH = 0.30
    BORDERLINE_MARGIN = 0.05
    all_fault_labels = _POSTURE_FAULT_LABELS | _OTHER_FAULT_LABELS

    SUGGESTED_ACTIONS = {
        1: "Confirm good form → add to training data as good_form if confirmed",
        2: "Confirm label → add to training data as posture_fault if label correct, "
           "else update labels_override.json to good_form",
        3: "Watch video → determine true label (good_form or posture_fault)",
    }

    seen: set = set()
    queue: list = []

    def _entry(r: dict, priority: int, reason: str) -> dict:
        abs_path = str(Path(video_dir) / r["filename"]) if video_dir else r["filename"]
        return {
            "priority": priority,
            "reason": reason,
            "filename": r["filename"],
            "folder_label": r.get("folder_label", ""),
            "label_used": r.get("label_used", ""),
            "decision": r.get("decision", ""),
            "prob_fault": r.get("prob_fault"),
            "confidence": r.get("confidence"),
            "missing_ratio": r.get("missing_ratio"),
            "duration_sec": r.get("duration_sec"),
            "flags": r.get("quality_flags") or [],
            "abs_path": abs_path,
            "suggested_action": SUGGESTED_ACTIONS.get(priority, "Review needed"),
        }

    for r in results:
        if r.get("status") != "COMPLETED":
            continue
        fn = r.get("filename", "")
        prob = r.get("prob_fault")
        label = r.get("label_used", "")
        decision = r.get("decision", "")

        if prob is None:
            continue

        # P1: high-confidence FP
        if (
            prob >= HCONF_FP_THRESH
            and label in _GOOD_FORM_LABELS
            and decision == "fault"
            and fn not in seen
        ):
            seen.add(fn)
            queue.append(_entry(r, 1, f"high_conf_FP: prob_fault={prob:.4f} labeled_as=good_form"))

        # P2: high-confidence FN (not already added as P1)
        elif (
            prob <= HCONF_FN_THRESH
            and label in all_fault_labels
            and decision == "good_form"
            and fn not in seen
        ):
            seen.add(fn)
            queue.append(_entry(r, 2, f"high_conf_FN: prob_fault={prob:.4f} labeled_as={label}"))

        # P3: borderline (not already in queue)
        if fn not in seen and abs(prob - threshold) < BORDERLINE_MARGIN:
            seen.add(fn)
            queue.append(_entry(r, 3, f"borderline: prob_fault={prob:.4f} (threshold±{BORDERLINE_MARGIN})"))

    # Sort: priority asc, then confidence desc
    queue.sort(key=lambda x: (x["priority"], -(x["confidence"] or 0.0)))
    return queue


def run_batch_mode(args):
    """Batch mode: process all videos in a directory."""
    api = args.api_base.rstrip("/")
    video_dir = args.video_dir

    email = os.environ.get("TEST_USER_EMAIL")
    password = os.environ.get("TEST_USER_PASSWORD")
    if not email or not password:
        fail("Set TEST_USER_EMAIL and TEST_USER_PASSWORD environment variables")

    if not os.path.isdir(video_dir):
        fail(f"Video directory not found: {video_dir}")

    # Check API connectivity
    try:
        r = requests.get(f"{api}/health", timeout=5)
        r.raise_for_status()
    except Exception as e:
        fail(f"API not reachable at {api}/health: {e}")

    # Load labels override if provided
    labels_override: dict = {}
    if args.labels_override:
        try:
            with open(args.labels_override) as f:
                raw = json.load(f)
            labels_override = {k: v for k, v in raw.items() if not k.startswith("_")}
            print(f"Labels override loaded: {args.labels_override} ({len(labels_override)} entries)")
        except Exception as e:
            fail(f"Failed to load labels override: {e}")

    # Infer default label from folder name
    folder_label = _infer_folder_label(video_dir)

    # Discover video files
    video_files = sorted(
        p for p in Path(video_dir).iterdir()
        if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS
    )

    if not video_files:
        fail(f"No video files found in {video_dir} (extensions: {VIDEO_EXTENSIONS})")

    if args.max and args.max < len(video_files):
        video_files = video_files[: args.max]

    exercise_name = EXERCISE_NAME_MAP.get(args.exercise_type, "Low Bar Squat")

    print(f"API:           {api}")
    print(f"Video dir:     {video_dir}")
    print(f"Videos found:  {len(video_files)}")
    print(f"Exercise:      {exercise_name}")
    print(f"Threshold:     {args.threshold_mode or 'default'}")
    print(f"PV1 mode:      {args.posture_v1_mode or 'active'}")
    print(f"Folder label:  {folder_label}")
    if labels_override:
        print(f"Overrides:     {len(labels_override)} filename(s)")

    # Authenticate once
    print("\nAuthenticating...")
    headers = authenticate(api, email, password)
    print(f"  Authenticated as {email}")

    # Process each video
    results = []
    print(f"\nProcessing {len(video_files)} videos...")
    print("-" * 130)
    header = (
        f"{'Filename':40s} | {'Exercise':20s} | {'Decision':12s} | "
        f"{'ProbFault':9s} | {'Conf':7s} | {'MissR':8s} | "
        f"{'Frames':9s} | {'Dur':6s} | {'Cx':4s} | {'FB':5s} | {'Label':10s}"
    )
    print(header)
    print("-" * 130)

    for i, vf in enumerate(video_files, 1):
        print(f"\n[{i}/{len(video_files)}] {vf.name}")
        r = process_single_video(
            api=api,
            headers=headers,
            video_path=str(vf),
            exercise_name=exercise_name,
            threshold_mode=args.threshold_mode,
            posture_v1_mode=args.posture_v1_mode,
            timeout=args.timeout,
            verbose=True,
        )
        # Attach labels for metrics (override takes precedence over folder default)
        r["folder_label"] = folder_label  # raw folder-inferred default
        r["label_used"] = labels_override.get(vf.name, folder_label)
        # Borderline flag: abs(prob_fault - threshold) < 0.05
        prob = r.get("prob_fault")
        r["borderline"] = (prob is not None and abs(prob - 0.525) < 0.05)
        results.append(r)

        dur_str = f"{r['duration_sec']:.1f}s" if r.get("duration_sec") is not None else "?"
        print(
            f"  -> {format_summary_line(r)} | dur={dur_str} | label={r['label_used']}"
            + (f" | flags={r['quality_flags']}" if r.get("quality_flags") else "")
        )

    # ── Summary statistics ──────────────────────────────────────────────────
    print("\n" + "=" * 130)
    print("BATCH SUMMARY")
    print("=" * 130)

    total = len(results)
    completed = [r for r in results if r["status"] == "COMPLETED"]
    failed = [r for r in results if r.get("error")]
    decisions: dict = {}
    for r in completed:
        d = r.get("decision") or "unknown"
        decisions[d] = decisions.get(d, 0) + 1

    print(f"  Total:          {total}")
    print(f"  Completed:      {len(completed)}")
    print(f"  Failed/Error:   {len(failed)}")
    print(f"  Decisions:      {json.dumps(decisions)}")

    prob_faults = [r["prob_fault"] for r in completed if r.get("prob_fault") is not None]
    if prob_faults:
        print(f"  Avg prob_fault: {sum(prob_faults) / len(prob_faults):.4f}")
        print(f"  Min prob_fault: {min(prob_faults):.4f}")
        print(f"  Max prob_fault: {max(prob_faults):.4f}")

    complexities = [r["model_complexity"] for r in completed if r.get("model_complexity") is not None]
    if complexities:
        cx_counts: dict = {}
        for c in complexities:
            cx_counts[c] = cx_counts.get(c, 0) + 1
        print(f"  Complexity:     {json.dumps(cx_counts)}")

    fallbacks = [r["pose_complexity_fallback"] for r in completed if r.get("pose_complexity_fallback") is not None]
    if fallbacks:
        fb_true = sum(1 for f in fallbacks if f)
        print(f"  Fallbacks:      {fb_true}/{len(fallbacks)}")

    latencies = [r["latency_ms"] for r in completed if r.get("latency_ms") is not None]
    if latencies:
        print(f"  Avg latency:    {sum(latencies) / len(latencies):.0f}ms")

    borderlines = [r for r in completed if r.get("borderline")]
    print(f"  Borderline:     {len(borderlines)} (|prob_fault-0.525|<0.05)")

    # ── Confusion matrix (requires label_used) ───────────────────────────────
    scope = getattr(args, "metrics_scope", "all") or "all"
    metrics = _compute_metrics(completed, scope=scope)
    if metrics["scorable_n"] > 0:
        scope_label = "posture_only (excl. other_fault)" if scope == "posture_only" else "all faults"
        print(f"\n  CONFUSION MATRIX (n={metrics['scorable_n']}, scope={scope_label})")
        print(f"  {'':25s}  Pred: fault   Pred: good_form")
        print(f"  {'True: fault':25s}       {metrics['TP']:2d}           {metrics['FN']:2d}   (+ {metrics['uncertain_fault']} uncertain)")
        print(f"  {'True: good_form':25s}       {metrics['FP']:2d}           {metrics['TN']:2d}   (+ {metrics['uncertain_good']} uncertain)")
        print(f"\n  Precision: {metrics['precision']:.3f}  Recall: {metrics['recall']:.3f}  "
              f"F1: {metrics['f1']:.3f}  Accuracy: {metrics['accuracy']:.3f}  "
              f"UncertainRate: {metrics['uncertain_rate']:.3f}")

        if metrics["errors"]:
            print(f"\n  WRONG CASES ({len(metrics['errors'])}):")
            for e in metrics["errors"]:
                flags_str = str(e.get("quality_flags") or [])
                dur_str = f"{e['duration_sec']:.1f}s" if e.get("duration_sec") is not None else "?"
                print(
                    f"    [{e['_error_type']}] {e['filename']}  "
                    f"label={e['label_used']}  pred={e['decision']}  "
                    f"prob={e.get('prob_fault', '?'):.4f}  conf={e.get('confidence', '?'):.3f}  "
                    f"dur={dur_str}  flags={flags_str}"
                )

    print("=" * 130)

    # ── Build review queue ──────────────────────────────────────────────────
    review_queue = _build_review_queue(completed, threshold=0.525, video_dir=video_dir)
    if review_queue:
        print(f"\n  REVIEW QUEUE ({len(review_queue)} videos need human review):")
        for i, item in enumerate(review_queue, 1):
            print(
                f"    [{i}] P{item['priority']} {item['filename']}  "
                f"label={item['label_used']}  decision={item['decision']}  "
                f"prob={item['prob_fault']:.4f}  conf={item.get('confidence', 0):.3f}  "
                f"— {item['reason']}"
            )
        print(f"\n  Suggested actions printed in review_queue.json")
    else:
        print("\n  REVIEW QUEUE: empty (no high-confidence errors or borderline cases)")

    # ── Write JSON report ───────────────────────────────────────────────────
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "api_base": api,
        "video_dir": str(video_dir),
        "exercise_type": args.exercise_type,
        "threshold_mode": args.threshold_mode,
        "posture_v1_mode": args.posture_v1_mode,
        "labels_override_path": str(args.labels_override) if args.labels_override else None,
        "folder_label": folder_label,
        "metrics_scope": scope,
        "total_videos": total,
        "completed": len(completed),
        "failed": len(failed),
        "decisions": decisions,
        "metrics": {k: v for k, v in metrics.items() if k != "errors"},
        "review_queue_count": len(review_queue),
        "results": results,
    }
    report_path = OUTPUT_DIR / "e2e_posture_v1_batch_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nReport written to: {report_path}")

    # Write review queue as a standalone file
    review_queue_path = OUTPUT_DIR / "review_queue.json"
    review_queue_doc = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "video_dir": str(video_dir),
        "threshold": 0.525,
        "total_in_queue": len(review_queue),
        "priority_summary": {
            "P1_high_conf_FP": sum(1 for x in review_queue if x["priority"] == 1),
            "P2_high_conf_FN": sum(1 for x in review_queue if x["priority"] == 2),
            "P3_borderline": sum(1 for x in review_queue if x["priority"] == 3),
        },
        "how_to_open": "python scripts/open_review_videos.py [--priority 1]",
        "how_to_update_labels": (
            "Edit backend/test_videos/labels_override.json — "
            "valid values: good_form, posture_fault, other_fault, messy"
        ),
        "items": review_queue,
    }
    with open(review_queue_path, "w") as f:
        json.dump(review_queue_doc, f, indent=2, default=str)
    print(f"Review queue written to: {review_queue_path}")

    if failed:
        print(f"\nWARNING: {len(failed)} video(s) had errors")
        for r in failed:
            print(f"  {r['filename']}: {r['error']}")

    print(f"\n{'PASS' if not failed else 'PARTIAL PASS'}")


def main():
    parser = argparse.ArgumentParser(
        description="E2E PostureV1 smoke test (single or batch)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Single video:
    python scripts/e2e_posture_v1_smoke.py --video squat.mp4

  Batch (all videos in directory):
    python scripts/e2e_posture_v1_smoke.py --video-dir /data/test_videos/

  Batch with limits:
    python scripts/e2e_posture_v1_smoke.py --video-dir /data/test_videos/ --max 5

  Non-squat exercise:
    python scripts/e2e_posture_v1_smoke.py --video deadlift.mp4 --exercise-type deadlift
        """,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--video", help="Path to a single video file (MP4/MOV/WebM)")
    group.add_argument("--video-dir", help="Directory containing video files for batch processing")
    parser.add_argument("--api-base", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--threshold-mode", default=None, choices=["default", "strict", "safety"])
    parser.add_argument("--posture-v1-mode", default=None, choices=["active", "shadow"])
    parser.add_argument("--exercise-type", default="squat",
                        choices=list(EXERCISE_NAME_MAP.keys()),
                        help="Exercise type to submit (default: squat)")
    parser.add_argument("--max", type=int, default=None, help="Max videos to process in batch mode")
    parser.add_argument("--timeout", type=int, default=120, help="Max seconds to wait per video")
    parser.add_argument(
        "--labels-override",
        default=None,
        metavar="PATH",
        help="JSON file mapping filename -> true_label for evaluation metrics only (does not affect inference)",
    )
    parser.add_argument(
        "--metrics-scope",
        default="all",
        choices=["all", "posture_only"],
        dest="metrics_scope",
        help=(
            "Confusion-matrix scope: "
            "'all' scores good_form vs fault/posture_fault/other_fault; "
            "'posture_only' scores good_form vs fault/posture_fault only "
            "(excludes other_fault like stability/depth faults). "
            "Default: all"
        ),
    )
    args = parser.parse_args()

    if args.video:
        run_single_mode(args)
    else:
        run_batch_mode(args)


if __name__ == "__main__":
    main()
