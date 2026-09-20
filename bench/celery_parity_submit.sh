#!/usr/bin/env bash
# Phase E at small scale: push N raw .mp4 files through the real API -> Celery -> Postgres path.
# Writes "video form_check_id" pairs to stdout. Companion: bench/celery_parity_offline.py
set -uo pipefail
BASE="${BASE:-http://localhost:8000}"
VID_DIR="${VID_DIR:-$HOME/Desktop/Squat More/Labeled_Dataset/videos}"
SEL="${SEL:-bench/results/parity_20_selection.json}"
EMAIL="${EMAIL:-day1smoke@example.com}"; PASSWORD="${PASSWORD:-Day1Smoke123!}"
curl -s -o /dev/null -X POST "$BASE/api/v1/auth/register" -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\",\"confirm_password\":\"$PASSWORD\",\"full_name\":\"Parity\"}"
TOKEN=$(curl -s -X POST "$BASE/api/v1/auth/login" -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "username=$EMAIL" --data-urlencode "password=$PASSWORD" \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))")
[ -n "$TOKEN" ] || { echo "login failed" >&2; exit 1; }
for v in $(python3 -c "import json; print(' '.join(r['video'] for r in json.load(open('$SEL'))))"); do
  ID=$(curl -s -X POST "$BASE/api/v1/form-checks/submit?exercise_name=squat&threshold_mode=default" \
        -H "Authorization: Bearer $TOKEN" -F "video_upload=@$VID_DIR/$v.mp4;type=video/mp4" \
      | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
  echo "$v $ID"
  sleep 1
done
