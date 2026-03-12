#!/usr/bin/env python3
"""
Telemetry aggregation report for PostureV1 inference logs.

Queries the posture_v1_inference_logs table and produces an aggregated
report with key metrics for shipping confidence.

Usage:
    python scripts/report_posture_v1_telemetry.py
    python scripts/report_posture_v1_telemetry.py --database-url postgresql://...
    python scripts/report_posture_v1_telemetry.py --since 2026-02-01
    python scripts/report_posture_v1_telemetry.py --limit 1000

Environment variables:
    DATABASE_URL - PostgreSQL connection string (required if --database-url not provided)

Output:
    Prints report to stdout and saves JSON to scripts/output/posture_v1_telemetry_report.json
"""

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "output"


def get_db_connection(database_url: str):
    """Create a database connection using psycopg2."""
    try:
        import psycopg2
        import psycopg2.extras
    except ImportError:
        print("ERROR: psycopg2 not installed. Install with: pip install psycopg2-binary", file=sys.stderr)
        sys.exit(1)

    try:
        conn = psycopg2.connect(database_url)
        return conn
    except Exception as e:
        print(f"ERROR: Could not connect to database: {e}", file=sys.stderr)
        sys.exit(1)


def fetch_telemetry_rows(conn, since: str | None, limit: int | None) -> list[dict]:
    """Fetch telemetry rows from posture_v1_inference_logs."""
    import psycopg2.extras

    query = """
        SELECT
            id, created_at, form_check_id, video_id,
            decision, prob_fault, confidence, threshold, threshold_mode, posture_v1_mode,
            sequence_length, missing_ratio, outlier_z_gt3, outlier_z_gt6,
            angle_validity, gate_flags,
            top_signals, named_scores,
            model_version, latency_ms,
            error
        FROM posture_v1_inference_logs
    """
    conditions = []
    params = []

    if since:
        conditions.append("created_at >= %s")
        params.append(since)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY created_at DESC"

    if limit:
        query += " LIMIT %s"
        params.append(limit)

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(query, params)
        rows = cur.fetchall()

    return [dict(r) for r in rows]


def compute_report(rows: list[dict]) -> dict:
    """Compute aggregated metrics from telemetry rows."""
    if not rows:
        return {
            "total_inferences": 0,
            "message": "No telemetry rows found",
        }

    total = len(rows)

    # Decision breakdown
    decision_counts = Counter(r["decision"] for r in rows)
    uncertain_count = decision_counts.get("uncertain", 0)
    uncertain_rate = round(uncertain_count / total, 4) if total > 0 else 0

    # Error rate
    error_rows = [r for r in rows if r.get("error")]
    error_rate = round(len(error_rows) / total, 4) if total > 0 else 0

    # Missing ratio stats
    missing_ratios = [r["missing_ratio"] for r in rows if r.get("missing_ratio") is not None]
    missing_ratio_stats = {}
    if missing_ratios:
        missing_ratio_stats = {
            "avg": round(mean(missing_ratios), 4),
            "median": round(median(missing_ratios), 4),
            "min": round(min(missing_ratios), 4),
            "max": round(max(missing_ratios), 4),
            "count": len(missing_ratios),
        }

    # Latency stats
    latencies = [r["latency_ms"] for r in rows if r.get("latency_ms") is not None]
    latency_stats = {}
    if latencies:
        sorted_lat = sorted(latencies)
        p50_idx = len(sorted_lat) // 2
        p95_idx = int(len(sorted_lat) * 0.95)
        p99_idx = int(len(sorted_lat) * 0.99)
        latency_stats = {
            "avg_ms": round(mean(latencies), 1),
            "median_ms": round(median(latencies), 1),
            "p95_ms": round(sorted_lat[min(p95_idx, len(sorted_lat) - 1)], 1),
            "p99_ms": round(sorted_lat[min(p99_idx, len(sorted_lat) - 1)], 1),
            "min_ms": round(min(latencies), 1),
            "max_ms": round(max(latencies), 1),
            "count": len(latencies),
        }

    # Prob fault stats (non-uncertain only)
    prob_faults = [
        r["prob_fault"] for r in rows
        if r.get("prob_fault") is not None and r.get("decision") != "uncertain"
    ]
    prob_fault_stats = {}
    if prob_faults:
        prob_fault_stats = {
            "avg": round(mean(prob_faults), 4),
            "median": round(median(prob_faults), 4),
            "min": round(min(prob_faults), 4),
            "max": round(max(prob_faults), 4),
            "count": len(prob_faults),
        }

    # Confidence stats (non-uncertain only)
    confidences = [
        r["confidence"] for r in rows
        if r.get("confidence") is not None and r.get("decision") != "uncertain"
    ]
    confidence_stats = {}
    if confidences:
        confidence_stats = {
            "avg": round(mean(confidences), 4),
            "median": round(median(confidences), 4),
            "min": round(min(confidences), 4),
            "max": round(max(confidences), 4),
        }

    # Sequence length stats
    seq_lengths = [r["sequence_length"] for r in rows if r.get("sequence_length") is not None]
    seq_length_stats = {}
    if seq_lengths:
        seq_length_stats = {
            "avg": round(mean(seq_lengths), 0),
            "median": round(median(seq_lengths), 0),
            "min": min(seq_lengths),
            "max": max(seq_lengths),
        }

    # Gate flags frequency
    gate_flag_counts = Counter()
    for r in rows:
        flags = r.get("gate_flags") or []
        if isinstance(flags, list):
            for f in flags:
                gate_flag_counts[f] += 1

    # Outlier stats
    z3_counts = [r["outlier_z_gt3"] for r in rows if r.get("outlier_z_gt3") is not None]
    z6_counts = [r["outlier_z_gt6"] for r in rows if r.get("outlier_z_gt6") is not None]
    outlier_stats = {}
    if z3_counts:
        outlier_stats["z_gt3_avg"] = round(mean(z3_counts), 1)
    if z6_counts:
        outlier_stats["z_gt6_avg"] = round(mean(z6_counts), 1)

    # Breakdown by threshold_mode
    mode_breakdown = defaultdict(lambda: {"count": 0, "decisions": Counter()})
    for r in rows:
        mode = r.get("threshold_mode") or "default"
        mode_breakdown[mode]["count"] += 1
        mode_breakdown[mode]["decisions"][r["decision"]] += 1
    # Convert Counters to dicts for JSON serialization
    mode_breakdown = {
        k: {"count": v["count"], "decisions": dict(v["decisions"])}
        for k, v in mode_breakdown.items()
    }

    # Breakdown by posture_v1_mode (active vs shadow)
    pv1_mode_breakdown = defaultdict(lambda: {"count": 0, "decisions": Counter()})
    for r in rows:
        pmode = r.get("posture_v1_mode") or "active"
        pv1_mode_breakdown[pmode]["count"] += 1
        pv1_mode_breakdown[pmode]["decisions"][r["decision"]] += 1
    pv1_mode_breakdown = {
        k: {"count": v["count"], "decisions": dict(v["decisions"])}
        for k, v in pv1_mode_breakdown.items()
    }

    # Breakdown by decision
    decision_details = {}
    for decision_val in decision_counts:
        subset = [r for r in rows if r["decision"] == decision_val]
        pfs = [r["prob_fault"] for r in subset if r.get("prob_fault") is not None]
        confs = [r["confidence"] for r in subset if r.get("confidence") is not None]
        lats = [r["latency_ms"] for r in subset if r.get("latency_ms") is not None]
        decision_details[decision_val] = {
            "count": len(subset),
            "pct": round(len(subset) / total * 100, 1),
            "avg_prob_fault": round(mean(pfs), 4) if pfs else None,
            "avg_confidence": round(mean(confs), 4) if confs else None,
            "avg_latency_ms": round(mean(lats), 1) if lats else None,
        }

    # Model version breakdown
    version_counts = Counter(r.get("model_version") or "unknown" for r in rows)

    # Time range
    created_ats = [r["created_at"] for r in rows if r.get("created_at")]
    time_range = {}
    if created_ats:
        time_range = {
            "earliest": str(min(created_ats)),
            "latest": str(max(created_ats)),
        }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_inferences": total,
        "time_range": time_range,
        "error_count": len(error_rows),
        "error_rate": error_rate,
        "uncertain_count": uncertain_count,
        "uncertain_rate": uncertain_rate,
        "decisions": dict(decision_counts),
        "decision_details": decision_details,
        "missing_ratio": missing_ratio_stats,
        "latency": latency_stats,
        "prob_fault": prob_fault_stats,
        "confidence": confidence_stats,
        "sequence_length": seq_length_stats,
        "outliers": outlier_stats,
        "gate_flags": dict(gate_flag_counts.most_common(20)),
        "by_threshold_mode": mode_breakdown,
        "by_posture_v1_mode": pv1_mode_breakdown,
        "model_versions": dict(version_counts),
    }


def print_report(report: dict):
    """Print a human-readable report to stdout."""
    print("=" * 70)
    print("POSTURE V1 TELEMETRY REPORT")
    print("=" * 70)

    if report.get("total_inferences") == 0:
        print(f"\n  {report.get('message', 'No data')}")
        print("=" * 70)
        return

    print(f"\n  Generated:        {report['generated_at']}")
    tr = report.get("time_range", {})
    if tr:
        print(f"  Time range:       {tr.get('earliest', '?')} -> {tr.get('latest', '?')}")
    print(f"  Total inferences: {report['total_inferences']}")
    print(f"  Error count:      {report['error_count']} ({report['error_rate']:.1%})")
    print(f"  Uncertain rate:   {report['uncertain_count']} ({report['uncertain_rate']:.1%})")

    print(f"\n  Decisions:")
    for d, detail in report.get("decision_details", {}).items():
        print(f"    {d:15s}: {detail['count']:4d} ({detail['pct']:5.1f}%)  "
              f"avg_prob={detail.get('avg_prob_fault', '?')}  "
              f"avg_conf={detail.get('avg_confidence', '?')}")

    mr = report.get("missing_ratio", {})
    if mr:
        print(f"\n  Missing ratio:    avg={mr['avg']:.4f}  median={mr['median']:.4f}  "
              f"min={mr['min']:.4f}  max={mr['max']:.4f}")

    lat = report.get("latency", {})
    if lat:
        print(f"  Latency:          avg={lat['avg_ms']:.0f}ms  p50={lat['median_ms']:.0f}ms  "
              f"p95={lat['p95_ms']:.0f}ms  p99={lat['p99_ms']:.0f}ms")

    pf = report.get("prob_fault", {})
    if pf:
        print(f"  Prob(fault):      avg={pf['avg']:.4f}  median={pf['median']:.4f}  "
              f"min={pf['min']:.4f}  max={pf['max']:.4f}")

    conf = report.get("confidence", {})
    if conf:
        print(f"  Confidence:       avg={conf['avg']:.4f}  median={conf['median']:.4f}")

    sl = report.get("sequence_length", {})
    if sl:
        print(f"  Sequence length:  avg={sl['avg']:.0f}  median={sl['median']:.0f}  "
              f"min={sl['min']}  max={sl['max']}")

    ol = report.get("outliers", {})
    if ol:
        print(f"  Outliers:         z>3 avg={ol.get('z_gt3_avg', '?')}  "
              f"z>6 avg={ol.get('z_gt6_avg', '?')}")

    flags = report.get("gate_flags", {})
    if flags:
        print(f"\n  Top gate flags:")
        for flag, count in list(flags.items())[:10]:
            print(f"    {flag:40s}: {count}")

    modes = report.get("by_threshold_mode", {})
    if modes:
        print(f"\n  By threshold mode:")
        for mode, data in modes.items():
            print(f"    {mode:15s}: {data['count']} inferences  {dict(data['decisions'])}")

    pv1_modes = report.get("by_posture_v1_mode", {})
    if pv1_modes:
        print(f"\n  By PV1 mode:")
        for mode, data in pv1_modes.items():
            print(f"    {mode:15s}: {data['count']} inferences  {dict(data['decisions'])}")

    versions = report.get("model_versions", {})
    if versions:
        print(f"\n  Model versions:   {dict(versions)}")

    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="PostureV1 telemetry aggregation report")
    parser.add_argument("--database-url", default=None,
                        help="PostgreSQL connection string (or set DATABASE_URL env var)")
    parser.add_argument("--since", default=None,
                        help="Only include rows created after this date (YYYY-MM-DD)")
    parser.add_argument("--limit", type=int, default=None,
                        help="Max rows to fetch")
    args = parser.parse_args()

    database_url = args.database_url or os.environ.get("DATABASE_URL")
    if not database_url:
        print("ERROR: Provide --database-url or set DATABASE_URL environment variable", file=sys.stderr)
        sys.exit(1)

    print("Connecting to database...")
    conn = get_db_connection(database_url)

    print("Fetching telemetry rows...")
    rows = fetch_telemetry_rows(conn, since=args.since, limit=args.limit)
    conn.close()

    print(f"Fetched {len(rows)} rows\n")

    report = compute_report(rows)
    print_report(report)

    # Save JSON report
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = OUTPUT_DIR / "posture_v1_telemetry_report.json"

    # Serialize datetime objects
    def json_serial(obj):
        if hasattr(obj, "isoformat"):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")

    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=json_serial)

    print(f"\nJSON report saved to: {report_path}")


if __name__ == "__main__":
    main()
