#!/usr/bin/env bash
# Re-run the Stage A decision-trail report (THE TRAIL + assertions A1-A10 + determinism)
# over every form check owned by users whose email matches a SQL LIKE pattern.
#
# stage_a_decision_trail.sh submits a batch and then polls up to TIMEOUT_S; on a batch
# larger than its timeout it prints the trail against a half-drained queue. This script
# is the same report, decoupled from submission, so it can be run once the queue has
# actually drained (and re-run at any later time -- the trail is append-only).
#
#   bash bench/trail_report.sh 'gate1b_%'
set -uo pipefail
LIKE="${1:?usage: trail_report.sh <email LIKE pattern>}"
# Resolved from this script's location, not the caller's cwd: run from anywhere else and
# `docker compose` silently found no file, every query returned "", and every assertion
# printed `got , want 0` -- a report that fails without saying why.
COMPOSE="${COMPOSE:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/backend/deployment/docker-compose.yml}"
[ -f "$COMPOSE" ] || { echo "compose file not found: $COMPOSE" >&2; exit 2; }
psql_q() { docker compose -f "$COMPOSE" exec -T db psql -U postgres -d formiq -tAc "$1" 2>/dev/null; }
IDS="SELECT id FROM form_checks WHERE user_id IN (SELECT id FROM users WHERE email LIKE '$LIKE')"

echo "=== decision trail for users LIKE '$LIKE' ==="
echo "--- form checks by status ---"
psql_q "SELECT '  ' || status || ' : ' || count(*) FROM form_checks WHERE id IN ($IDS) GROUP BY status ORDER BY status;"
echo "--- runs by status ---"
psql_q "SELECT '  ' || status || ' : ' || count(*) FROM analysis_runs WHERE form_check_id IN ($IDS) GROUP BY status ORDER BY status;"
echo "--- runs by error_type (failed/abandoned) ---"
psql_q "SELECT '  ' || COALESCE(error_type,'(null)') || ' : ' || count(*) FROM analysis_runs
        WHERE form_check_id IN ($IDS) AND status <> 'completed' GROUP BY error_type ORDER BY 1;"
echo "--- decisions by checker ---"
psql_q "SELECT '  ' || d.checker_name || '/' || d.target || ' ' || d.decision
             || '  fitted=' || d.fitted || ' advisory=' || d.advisory || '  n=' || count(*)
        FROM checker_decisions d JOIN analysis_runs r ON r.id = d.run_id
        WHERE r.form_check_id IN ($IDS)
        GROUP BY d.checker_name, d.target, d.decision, d.fitted, d.advisory
        ORDER BY d.checker_name, d.decision;"
echo "--- pose passes observed ---"
psql_q "SELECT '  ' || COALESCE(pose_pass_id,'(null)') || '  n=' || count(*)
        FROM analysis_runs WHERE form_check_id IN ($IDS) GROUP BY pose_pass_id;"
echo "--- latency (completed runs, ms) ---"
psql_q "SELECT '  n=' || count(*) || '  p50=' || percentile_cont(0.5) WITHIN GROUP (ORDER BY latency_ms)::int
             || '  p90=' || percentile_cont(0.9) WITHIN GROUP (ORDER BY latency_ms)::int
             || '  max=' || max(latency_ms)::int
        FROM analysis_runs WHERE form_check_id IN ($IDS) AND status='completed' AND latency_ms IS NOT NULL;"

fail=0
chk() { if [ "$3" = "$4" ]; then printf "  A%s PASS  %-52s %s\n" "$1" "$2" "$3"
        else printf "  A%s FAIL  %-52s got %s, want %s\n" "$1" "$2" "$3" "$4"; fail=1; fi; }
echo; echo "=== ASSERTIONS ==="
chk 1 "terminal form checks with no run row" "$(psql_q "SELECT count(*) FROM form_checks f WHERE f.id IN ($IDS)
  AND f.status IN ('COMPLETED','FAILED') AND NOT EXISTS (SELECT 1 FROM analysis_runs r WHERE r.form_check_id = f.id);")" 0
chk 2 "completed runs with no checker decision" "$(psql_q "SELECT count(*) FROM analysis_runs r WHERE r.form_check_id IN ($IDS)
  AND r.status='completed' AND NOT EXISTS (SELECT 1 FROM checker_decisions d WHERE d.run_id = r.id);")" 0
chk 3 "closed runs missing a pose_pass_id" "$(psql_q "SELECT count(*) FROM analysis_runs WHERE form_check_id IN ($IDS)
  AND finished_at IS NOT NULL AND status='completed' AND pose_pass_id IS NULL;")" 0
chk 4 "runs still open" "$(psql_q "SELECT count(*) FROM analysis_runs WHERE form_check_id IN ($IDS) AND finished_at IS NULL;")" 0
chk 5 "form checks carrying a depth_score" "$(psql_q "SELECT count(*) FROM form_checks WHERE id IN ($IDS) AND depth_score IS NOT NULL;")" 0
chk 6 "rule decisions not marked unfitted+advisory" "$(psql_q "SELECT count(*) FROM checker_decisions d JOIN analysis_runs r ON r.id = d.run_id
  WHERE r.form_check_id IN ($IDS) AND d.checker_kind = 'rule' AND NOT (d.fitted = false AND d.advisory = true);")" 0
chk 7 "answered rule decisions with no score" "$(psql_q "SELECT count(*) FROM checker_decisions d JOIN analysis_runs r ON r.id = d.run_id
  WHERE r.form_check_id IN ($IDS) AND d.checker_kind = 'rule' AND d.abstained = false AND d.score IS NULL;")" 0
chk 8 "decisions with no inputs_digest" "$(psql_q "SELECT count(*) FROM checker_decisions d JOIN analysis_runs r ON r.id = d.run_id
  WHERE r.form_check_id IN ($IDS) AND d.checker_kind = 'rule' AND d.inputs_digest IS NULL;")" 0
chk 9 "completed runs with no n_frames" "$(psql_q "SELECT count(*) FROM analysis_runs WHERE form_check_id IN ($IDS)
  AND status = 'completed' AND n_frames IS NULL;")" 0
# A10 (G-48): a terminal row must agree with its latest closed run, and no video may have been
# judged twice for real. form_checks.status holds the enum NAME ('COMPLETED'); analysis_runs.
# outcome_status holds the VALUE written at close ('completed'). A duplicate dispatch that flipped a
# finished row never opened a run, so "status disagrees with the latest closed run" is exactly the
# flip -- queryable today, no new column. The second term counts videos with more than one real
# (non-cache) completed run: double processing.
chk 10 "terminal rows disagreeing with their latest closed run, or judged twice" "$(psql_q "
  SELECT (SELECT count(*) FROM form_checks f
            JOIN LATERAL (SELECT outcome_status FROM analysis_runs r
                          WHERE r.form_check_id = f.id AND r.status IN ('completed','failed')
                          ORDER BY finished_at DESC LIMIT 1) lr ON true
           WHERE f.id IN ($IDS) AND f.status IN ('COMPLETED','FAILED')
             AND upper(lr.outcome_status) <> f.status::text)
       + (SELECT count(*) FROM (SELECT form_check_id FROM analysis_runs
                                WHERE form_check_id IN ($IDS) AND status = 'completed'
                                  AND COALESCE(pose_source,'') <> 'cache'
                                GROUP BY form_check_id HAVING count(*) > 1) d);")" 0
echo; echo "--- determinism: digests with more than one distinct verdict ---"
psql_q "SELECT '  ' || d.checker_name || ' ' || d.inputs_digest || ' -> '
             || count(DISTINCT d.decision || ':' || COALESCE(d.score::text,'-')) || ' distinct over ' || count(*) || ' rows'
        FROM checker_decisions d JOIN analysis_runs r ON r.id = d.run_id
        WHERE r.form_check_id IN ($IDS) AND d.inputs_digest IS NOT NULL
        GROUP BY d.checker_name, d.inputs_digest HAVING count(*) > 1
          AND count(DISTINCT d.decision || ':' || COALESCE(d.score::text,'-')) > 1;"
echo "  (empty = deterministic)"
echo; [ "$fail" = "0" ] && echo "=== ALL ASSERTIONS PASS ===" || echo "=== FAILURES ABOVE ==="
exit "$fail"
