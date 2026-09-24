#!/usr/bin/env bash
# The D table from the trail: the trail report (A1-A10) plus per-stage p50/p90 from
# analysis_runs.settings_snapshot->'stage_ms' (plan D6), for users whose email matches a LIKE pattern.
#   bash bench/pipeline_dashboard.sh 'w2val_%'
set -uo pipefail
LIKE="${1:?usage: pipeline_dashboard.sh <email LIKE pattern>}"
R="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE="${COMPOSE:-$R/backend/deployment/docker-compose.yml}"
psql_q() { docker compose -f "$COMPOSE" exec -T db psql -U postgres -d formiq -tAF'|' -c "$1" 2>/dev/null; }
IDS="SELECT id FROM form_checks WHERE user_id IN (SELECT id FROM users WHERE email LIKE '$LIKE')"
bash "$R/bench/trail_report.sh" "$LIKE"
echo
echo "--- throughput ---"
psql_q "SELECT 'videos=' || count(*) || '  videos/min=' || round(count(*)*60.0/GREATEST(extract(epoch from max(finished_at)-min(started_at)),1),2)
               || '  p50_ms=' || percentile_cont(0.5) WITHIN GROUP (ORDER BY latency_ms)::int
               || '  p90_ms=' || percentile_cont(0.9) WITHIN GROUP (ORDER BY latency_ms)::int
        FROM analysis_runs WHERE form_check_id IN ($IDS) AND status='completed';"
echo "--- per-stage wall time, ms (runs that carry stage_ms) ---"
psql_q "SELECT rpad(k,18) || ' n=' || count(*) || '  p50=' || percentile_cont(0.5) WITHIN GROUP (ORDER BY v::float)::int
               || '  p90=' || percentile_cont(0.9) WITHIN GROUP (ORDER BY v::float)::int
               || '  share_of_p50_total=' || round((100.0 * percentile_cont(0.5) WITHIN GROUP (ORDER BY v::float)
                    / NULLIF((SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY latency_ms) FROM analysis_runs r2
                              WHERE r2.form_check_id IN ($IDS) AND r2.status='completed' AND r2.settings_snapshot IS NOT NULL),0))::numeric, 1) || '%'
        FROM analysis_runs r, json_each_text((r.settings_snapshot::json)->'stage_ms') AS s(k, v)
        WHERE r.form_check_id IN ($IDS) AND r.status='completed' AND r.settings_snapshot IS NOT NULL
        GROUP BY k ORDER BY percentile_cont(0.5) WITHIN GROUP (ORDER BY v::float) DESC;"
psql_q "SELECT 'completed runs without stage_ms: ' || count(*) FROM analysis_runs WHERE form_check_id IN ($IDS) AND status='completed' AND settings_snapshot IS NULL;"
