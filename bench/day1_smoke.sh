#!/usr/bin/env bash
#
# Day 1 smoke: prove the FormIQ pipeline processes a real squat video
# end-to-end against the LOCAL docker-compose stack.
#
#   upload -> Celery -> MediaPipe pose extraction -> PostureV1 CNN-LSTM -> COMPLETED
#
# Unlike the repo-root smoke_test.sh (which points at the deployed Render API
# and only prints output), this script ASSERTS a terminal COMPLETED status and
# exits non-zero otherwise, so it is usable as evidence.
#
# Usage:
#   docker compose -f backend/deployment/docker-compose.yml up -d
#   bash bench/day1_smoke.sh
#
# Env overrides:
#   BASE   API base URL        (default http://localhost:8000)
#   VIDEO  path to test video  (default backend/test_videos/good/T6ad8Et3C5Q_good_rep_1.mp4)
#
set -uo pipefail

BASE="${BASE:-http://localhost:8000}"
VIDEO="${VIDEO:-backend/test_videos/good/T6ad8Et3C5Q_good_rep_1.mp4}"
# NB: not a .local address — email-validator rejects reserved TLDs with
# "The part after the @-sign is a special-use or reserved name".
EMAIL="${EMAIL:-day1smoke@example.com}"
PASSWORD="${PASSWORD:-Day1Smoke123!}"
MAX_POLLS="${MAX_POLLS:-60}"
POLL_SECONDS="${POLL_SECONDS:-5}"

say() { printf '\n=== %s ===\n' "$1"; }
die() { printf '\nFAIL: %s\n' "$1" >&2; exit 1; }

say "Environment"
echo "BASE=$BASE"
echo "VIDEO=$VIDEO"
[ -f "$VIDEO" ] || die "video not found: $VIDEO (run from repo root)"
ls -lh "$VIDEO"

say "API reachable?"
curl -fsS --max-time 10 "$BASE/" || die "API not reachable at $BASE — is the stack up?"
echo

# ---------------------------------------------------------------------------
# 1. Register (idempotent — 400/409 if the user already exists) + login
# ---------------------------------------------------------------------------
say "Register (ok if already exists)"
curl -s -o /dev/null -w 'register HTTP %{http_code}\n' \
  -X POST "$BASE/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\",\"confirm_password\":\"$PASSWORD\",\"full_name\":\"Day1 Smoke\"}"

say "Login"
LOGIN_JSON=$(curl -s -X POST "$BASE/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "username=$EMAIL" \
  --data-urlencode "password=$PASSWORD")

TOKEN=$(printf '%s' "$LOGIN_JSON" \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)

[ -n "$TOKEN" ] || die "login returned no access_token. Response: $LOGIN_JSON"
echo "token acquired (${#TOKEN} chars)"

# ---------------------------------------------------------------------------
# 2. Submit the video
# ---------------------------------------------------------------------------
say "Submit squat video"
SUBMIT_START=$(date +%s)
SUBMIT_JSON=$(curl -s -X POST \
  "$BASE/api/v1/form-checks/submit?exercise_name=squat&threshold_mode=default" \
  -H "Authorization: Bearer $TOKEN" \
  -F "video_upload=@$VIDEO;type=video/mp4")

printf '%s\n' "$SUBMIT_JSON" | python3 -m json.tool 2>/dev/null || printf '%s\n' "$SUBMIT_JSON"

FORM_CHECK_ID=$(printf '%s' "$SUBMIT_JSON" \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
[ -n "$FORM_CHECK_ID" ] || die "submit did not return an id. Response: $SUBMIT_JSON"
echo "FORM_CHECK_ID=$FORM_CHECK_ID"

# ---------------------------------------------------------------------------
# 3. Poll to a terminal state
# ---------------------------------------------------------------------------
say "Poll until terminal (max $((MAX_POLLS * POLL_SECONDS))s)"
STATUS=""
FINAL_JSON=""
for i in $(seq 1 "$MAX_POLLS"); do
  FINAL_JSON=$(curl -s "$BASE/api/v1/form-checks/$FORM_CHECK_ID" \
    -H "Authorization: Bearer $TOKEN")
  STATUS=$(printf '%s' "$FINAL_JSON" \
    | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null)
  printf 'poll %02d  t=%03ds  status=%s\n' "$i" "$(( $(date +%s) - SUBMIT_START ))" "${STATUS:-<unparseable>}"
  case "$STATUS" in
    completed|COMPLETED|failed|FAILED) break ;;
  esac
  sleep "$POLL_SECONDS"
done
ELAPSED=$(( $(date +%s) - SUBMIT_START ))

say "Final form check"
printf '%s\n' "$FINAL_JSON" | python3 -m json.tool 2>/dev/null || printf '%s\n' "$FINAL_JSON"

say "PostureV1 result"
printf '%s' "$FINAL_JSON" | python3 -c '
import sys, json
d = json.load(sys.stdin)
pv1 = (d.get("results") or {}).get("posture_v1") or {}
print("decision      :", pv1.get("decision"))
print("prob_fault    :", pv1.get("prob_fault"))
print("confidence    :", pv1.get("confidence"))
print("threshold     :", pv1.get("threshold"))
print("model_version :", pv1.get("model_version"))
print("latency_ms    :", pv1.get("latency_ms"))
print("quality_flags :", pv1.get("quality_flags"))
print("posture_score :", d.get("posture_score"))
' 2>/dev/null || echo "(could not parse posture_v1 block)"

say "Verdict"
echo "elapsed_seconds=$ELAPSED"
case "$STATUS" in
  completed|COMPLETED)
    echo "PASS: form check reached COMPLETED"
    exit 0
    ;;
  failed|FAILED)
    die "form check reached FAILED (see error/details above)"
    ;;
  *)
    die "form check never reached a terminal state (last status='${STATUS:-<none>}' after ${ELAPSED}s)"
    ;;
esac
