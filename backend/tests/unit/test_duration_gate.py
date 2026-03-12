"""Unit tests for PostureV1 duration gate and labels-override isolation.

Tests the behavioral contract of ``_apply_duration_gate`` from
``app.tasks.analysis_tasks``.  The function is a pure, stateless utility
(6 lines of Python with no external dependencies), so it is replicated
inline here to avoid importing the heavyweight Celery/DB-bound module and
polluting ``sys.modules`` for the rest of the test session.

Maintenance note
----------------
If ``_apply_duration_gate`` changes in ``analysis_tasks.py``, update the
``_apply_duration_gate`` definition in this file to match.  The docstring
contract and tests describe the expected behaviour — both the inline copy
and the real implementation must satisfy them.
"""

# ---------------------------------------------------------------------------
# Reference implementation (mirrors analysis_tasks._apply_duration_gate).
# Kept inline to avoid sys.modules pollution from importing analysis_tasks.
# ---------------------------------------------------------------------------

def _apply_duration_gate(
    pv1_decision: str,
    pv1_confidence: float,
    quality_flags: list,
    n_frames: int,
    fps: float,
    is_squat: bool,
    gate_sec: float = 6.5,
) -> tuple:
    """
    Behavioral contract of ``analysis_tasks._apply_duration_gate``.

    If ``is_squat`` AND ``n_frames / max(fps, 1.0) > gate_sec``
    AND ``pv1_decision != 'uncertain'``:
      - ``decision``  → ``"uncertain"``
      - ``confidence`` → ``0.0``
      - ``"duration_too_long_single_rep"`` appended to ``quality_flags``

    The caller's ``quality_flags`` list is never mutated; a copy is returned.

    gate_sec default is 6.5 (0.5 s above product max of 6 s) to absorb
    setInterval drift from the frontend MediaRecorder auto-stop.

    Returns:
        (decision, confidence, quality_flags_copy, rep_duration_sec)
    """
    rep_duration_sec = n_frames / max(fps, 1.0)
    flags = list(quality_flags)  # copy; never mutate caller's list
    if is_squat and rep_duration_sec > gate_sec and pv1_decision != "uncertain":
        pv1_decision = "uncertain"
        pv1_confidence = 0.0
        flags.append("duration_too_long_single_rep")
    return pv1_decision, pv1_confidence, flags, rep_duration_sec


# ===========================================================================
# Tests: _apply_duration_gate
# ===========================================================================

class TestDurationGate:
    """
    Unit tests for the PostureV1 slow-cadence duration gate.

    Contract:
      If is_squat AND n_frames/fps > gate_sec AND decision != "uncertain":
        → decision  = "uncertain"
        → confidence = 0.0
        → "duration_too_long_single_rep" appended to quality_flags (copy)
    """

    # ------------------------------------------------------------------
    # Triggering cases
    # ------------------------------------------------------------------

    def test_triggers_on_slow_squat_fault(self):
        """200 frames @ 24 fps = 8.33 s > 6.0 s → gate fires on fault decision."""
        dec, conf, flags, dur = _apply_duration_gate(
            pv1_decision="fault",
            pv1_confidence=0.90,
            quality_flags=[],
            n_frames=200,
            fps=24.0,
            is_squat=True,
        )
        assert dec == "uncertain", f"Expected uncertain, got {dec!r}"
        assert conf == 0.0
        assert "duration_too_long_single_rep" in flags
        assert abs(dur - 200 / 24.0) < 1e-6

    def test_triggers_on_slow_squat_good_form(self):
        """Good-form on a 9-second squat is also gated → uncertain (VFcZv4SOBJE case)."""
        dec, conf, flags, dur = _apply_duration_gate(
            pv1_decision="good_form",
            pv1_confidence=0.75,
            quality_flags=[],
            n_frames=270,
            fps=30.0,
            is_squat=True,
        )
        # 270 / 30 = 9.0 s > 6.5 s
        assert dec == "uncertain"
        assert conf == 0.0
        assert "duration_too_long_single_rep" in flags
        assert abs(dur - 9.0) < 1e-6

    def test_triggers_with_custom_gate_sec(self):
        """gate_sec=4.0 fires on a 5-second squat that would pass the default gate."""
        dec, conf, flags, dur = _apply_duration_gate(
            pv1_decision="fault",
            pv1_confidence=0.85,
            quality_flags=[],
            n_frames=150,
            fps=30.0,
            is_squat=True,
            gate_sec=4.0,   # 5.0 s > 4.0 s → triggers
        )
        assert dec == "uncertain"
        assert "duration_too_long_single_rep" in flags

    def test_zero_fps_uses_floor_of_one(self):
        """fps=0.0 uses max(fps, 1.0)=1.0 fallback to avoid division-by-zero.

        10 frames / 1.0 = 10.0 s > 6.5 s → gate fires.
        """
        dec, conf, flags, dur = _apply_duration_gate(
            pv1_decision="fault",
            pv1_confidence=0.9,
            quality_flags=[],
            n_frames=10,
            fps=0.0,
            is_squat=True,
        )
        assert dec == "uncertain"
        assert abs(dur - 10.0) < 1e-6

    # ------------------------------------------------------------------
    # Non-triggering cases
    # ------------------------------------------------------------------

    def test_no_trigger_below_threshold(self):
        """150 frames @ 30 fps = 5.0 s ≤ 6.5 s: gate does NOT fire."""
        dec, conf, flags, dur = _apply_duration_gate(
            pv1_decision="fault",
            pv1_confidence=0.85,
            quality_flags=[],
            n_frames=150,
            fps=30.0,
            is_squat=True,
        )
        assert dec == "fault"
        assert conf == 0.85
        assert "duration_too_long_single_rep" not in flags
        assert abs(dur - 5.0) < 1e-6

    def test_no_trigger_in_drift_zone(self):
        """183 frames @ 30 fps = 6.1 s: within the 0.5 s drift margin, gate must NOT fire.

        Frontend setInterval drift produces blobs ~6.05–6.15 s when recording
        stops at the 6-second tick. The gate_sec=6.5 absorbs this without
        incorrectly gating valid 6-second clips.
        """
        dec, conf, flags, dur = _apply_duration_gate(
            pv1_decision="fault",
            pv1_confidence=0.85,
            quality_flags=[],
            n_frames=183,
            fps=30.0,
            is_squat=True,
        )
        assert dec == "fault", "6.1 s clip (drift zone) must NOT trigger the gate"
        assert "duration_too_long_single_rep" not in flags
        assert abs(dur - 6.1) < 1e-6

    def test_no_trigger_exactly_at_threshold(self):
        """195 frames @ 30 fps = exactly 6.5 s: gate requires STRICTLY >, no fire."""
        dec, conf, flags, dur = _apply_duration_gate(
            pv1_decision="fault",
            pv1_confidence=0.85,
            quality_flags=[],
            n_frames=195,
            fps=30.0,
            is_squat=True,
        )
        assert dec == "fault", "Exactly 6.5 s must NOT trigger the gate (strict >)"
        assert "duration_too_long_single_rep" not in flags
        assert abs(dur - 6.5) < 1e-6

    def test_no_trigger_for_non_squat(self):
        """Non-squat with 10 s duration: gate is squat-only, must not fire."""
        dec, conf, flags, dur = _apply_duration_gate(
            pv1_decision="fault",
            pv1_confidence=0.9,
            quality_flags=[],
            n_frames=300,
            fps=30.0,
            is_squat=False,
        )
        assert dec == "fault"
        assert conf == 0.9
        assert "duration_too_long_single_rep" not in flags

    def test_no_trigger_when_already_uncertain(self):
        """Already-uncertain decisions skip the gate (condition: decision != 'uncertain')."""
        dec, conf, flags, dur = _apply_duration_gate(
            pv1_decision="uncertain",
            pv1_confidence=0.0,
            quality_flags=["low_quality"],
            n_frames=300,
            fps=24.0,
            is_squat=True,
        )
        assert dec == "uncertain"
        assert "duration_too_long_single_rep" not in flags, (
            "Gate must not double-flag already-uncertain results"
        )

    # ------------------------------------------------------------------
    # Side-effect / purity
    # ------------------------------------------------------------------

    def test_does_not_mutate_input_flags(self):
        """The caller's quality_flags list must never be mutated."""
        original = ["existing_flag"]
        _apply_duration_gate(
            pv1_decision="fault",
            pv1_confidence=0.9,
            quality_flags=original,
            n_frames=300,
            fps=24.0,
            is_squat=True,
        )
        assert original == ["existing_flag"], (
            "_apply_duration_gate mutated the caller's quality_flags list"
        )

    def test_existing_flags_preserved_when_gate_fires(self):
        """Pre-existing flags are kept in the returned list when gate fires."""
        dec, conf, flags, dur = _apply_duration_gate(
            pv1_decision="fault",
            pv1_confidence=0.9,
            quality_flags=["pre_existing_flag"],
            n_frames=270,
            fps=30.0,
            is_squat=True,
        )
        assert "pre_existing_flag" in flags
        assert "duration_too_long_single_rep" in flags

    def test_duration_sec_computed_correctly(self):
        """rep_duration_sec = n_frames / max(fps, 1.0) is returned as 4th element."""
        cases = [
            (90,  30.0,  3.0),
            (89,  29.97, 89 / 29.97),
            (100, 25.0,  4.0),
        ]
        for n, fps, expected_dur in cases:
            _, _, _, dur = _apply_duration_gate(
                pv1_decision="fault",
                pv1_confidence=0.8,
                quality_flags=[],
                n_frames=n,
                fps=fps,
                is_squat=False,   # non-squat so gate can't fire
            )
            assert abs(dur - expected_dur) < 1e-4, (
                f"n={n}, fps={fps}: expected {expected_dur:.4f}, got {dur:.4f}"
            )

    def test_real_case_VFcZv4SOBJE(self):
        """Regression: VFcZv4SOBJE (218 frames, 23.98 fps → 9.09 s) gates to uncertain."""
        dec, conf, flags, dur = _apply_duration_gate(
            pv1_decision="fault",
            pv1_confidence=0.117,
            quality_flags=["padded_82_frames"],
            n_frames=218,
            fps=23.98,
            is_squat=True,
        )
        assert dec == "uncertain"
        assert conf == 0.0
        assert "duration_too_long_single_rep" in flags
        assert abs(dur - 218 / 23.98) < 0.01

    def test_boundary_case_exactly_6s_does_not_gate(self):
        """0o2LX-quNZk: 150 frames @ 25 fps = exactly 6.0 s — no gate."""
        dec, conf, flags, dur = _apply_duration_gate(
            pv1_decision="good_form",
            pv1_confidence=0.387,
            quality_flags=["padded_150_frames"],
            n_frames=150,
            fps=25.0,
            is_squat=True,
        )
        assert dec == "good_form", "Exactly 6.0 s must NOT be gated"
        assert abs(dur - 6.0) < 1e-6


# ===========================================================================
# Tests: Labels-override isolation
# ===========================================================================

class TestLabelsOverrideIsolation:
    """
    Verify that the labels-override mechanism (from e2e_posture_v1_smoke.py)
    only changes the *evaluation* label and never affects inference outputs.

    The label override is applied as:
        label_used = labels_override.get(filename, folder_label)

    Inference fields (prob_fault, predicted, confidence) come from the model
    and must remain identical regardless of label_used.
    """

    @staticmethod
    def _apply_override(filename: str, folder_label: str, override: dict) -> str:
        """Replicates label_used assignment from e2e_posture_v1_smoke.run_batch_mode()."""
        return override.get(filename, folder_label)

    def test_override_replaces_folder_label(self):
        """Override entry replaces the folder-inferred label for that file."""
        override = {"RClKKQqsvXA_good_rep_1.mp4": "messy"}
        label_used = self._apply_override("RClKKQqsvXA_good_rep_1.mp4", "good_form", override)
        assert label_used == "messy"

    def test_no_override_keeps_folder_label(self):
        """When filename is absent from override, the folder label is used."""
        override = {"other.mp4": "good_form"}
        label_used = self._apply_override("test_video.mp4", "fault", override)
        assert label_used == "fault"

    def test_empty_override_never_changes_labels(self):
        """Empty override dict must leave all labels unchanged."""
        override = {}
        for filename, folder_label in [
            ("video_a.mp4", "good_form"),
            ("video_b.mp4", "fault"),
            ("video_c.mp4", "messy"),
        ]:
            assert self._apply_override(filename, folder_label, override) == folder_label

    def test_inference_fields_independent_of_label(self):
        """Inference outputs (prob_fault, predicted, confidence) must not change
        when label_used is overridden.

        Simulates the result dict produced by process_single_video() in
        e2e_posture_v1_smoke.py where label_used is attached post-inference.
        """
        # Simulate fixed inference output from the model
        inference = {
            "filename": "RClKKQqsvXA_good_rep_1.mp4",
            "predicted": "fault",
            "prob_fault": 0.5702,
            "confidence": 0.141,
        }

        # Apply override (changes label_used only)
        override = {"RClKKQqsvXA_good_rep_1.mp4": "messy"}
        label_used = self._apply_override(
            inference["filename"], "good_form", override
        )

        # label changed for evaluation purposes
        assert label_used == "messy"

        # inference fields completely unaffected
        assert inference["predicted"]  == "fault"
        assert inference["prob_fault"] == 0.5702
        assert inference["confidence"] == 0.141

    def test_multiple_overrides_applied_correctly(self):
        """All override entries are applied to their respective files."""
        override = {
            "1663_posture_fault_1.mp4": "good_form",
            "1664_posture_fault_1.mp4": "good_form",
            "1673_posture_fault_1.mp4": "good_form",
            "RClKKQqsvXA_good_rep_1.mp4": "messy",
        }
        cases = [
            ("1663_posture_fault_1.mp4",     "fault",      "good_form"),
            ("1664_posture_fault_1.mp4",     "fault",      "good_form"),
            ("1673_posture_fault_1.mp4",     "fault",      "good_form"),
            ("RClKKQqsvXA_good_rep_1.mp4",  "good_form",  "messy"),
            ("other_video.mp4",             "fault",      "fault"),    # not overridden
        ]
        for filename, folder_label, expected_label_used in cases:
            got = self._apply_override(filename, folder_label, override)
            assert got == expected_label_used, (
                f"{filename}: expected label_used={expected_label_used!r}, got {got!r}"
            )


# ===========================================================================
# Tests: _infer_folder_label contract
# ===========================================================================

class TestInferFolderLabel:
    """
    Tests for the _infer_folder_label logic (e2e_posture_v1_smoke.py).

    Contract:
      - Path containing 'good'  → 'good_form'
      - Path containing 'fault' → 'fault'
      - Path containing 'messy' → 'messy'
      - Otherwise               → 'unknown'
    Priority order: good > fault > messy (first match wins).
    """

    @staticmethod
    def _infer(path: str) -> str:
        """Replica of _infer_folder_label from e2e_posture_v1_smoke.py."""
        p = path.lower()
        if "good"  in p: return "good_form"
        if "fault" in p: return "fault"
        if "messy" in p: return "messy"
        return "unknown"

    def test_good_folder_variants(self):
        assert self._infer("/videos/good") == "good_form"
        assert self._infer("/videos/good_rep") == "good_form"
        assert self._infer("/videos/Good_Form") == "good_form"   # case-insensitive
        assert self._infer("/test_videos/good/") == "good_form"

    def test_fault_folder_variants(self):
        assert self._infer("/videos/fault") == "fault"
        assert self._infer("/videos/posture_fault_1") == "fault"
        assert self._infer("/Penn_Action/Fault") == "fault"

    def test_messy_folder(self):
        assert self._infer("/videos/messy") == "messy"
        assert self._infer("/videos/MESSY_reps") == "messy"

    def test_unknown_folder(self):
        assert self._infer("/videos/unlabeled") == "unknown"
        assert self._infer("/tmp/random") == "unknown"
        assert self._infer("") == "unknown"

    def test_good_takes_priority_over_fault(self):
        """If path contains both 'good' and 'fault', 'good_form' wins."""
        assert self._infer("/good_fault_test") == "good_form"


# ===========================================================================
# Tests: _compute_metrics contract
# ===========================================================================

class TestComputeMetrics:
    """
    Tests for the _compute_metrics confusion-matrix helper (e2e_posture_v1_smoke.py).

    Contract:
    - Only videos with label_used in ("good_form", "fault") are counted.
    - "messy"/"unknown" labels are excluded.
    - "uncertain" decisions are counted separately (abstain), not in TP/FP/TN/FN.
    - Borderline: abs(prob_fault - threshold) < 0.05
    """

    THRESHOLD = 0.525
    THRESHOLD_MARGIN = 0.05

    def _compute(self, results):
        """Inline replica of _compute_metrics from e2e_posture_v1_smoke.py."""
        scorable = [r for r in results if r.get("label_used") in ("good_form", "fault")]
        TP = FP = TN = FN = unc_fault = unc_good = borderline = 0
        errors = []
        for r in scorable:
            label = r["label_used"]
            pred  = r.get("decision") or "unknown"
            prob  = r.get("prob_fault")
            if prob is not None and abs(prob - self.THRESHOLD) < self.THRESHOLD_MARGIN:
                borderline += 1
            if pred == "uncertain":
                if label == "fault": unc_fault += 1
                else:                unc_good  += 1
                continue
            if label == "fault":
                if pred == "fault": TP += 1
                else:               FN += 1; errors.append({**r, "_error_type": "FN"})
            else:
                if pred == "good_form": TN += 1
                else:                   FP += 1; errors.append({**r, "_error_type": "FP"})
        n = len(scorable)
        decided = TP + FP + TN + FN
        prec = TP / (TP + FP) if (TP + FP) else 0.0
        rec  = TP / (TP + FN) if (TP + FN) else 0.0
        f1   = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        acc  = (TP + TN) / decided if decided else 0.0
        unc_rate = (unc_fault + unc_good) / n if n else 0.0
        return {
            "scorable_n": n,
            "TP": TP, "FP": FP, "TN": TN, "FN": FN,
            "uncertain_fault": unc_fault, "uncertain_good": unc_good,
            "precision": round(prec, 3), "recall": round(rec, 3),
            "f1": round(f1, 3), "accuracy": round(acc, 3),
            "uncertain_rate": round(unc_rate, 3),
            "borderline_count": borderline, "errors": errors,
        }

    def _r(self, label_used, decision, prob_fault):
        return {"label_used": label_used, "decision": decision,
                "prob_fault": prob_fault, "filename": "test.mp4"}

    def test_perfect_classifier(self):
        results = [
            self._r("fault",     "fault",     0.80),
            self._r("fault",     "fault",     0.75),
            self._r("good_form", "good_form", 0.20),
            self._r("good_form", "good_form", 0.15),
        ]
        m = self._compute(results)
        assert m["TP"] == 2 and m["FP"] == 0 and m["TN"] == 2 and m["FN"] == 0
        assert m["precision"] == 1.0
        assert m["recall"]    == 1.0
        assert m["f1"]        == 1.0
        assert m["accuracy"]  == 1.0

    def test_messy_excluded(self):
        results = [
            self._r("messy",     "fault",     0.80),   # excluded
            self._r("unknown",   "good_form", 0.10),   # excluded
            self._r("good_form", "good_form", 0.20),   # counted
        ]
        m = self._compute(results)
        assert m["scorable_n"] == 1
        assert m["TN"] == 1

    def test_uncertain_counted_separately(self):
        results = [
            self._r("fault",     "uncertain", 0.50),   # abstain
            self._r("good_form", "uncertain", 0.50),   # abstain
            self._r("good_form", "good_form", 0.20),
        ]
        m = self._compute(results)
        assert m["TP"] == 0 and m["FP"] == 0
        assert m["uncertain_fault"] == 1
        assert m["uncertain_good"]  == 1
        assert m["TN"] == 1

    def test_borderline_count(self):
        """prob_fault within 0.05 of threshold (0.525) is borderline."""
        results = [
            self._r("fault",     "fault",     0.55),    # |0.55-0.525|=0.025 → borderline
            self._r("fault",     "fault",     0.80),    # not borderline
            self._r("good_form", "good_form", 0.50),    # |0.50-0.525|=0.025 → borderline
        ]
        m = self._compute(results)
        assert m["borderline_count"] == 2

    def test_false_positive_logged_in_errors(self):
        results = [self._r("good_form", "fault", 0.60)]
        m = self._compute(results)
        assert m["FP"] == 1
        assert len(m["errors"]) == 1
        assert m["errors"][0]["_error_type"] == "FP"

    def test_false_negative_logged_in_errors(self):
        results = [self._r("fault", "good_form", 0.40)]
        m = self._compute(results)
        assert m["FN"] == 1
        assert len(m["errors"]) == 1
        assert m["errors"][0]["_error_type"] == "FN"

    def test_empty_results(self):
        m = self._compute([])
        assert m["scorable_n"] == 0
        assert m["TP"] == m["FP"] == m["TN"] == m["FN"] == 0

    def test_all_uncertain(self):
        results = [
            self._r("fault",     "uncertain", 0.50),
            self._r("good_form", "uncertain", 0.50),
        ]
        m = self._compute(results)
        assert m["TP"] == m["FP"] == m["TN"] == m["FN"] == 0
        assert m["uncertain_fault"] == 1
        assert m["uncertain_good"]  == 1
        assert m["uncertain_rate"]  == 1.0


# ===========================================================================
# Tests: Scope-aware _compute_metrics  (scope="posture_only" vs scope="all")
# ===========================================================================

class TestComputeMetricsScope:
    """
    Tests for the scope-aware _compute_metrics added in the review-queue
    hardening pass (Feb 2026).

    scope="posture_only": scorable = {good_form, fault, posture_fault}
                          other_fault is excluded so stability/depth faults
                          don't penalise PostureV1 recall.
    scope="all":          scorable = {good_form, fault, posture_fault, other_fault}
    """

    THRESHOLD = 0.525
    THRESHOLD_MARGIN = 0.05
    _PF = frozenset({"fault", "posture_fault"})
    _OF = frozenset({"other_fault"})
    _GF = frozenset({"good_form"})

    # ------------------------------------------------------------------
    # Inline replica — mirrors _compute_metrics(scope=...) in smoke script
    # ------------------------------------------------------------------
    def _compute(self, results, scope="all"):
        all_fault = self._PF | self._OF
        in_scope_fault = self._PF if scope == "posture_only" else all_fault
        if scope == "posture_only":
            scorable = [r for r in results if r.get("label_used") in (self._GF | self._PF)]
        else:
            scorable = [r for r in results if r.get("label_used") in (self._GF | all_fault)]

        TP = FP = TN = FN = unc_fault = unc_good = bl = 0
        errors = []
        for r in scorable:
            label = r["label_used"]
            pred  = r.get("decision") or "unknown"
            prob  = r.get("prob_fault")
            if prob is not None and abs(prob - self.THRESHOLD) < self.THRESHOLD_MARGIN:
                bl += 1
            if pred == "uncertain":
                if label in in_scope_fault: unc_fault += 1
                else:                       unc_good  += 1
                continue
            if label in in_scope_fault:
                if pred == "fault": TP += 1
                else:               FN += 1; errors.append({**r, "_error_type": "FN"})
            else:
                if pred == "good_form": TN += 1
                else:                   FP += 1; errors.append({**r, "_error_type": "FP"})
        n      = len(scorable)
        dec    = TP + FP + TN + FN
        prec   = TP / (TP + FP) if (TP + FP) else 0.0
        rec    = TP / (TP + FN) if (TP + FN) else 0.0
        f1     = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        acc    = (TP + TN) / dec if dec else 0.0
        ur     = (unc_fault + unc_good) / n if n else 0.0
        return {
            "scope": scope, "scorable_n": n,
            "TP": TP, "FP": FP, "TN": TN, "FN": FN,
            "uncertain_fault": unc_fault, "uncertain_good": unc_good,
            "precision": round(prec, 3), "recall": round(rec, 3),
            "f1": round(f1, 3), "accuracy": round(acc, 3),
            "uncertain_rate": round(ur, 3), "borderline_count": bl,
            "errors": errors,
        }

    def _r(self, label_used, decision, prob_fault, filename="test.mp4"):
        return {
            "label_used": label_used, "decision": decision,
            "prob_fault": prob_fault, "filename": filename,
        }

    # ------------------------------------------------------------------
    # posture_only scope tests
    # ------------------------------------------------------------------

    def test_posture_only_excludes_other_fault(self):
        """other_fault videos must be excluded from scorable in posture_only scope."""
        results = [
            self._r("good_form",   "good_form", 0.20),
            self._r("posture_fault", "fault",   0.80),
            self._r("other_fault", "fault",     0.65),   # out-of-scope
        ]
        m = self._compute(results, scope="posture_only")
        assert m["scorable_n"] == 2, "other_fault should be excluded in posture_only"
        assert m["TP"] == 1
        assert m["TN"] == 1

    def test_posture_only_other_fault_does_not_count_as_fn(self):
        """Stability/depth faults predicted as good_form must NOT raise FN in posture_only."""
        results = [
            self._r("other_fault", "good_form", 0.15),  # model wrong but out-of-scope
            self._r("good_form",   "good_form", 0.20),
        ]
        m = self._compute(results, scope="posture_only")
        assert m["FN"] == 0, "other_fault miss should not appear as FN in posture_only"
        assert m["TN"] == 1

    def test_all_scope_includes_other_fault_as_fault(self):
        """other_fault videos are included (as fault class) in all scope."""
        results = [
            self._r("other_fault", "good_form", 0.15),   # FN in all scope
            self._r("good_form",   "good_form", 0.20),
        ]
        m = self._compute(results, scope="all")
        assert m["scorable_n"] == 2
        assert m["FN"] == 1, "other_fault miss should be FN in all scope"
        assert m["TN"] == 1

    def test_posture_fault_alias_treated_as_fault(self):
        """'posture_fault' explicit label is counted as fault in both scopes."""
        results = [
            self._r("posture_fault", "fault",     0.80),  # TP
            self._r("posture_fault", "good_form", 0.25),  # FN
            self._r("good_form",     "good_form", 0.15),  # TN
        ]
        for scope in ("posture_only", "all"):
            m = self._compute(results, scope=scope)
            assert m["TP"] == 1, f"scope={scope}: expected TP=1"
            assert m["FN"] == 1, f"scope={scope}: expected FN=1"
            assert m["TN"] == 1, f"scope={scope}: expected TN=1"

    def test_legacy_fault_label_counted_in_posture_only(self):
        """Legacy 'fault' label (backwards compat) is in-scope for posture_only."""
        results = [
            self._r("fault",     "fault",     0.75),   # TP
            self._r("good_form", "good_form", 0.20),   # TN
        ]
        m = self._compute(results, scope="posture_only")
        assert m["TP"] == 1 and m["TN"] == 1

    def test_scope_field_returned(self):
        """Returned dict must include 'scope' key matching the requested scope."""
        for scope in ("posture_only", "all"):
            m = self._compute([], scope=scope)
            assert m["scope"] == scope

    def test_messy_excluded_in_both_scopes(self):
        """'messy' is always excluded regardless of scope."""
        results = [self._r("messy", "fault", 0.80)]
        for scope in ("posture_only", "all"):
            m = self._compute(results, scope=scope)
            assert m["scorable_n"] == 0

    def test_all_scope_default(self):
        """Default scope is 'all' — same label filter as old behaviour for fault/good_form."""
        results = [
            self._r("fault",     "fault",     0.80),
            self._r("good_form", "good_form", 0.20),
        ]
        m = self._compute(results)   # no explicit scope → defaults to all
        assert m["scope"] == "all"
        assert m["TP"] == 1 and m["TN"] == 1


# ===========================================================================
# Tests: _build_review_queue  (prioritised review list)
# ===========================================================================

class TestBuildReviewQueue:
    """
    Tests for _build_review_queue from e2e_posture_v1_smoke.py (Feb 2026).

    Priority contract:
      P1 — High-confidence FP: prob_fault >= 0.70, labeled good_form, decision=fault
      P2 — High-confidence FN: prob_fault <= 0.30, labeled fault/posture_fault, decision=good_form
      P3 — Borderline: abs(prob_fault - 0.525) < 0.05, not already in P1/P2
    """

    THRESHOLD = 0.525
    _PF = frozenset({"fault", "posture_fault"})
    _OF = frozenset({"other_fault"})
    _GF = frozenset({"good_form"})

    def _build(self, results, threshold=0.525, video_dir=""):
        """Inline replica of _build_review_queue from e2e_posture_v1_smoke.py."""
        HCONF_FP = 0.70
        HCONF_FN = 0.30
        BL_MARGIN = 0.05
        all_fault = self._PF | self._OF

        ACTIONS = {
            1: "Confirm good form → add to training data as good_form if confirmed",
            2: "Confirm label → update labels_override.json if Penn Action mislabel",
            3: "Watch video → determine true label (good_form or posture_fault)",
        }

        seen: set = set()
        queue: list = []

        def _entry(r, priority, reason):
            from pathlib import Path
            abs_path = str(Path(video_dir) / r["filename"]) if video_dir else r["filename"]
            return {
                "priority": priority, "reason": reason,
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
                "suggested_action": ACTIONS.get(priority, "Review needed"),
            }

        for r in results:
            if r.get("status") != "COMPLETED":
                continue
            fn    = r.get("filename", "")
            prob  = r.get("prob_fault")
            label = r.get("label_used", "")
            dec   = r.get("decision", "")
            if prob is None:
                continue
            if prob >= HCONF_FP and label in self._GF and dec == "fault" and fn not in seen:
                seen.add(fn)
                queue.append(_entry(r, 1, f"high_conf_FP: prob_fault={prob:.4f}"))
            elif prob <= HCONF_FN and label in all_fault and dec == "good_form" and fn not in seen:
                seen.add(fn)
                queue.append(_entry(r, 2, f"high_conf_FN: prob_fault={prob:.4f}"))
            if fn not in seen and abs(prob - threshold) < BL_MARGIN:
                seen.add(fn)
                queue.append(_entry(r, 3, f"borderline: prob_fault={prob:.4f}"))

        queue.sort(key=lambda x: (x["priority"], -(x["confidence"] or 0.0)))
        return queue

    def _r(self, label_used, decision, prob_fault, confidence=None, filename="test.mp4"):
        if confidence is None:
            confidence = abs(2 * prob_fault - 1)
        return {
            "status": "COMPLETED",
            "filename": filename,
            "label_used": label_used,
            "folder_label": "fault" if "fault" in label_used else "good",
            "decision": decision,
            "prob_fault": prob_fault,
            "confidence": confidence,
            "quality_flags": [],
        }

    # ------------------------------------------------------------------
    # P1: High-confidence FP
    # ------------------------------------------------------------------

    def test_p1_high_conf_fp_added(self):
        """prob_fault >= 0.70, labeled good_form, decision=fault → P1."""
        results = [self._r("good_form", "fault", 0.75, filename="suspect.mp4")]
        queue = self._build(results)
        assert len(queue) == 1
        item = queue[0]
        assert item["priority"] == 1
        assert "high_conf_FP" in item["reason"]
        assert item["filename"] == "suspect.mp4"

    def test_p1_not_triggered_below_0_70(self):
        """prob_fault = 0.69 (just below P1 threshold) → not P1."""
        results = [self._r("good_form", "fault", 0.69, filename="ok.mp4")]
        queue = self._build(results)
        # Should be borderline (|0.69-0.525|=0.165 > 0.05) or empty — NOT P1
        p1_items = [x for x in queue if x["priority"] == 1]
        assert len(p1_items) == 0

    def test_p1_not_triggered_for_fault_label(self):
        """High prob on a fault-labeled video is a TP, not a FP — no P1 entry."""
        results = [self._r("fault", "fault", 0.85, filename="tp.mp4")]
        queue = self._build(results)
        assert len(queue) == 0

    # ------------------------------------------------------------------
    # P2: High-confidence FN
    # ------------------------------------------------------------------

    def test_p2_high_conf_fn_added(self):
        """prob_fault <= 0.30, labeled fault, decision=good_form → P2."""
        results = [self._r("fault", "good_form", 0.15, filename="label_err.mp4")]
        queue = self._build(results)
        assert len(queue) == 1
        item = queue[0]
        assert item["priority"] == 2
        assert "high_conf_FN" in item["reason"]

    def test_p2_posture_fault_label_also_triggers(self):
        """'posture_fault' explicit label triggers P2 just like 'fault'."""
        results = [self._r("posture_fault", "good_form", 0.20, filename="pf_miss.mp4")]
        queue = self._build(results)
        assert len(queue) == 1
        assert queue[0]["priority"] == 2

    def test_p2_other_fault_also_triggers(self):
        """other_fault labeled video with prob_fault <= 0.30 → P2 (model wrong in any scope)."""
        results = [self._r("other_fault", "good_form", 0.10, filename="stab_miss.mp4")]
        queue = self._build(results)
        assert len(queue) == 1
        assert queue[0]["priority"] == 2

    def test_p2_not_triggered_above_0_30(self):
        """prob_fault = 0.35 (above P2 threshold) → not P2."""
        results = [self._r("fault", "good_form", 0.35, filename="borderline.mp4")]
        queue = self._build(results)
        p2_items = [x for x in queue if x["priority"] == 2]
        assert len(p2_items) == 0

    # ------------------------------------------------------------------
    # P3: Borderline
    # ------------------------------------------------------------------

    def test_p3_borderline_added(self):
        """abs(prob_fault - 0.525) < 0.05 and not already P1/P2 → P3."""
        results = [self._r("fault", "good_form", 0.50, filename="near_thresh.mp4")]
        # prob=0.50, |0.50-0.525|=0.025 < 0.05 → borderline
        # Also would normally be P2 candidate (prob<=0.30) — but 0.50 > 0.30 so no
        queue = self._build(results)
        p3_items = [x for x in queue if x["priority"] == 3]
        assert len(p3_items) == 1
        assert "borderline" in p3_items[0]["reason"]

    def test_p3_not_added_outside_margin(self):
        """|prob_fault - 0.525| >= 0.05 → NOT P3."""
        results = [self._r("fault", "good_form", 0.60, filename="clear.mp4")]
        # |0.60 - 0.525| = 0.075 >= 0.05 → no P3
        queue = self._build(results)
        assert len(queue) == 0

    # ------------------------------------------------------------------
    # Deduplication and priority logic
    # ------------------------------------------------------------------

    def test_p1_video_not_also_added_as_p3(self):
        """A P1 video near the threshold must not get a duplicate P3 entry."""
        # prob=0.56: |0.56-0.525|=0.035 < 0.05 → could be P3
        # but also if decision=fault and label=good_form AND prob>=0.70 → nope (0.56 < 0.70)
        # Use prob=0.73 for P1 — NOT borderline since |0.73-0.525|=0.205 > 0.05
        results = [self._r("good_form", "fault", 0.73, filename="fp_far.mp4")]
        queue = self._build(results)
        assert len(queue) == 1   # only P1, no duplicate P3

    def test_p2_video_not_also_added_as_p3(self):
        """A P2 video (prob=0.20) is not borderline, so no P3 entry."""
        results = [self._r("fault", "good_form", 0.20, filename="fn_far.mp4")]
        # |0.20-0.525|=0.325 → not borderline
        queue = self._build(results)
        assert len(queue) == 1   # only P2

    def test_same_video_not_duplicated(self):
        """The same video can appear at most once in the queue."""
        # A borderline FN at prob=0.50: could trigger P3 (if prob between 0.30 and 0.70)
        # Not P1 (prob < 0.70) and not P2 (prob > 0.30) → only P3 candidate
        results = [
            self._r("fault", "good_form", 0.50, filename="same.mp4"),
        ]
        queue = self._build(results)
        filenames = [x["filename"] for x in queue]
        assert filenames.count("same.mp4") <= 1

    # ------------------------------------------------------------------
    # Sorting
    # ------------------------------------------------------------------

    def test_p1_appears_before_p2_before_p3(self):
        """Priority 1 < 2 < 3 in output order."""
        results = [
            self._r("good_form",   "fault",     0.85, confidence=0.70, filename="fp.mp4"),   # P1
            self._r("fault",       "good_form", 0.10, confidence=0.80, filename="fn.mp4"),   # P2
            self._r("fault",       "good_form", 0.51, confidence=0.02, filename="bl.mp4"),   # P3
        ]
        queue = self._build(results)
        priorities = [x["priority"] for x in queue]
        assert priorities == sorted(priorities), f"Queue not sorted by priority: {priorities}"

    def test_within_same_priority_sorted_by_confidence_desc(self):
        """Within same priority, higher confidence appears first."""
        results = [
            self._r("fault", "good_form", 0.15, confidence=0.30, filename="low_conf.mp4"),  # P2
            self._r("fault", "good_form", 0.10, confidence=0.80, filename="high_conf.mp4"),  # P2
        ]
        queue = self._build(results)
        p2 = [x for x in queue if x["priority"] == 2]
        assert len(p2) == 2
        assert p2[0]["confidence"] >= p2[1]["confidence"], (
            "Higher-confidence P2 entry must appear first"
        )

    # ------------------------------------------------------------------
    # Edge cases
    # ------------------------------------------------------------------

    def test_non_completed_excluded(self):
        """Videos with status != COMPLETED are excluded from the queue."""
        results = [
            {
                "status": "FAILED",
                "filename": "broken.mp4",
                "label_used": "good_form",
                "decision": "fault",
                "prob_fault": 0.90,
                "confidence": 0.80,
            }
        ]
        queue = self._build(results)
        assert len(queue) == 0

    def test_missing_prob_fault_excluded(self):
        """Videos without prob_fault (model error / pre-inference) are excluded."""
        results = [
            {
                "status": "COMPLETED",
                "filename": "no_prob.mp4",
                "label_used": "good_form",
                "decision": "fault",
                "prob_fault": None,
                "confidence": 0.70,
            }
        ]
        queue = self._build(results)
        assert len(queue) == 0

    def test_empty_results_returns_empty_queue(self):
        queue = self._build([])
        assert queue == []

    def test_all_tn_returns_empty_queue(self):
        """Clean batch with no errors produces no review items."""
        results = [
            self._r("good_form", "good_form", 0.20, filename="tn1.mp4"),
            self._r("good_form", "good_form", 0.30, filename="tn2.mp4"),
            self._r("fault",     "fault",     0.75, filename="tp.mp4"),
        ]
        queue = self._build(results)
        assert len(queue) == 0
