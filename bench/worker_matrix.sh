#!/usr/bin/env bash
# Worker concurrency x threads matrix (plan D2b, G-46).
#
# For each cell the worker is recreated with WORKER_CONCURRENCY / WORKER_THREADS, N videos go
# through the live pipeline under a cell-specific user (the Stage A harness), the worker's RSS is
# sampled every 10 s, and the cell's numbers come from the decision trail:
#   videos/min, p50 and p90 latency (analysis_runs.latency_ms), peak RSS, SIGKILLs, child recycles.
# Baseline to beat, measured 2026-09-24 with the old settings (concurrency 4, threads unbounded,
# no recycling): 7 SIGKILLs / 900 videos, 6-10 videos/min, p50 28-38 s.
#
#   CELLS="2:1 2:2 3:1 3:2 4:1 4:2" N=80 bash bench/worker_matrix.sh
#
# Writes bench/results/worker_matrix/<cell>.{harness.txt,rss} and appends one line per cell to
# bench/results/worker_matrix/matrix.tsv. Leaves the worker running with the compose defaults.
set -uo pipefail
R="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE="$R/backend/deployment/docker-compose.yml"
CELLS="${CELLS:-2:1 2:2 3:1 3:2 4:1 4:2}"
N="${N:-80}"
SEL="${SEL:-$R/bench/results/gate1b_selection.json}"
OUT="$R/bench/results/worker_matrix"; mkdir -p "$OUT"
psql_q() { docker compose -f "$COMPOSE" exec -T db psql -U postgres -d formiq -tAc "$1" 2>/dev/null; }

[ -f "$OUT/matrix.tsv" ] || echo -e "concurrency\tthreads\tn\tterminal\tcompleted\tvideos_per_min\tp50_ms\tp90_ms\tpeak_rss\tsigkills\trecycles\tuser" > "$OUT/matrix.tsv"
for cell in $CELLS; do
  C="${cell%%:*}"; T="${cell##*:}"; TAG="mx_c${C}t${T}_$(date +%s)"
  echo "=== cell concurrency=$C threads=$T  user=${TAG}@example.com  $(date) ==="
  WORKER_CONCURRENCY=$C WORKER_THREADS=$T docker compose -f "$COMPOSE" up -d --force-recreate --no-deps worker >/dev/null 2>&1
  sleep 25
  ( while true; do docker stats --no-stream --format '{{.MemUsage}}' deployment-worker-1 2>/dev/null | awk '{print $1}'; sleep 10; done ) > "$OUT/$TAG.rss" &
  SAMPLER=$!
  START=$(date +%s)
  SEL="$SEL" N="$N" TIMEOUT_S=3600 SUBMIT_STAGGER=1 EMAIL="${TAG}@example.com" \
    bash "$R/bench/stage_a_decision_trail.sh" > "$OUT/$TAG.harness.txt" 2>&1
  END=$(date +%s); kill "$SAMPLER" 2>/dev/null
  WINDOW=$((END - START + 40))
  KILLS=$(docker compose -f "$COMPOSE" logs --since "${WINDOW}s" worker 2>/dev/null | grep -c "exited with 'signal 9")
  RECYCLES=$(docker compose -f "$COMPOSE" logs --since "${WINDOW}s" worker 2>/dev/null | grep -ciE "worker: maxtasksperchild|max memory|worker exited after")
  IDS="SELECT id FROM form_checks WHERE user_id IN (SELECT id FROM users WHERE email='${TAG}@example.com')"
  STATS=$(psql_q "SELECT count(*) || E'\t' || round(count(*)*60.0/GREATEST(extract(epoch from max(finished_at)-min(started_at)),1),2)
                   || E'\t' || percentile_cont(0.5) WITHIN GROUP (ORDER BY latency_ms)::int
                   || E'\t' || percentile_cont(0.9) WITHIN GROUP (ORDER BY latency_ms)::int
                  FROM analysis_runs WHERE form_check_id IN ($IDS) AND status='completed';")
  TERMINAL=$(psql_q "SELECT count(*) FROM form_checks WHERE id IN ($IDS) AND status IN ('COMPLETED','FAILED');")
  PEAK=$(python3 - "$OUT/$TAG.rss" <<'PY'
import sys, re
best = 0.0
for l in open(sys.argv[1]):
    m = re.match(r"([\d.]+)\s*([KMG]i?B)", l.strip())
    if not m: continue
    v, u = float(m.group(1)), m.group(2)[0]
    best = max(best, v * {"K": 1/1024, "M": 1, "G": 1024}[u])
print(f"{best:.0f}MiB")
PY
)
  echo -e "$C\t$T\t$N\t${TERMINAL:-?}\t${STATS:-?}\t$PEAK\t$KILLS\t$RECYCLES\t${TAG}@example.com" | tee -a "$OUT/matrix.tsv"
done
echo "=== restoring the worker to the compose defaults ==="
docker compose -f "$COMPOSE" up -d --force-recreate --no-deps worker >/dev/null 2>&1
column -t -s $'\t' "$OUT/matrix.tsv"
