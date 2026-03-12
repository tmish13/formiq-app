/**
 * Progress story generation — pure, deterministic, zero side effects.
 *
 * Computes per-exercise estimated-1RM progression across all localStorage
 * sessions and generates a brief AI coaching insight about training balance.
 *
 * Progression is based on session-level e1RM (Epley + RIR), not raw top
 * weight, so increasing reps or logging RIR correctly shows as improvement
 * even when the bar weight stays the same.
 */

import { listSessions, listSetLogsForSession } from "../features/training/storage";
import { EXERCISES } from "../features/training/catalog";
import {
  setE1RM,
  getExerciseSessionHistory,
  getRecentVsPriorAvgRIR,
  getConsistencyLabel,
  getSessionsInLastDays,
  getExerciseCoachingRecommendation,
  getRepresentativeSessionPerformance,
  classifySession,
} from "./e1rm";
import type { CoachingRecommendation } from "./e1rm";

export interface ExerciseProgress {
  exerciseId: string;
  exerciseName: string;
  /** Estimated 1RM (lb) from the earliest session for this exercise. */
  firstE1RMLb: number;
  /** Estimated 1RM (lb) from the most recent session for this exercise. */
  lastE1RMLb: number;
  /**
   * Positive = improved e1RM (lb), negative = regressed.
   * Based on e1RM delta, not raw weight delta.
   */
  deltLb: number;
  sessionCount: number;
  pattern: string;
}

export interface ProgressStory {
  exercises: ExerciseProgress[];
  aiInsight: string;
  totalSessions: number;
  isEmpty: boolean;
}

// ---------------------------------------------------------------------------
// Strength Trend (recency-based, replaces naive first-vs-last comparison)
// ---------------------------------------------------------------------------

export type TrendCategory =
  | "strong_progress"
  | "improving"
  | "stable"
  | "slight_decline"
  | "needs_attention"
  | "insufficient_data";

export interface ExerciseTrend {
  exerciseId: string;
  exerciseName: string;
  pattern: string;
  /** Recency-weighted average e1RM from the most recent 1–3 sessions. */
  recentE1RM: number;
  /**
   * Average e1RM from the prior 1–3 sessions before the recent block.
   * null when there are fewer than 4 total sessions for this exercise
   * (in that case a simpler first-vs-last comparison is used instead).
   */
  baselineE1RM: number | null;
  /**
   * Percentage change from baseline to recent.
   * null only when sessionCount < 2.
   */
  pctChange: number | null;
  trend: TrendCategory;
  sessionCount: number;
  // Coaching analytics (populated by generateStrengthTrend)
  avgRIRRecent: number | null;
  avgRIRPrior: number | null;
  rirTrend: "easier" | "harder" | "flat" | "unknown";
  frequency14d: number;
  frequency28d: number;
  consistency: "Consistent" | "Building consistency" | "Inconsistent";
  coaching: CoachingRecommendation;
  confidence: "high" | "medium" | "low";
}

export interface StrengthTrend {
  exercises: ExerciseTrend[];
  /** One-sentence coaching narrative. Empty string when isEmpty. */
  narrative: string;
  /** True when there is not enough data to show any trend at all. */
  isEmpty: boolean;
}

function classifyTrend(
  pctChange: number,
  rirTrend: "easier" | "harder" | "flat" | "unknown" = "unknown",
): TrendCategory {
  // Base bucket from % e1RM change
  let base: TrendCategory;
  if (pctChange >= 5)  base = "strong_progress";
  else if (pctChange >= 2)  base = "improving";
  else if (pctChange > -2)  base = "stable";
  else if (pctChange >= -5) base = "slight_decline";
  else base = "needs_attention";

  // RIR context: adapt to same load = positive signal; struggle at same load = negative
  if (rirTrend === "easier") {
    if (base === "stable")        return "improving";
    if (base === "slight_decline") return "stable";
  }
  if (rirTrend === "harder") {
    if (base === "stable")        return "slight_decline";
    if (base === "slight_decline") return "needs_attention";
  }

  return base;
}

function buildNarrative(exercises: ExerciseTrend[]): string {
  const lower = exercises.filter((e) => ["squat", "hinge"].includes(e.pattern));
  const push  = exercises.filter((e) => ["horizontal_push", "vertical_push"].includes(e.pattern));
  const pull  = exercises.filter((e) => ["horizontal_pull", "vertical_pull"].includes(e.pattern));

  const improving = exercises.filter((e) => (e.pctChange ?? 0) >= 2);
  const declining = exercises.filter((e) => (e.pctChange ?? 0) <= -2);

  const best = exercises[0]; // sorted by pctChange desc

  if (best.trend === "strong_progress" || best.trend === "improving") {
    if (lower.some((e) => e.trend === "strong_progress" || e.trend === "improving")) {
      return "Lower body strength is trending up. Keep squat and hinge frequency high.";
    }
    if (push.length && pull.length) {
      const avgPush = push.reduce((s, e) => s + (e.pctChange ?? 0), 0) / push.length;
      const avgPull = pull.reduce((s, e) => s + (e.pctChange ?? 0), 0) / pull.length;
      if (avgPush > avgPull + 3) {
        return "Pushing strength is leading. Add more row and pull work to keep push/pull balanced.";
      }
      if (avgPull > avgPush + 3) {
        return "Pulling strength is improving fastest. Add push volume to maintain balance.";
      }
    }
    return `${best.exerciseName} is progressing well. Keep current training frequency and load.`;
  }

  if (declining.length > improving.length) {
    return "Strength is fluctuating. Train consistently and log RIR accurately for better trend data.";
  }

  return "Strength is holding steady. Push for small, consistent load increases each session.";
}

/**
 * Generates a recency-based strength trend per exercise.
 *
 * For each exercise with ≥2 logged sessions:
 *   - RECENT  = avg e1RM of the last 3 sessions
 *   - BASELINE = avg e1RM of the 3 sessions before that (when ≥4 sessions exist)
 *   - pctChange = (recent − baseline) / baseline × 100
 *
 * With 2–3 sessions: compares last vs first session (no block average).
 * With 1 session: omitted (no trend possible).
 */
export function generateStrengthTrend(): StrengthTrend {
  const sessions = listSessions(50);

  if (sessions.length === 0) {
    return { exercises: [], narrative: "", isEmpty: true };
  }

  // Build per-exercise session e1RM history.
  // listSessions() returns newest-first; we push in that order, then sort chronologically below.
  // topWeightLb and avgRIR are stored alongside e1RM so classifySession() can filter smarter.
  const history: Record<string, Array<{
    date: string;
    e1RM: number;
    topWeightLb: number;
    avgRIR: number | null;
  }>> = {};

  for (const sess of sessions) {
    const sets = listSetLogsForSession(sess.id);
    const candidateExIds = Array.from(new Set(
      sets
        .filter((s) => s.setType === "working" && s.weightLb > 0 && s.reps > 0)
        .map((s) => s.exerciseId),
    ));

    for (const exId of candidateExIds) {
      const perf = getRepresentativeSessionPerformance(sets, exId);
      if (perf.sessionE1RM === null) continue;
      if (!history[exId]) history[exId] = [];
      history[exId].push({
        date: sess.startedAt,
        e1RM: perf.sessionE1RM,
        topWeightLb: perf.sessionTopSet?.weightLb ?? 0,
        avgRIR: perf.sessionAvgRIR,
      });
    }
  }

  const exercises: ExerciseTrend[] = [];

  for (const [exId, records] of Object.entries(history)) {
    if (records.length < 2) continue; // need ≥2 sessions for any trend

    // Sort chronologically: oldest first
    const sorted = [...records].sort((a, b) => a.date.localeCompare(b.date));

    // Exclude LIGHT sessions from trend blocks (intentional deloads / technique work).
    // HARD_DROP sessions (heavy effort but lighter weight) are real data — kept in.
    // Uses per-session top weight + RIR, so the classification is smarter than a raw e1RM ratio.
    const peakTopWeight = Math.max(...sorted.map((r) => r.topWeightLb));
    const trendRecords = (() => {
      const filtered = sorted.filter(
        (r) => classifySession(r.topWeightLb, peakTopWeight, r.avgRIR) !== "light",
      );
      return filtered.length >= 2 ? filtered : sorted; // fallback if all sessions are light
    })();
    const n = trendRecords.length;
    if (n < 2) continue;

    const ex = EXERCISES.find((e) => e.id === exId);

    let recentE1RM: number;
    let baselineE1RM: number | null;
    let pctChange: number;

    if (n >= 4) {
      // Recent block = last 3; baseline = the 3 sessions immediately before recent block
      const recentVals  = trendRecords.slice(-3).map((r) => r.e1RM);
      const baselineVals = trendRecords.slice(Math.max(0, n - 6), n - 3).map((r) => r.e1RM);
      const avg = (arr: number[]) => arr.reduce((a, b) => a + b, 0) / arr.length;
      recentE1RM   = Math.round(avg(recentVals));
      baselineE1RM = Math.round(avg(baselineVals));
      pctChange    = Math.round(((recentE1RM - baselineE1RM) / baselineE1RM) * 1000) / 10;
    } else {
      // 2–3 sessions: latest vs earliest (no full block averages)
      recentE1RM   = Math.round(trendRecords[n - 1].e1RM);
      baselineE1RM = Math.round(trendRecords[0].e1RM);
      pctChange    = Math.round(((recentE1RM - baselineE1RM) / baselineE1RM) * 1000) / 10;
    }

    // Coaching analytics — per-exercise session history from localStorage
    const exHistory = getExerciseSessionHistory(exId);
    const rirData = getRecentVsPriorAvgRIR(exHistory);
    const consistency = getConsistencyLabel(exHistory);
    const freq14d = getSessionsInLastDays(exHistory, 14);
    const freq28d = getSessionsInLastDays(exHistory, 28);
    const coaching = getExerciseCoachingRecommendation(
      exId,
      ex?.movementPattern ?? "",
      exHistory,
      pctChange,
    );

    exercises.push({
      exerciseId: exId,
      exerciseName: ex?.name ?? exId,
      pattern: ex?.movementPattern ?? "",
      recentE1RM,
      baselineE1RM,
      pctChange,
      trend: classifyTrend(pctChange, rirData.trend),
      sessionCount: sorted.length, // total sessions including deloads
      avgRIRRecent: rirData.recent,
      avgRIRPrior: rirData.prior,
      rirTrend: rirData.trend,
      frequency14d: freq14d,
      frequency28d: freq28d,
      consistency,
      coaching,
      confidence: coaching.confidence,
    });
  }

  if (!exercises.length) {
    const msg = sessions.length === 1
      ? "Log a few more workouts to unlock strength trend insights."
      : "Log each lift at least twice to unlock strength trend comparisons.";
    return { exercises: [], narrative: msg, isEmpty: false };
  }

  // Sort: strongest positive change first
  exercises.sort((a, b) => (b.pctChange ?? 0) - (a.pctChange ?? 0));

  // Early-user narrative: when most exercises still have < 3 sessions,
  // the block-comparison trends are too shallow to coach from — say so.
  const lowDataCount = exercises.filter((e) => e.sessionCount < 3).length;
  const narrative =
    lowDataCount > exercises.length / 2
      ? "You're still building your training baseline. Log a few more workouts to unlock deeper trend insights."
      : buildNarrative(exercises);

  return {
    exercises: exercises.slice(0, 4),
    narrative,
    isEmpty: false,
  };
}

// ---------------------------------------------------------------------------
// Legacy progress story (kept for backward compat; UI uses generateStrengthTrend)
// ---------------------------------------------------------------------------

export function generateProgressStory(): ProgressStory {
  const sessions = listSessions(50);
  if (sessions.length === 0) {
    return { exercises: [], aiInsight: "", totalSessions: 0, isEmpty: true };
  }

  const history: Record<string, Array<{ date: string; e1RMLb: number }>> = {};

  for (const sess of sessions) {
    const sets = listSetLogsForSession(sess.id);
    const candidateExIds = Array.from(new Set(
      sets
        .filter((s) => s.setType === "working" && s.weightLb > 0 && s.reps > 0)
        .map((s) => s.exerciseId),
    ));

    for (const exId of candidateExIds) {
      const perf = getRepresentativeSessionPerformance(sets, exId);
      if (perf.sessionE1RM === null) continue;
      if (!history[exId]) history[exId] = [];
      history[exId].push({ date: sess.startedAt, e1RMLb: perf.sessionE1RM });
    }
  }

  const progress: ExerciseProgress[] = [];

  for (const [exId, records] of Object.entries(history)) {
    if (records.length < 2) continue;
    const sorted = [...records].sort((a, b) => a.date.localeCompare(b.date));
    const first = sorted[0].e1RMLb;
    const last  = sorted[sorted.length - 1].e1RMLb;
    const ex    = EXERCISES.find((e) => e.id === exId);
    progress.push({
      exerciseId: exId,
      exerciseName: ex?.name ?? exId,
      firstE1RMLb: first,
      lastE1RMLb: last,
      deltLb: last - first,
      sessionCount: records.length,
      pattern: ex?.movementPattern ?? "",
    });
  }

  if (!progress.length) {
    const movementsSeen = new Set<string>();
    for (const sess of sessions) {
      const working = listSetLogsForSession(sess.id).filter(
        (s) => s.setType === "working" && s.weightLb > 0 && s.reps > 0,
      );
      for (const s of working) {
        const ex = EXERCISES.find((e) => e.id === s.exerciseId);
        if (ex?.movementPattern) movementsSeen.add(ex.movementPattern);
      }
    }
    const PATTERN_LABELS: Record<string, string> = {
      squat: "lower body", hinge: "hip hinge", horizontal_push: "pressing",
      vertical_push: "overhead pressing", horizontal_pull: "rowing", vertical_pull: "pulling",
    };
    const patternNames = Array.from(movementsSeen).map((p) => PATTERN_LABELS[p] ?? p).slice(0, 3);
    let insight: string;
    if (sessions.length === 1) {
      insight = "Great start — first workout logged. Keep at it to unlock lift-by-lift strength trends.";
    } else if (patternNames.length > 0) {
      insight = `${sessions.length} workouts logged covering ${patternNames.join(", ")}. Log each lift a few more times to unlock strength trend insights.`;
    } else {
      insight = `${sessions.length} workouts logged. Keep training consistently to unlock lift-by-lift strength trend insights.`;
    }
    return { exercises: [], aiInsight: insight, totalSessions: sessions.length, isEmpty: false };
  }

  progress.sort((a, b) => b.deltLb - a.deltLb);

  const avgDelta = (arr: ExerciseProgress[]) =>
    arr.length ? arr.reduce((s, e) => s + e.deltLb, 0) / arr.length : 0;
  const push  = progress.filter((e) => ["horizontal_push", "vertical_push"].includes(e.pattern));
  const pull  = progress.filter((e) => ["horizontal_pull", "vertical_pull"].includes(e.pattern));
  const lower = progress.filter((e) => ["squat", "hinge"].includes(e.pattern));
  const avgPush  = avgDelta(push);
  const avgPull  = avgDelta(pull);
  const avgLower = avgDelta(lower);

  const best = progress[0];
  let aiInsight = best.deltLb > 0 ? `${best.exerciseName} shows the strongest progression (+${best.deltLb} lb e1RM). ` : "";
  if (pull.length && push.length) {
    if (avgPull > avgPush + 5)     aiInsight += "Pulling strength is improving faster — add push volume to balance.";
    else if (avgPush > avgPull + 5) aiInsight += "Pushing strength is improving faster — add more row and pull work to balance.";
    else                            aiInsight += "Push and pull are progressing evenly — good balance.";
  } else if (lower.length > 0 && avgLower > 0) {
    aiInsight += "Consistent lower body progress. Keep compound lift frequency up.";
  } else if (progress.every((e) => e.deltLb >= 0)) {
    aiInsight += "Consistent progress across all tracked movements.";
  } else {
    aiInsight += "Log RIR consistently to get better next-session load recommendations.";
  }

  return { exercises: progress.slice(0, 4), aiInsight, totalSessions: sessions.length, isEmpty: false };
}
