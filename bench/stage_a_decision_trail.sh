#!/usr/bin/env bash
# Stage A acceptance: does every analysis leave an explainable trail?
#
# Phase 1's acceptance was "every dispatched task reaches a terminal state".
# This is the next question: for every task that finished, can we say WHAT was
# decided, BY WHICH checker, FROM WHICH inputs, and under WHICH pose pass?
#
# Six assertions, each printed with its number so a failure names itself:
#   A1  every terminal form check has an analysis_runs row
#   A2  every run has at least one checker_decisions row
#   A3  every closed run carries a pose_pass_id            (G-39)
#   A4  no run is left open after the batch drains
#   A5  depth_score is NULL everywhere                     (no unfitted verdict ships)
#   A6  every rule decision is recorded fitted=false AND advisory=true
#   A7  every decision that is NOT an abstention carries its score/prob
#   A8  every decision records the digest of the keypoints it saw
#   A9  every closed run records how many frames it judged
#
# A7-A9 exist because A1-A6 asserted rows EXIST and never that they were
# FILLED. They were not: depth's score was dropped by the outcome mapping and
# inputs_digest/n_frames were never written at all, on every row, silently.
# A green row-count check is not a green audit trail.
#
#   bash bench/stage_a_decision_trail.sh
#
# Env: BASE, VID_DIR, SEL, N, TIMEOUT_S
set -uo pipefail
BASE="${BASE:-http://localhost:8000}"
VID_DIR="${VID_DIR:-$HOME/Desktop/Squat More/Labeled_Dataset/videos}"
SEL="${SEL:-bench/results/parity_20_selection.json}"
N="${N:-8}"
TIMEOUT_S="${TIMEOUT_S:-1800}"
# A small stagger keeps the worker saturated while staying under the API memory
# cliff measured in G-36 (at 20 simultaneous uploads gunicorn workers are
# OOM-killed and requests are lost with no server-side log).
SUBMIT_STAGGER="${SUBMIT_STAGGER:-2}"
EMAIL="${EMAIL:-stagea_$(date +%s)@example.com}"
PASSWORD="${PASSWORD:-StageABatch123!}"
COMPOSE="backend/deployment/docker-compose.yml"

psql_q() { docker compose -f "$COMPOSE" exec -T db psql -U postgres -d formiq -tAc "$1"; }

echo "=== Stage A decision trail ==="
echo "user   : $EMAIL"
echo "videos : $N"
echo

curl -s -o /dev/null -X POST "$BASE/api/v1/auth/register" -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\",\"confirm_password\":\"$PASSWORD\",\"full_name\":\"StageA\"}"
TOKEN=$(curl -s -X POST "$BASE/api/v1/auth/login" -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "username=$EMAIL" --data-urlencode "password=$PASSWORD" \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))")
[ -n "$TOKEN" ] || { echo "login failed" >&2; exit 1; }

VIDEOS=$(python3 -c "import json; rs=json.load(open('$SEL')); print(' '.join(r['video'] for r in rs[:$N]))")
OUT=$(mktemp -d)
T0=$(date +%s)
for v in $VIDEOS; do
  (
    BODY=$(curl -s -X POST \
          "$BASE/api/v1/form-checks/submit?exercise_name=squat&threshold_mode=default" \
          -H "Authorization: Bearer $TOKEN" -F "video_upload=@$VID_DIR/$v.mp4;type=video/mp4")
    ID=$(printf '%s' "$BODY" \
        | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
    echo "$v ${ID:-NO_ID}" > "$OUT/$v"
  ) &
  [ "$SUBMIT_STAGGER" != "0" ] && sleep "$SUBMIT_STAGGER"
done
wait
cat "$OUT"/* | sort > "$OUT/pairs.txt"
SUBMITTED=$(awk '$2!="NO_ID"' "$OUT/pairs.txt" | wc -l | tr -d ' ')
echo "submitted $SUBMITTED/$N"
IDS=$(awk '$2!="NO_ID" {print "\x27"$2"\x27"}' "$OUT/pairs.txt" | paste -sd, -)
[ -n "$IDS" ] || { echo "no ids captured" >&2; exit 1; }

echo
echo "--- polling for terminal status ---"
while :; do
  ELAPSED=$(( $(date +%s) - T0 ))
  NONTERM=$(psql_q "SELECT count(*) FROM form_checks WHERE id IN ($IDS) AND status IN ('PENDING','PROCESSING');")
  printf "  t=%4ds  non-terminal=%s\n" "$ELAPSED" "${NONTERM:-?}"
  [ "${NONTERM:-1}" = "0" ] && break
  [ "$ELAPSED" -ge "$TIMEOUT_S" ] && { echo "  TIMED OUT"; break; }
  sleep 10
done

echo
echo "=== THE TRAIL ==="
echo "--- runs by status ---"
psql_q "SELECT '  ' || status || ' : ' || count(*) FROM analysis_runs
        WHERE form_check_id IN ($IDS) GROUP BY status ORDER BY status;"
echo "--- decisions by checker ---"
psql_q "SELECT '  ' || d.checker_name || '/' || d.target || ' ' || d.decision
             || '  fitted=' || d.fitted || ' advisory=' || d.advisory
             || '  n=' || count(*)
        FROM checker_decisions d JOIN analysis_runs r ON r.id = d.run_id
        WHERE r.form_check_id IN ($IDS)
        GROUP BY d.checker_name, d.target, d.decision, d.fitted, d.advisory
        ORDER BY d.checker_name, d.decision;"
echo "--- pose passes observed ---"
psql_q "SELECT '  ' || COALESCE(pose_pass_id,'(null)') || '  n=' || count(*)
        FROM analysis_runs WHERE form_check_id IN ($IDS) GROUP BY pose_pass_id;"

fail=0
chk() { # chk <n> <description> <actual> <expected>
  if [ "$3" = "$4" ]; then printf "  A%s PASS  %-52s %s\n" "$1" "$2" "$3"
  else printf "  A%s FAIL  %-52s got %s, want %s\n" "$1" "$2" "$3" "$4"; fail=1; fi
}

echo
echo "=== ASSERTIONS ==="
chk 1 "terminal form checks with no run row" \
  "$(psql_q "SELECT count(*) FROM form_checks f WHERE f.id IN ($IDS)
             AND f.status IN ('COMPLETED','FAILED')
             AND NOT EXISTS (SELECT 1 FROM analysis_runs r WHERE r.form_check_id = f.id);")" 0
chk 2 "runs with no checker decision" \
  "$(psql_q "SELECT count(*) FROM analysis_runs r WHERE r.form_check_id IN ($IDS)
             AND r.pose_source IS DISTINCT FROM 'cache'
             AND NOT EXISTS (SELECT 1 FROM checker_decisions d WHERE d.run_id = r.id);")" 0
chk 3 "closed runs missing a pose_pass_id" \
  "$(psql_q "SELECT count(*) FROM analysis_runs WHERE form_check_id IN ($IDS)
             AND finished_at IS NOT NULL AND pose_pass_id IS NULL;")" 0
chk 4 "runs still open" \
  "$(psql_q "SELECT count(*) FROM analysis_runs WHERE form_check_id IN ($IDS)
             AND finished_at IS NULL;")" 0
chk 5 "form checks carrying a depth_score" \
  "$(psql_q "SELECT count(*) FROM form_checks WHERE id IN ($IDS) AND depth_score IS NOT NULL;")" 0
chk 6 "rule decisions not marked unfitted+advisory" \
  "$(psql_q "SELECT count(*) FROM checker_decisions d JOIN analysis_runs r ON r.id = d.run_id
             WHERE r.form_check_id IN ($IDS) AND d.checker_kind = 'rule'
             AND NOT (d.fitted = false AND d.advisory = true);")" 0

chk 7 "answered rule decisions with no score" \
  "$(psql_q "SELECT count(*) FROM checker_decisions d JOIN analysis_runs r ON r.id = d.run_id
             WHERE r.form_check_id IN ($IDS) AND d.checker_kind = 'rule'
             AND d.abstained = false AND d.score IS NULL;")" 0
chk 8 "decisions with no inputs_digest" \
  "$(psql_q "SELECT count(*) FROM checker_decisions d JOIN analysis_runs r ON r.id = d.run_id
             WHERE r.form_check_id IN ($IDS) AND d.checker_kind = 'rule'
             AND d.inputs_digest IS NULL;")" 0
chk 9 "completed runs with no n_frames" \
  "$(psql_q "SELECT count(*) FROM analysis_runs WHERE form_check_id IN ($IDS)
             AND status = 'completed' AND n_frames IS NULL;")" 0

echo
echo "--- determinism: same inputs_digest => same decision? ---"
psql_q "SELECT '  ' || d.checker_name || ' ' || d.inputs_digest || ' -> '
             || count(DISTINCT d.decision || ':' || COALESCE(d.score::text,'-'))
             || ' distinct verdict(s) over ' || count(*) || ' rows'
        FROM checker_decisions d JOIN analysis_runs r ON r.id = d.run_id
        WHERE r.form_check_id IN ($IDS) AND d.inputs_digest IS NOT NULL
        GROUP BY d.checker_name, d.inputs_digest
        HAVING count(*) > 1;"
echo "  (more than 1 distinct verdict for one digest = nondeterminism)"

echo
[ "$fail" = "0" ] && echo "=== ALL ASSERTIONS PASS ===" || echo "=== FAILURES ABOVE ==="
echo "ids: $OUT/pairs.txt"
exit "$fail"
