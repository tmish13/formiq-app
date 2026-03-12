# PostureV1 Production Validation Playbook

## What This Proves

Executing this playbook end-to-end confirms:

1. **Model artifacts are deployed** and loaded correctly (PyTorch weights, scaler, manifest)
2. **Full pipeline works**: upload -> Celery processing -> MediaPipe (complexity=2) -> PostureV1 inference -> scores stored in DB -> API returns real ML results
3. **No hardcoded mocks** exist in production code paths
4. **Frontend renders real ML scores** (not stubs)
5. **Edge cases are handled**: non-squat exercises, low-quality video, uncertain decisions
6. **Telemetry is recorded** for every inference
7. **Accuracy meets bar**: precision/recall/F1 on holdout videos
8. **Ship/no-ship gate** is satisfied

---

## A) Pre-Flight Checklist

Run these checks BEFORE anything else. Fix any failures before proceeding.

### A1. Services Running

```bash
# Check backend API
curl -s http://localhost:8000/health | python3 -m json.tool
# EXPECT: {"status": "healthy", ...}

# Check Redis
redis-cli ping
# EXPECT: PONG

# Check PostgreSQL
psql -h localhost -U postgres -c "SELECT 1;"
# EXPECT: ?column? = 1

# Check Celery worker is alive
cd /Users/tarpanmishra/formiq-app-3/backend
celery -A app.core.celery_app inspect ping
# EXPECT: At least one worker responds with "pong"
```

**STOP if any service is down. Start them:**
```bash
# Terminal 1 — Backend
cd /Users/tarpanmishra/formiq-app-3/backend
uvicorn app.main:app --reload --port 8000

# Terminal 2 — Celery worker
cd /Users/tarpanmishra/formiq-app-3/backend
celery -A app.core.celery_app worker --loglevel=info

# Terminal 3 — Frontend
cd /Users/tarpanmishra/formiq-app-3/frontend
npm start
# Runs on http://localhost:3000

# Redis and PostgreSQL should already be running via brew/docker
```

### A2. Model Artifacts Present

```bash
ls -la /Users/tarpanmishra/formiq-app-3/backend/app/ml/posture_v1/artifacts/
# EXPECT all three files:
#   posture_v1.pt             (PyTorch model weights)
#   posture_v1_scaler.joblib  (sklearn feature scaler)
#   posture_v1_manifest.json  (metadata/config)
```

**STOP if any file is missing.** Redeploy from the ML repo.

### A3. Config Flags

```bash
cd /Users/tarpanmishra/formiq-app-3/backend
python3 -c "
from app.core.config import settings
print(f'USE_POSTURE_V1:      {settings.USE_POSTURE_V1}')
print(f'POSE_MODEL_COMPLEXITY: {settings.POSE_MODEL_COMPLEXITY}')
print(f'POSTURE_V1_THRESHOLD:  {settings.POSTURE_V1_THRESHOLD}')
"
# EXPECT:
#   USE_POSTURE_V1:       True
#   POSE_MODEL_COMPLEXITY: 2
#   POSTURE_V1_THRESHOLD:  0.525
```

**STOP if USE_POSTURE_V1 is False** — the model won't run.

### A4. Test Videos Present

```bash
ls /Users/tarpanmishra/formiq-app-3/backend/test_videos/good/  | wc -l
ls /Users/tarpanmishra/formiq-app-3/backend/test_videos/fault/ | wc -l
ls /Users/tarpanmishra/formiq-app-3/backend/test_videos/messy/ | wc -l
# EXPECT: good=8, fault=13, messy=3 (total 24)
```

### A5. Test User Credentials

You need a registered user. Either:
- Register via the frontend at `http://localhost:3000` (sign up flow), OR
- Register via API:

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "testval@formiq.com", "password": "TestVal2026!", "username": "testval"}' \
  | python3 -m json.tool
# EXPECT: 200/201 with user object
```

Then export (in EVERY terminal where you run scripts):
```bash
export TEST_USER_EMAIL="testval@formiq.com"
export TEST_USER_PASSWORD="TestVal2026!"
```

Verify login works:
```bash
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=${TEST_USER_EMAIL}&password=${TEST_USER_PASSWORD}" \
  | python3 -m json.tool
# EXPECT: {"access_token": "eyJ...", "token_type": "bearer"}
```

**STOP if login fails.** Check credentials, check DB connection.

### A6. No Hardcoded Mocks (Quick Grep)

Run these greps to confirm production code has no fake scores:

```bash
cd /Users/tarpanmishra/formiq-app-3

# Backend: check for suspicious hardcoded decisions/scores in the pipeline
grep -rn "good_form\|posture_fault" backend/app/tasks/analysis_tasks.py | grep -v "#\|import\|log\|print\|==\|!="
# EXPECT: Only legitimate constant references (threshold comparison, telemetry logging), NO hardcoded return values

# Backend: check for fake/mock in production services
grep -rn "mock\|fake\|hardcode\|stub" backend/app/services/ml_model_service.py backend/app/tasks/analysis_tasks.py backend/app/services/ai_service.py 2>/dev/null | grep -iv "test\|#\|doc"
# EXPECT: Zero matches (or only comments)

# Frontend: check that AnalysisPage reads real API data
grep -n "mock\|fake\|hardcode\|stub\|= 85\|= 90\|= 95" frontend/src/pages/AnalysisPage.tsx | grep -iv "test\|//"
# EXPECT: Zero matches

# Frontend: check ModernResultsPage
grep -n "mock\|fake\|hardcode\|stub" frontend/src/pages/ModernResultsPage.tsx | grep -iv "test\|//"
# EXPECT: Zero matches
```

**STOP if any grep shows real hardcoded values in production paths.**

---

## B) Backend Validation

### B1. Database Migration Sanity

```bash
cd /Users/tarpanmishra/formiq-app-3/backend
alembic current
# EXPECT: Shows current revision (should not say "head is ahead" or "offline")

alembic check
# EXPECT: No pending migrations detected
# NOTE: If it warns about model drift, that's OK for now — confirm the tables exist:

python3 -c "
from sqlalchemy import inspect, create_engine
from app.core.config import settings
e = create_engine(str(settings.DATABASE_URL))
i = inspect(e)
tables = i.get_table_names()
required = ['form_checks', 'videos', 'users', 'posture_v1_inference_logs']
for t in required:
    status = 'OK' if t in tables else 'MISSING'
    print(f'  {t}: {status}')
"
# EXPECT: All four tables show OK
```

**STOP if posture_v1_inference_logs is MISSING.** Run the migration that creates it.

### B2. Quick Unit Test Check

```bash
cd /Users/tarpanmishra/formiq-app-3/backend

# PostureV1-specific tests (fast, no DB needed)
python -m pytest tests/unit/test_posture_v1.py --noconftest -v 2>&1 | tail -30
# EXPECT: All tests PASSED

# MediaPipe complexity tests
python -m pytest tests/unit/test_mediapipe_complexity.py --noconftest -v 2>&1 | tail -20
# EXPECT: All tests PASSED
```

**STOP if any test fails.** Fix before proceeding to E2E.

---

## C) E2E Script Validation

### C1. Single Video Smoke Test

Pick one known good-form video and run:

```bash
cd /Users/tarpanmishra/formiq-app-3/backend

python scripts/e2e_posture_v1_smoke.py \
  --video test_videos/good/good_squat_01.mp4
```

**What to look for in the output:**
```
[1/6] Authenticating...        → Must succeed
[2/6] Uploading video...       → FormCheck ID and Video ID printed
[3/6] Polling for completion   → Status transitions, ends with COMPLETED (not FAILED/TIMEOUT)
[4/6] Fetching ML analysis     → 200 response
[5/6] Validating results...
  model_complexity: 2 (verified)   ← CRITICAL: must be 2
  pose_complexity_fallback: False  ← CRITICAL: must be False
  decision:    good_form OR fault  ← Must be one of: good_form, fault, uncertain
  prob_fault:  0.XXXX             ← Must be 0.0–1.0
  confidence:  0.XXX              ← Must be 0.0–1.0
[6/6] Summary
  PASS
```

**STOP conditions:**
- `FAIL: Login failed` → credentials wrong
- `FAIL: Upload failed` → check backend logs for S3/storage errors
- Status stuck at PROCESSING → Celery worker not running or crashed
- `model_complexity: None` → analysis_tasks.py missing complexity in payload
- `FAIL: ...FAILED status` → check Celery worker terminal for traceback

### C2. Batch E2E — Good Form Videos

```bash
cd /Users/tarpanmishra/formiq-app-3/backend

python scripts/e2e_posture_v1_smoke.py \
  --video-dir test_videos/good \
  --exercise-type squat
```

**Record the output.** Key metrics from BATCH SUMMARY:
- `Completed: 8` (all 8 must complete)
- `Failed/Error: 0`
- `Decisions: {"good_form": X, "fault": Y, "uncertain": Z}`
- `Avg prob_fault: <value>`
- `Complexity: {"2": 8}` (all must be complexity=2)
- `Fallbacks: 0/8` (zero fallbacks)

**Save the JSON report:**
```bash
cat scripts/output/e2e_posture_v1_batch_report.json | python3 -m json.tool > /tmp/good_report.json
cp scripts/output/e2e_posture_v1_batch_report.json scripts/output/good_batch_report.json
```

**Expectations for good/ folder:**
| Metric | Target | Acceptable |
|--------|--------|------------|
| good_form decisions | >= 6/8 (75%) | >= 5/8 (62.5%) |
| uncertain decisions | <= 2 | <= 3 |
| fault decisions | 0 | <= 1 (false positive) |
| Avg prob_fault | < 0.40 | < 0.50 |
| Complexity=2 | 8/8 | 8/8 (hard requirement) |

**STOP if:** More than 1 false positive (fault on a good video), or any video has complexity != 2.

### C3. Batch E2E — Fault Videos

```bash
cd /Users/tarpanmishra/formiq-app-3/backend

python scripts/e2e_posture_v1_smoke.py \
  --video-dir test_videos/fault \
  --exercise-type squat
```

**Save report:**
```bash
cp scripts/output/e2e_posture_v1_batch_report.json scripts/output/fault_batch_report.json
```

**Expectations for fault/ folder:**
| Metric | Target | Acceptable |
|--------|--------|------------|
| fault decisions | >= 9/13 (69%) | >= 7/13 (54%) |
| uncertain decisions | <= 3 | <= 5 |
| good_form decisions | <= 1 | <= 2 (false negatives) |
| Avg prob_fault | > 0.55 | > 0.50 |

**STOP if:** More than 2 false negatives (good_form on a fault video), indicating the model misses faults.

### C4. Batch E2E — Messy Videos

```bash
cd /Users/tarpanmishra/formiq-app-3/backend

python scripts/e2e_posture_v1_smoke.py \
  --video-dir test_videos/messy \
  --exercise-type squat
```

**Save report:**
```bash
cp scripts/output/e2e_posture_v1_batch_report.json scripts/output/messy_batch_report.json
```

**Expectations for messy/ folder:**
These are stability-fault videos (out-of-distribution for the binary model). Acceptable outcomes:
| Metric | Ideal | Acceptable |
|--------|-------|------------|
| uncertain decisions | >= 2/3 | >= 1/3 |
| fault decisions | Any | Any (not a false positive since they ARE bad form) |
| good_form decisions | 0 | <= 1 |

**NOTE:** Messy videos are NOT a hard gate — they test graceful degradation. The model was not trained on stability faults, so uncertain or fault are both OK. Only good_form is concerning.

### C5. Non-Squat Exercise Test

Test that non-squat exercises return `not_supported`:

```bash
cd /Users/tarpanmishra/formiq-app-3/backend

# Use any video — the exercise type matters, not the content
python scripts/e2e_posture_v1_smoke.py \
  --video test_videos/good/good_squat_01.mp4 \
  --exercise-type deadlift
```

**EXPECT:** The script should show `decision: not_supported` in the output. The ML analysis response should contain:
```json
{"posture_v1": {"status": "not_supported", "exercise_type": "Deadlift", "reason": "..."}}
```

And should NOT contain `named_scores`, `prob_fault`, `confidence`, or `posture_score`.

### C6. Compute Precision/Recall/F1

After all three batch runs complete, run this snippet:

```bash
cd /Users/tarpanmishra/formiq-app-3/backend

python3 << 'METRICS_EOF'
import json

def load_report(path):
    with open(path) as f:
        return json.load(f)

good_report = load_report("scripts/output/good_batch_report.json")
fault_report = load_report("scripts/output/fault_batch_report.json")
messy_report = load_report("scripts/output/messy_batch_report.json")

# Classification: good_form = negative, fault = positive, uncertain = excluded
# Ground truth: good/ = negative, fault/ = positive, messy/ = out-of-distribution

good_results = good_report["results"]
fault_results = fault_report["results"]
messy_results = messy_report["results"]

# Exclude uncertain from precision/recall (they abstained)
TP = sum(1 for r in fault_results if r.get("decision") == "fault")
FN = sum(1 for r in fault_results if r.get("decision") == "good_form")
FP = sum(1 for r in good_results  if r.get("decision") == "fault")
TN = sum(1 for r in good_results  if r.get("decision") == "good_form")

uncertain_good  = sum(1 for r in good_results  if r.get("decision") == "uncertain")
uncertain_fault = sum(1 for r in fault_results if r.get("decision") == "uncertain")
uncertain_messy = sum(1 for r in messy_results if r.get("decision") == "uncertain")

total_good = len(good_results)
total_fault = len(fault_results)
total_messy = len(messy_results)

precision = TP / (TP + FP) if (TP + FP) > 0 else 0.0
recall    = TP / (TP + FN) if (TP + FN) > 0 else 0.0
f1        = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

uncertain_rate = (uncertain_good + uncertain_fault) / (total_good + total_fault) if (total_good + total_fault) > 0 else 0.0

# Prob fault averages
good_pf  = [r["prob_fault"] for r in good_results  if r.get("prob_fault") is not None]
fault_pf = [r["prob_fault"] for r in fault_results if r.get("prob_fault") is not None]
messy_pf = [r["prob_fault"] for r in messy_results if r.get("prob_fault") is not None]

# Complexity check
all_results = good_results + fault_results + messy_results
cx_violations = [r["filename"] for r in all_results if r.get("model_complexity") not in (2, None)]
fb_violations = [r["filename"] for r in all_results if r.get("pose_complexity_fallback") is True]

print("=" * 60)
print("POSTURE V1 VALIDATION METRICS")
print("=" * 60)
print()
print(f"  good/ folder:   {total_good} videos")
print(f"    good_form:  {TN}  |  fault: {FP}  |  uncertain: {uncertain_good}")
print(f"    avg prob_fault: {sum(good_pf)/len(good_pf):.4f}" if good_pf else "    avg prob_fault: N/A")
print()
print(f"  fault/ folder:  {total_fault} videos")
print(f"    fault:      {TP}  |  good_form: {FN}  |  uncertain: {uncertain_fault}")
print(f"    avg prob_fault: {sum(fault_pf)/len(fault_pf):.4f}" if fault_pf else "    avg prob_fault: N/A")
print()
print(f"  messy/ folder:  {total_messy} videos")
print(f"    uncertain: {uncertain_messy}  |  fault: {sum(1 for r in messy_results if r.get('decision')=='fault')}  |  good_form: {sum(1 for r in messy_results if r.get('decision')=='good_form')}")
print(f"    avg prob_fault: {sum(messy_pf)/len(messy_pf):.4f}" if messy_pf else "    avg prob_fault: N/A")
print()
print("-" * 60)
print(f"  PRECISION:      {precision:.3f}   (TP={TP}, FP={FP})")
print(f"  RECALL:         {recall:.3f}   (TP={TP}, FN={FN})")
print(f"  F1 SCORE:       {f1:.3f}")
print(f"  UNCERTAIN RATE: {uncertain_rate:.1%}  ({uncertain_good + uncertain_fault}/{total_good + total_fault})")
print("-" * 60)
print()

# Complexity gate
if cx_violations:
    print(f"  COMPLEXITY VIOLATION: {cx_violations}")
else:
    print(f"  Complexity: ALL videos processed with complexity=2")

if fb_violations:
    print(f"  FALLBACK WARNING: {fb_violations}")
else:
    print(f"  Fallbacks: NONE (all complexity=2, no fallback to 1)")

# False positive analysis
if FP > 0:
    fp_videos = [r for r in good_results if r.get("decision") == "fault"]
    print(f"\n  FALSE POSITIVES (good videos called fault):")
    for r in fp_videos:
        print(f"    {r['filename']}: prob_fault={r.get('prob_fault', '?')}, missing_ratio={r.get('missing_ratio', '?')}, frames={r.get('frames_detected', '?')}/{r.get('original_frames', '?')}")

# False negative analysis
if FN > 0:
    fn_videos = [r for r in fault_results if r.get("decision") == "good_form"]
    print(f"\n  FALSE NEGATIVES (fault videos called good_form):")
    for r in fn_videos:
        print(f"    {r['filename']}: prob_fault={r.get('prob_fault', '?')}, missing_ratio={r.get('missing_ratio', '?')}, frames={r.get('frames_detected', '?')}/{r.get('original_frames', '?')}")

# Gate flag analysis
print(f"\n  TOP GATE FLAGS (from uncertain decisions):")
uncertain_videos = [r for r in all_results if r.get("decision") == "uncertain"]
if uncertain_videos:
    for r in uncertain_videos:
        print(f"    {r['filename']}: prob_fault={r.get('prob_fault', '?')}, missing_ratio={r.get('missing_ratio', '?')}")
else:
    print(f"    None — no uncertain decisions")

print()
print("=" * 60)

# SHIP GATE
ship = True
reasons = []

if precision < 0.70:
    ship = False
    reasons.append(f"Precision {precision:.3f} < 0.70")
if recall < 0.50:
    ship = False
    reasons.append(f"Recall {recall:.3f} < 0.50")
if f1 < 0.55:
    ship = False
    reasons.append(f"F1 {f1:.3f} < 0.55")
if uncertain_rate > 0.40:
    ship = False
    reasons.append(f"Uncertain rate {uncertain_rate:.1%} > 40%")
if cx_violations:
    ship = False
    reasons.append(f"Complexity violations: {cx_violations}")

if ship:
    print("VERDICT: SHIP")
    print("All metrics within acceptable bounds.")
else:
    print("VERDICT: NO SHIP")
    for r in reasons:
        print(f"  - {r}")

print("=" * 60)
METRICS_EOF
```

---

## D) Telemetry Validation

### D1. Confirm Telemetry Table Has Rows

After the batch runs in Section C, the `posture_v1_inference_logs` table should have rows:

```bash
cd /Users/tarpanmishra/formiq-app-3/backend

python3 -c "
from sqlalchemy import create_engine, text
from app.core.config import settings
e = create_engine(str(settings.DATABASE_URL))
with e.connect() as c:
    count = c.execute(text('SELECT COUNT(*) FROM posture_v1_inference_logs')).scalar()
    print(f'Telemetry rows: {count}')
    if count > 0:
        row = c.execute(text('SELECT decision, prob_fault, confidence, model_version, latency_ms, sequence_length, missing_ratio, threshold, gate_flags FROM posture_v1_inference_logs ORDER BY created_at DESC LIMIT 1')).fetchone()
        print(f'Latest row:')
        print(f'  decision:        {row[0]}')
        print(f'  prob_fault:      {row[1]}')
        print(f'  confidence:      {row[2]}')
        print(f'  model_version:   {row[3]}')
        print(f'  latency_ms:      {row[4]}')
        print(f'  sequence_length: {row[5]}')
        print(f'  missing_ratio:   {row[6]}')
        print(f'  threshold:       {row[7]}')
        print(f'  gate_flags:      {row[8]}')
"
```

**EXPECT:**
- `Telemetry rows: >= 24` (from the 24 batch videos)
- `decision` is one of: good_form, fault, uncertain
- `prob_fault` is 0.0–1.0
- `confidence` is 0.0–1.0
- `threshold` is ~0.525
- `latency_ms` is a reasonable number (10–5000ms)
- `gate_flags` is a JSON array (possibly empty `[]`)

### D2. Run Telemetry Aggregation Report

```bash
cd /Users/tarpanmishra/formiq-app-3/backend

python scripts/report_posture_v1_telemetry.py --limit 200
```

**What to look for:**
```
POSTURE V1 TELEMETRY REPORT
======================================================================
  Total inferences: >= 24
  Error count:      0 (0.0%)     ← Must be 0%
  Uncertain rate:   X (Y%)       ← Should be < 40%

  Decisions:
    good_form       : ...
    fault           : ...
    uncertain       : ...

  Latency:          avg=XXms  p50=XXms  p95=XXms  p99=XXms
  Prob(fault):      avg=X.XXXX  median=X.XXXX

  Model versions:   {"posture_v1_cnn_lstm": N}  ← Must show correct model name
======================================================================
```

**Verify:**
- [ ] Error rate is 0%
- [ ] Total inferences >= 24
- [ ] Latency p95 < 5000ms
- [ ] Model version is consistent (single version string)
- [ ] No gate_flags dominating (if one flag appears on >50% of videos, investigate)

### D3. Confirm model_complexity in Telemetry (DB Check)

```bash
cd /Users/tarpanmishra/formiq-app-3/backend

python3 -c "
from sqlalchemy import create_engine, text
from app.core.config import settings
e = create_engine(str(settings.DATABASE_URL))
with e.connect() as c:
    # Check a recent form_check's posture_v1 preprocessing for model_complexity
    rows = c.execute(text('''
        SELECT fc.id, fc.posture_score, fc.confidence_score
        FROM form_checks fc
        ORDER BY fc.created_at DESC LIMIT 5
    ''')).fetchall()
    print('Recent form_checks:')
    for r in rows:
        print(f'  id={r[0]}, posture_score={r[1]}, confidence_score={r[2]}')
"
```

**EXPECT:** posture_score is 0–100 and confidence_score is 0–1 for completed squat form checks.

---

## E) Frontend Manual Validation

Open `http://localhost:3000` in your browser.

### E1. Login/Register

1. Go to `http://localhost:3000`
2. If not logged in, you'll see login/register screen
3. Log in with the same test user credentials you exported
4. **VERIFY:** You're redirected to the dashboard/home. Browser dev tools (Application > Local Storage or Cookies) should show a JWT token stored.

### E2. Record Page — Exercise Selection

1. Navigate to the Record page (usually via a "New Analysis" or "Record" button)
2. **VERIFY:** You see an exercise selection grid with cards:
   - **Squat** — should say "AI Scoring" or be marked as supported
   - **Deadlift, Bench Press, etc.** — should say "Coming Soon" or be visually muted
3. Select **Squat**
4. **VERIFY:** The squat card is highlighted/selected

### E3. Upload a Good-Form Squat Video

1. With Squat selected, upload one of the good videos (e.g., `good_squat_01.mp4`)
2. You should be redirected to the Processing page (`/processing/:videoId`)
3. **VERIFY on Processing page:**
   - Shows a progress indicator (spinner, progress bar, or status text)
   - Status transitions: uploading -> processing -> analyzing -> completed
   - Does NOT hang forever (should complete within 60–120 seconds)
4. On completion, you should auto-redirect to the Analysis page (`/analysis/:id`)

### E4. Analysis Page — Real ML Scores (Good Form)

On the Analysis page, **VERIFY:**

1. **Posture Score** is displayed as a number (0–100). It should NOT be exactly 50, 75, 85, or 90 (suspiciously round = mock). Real ML scores are like 72.3, 88.1, etc.
2. **Decision** is shown (good_form, fault, or uncertain)
3. If decision is **good_form** or **fault**:
   - Named scores / component scores are visible (e.g., back angle, knee alignment)
   - Confidence indicator is shown
   - Top signals may be listed
4. If decision is **uncertain**:
   - An info card is shown explaining the model was unsure
   - May suggest re-recording with better angle/lighting
5. **Open browser DevTools → Network tab**, find the `/ml-analysis` API call:
   - Response should contain `posture_v1.decision`, `posture_v1.prob_fault`, `posture_v1.confidence`
   - `posture_v1.preprocessing.model_complexity` should be `2`
   - `posture_v1.named_scores` should be a non-empty object (when not uncertain)

### E5. Upload a Non-Squat Exercise

1. Go back to Record page
2. Select **Deadlift** (or any non-squat exercise)
3. Upload the same video
4. Wait for processing to complete
5. On the Analysis page, **VERIFY:**
   - You see an **"AI Scoring Coming Soon"** card (blue background)
   - The card says something like "AI-powered form analysis for Deadlift is not yet available. Currently supported: Squat."
   - There are NO named_scores, NO prob_fault, NO confidence displayed
   - The page does NOT crash or show errors
6. **DevTools check:** The `/ml-analysis` response should contain:
   ```json
   {"posture_v1": {"status": "not_supported", "exercise_type": "Deadlift", "reason": "..."}}
   ```

### E6. Upload a Low-Quality / Messy Video

1. Go back to Record page, select **Squat**
2. Upload one of the messy videos (e.g., `1665_stability_fault_1.mp4`)
3. Wait for processing
4. On Analysis page, check:
   - If decision is **uncertain**: an info/warning card should appear (quality flags)
   - If decision is **fault**: that's acceptable (these ARE bad form)
   - If decision is **good_form**: this is concerning — note it down

---

## F) Edge-Case Tests

### F1. Very Short Clip (< 1 second)

If you have a clip under 1 second (or trim one):
```bash
# Create a 0.5s clip from an existing video
ffmpeg -i test_videos/good/good_squat_01.mp4 -t 0.5 -c copy /tmp/too_short.mp4 2>/dev/null

python scripts/e2e_posture_v1_smoke.py --video /tmp/too_short.mp4
```

**EXPECT:** Either `uncertain` (quality gate triggered due to insufficient frames) or a graceful error. Should NOT crash the worker.

### F2. Non-Video File

```bash
echo "not a video" > /tmp/fake.mp4
python scripts/e2e_posture_v1_smoke.py --video /tmp/fake.mp4
```

**EXPECT:** Upload may succeed but processing should fail gracefully (FAILED status, not a worker crash).

### F3. Large/Long Video

If you have a video > 30 seconds:
```bash
python scripts/e2e_posture_v1_smoke.py --video /path/to/long_video.mp4 --timeout 300
```

**EXPECT:** Completes (may be slow). Check that `missing_ratio` and `frames_detected` are reasonable. The model pads/truncates to 300 frames, so very long videos should still work.

### F4. Check Celery Worker Logs

After all tests, scan the Celery worker terminal for:
```
# Look for these GOOD signs:
"PostureV1 inference complete"
"model_complexity=2"

# Look for these BAD signs:
"Traceback"
"Error"
"CUDA out of memory"  (shouldn't happen on CPU)
"NaN"
"infinity"
```

---

## G) Pass/Fail Rubric & Ship Gate

### Required Metrics (from Section C6 output)

| Metric | Ship Threshold | No-Ship Threshold |
|--------|---------------|-------------------|
| Precision | >= 0.70 | < 0.60 |
| Recall | >= 0.50 | < 0.40 |
| F1 Score | >= 0.55 | < 0.45 |
| Uncertain Rate | <= 40% | > 50% |
| Complexity=2 | 100% of videos | Any violation |
| Fallback to cx=1 | 0 | Any |
| Telemetry error rate | 0% | > 5% |
| Processing success rate | >= 95% | < 90% |
| Latency p95 | < 5000ms | > 10000ms |

### Decision Matrix

| Outcome | Action |
|---------|--------|
| **All green** | SHIP. PostureV1 is production-ready. |
| **Precision < 0.70 but > 0.60** | INVESTIGATE false positives. Check if they're borderline videos. Consider raising threshold from 0.525 to 0.55. |
| **Recall < 0.50 but > 0.40** | INVESTIGATE false negatives. Check if fault videos have high missing_ratio. Consider lowering threshold. |
| **Uncertain rate > 40%** | INVESTIGATE gate flags. If mostly `high_missing_ratio`, the videos may need better pose detection. If `angle_validity`, check MediaPipe output quality. |
| **Complexity violations** | DO NOT SHIP. Fix the complexity config and re-run. |
| **Telemetry errors > 0%** | Check DB connectivity. Telemetry failures shouldn't block inference but indicate infrastructure issues. |
| **Worker crashes** | DO NOT SHIP. Fix the crash, add error handling, re-run. |

### Threshold Adjustment Guide

If precision and recall are both marginal, try adjusting the threshold:

```bash
# Try strict threshold (0.55)
python scripts/e2e_posture_v1_smoke.py --video-dir test_videos/good --exercise-type squat --threshold-mode strict
python scripts/e2e_posture_v1_smoke.py --video-dir test_videos/fault --exercise-type squat --threshold-mode strict

# Try safety threshold (0.50)
python scripts/e2e_posture_v1_smoke.py --video-dir test_videos/good --exercise-type squat --threshold-mode safety
python scripts/e2e_posture_v1_smoke.py --video-dir test_videos/fault --exercise-type squat --threshold-mode safety
```

Compare the precision/recall at each threshold to find the best operating point.

---

## Final Checklist (Print and Check Off)

```
PRE-FLIGHT
[ ] Backend API responds at /health
[ ] Redis responds to PING
[ ] PostgreSQL is accessible
[ ] Celery worker responds to inspect ping
[ ] All 3 model artifacts present
[ ] USE_POSTURE_V1 = True, POSE_MODEL_COMPLEXITY = 2
[ ] Test videos: good=8, fault=13, messy=3
[ ] Test user can log in
[ ] No hardcoded mocks in production code

BACKEND
[ ] Required DB tables exist (form_checks, posture_v1_inference_logs)
[ ] PostureV1 unit tests pass
[ ] MediaPipe complexity unit tests pass

E2E SCRIPTS
[ ] Single video smoke test: PASS
[ ] Batch good/:  completed=8, no errors
[ ] Batch fault/: completed=13, no errors
[ ] Batch messy/: completed=3, no errors
[ ] Non-squat exercise returns not_supported
[ ] Precision >= 0.70
[ ] Recall >= 0.50
[ ] F1 >= 0.55
[ ] Uncertain rate <= 40%
[ ] Complexity=2 on 100% of videos
[ ] Zero fallbacks

TELEMETRY
[ ] posture_v1_inference_logs has >= 24 rows
[ ] Error rate = 0%
[ ] Latency p95 < 5000ms
[ ] Model version is consistent

FRONTEND
[ ] Login works, JWT stored
[ ] Exercise selection grid renders correctly
[ ] Squat upload -> processing -> analysis with real scores
[ ] Non-squat upload -> "Coming Soon" card, no crash
[ ] Uncertain decision -> info card with re-record suggestion
[ ] DevTools: /ml-analysis response has real PostureV1 fields

EDGE CASES
[ ] Short clip: graceful uncertain or error
[ ] Non-video file: graceful failure
[ ] No Celery worker crashes in logs

VERDICT: [ ] SHIP  /  [ ] NO SHIP
```

---

## H. How to Review Videos and Update Labels

When the batch script flags videos in the **review queue** (high-confidence FPs,
high-confidence FNs, or borderline cases), follow this workflow to confirm labels
and keep `labels_override.json` accurate.

### H.1 Generate the Review Queue

Run any batch with `--labels-override` to automatically produce
`backend/scripts/output/review_queue.json`:

```bash
python scripts/e2e_posture_v1_smoke.py \
  --video-dir test_videos/fault/ \
  --labels-override test_videos/labels_override.json \
  --metrics-scope posture_only
```

The review queue is also embedded inside `e2e_posture_v1_batch_report.json` for
reference.

### H.2 Open and Watch the Videos

```bash
# Print all review items with abs paths and `open` commands
python scripts/open_review_videos.py

# Print only Priority-1 high-confidence FPs
python scripts/open_review_videos.py --priority 1

# Auto-open each video in macOS default player
python scripts/open_review_videos.py --open

# Non-default queue file
python scripts/open_review_videos.py --queue /path/to/review_queue.json
```

**Priority levels:**

| Priority | Condition | Suggested action |
|----------|-----------|-----------------|
| P1 — High-confidence FP | `prob_fault >= 0.70` but labeled `good_form` | If confirmed good form, add to training data; if borderline form, leave as-is |
| P2 — High-confidence FN | `prob_fault <= 0.30` but labeled `posture_fault`/`fault` | If form looks good on video, override label to `good_form`; if genuinely bad, note as missed fault |
| P3 — Borderline | `abs(prob_fault - 0.525) < 0.05` | Watch video and decide label |

### H.3 Update labels_override.json

Edit `backend/test_videos/labels_override.json` to correct any confirmed mislabels:

```json
{
  "_comment": "Valid values: good_form | posture_fault | other_fault | messy",
  "1678_posture_fault_1.mp4": "good_form",
  "1677_good_rep_1.mp4":     "good_form",
  "1665_stability_fault_1.mp4": "other_fault"
}
```

**Label schema:**

| Value | Meaning | Included in scope |
|-------|---------|-------------------|
| `good_form` | Confirmed good form | Both `all` and `posture_only` |
| `posture_fault` | Confirmed posture fault (in-scope for PostureV1) | Both |
| `fault` | Legacy alias for `posture_fault` (backwards compat) | Both |
| `other_fault` | Stability/depth/other out-of-scope fault | `all` only (excluded from `posture_only`) |
| `messy` | Unusable video (bad angle, cut short, etc.) | Neither |

### H.4 Re-run with Updated Labels

```bash
# Run against all three folders to get updated combined metrics
for folder in good fault messy; do
  python scripts/e2e_posture_v1_smoke.py \
    --video-dir test_videos/$folder/ \
    --labels-override test_videos/labels_override.json \
    --metrics-scope posture_only
done
```

Then update `backend/scripts/output/posture_v1_combined_report.json` and
`posture_v1_labels_and_results.csv` to reflect the corrected labels.

### H.5 Scope-Aware Metrics Reference

`--metrics-scope posture_only` excludes `other_fault` videos from the confusion
matrix. This prevents stability/depth faults (which PostureV1 was not trained on)
from dragging down reported recall.

```
posture_only:  scorable = {good_form, fault, posture_fault}
all:           scorable = {good_form, fault, posture_fault, other_fault}
```

Use `posture_only` for day-to-day PostureV1 evaluation.
Use `all` when you want a full picture including out-of-scope faults.

---

*Generated for FormIQ PostureV1 validation — February 2026*
