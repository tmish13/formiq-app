#!/usr/bin/env bash
# Phase 1 acceptance: push N videos through API -> Celery -> Postgres CONCURRENTLY.
#
# Concurrency is the point. The original failure needed simultaneous tasks: under
# -P gevent every task shared one thread and one event loop, so the second
# concurrent asyncio.run() raised "cannot be called from a running event loop".
# The serial harness (celery_parity_submit.sh) does not reproduce it.
#
#   bash bench/phase1_concurrent_batch.sh
#
# Env: BASE, VID_DIR, SEL, N, TIMEOUT_S, EMAIL
set -uo pipefail
BASE="${BASE:-http://localhost:8000}"
VID_DIR="${VID_DIR:-$HOME/Desktop/Squat More/Labeled_Dataset/videos}"
SEL="${SEL:-bench/results/parity_20_selection.json}"
N="${N:-20}"
TIMEOUT_S="${TIMEOUT_S:-1800}"
# Fresh user per run: content-hash idempotency is scoped to (user, bytes, model),
# so reusing an account would dedupe against the previous run and dispatch nothing.
EMAIL="${EMAIL:-phase1_$(date +%s)@example.com}"
PASSWORD="${PASSWORD:-Phase1Batch123!}"
COMPOSE="backend/deployment/docker-compose.yml"

psql_q() { docker compose -f "$COMPOSE" exec -T db psql -U postgres -d formiq -tAc "$1"; }

echo "=== Phase 1 concurrent batch ==="
echo "user      : $EMAIL"
echo "videos    : $N"
echo "worker    : $(docker compose -f "$COMPOSE" logs worker --tail 500 2>&1 | grep -oE 'concurrency: [0-9]+ \([a-z]+\)' | tail -1)"
echo

curl -s -o /dev/null -X POST "$BASE/api/v1/auth/register" -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\",\"confirm_password\":\"$PASSWORD\",\"full_name\":\"Phase1\"}"
TOKEN=$(curl -s -X POST "$BASE/api/v1/auth/login" -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "username=$EMAIL" --data-urlencode "password=$PASSWORD" \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))")
[ -n "$TOKEN" ] || { echo "login failed" >&2; exit 1; }

VIDEOS=$(python3 -c "import json; rs=json.load(open('$SEL')); print(' '.join(r['video'] for r in rs[:$N]))")

OUT=$(mktemp -d)
echo "--- submitting $N videos in parallel ---"
T0=$(date +%s)
for v in $VIDEOS; do
  (
    BODY=$(curl -s -w '\n%{http_code} %{time_total}' \
          -X POST "$BASE/api/v1/form-checks/submit?exercise_name=squat&threshold_mode=default" \
          -H "Authorization: Bearer $TOKEN" -F "video_upload=@$VID_DIR/$v.mp4;type=video/mp4" 2>"$OUT/$v.curlerr")
    RC=$?
    META=$(printf '%s' "$BODY" | tail -1)
    ID=$(printf '%s' "$BODY" | sed '$d' \
        | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
    echo "$v ${ID:-NO_ID} curl_rc=$RC http=${META:-none}" > "$OUT/$v"
  ) &
done
wait
T_SUBMIT=$(( $(date +%s) - T0 ))
cat "$OUT"/*.curlerr > "$OUT/curl_errors.txt" 2>/dev/null
for f in "$OUT"/*; do case "$f" in *.curlerr) continue;; esac; cat "$f"; done | sort > "$OUT/pairs.txt"
SUBMITTED=$(awk '$2!="NO_ID"' "$OUT/pairs.txt" | wc -l | tr -d ' ')
echo "submitted $SUBMITTED/$N in ${T_SUBMIT}s"
if [ "$SUBMITTED" != "$N" ]; then
  echo "  --- submissions that did NOT produce a form check ---"
  awk '$2=="NO_ID"' "$OUT/pairs.txt" | sed 's/^/  /'
  echo "  --- curl stderr ---"
  sed 's/^/  /' "$OUT/curl_errors.txt" | sort -u | head -20
fi

# Only real UUIDs go into the IN list: an empty string makes Postgres reject the
# whole query as invalid uuid input, which silently breaks the poll loop below.
IDS=$(awk '$2!="NO_ID" {print "\x27"$2"\x27"}' "$OUT/pairs.txt" | paste -sd, -)
[ -n "$IDS" ] || { echo "no ids captured" >&2; exit 1; }

echo
echo "--- polling for terminal status (timeout ${TIMEOUT_S}s) ---"
while :; do
  ELAPSED=$(( $(date +%s) - T0 ))
  COUNTS=$(psql_q "SELECT status, count(*) FROM form_checks WHERE id IN ($IDS) GROUP BY status ORDER BY status;" | tr '\n' ' ')
  NONTERM=$(psql_q "SELECT count(*) FROM form_checks WHERE id IN ($IDS) AND status IN ('PENDING','PROCESSING');")
  printf "  t=%4ds  %s\n" "$ELAPSED" "$COUNTS"
  [ "${NONTERM:-1}" = "0" ] && break
  [ "$ELAPSED" -ge "$TIMEOUT_S" ] && { echo "  TIMED OUT with $NONTERM non-terminal"; break; }
  sleep 10
done
T_TOTAL=$(( $(date +%s) - T0 ))

echo
echo "=== RESULT ==="
echo "wall clock            : ${T_TOTAL}s"
echo "submitted             : $SUBMITTED/$N"
psql_q "SELECT 'status ' || status || ' : ' || count(*) FROM form_checks WHERE id IN ($IDS) GROUP BY status ORDER BY status;"
echo "stuck (PENDING/PROC)  : $(psql_q "SELECT count(*) FROM form_checks WHERE id IN ($IDS) AND status IN ('PENDING','PROCESSING');")"
echo "distinct content_hash : $(psql_q "SELECT count(DISTINCT content_hash) FROM form_checks WHERE id IN ($IDS);")"
echo "null content_hash     : $(psql_q "SELECT count(*) FROM form_checks WHERE id IN ($IDS) AND content_hash IS NULL;")"
echo
echo "--- per-video ---"
psql_q "SELECT f.id || ' ' || f.status || ' score=' || COALESCE(f.posture_score::text,'NULL') FROM form_checks f WHERE f.id IN ($IDS) ORDER BY f.created_at;"
echo
echo "pairs: $OUT/pairs.txt"
