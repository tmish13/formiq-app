#!/usr/bin/env bash
# Phase 1 acceptance, part 2: the behaviours that only show up when something
# goes wrong. Run against the live stack after phase1_concurrent_batch.sh.
#
#   bash bench/phase1_recovery_checks.sh
#
# 1. duplicate submit  -> one row, one inference, second call returns the first id
# 2. corrupt video     -> FAILED with a reason, and NOT retried (permanent)
# 3. stranded row      -> the reaper re-dispatches it, then gives up on strike two
set -uo pipefail
BASE="${BASE:-http://localhost:8000}"
VID_DIR="${VID_DIR:-$HOME/Desktop/Squat More/Labeled_Dataset/videos}"
VIDEO="${VIDEO:-33387_1}"
EMAIL="${EMAIL:-recov_$(date +%s)@example.com}"
PASSWORD="${PASSWORD:-Recovery123!}"
COMPOSE="backend/deployment/docker-compose.yml"

psql_q() { docker compose -f "$COMPOSE" exec -T db psql -U postgres -d formiq -tAc "$1" 2>/dev/null; }
submit() {  # $1 = file path -> prints the form_check id (or empty)
  curl -s -X POST "$BASE/api/v1/form-checks/submit?exercise_name=squat&threshold_mode=default" \
    -H "Authorization: Bearer $TOKEN" -F "video_upload=@$1;type=video/mp4" \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null
}
wait_terminal() {  # $1 = id, $2 = timeout
  local t=0
  while [ "$t" -lt "${2:-300}" ]; do
    local st; st=$(psql_q "SELECT status FROM form_checks WHERE id='$1';")
    case "$st" in COMPLETED|FAILED|CANCELLED) echo "$st"; return 0;; esac
    sleep 5; t=$((t+5))
  done
  psql_q "SELECT status FROM form_checks WHERE id='$1';"
}

curl -s -o /dev/null -X POST "$BASE/api/v1/auth/register" -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\",\"confirm_password\":\"$PASSWORD\",\"full_name\":\"Recovery\"}"
TOKEN=$(curl -s -X POST "$BASE/api/v1/auth/login" -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "username=$EMAIL" --data-urlencode "password=$PASSWORD" \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))")
[ -n "$TOKEN" ] || { echo "login failed" >&2; exit 1; }
echo "user: $EMAIL"

# ── 1. duplicate submit ──────────────────────────────────────────────────────
echo
echo "=== 1. duplicate submit (same user, same bytes, same model) ==="
ID1=$(submit "$VID_DIR/$VIDEO.mp4")
echo "first  submit -> $ID1"
S1=$(wait_terminal "$ID1" 300)
echo "first  status  : $S1"
ID2=$(submit "$VID_DIR/$VIDEO.mp4")
echo "second submit -> $ID2"
HASH=$(psql_q "SELECT content_hash FROM form_checks WHERE id='$ID1';")
ROWS=$(psql_q "SELECT count(*) FROM form_checks WHERE content_hash='$HASH' AND user_id=(SELECT id FROM users WHERE email='$EMAIL');")
echo "content_hash   : ${HASH:0:16}..."
echo "rows for it    : $ROWS   (expect 1)"
echo "same id back   : $([ "$ID1" = "$ID2" ] && echo YES || echo "NO  ($ID2)")"

# ── 2. corrupt video (permanent failure, no retry) ───────────────────────────
echo
echo "=== 2. corrupt video (permanent -> FAILED, no retry) ==="
BAD=$(mktemp -t corrupt).mp4
head -c 200000 /dev/urandom > "$BAD"
IDB=$(submit "$BAD")
echo "submit -> $IDB"
SB=$(wait_terminal "$IDB" 300)
echo "status : $SB"
echo "reason : $(psql_q "SELECT COALESCE(details->>'error_message','(none)') FROM form_checks WHERE id='$IDB';" | head -c 200)"
rm -f "$BAD"

# ── 3. stranded row -> reaper ────────────────────────────────────────────────
echo
echo "=== 3. stranded row (reaper) ==="
# Generate the id here rather than using RETURNING: psql -tAc prints the command
# tag ("INSERT 0 1") alongside the returned row, so $STUCK would hold both and
# every later query against it would silently match nothing.
STUCK=$(python3 -c "import uuid; print(uuid.uuid4())")
psql_q "INSERT INTO form_checks (id, user_id, exercise_id, video_id, video_url, status, created_at, updated_at)
  SELECT '$STUCK', user_id, exercise_id, video_id, video_url, 'PROCESSING', now() - interval '2 hours', now() - interval '2 hours'
  FROM form_checks WHERE id='$ID1';" >/dev/null
echo "planted PROCESSING row, last touched 2h ago: $STUCK"
echo "--- strike 1: expect re-dispatch (status -> PENDING, then the worker runs it) ---"
docker compose -f "$COMPOSE" exec -T worker python -c "
import warnings; warnings.filterwarnings('ignore')
from app.tasks.maintenance_tasks import _reap_stuck_form_checks
import asyncio, json
print('REAPER', json.dumps(asyncio.run(_reap_stuck_form_checks())))
" 2>&1 | grep REAPER
echo "status after   : $(psql_q "SELECT status FROM form_checks WHERE id='$STUCK';")"
echo "details        : $(psql_q "SELECT details::text FROM form_checks WHERE id='$STUCK';" | head -c 200)"
echo "final status   : $(wait_terminal "$STUCK" 300)"

echo
echo "--- strike 2: a row already re-dispatched and stuck again must FAIL, not loop ---"
psql_q "UPDATE form_checks SET status='PROCESSING', updated_at=now() - interval '2 hours' WHERE id='$STUCK';" >/dev/null
docker compose -f "$COMPOSE" exec -T worker python -c "
import warnings; warnings.filterwarnings('ignore')
from app.tasks.maintenance_tasks import _reap_stuck_form_checks
import asyncio, json
print('REAPER', json.dumps(asyncio.run(_reap_stuck_form_checks())))
" 2>&1 | grep REAPER
echo "status after   : $(psql_q "SELECT status FROM form_checks WHERE id='$STUCK';")"
echo "reason         : $(psql_q "SELECT details->>'error_message' FROM form_checks WHERE id='$STUCK';" | head -c 220)"
