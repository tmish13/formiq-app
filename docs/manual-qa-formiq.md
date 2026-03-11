# FormIQ Manual QA Script

Three test scenarios covering the key frontend + backend hardening changes.

---

## Scenario A: Good Squat

**Setup:** Upload a clean full-body squat video (1–3 reps, 2–5 seconds, full visibility of hips/knees/ankles).

**Steps:**
1. Log in → Record → upload good squat video.
2. Wait for processing to complete (ModernProcessingPage polls to completion).
3. Navigate to AnalysisPage (`/analysis/:id`).

**Expected behaviour:**

| Area | Expected |
|------|---------|
| Score | High score displayed (≥ 85 for truly good form) |
| Header | "Analysis Complete" or similar (NOT "Analysis Unavailable") |
| Summary | Starts with "Your form is strong on this rep." (score ≥ 85) or "Solid foundation with a few areas to refine." (score 70–84) |
| Key Findings | Visible, signals match actual pose issues |
| Named Scores | Visible (Torso Stability, Knee Symmetry, etc.) |
| Tips tab | Shows actual recommendations — no "Tips Unavailable" placeholder |
| "Next Target" | Shows "Excellent! Maintain this consistency…" (score ≥ 90) or "Aim for X% to reach the next level." |
| Dashboard → hero | "Your Form is Strong" + "Keep refining your technique" |
| Dashboard → stats | Real score shown (NOT 85% from hardcoded fallback) |

---

## Scenario B: Bad Squat

**Setup:** Upload a squat video with clear form faults (knees caving, excessive forward lean, etc.).

**Steps:**
1. Log in → Record → upload fault squat video.
2. Wait for processing to complete.
3. Navigate to AnalysisPage.

**Expected behaviour:**

| Area | Expected |
|------|---------|
| Score | Low score displayed (< 60 for bad form) |
| Header | Shows score, decision badge "Fault Detected" |
| Summary | Starts with "Your form shows notable issues…" (score 50–69) or "Significant form issues detected. Prioritize correcting these before adding weight." (score < 50) |
| Key Findings | Visible with relevant fault signals (trunk wobble, knee asymmetry, etc.) |
| Tips tab | Shows high-priority recommendations (NOT neutral fallback placeholders like "Your depth is excellent!") |
| "Next Target" | "Focus on the key findings above before adding more weight." |
| Dashboard | Score reflects the bad rep (e.g. 35%), NOT hardcoded 85% |

---

## Scenario C: Invalid Video (Face-Only / Static / No Movement)

**Setup:** Upload a short video that is either:
- A face/upper-body-only recording (body landmarks not visible), OR
- A static standing pose with no squat movement (hip/knee y-range < 0.05), OR
- A video that is too short/blank.

**Steps:**
1. Log in → Record → upload invalid video.
2. Wait for processing to complete.
3. Navigate to AnalysisPage.

**Expected behaviour:**

| Area | Expected |
|------|---------|
| Score display | Shows "—" (dash), NOT a numeric score |
| Header | "Analysis Unavailable" |
| Uncertain banner | Visible (e.g. "We couldn't reliably analyse this recording…") |
| Re-record CTA | Visible button / link to `/record` |
| Key Findings | Hidden (no signals shown) |
| Named Scores | Hidden |
| Tips tab | Shows "Tips Unavailable" placeholder card with "Record Again" button |
| "Next Target" | "Complete a valid analysis to set your next target." |
| Dashboard stats | NOT incremented by uncertain session (score remains NULL/excluded from stats) |
| Dashboard → API kill | Kill API mid-load → Dashboard shows all zeroes (0%, 0 sessions), NOT 85%/7d/8% hardcoded values |

---

## Settings / Navigation Checks

| Check | Expected |
|-------|---------|
| Header — Settings icon click | Navigates to `/profile` |
| Header — Bell icon | **Not visible** (removed) |
| Dashboard → 0 sessions | Hero: "Perfect Your Form" + "Record your first squat to get started" |
| Dashboard → 1 session | Hero subtitle: "2 more sessions to see your average score" |
| Dashboard → 2 sessions | Hero subtitle: "1 more session to see your average score" |

---

## Automated Verification Commands

```bash
# TypeScript — 0 errors in changed files
cd frontend && npx tsc --noEmit 2>&1 | grep -E "AnalysisPage|DashboardPage|AppLayout"

# Backend unit gate (expect 617+ tests passing)
cd backend && python -m pytest -q -m "not integration and not e2e and not slow"

# Check new unit tests pass
cd backend && python -m pytest -q tests/unit/test_motion_gate.py tests/unit/test_score_band.py -v
```
