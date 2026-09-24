#!/usr/bin/env bash
# audit/cache-is-the-db: a byte-identical re-upload must cost no inference and must leave a
# trail row. The Redis "analysis cache" was dead code (never written, never read; plan D3);
# what actually skips inference is the DB idempotency lookup on (user, content sha256, model
# version, spec hash). This runs the Stage A batch twice AS THE SAME USER with the same files:
# pass 1 judges the videos for real; pass 2 hits the lookup, which now (a) refuses a verdict
# from another pose pass and (b) records a run with pose_source='cache' copying the source
# verdict, so "how many uploads hit the cache" is a query.
#
#   bash bench/cache_hit_check.sh            # N=20 by default
#
# Env: N, SEL, EMAIL, BASE (passed through to stage_a_decision_trail.sh)
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
N="${N:-20}"; SEL="${SEL:-bench/results/parity_20_selection.json}"
EMAIL="${EMAIL:-cache_$(date +%s)@example.com}"; PASSWORD="${PASSWORD:-CacheCheck123!}"
COMPOSE="$ROOT/backend/deployment/docker-compose.yml"
psql_q() { docker compose -f "$COMPOSE" exec -T db psql -U postgres -d formiq -tAc "$1"; }
export EMAIL PASSWORD N SEL
cd "$ROOT"

echo "=== pass 1: real inference ($N videos) ==="
bash bench/stage_a_decision_trail.sh
echo; echo "=== pass 2: the same bytes, the same user ==="
T0=$(date +%s.%N)
bash bench/stage_a_decision_trail.sh
echo "pass 2 wall time: $(printf '%.1f' "$(echo "$(date +%s.%N) - $T0" | bc)") s"

U="(SELECT id FROM users WHERE email='$EMAIL')"
echo; echo "=== cache accounting for $EMAIL ==="
psql_q "SELECT 'form_checks (want $N)             : ' || count(*) FROM form_checks WHERE user_id = $U;"
psql_q "SELECT 'real completed runs (want $N)     : ' || count(*) FROM analysis_runs
        WHERE user_id = $U AND status='completed' AND COALESCE(pose_source,'') <> 'cache';"
psql_q "SELECT 'cache runs (want $N)              : ' || count(*) FROM analysis_runs
        WHERE user_id = $U AND pose_source = 'cache';"
psql_q "SELECT 'cache runs on another pass (want 0): ' || count(*) FROM analysis_runs c
        JOIN analysis_runs s ON s.id::text = (c.settings_snapshot::json)->>'cache_hit_of_run'
        WHERE c.user_id = $U AND c.pose_source = 'cache' AND c.pose_pass_id <> s.pose_pass_id;"
psql_q "SELECT 'verdict copied exactly (want $N)  : ' || count(*) FROM analysis_runs c
        JOIN analysis_runs s ON s.id::text = (c.settings_snapshot::json)->>'cache_hit_of_run'
        WHERE c.user_id = $U AND c.pose_source = 'cache' AND s.form_check_id = c.form_check_id
          AND c.final_decision IS NOT DISTINCT FROM s.final_decision
          AND c.final_score IS NOT DISTINCT FROM s.final_score
          AND c.n_frames IS NOT DISTINCT FROM s.n_frames;"
psql_q "SELECT 'cache latency ms p50 / max         : ' || round((percentile_cont(0.5) WITHIN GROUP (ORDER BY latency_ms))::numeric, 2)
        || ' / ' || round(max(latency_ms)::numeric, 2) FROM analysis_runs WHERE user_id = $U AND pose_source = 'cache';"
echo
bash bench/trail_report.sh "$EMAIL"
