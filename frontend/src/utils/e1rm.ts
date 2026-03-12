/**
 * e1RM (estimated 1-rep max) helpers — pure, side-effect-free math.
 *
 * Formula: Epley — weight * (1 + effectiveReps / 30)
 * RIR adjustment: effectiveReps = logged reps + (rir ?? 0), clamped 1–15.
 *
 * Bodyweight movements (weightLb ≤ 0) are excluded from all calculations.
 * Weighted bodyweight (e.g. pull-ups with an added belt load) are included,
 * but the e1RM reflects only the added load — not bodyweight + load — because
 * bodyweight is not stored in SetLog. Accept this limitation explicitly; do
 * not fabricate numbers.
 *
 * Session ordering: listSessions() in storage.ts sorts by startedAt descending
 * (newest first) and this is relied upon in currentExerciseE1RM. If that sort
 * guarantee ever changes, add an explicit sort here.
 */

import { listSessions, listSetLogsForSession } from "../features/training/storage";
import type { SetLog } from "../features/training/types";

/**
 * Effective reps to failure = logged reps + RIR.
 * Missing RIR is treated conservatively as 0 (no additional credit).
 * Clamped to 1–15 to avoid absurd Epley extrapolation at high rep counts.
 */
export function effectiveRepsToFailure(reps: number, rir?: number): number {
  return Math.min(Math.max(reps + (rir ?? 0), 1), 15);
}

/**
 * Epley estimated 1RM for a single set, with optional RIR adjustment.
 * e1RM = weight * (1 + effectiveReps / 30)
 * At 1 effective rep the formula collapses to the weight itself.
 */
export function setE1RM(weightLb: number, reps: number, rir?: number): number {
  const er = effectiveRepsToFailure(reps, rir);
  return er === 1 ? weightLb : Math.round(weightLb * (1 + er / 30));
}

// ---------------------------------------------------------------------------
// Noise-filtering: shared valid-set logic used by ALL analytics paths
// ---------------------------------------------------------------------------

/**
 * Returns the "clean" working sets for a single exercise within a session,
 * filtering out warmup-style noise that causes fake e1RM drops.
 *
 * Exclusion rules (applied in order):
 *   1. Must be setType="working", weightLb > 0, reps > 0
 *   2. reps ≤ 12  — high-rep conditioning sets are unreliable for e1RM comparison
 *   3. weightLb ≥ 60% of the heaviest working set for this exercise this session
 *      — removes obvious warmup/drop sets
 *
 * Fallback: if the 60% floor would exclude ALL candidates (impossible in practice,
 * but defensive), we keep the single heaviest candidate so the session isn't lost.
 */
export function getValidWorkingSets(sets: SetLog[], exerciseId: string): SetLog[] {
  const candidates = sets.filter(
    (s) =>
      s.exerciseId === exerciseId &&
      s.setType === "working" &&
      s.weightLb > 0 &&
      s.reps > 0 &&
      s.reps <= 12, // cap: high-rep sets produce noisy Epley extrapolations
  );
  if (!candidates.length) return [];

  const maxWeight = Math.max(...candidates.map((s) => s.weightLb));
  const WEIGHT_FLOOR = 0.60; // exclude sets < 60% of session max
  const filtered = candidates.filter((s) => s.weightLb >= maxWeight * WEIGHT_FLOOR);
  return filtered.length > 0
    ? filtered
    : [candidates.reduce((a, b) => (a.weightLb >= b.weightLb ? a : b))]; // safety fallback
}

export interface RepresentativePerformance {
  /** Best e1RM set within the valid working sets. */
  sessionTopSet: { weightLb: number; reps: number; rir?: number; e1RM: number } | null;
  /** Max setE1RM across valid working sets. null when none exist. */
  sessionE1RM: number | null;
  /** Average RIR across valid working sets; null when RIR was not logged on any set. */
  sessionAvgRIR: number | null;
  /** Average reps across valid working sets. */
  sessionAvgReps: number | null;
  /** Count of valid working sets after noise filtering. */
  sessionWorkingSetCount: number;
}

/**
 * Canonical function for per-session exercise analytics.
 * Uses getValidWorkingSets so all callers apply the same noise filter.
 */
export function getRepresentativeSessionPerformance(
  sets: SetLog[],
  exerciseId: string,
): RepresentativePerformance {
  const valid = getValidWorkingSets(sets, exerciseId);
  if (!valid.length) {
    return { sessionTopSet: null, sessionE1RM: null, sessionAvgRIR: null, sessionAvgReps: null, sessionWorkingSetCount: 0 };
  }

  const withE1RM = valid.map((s) => ({ ...s, e1RM: setE1RM(s.weightLb, s.reps, s.rir) }));
  const best = withE1RM.reduce((a, b) => (a.e1RM >= b.e1RM ? a : b));

  const rirVals = valid.filter((s) => s.rir != null).map((s) => s.rir as number);
  const sessionAvgRIR =
    rirVals.length > 0
      ? Math.round((rirVals.reduce((a, b) => a + b, 0) / rirVals.length) * 10) / 10
      : null;

  const sessionAvgReps = Math.round(
    (valid.reduce((s, v) => s + v.reps, 0) / valid.length) * 10,
  ) / 10;

  return {
    sessionTopSet: { weightLb: best.weightLb, reps: best.reps, rir: best.rir, e1RM: best.e1RM },
    sessionE1RM: best.e1RM,
    sessionAvgRIR,
    sessionAvgReps,
    sessionWorkingSetCount: valid.length,
  };
}

/**
 * Session-level e1RM for one exercise.
 * Now delegates to getValidWorkingSets so the same noise filter applies everywhere.
 */
export function sessionExerciseE1RM(sets: SetLog[], exerciseId: string): number | null {
  const valid = getValidWorkingSets(sets, exerciseId);
  if (!valid.length) return null;
  return Math.max(...valid.map((s) => setE1RM(s.weightLb, s.reps, s.rir)));
}

/**
 * Recency-weighted current e1RM for an exercise.
 *
 * Collects session-level e1RMs from the last 1–3 sessions that contain valid
 * working sets for this exercise, then applies recency weighting:
 *   1 session  → [1.0]
 *   2 sessions → [0.6, 0.4]
 *   3 sessions → [0.5, 0.3, 0.2]   (newest first)
 *
 * listSessions() is guaranteed to return sessions newest-first (sorted by
 * startedAt descending in storage.ts). No additional sort needed.
 *
 * Returns null if no sessions contain valid working sets for this exercise.
 */
export function currentExerciseE1RM(
  exerciseId: string,
  sessionLimit = 100,
): number | null {
  const sessions = listSessions(sessionLimit); // newest first — guaranteed
  const e1RMs: number[] = [];

  for (const sess of sessions) {
    if (e1RMs.length >= 3) break;
    const sets = listSetLogsForSession(sess.id);
    const val = sessionExerciseE1RM(sets, exerciseId);
    if (val !== null) e1RMs.push(val);
  }

  if (!e1RMs.length) return null;

  const WEIGHTS = [[1.0], [0.6, 0.4], [0.5, 0.3, 0.2]][e1RMs.length - 1];
  return Math.round(e1RMs.reduce((sum, v, i) => sum + v * WEIGHTS[i], 0));
}

// ---------------------------------------------------------------------------
// Coaching analytics helpers — deterministic, no side effects
// ---------------------------------------------------------------------------

export interface SessionHistoryEntry {
  sessionId: string;
  startedAt: string;
  /** Best e1RM across working sets this session for the exercise. */
  sessionE1RM: number;
  /** Average RIR across working sets; null when RIR was not logged. */
  avgRIR: number | null;
  workingSetCount: number;
  /** The set with the highest e1RM this session. */
  topSet: { weightLb: number; reps: number; rir?: number; e1RM: number } | null;
}

/**
 * Collects per-session representative performance for a single exercise.
 * Uses getRepresentativeSessionPerformance so the same noise filter applies.
 * Returns newest-first (matching listSessions() sort order).
 */
export function getExerciseSessionHistory(
  exerciseId: string,
  sessionLimit = 100,
): SessionHistoryEntry[] {
  const sessions = listSessions(sessionLimit);
  const result: SessionHistoryEntry[] = [];

  for (const sess of sessions) {
    const sets = listSetLogsForSession(sess.id);
    const perf = getRepresentativeSessionPerformance(sets, exerciseId);
    if (perf.sessionE1RM === null) continue; // no valid working sets this session

    result.push({
      sessionId: sess.id,
      startedAt: sess.startedAt,
      sessionE1RM: perf.sessionE1RM,
      avgRIR: perf.sessionAvgRIR,
      workingSetCount: perf.sessionWorkingSetCount,
      topSet: perf.sessionTopSet,
    });
  }

  return result; // newest-first
}

/** Count of sessions for this exercise within the last N days. */
export function getSessionsInLastDays(history: SessionHistoryEntry[], days: number): number {
  const cutoff = Date.now() - days * 24 * 60 * 60 * 1000;
  return history.filter((h) => new Date(h.startedAt).getTime() >= cutoff).length;
}

/**
 * Number of distinct ISO weeks (Mon-based) in the last `weeks` calendar weeks
 * in which this exercise appears.
 */
export function getDistinctTrainingWeeks(history: SessionHistoryEntry[], weeks = 4): number {
  const cutoff = Date.now() - weeks * 7 * 24 * 60 * 60 * 1000;
  const weekKeys = new Set<string>();
  for (const h of history) {
    if (new Date(h.startedAt).getTime() < cutoff) continue;
    const d = new Date(h.startedAt);
    const dayOfWeek = (d.getDay() + 6) % 7; // 0 = Mon
    const monday = new Date(d.getTime() - dayOfWeek * 86_400_000);
    weekKeys.add(monday.toISOString().slice(0, 10));
  }
  return weekKeys.size;
}

export function getConsistencyLabel(
  history: SessionHistoryEntry[],
): "Consistent" | "Building consistency" | "Inconsistent" {
  const weeks = getDistinctTrainingWeeks(history, 4);
  if (weeks >= 4) return "Consistent";
  if (weeks >= 2) return "Building consistency";
  return "Inconsistent";
}

/**
 * Compares avg RIR of the most recent 1–3 sessions to the prior 1–3.
 * "easier" = recent avg RIR is ≥ 0.5 higher than prior (same load feels lighter).
 * "harder" = recent avg RIR is ≥ 0.5 lower (same load feels heavier).
 */
export function getRecentVsPriorAvgRIR(history: SessionHistoryEntry[]): {
  recent: number | null;
  prior: number | null;
  trend: "easier" | "harder" | "flat" | "unknown";
} {
  const withRIR = history.filter((h) => h.avgRIR != null);
  if (withRIR.length < 1) return { recent: null, prior: null, trend: "unknown" };

  const recentSlice = withRIR.slice(0, Math.min(3, withRIR.length));
  const priorSlice = withRIR.slice(recentSlice.length, recentSlice.length + 3);

  const avgOf = (arr: SessionHistoryEntry[]) =>
    arr.reduce((s, h) => s + (h.avgRIR as number), 0) / arr.length;

  const recent = Math.round(avgOf(recentSlice) * 10) / 10;
  if (!priorSlice.length) return { recent, prior: null, trend: "unknown" };

  const prior = Math.round(avgOf(priorSlice) * 10) / 10;
  const diff = recent - prior;
  const trend: "easier" | "harder" | "flat" =
    diff >= 0.5 ? "easier" : diff <= -0.5 ? "harder" : "flat";

  return { recent, prior, trend };
}

const LOWER_BODY_PATTERNS = new Set([
  "squat", "hinge", "hip_extension", "knee_extension", "knee_flexion",
]);
const MAJOR_COMPOUND_PATTERNS = new Set([
  "squat", "hinge", "horizontal_push", "vertical_push", "horizontal_pull", "vertical_pull",
]);
const SECONDARY_PATTERNS = new Set(["hip_extension", "knee_extension", "knee_flexion"]);

/**
 * Session classification using both relative weight AND effort (RIR).
 *
 * - "light"     : top weight ≤ 75% of best AND RIR ≥ 2 (or no RIR data)
 *                 → intentional deload / technique work — excluded from trend averages
 * - "hard_drop" : top weight ≤ 75% of best AND RIR ≤ 1.5
 *                 → possible fatigue / bad day — NOT a deload, kept in trend averages
 * - "normal"    : top weight > 75% of best
 *                 → regular session, use existing analytics
 */
export type SessionClassification = "normal" | "light" | "hard_drop";

export function classifySession(
  topWeightLb: number,
  bestTopWeightLb: number,
  sessionAvgRIR: number | null,
  deloadRatio = 0.75,
): SessionClassification {
  if (bestTopWeightLb <= 0 || topWeightLb <= 0) return "normal";
  const weightRatio = topWeightLb / bestTopWeightLb;
  if (weightRatio > deloadRatio) return "normal";
  // Below threshold — RIR distinguishes intentional light work from a tough day
  if (sessionAvgRIR !== null && sessionAvgRIR <= 1.5) return "hard_drop";
  return "light"; // RIR ≥ 2, or no RIR data (benefit of the doubt → treat as intentional)
}

export interface CoachingRecommendation {
  action: "increase_load" | "add_reps" | "hold" | "pullback";
  label: "Increase load" | "Add reps first" | "Hold load steady" | "Slight pullback";
  reason: string;
  /** Concrete next-session target, e.g. "Next target: 225 lb for 5 reps @ RIR 2". Always set. */
  nextTargetText: string;
  suggestedIncreaseLb?: number;
  suggestedRangeText?: string;
  frequency14d: number;
  frequency28d: number;
  consistency: "Consistent" | "Building consistency" | "Inconsistent";
  avgRIRRecent: number | null;
  avgRIRPrior: number | null;
  rirTrend: "easier" | "harder" | "flat" | "unknown";
  confidence: "high" | "medium" | "low";
}

/**
 * Rule-based coaching recommendation for a single exercise.
 * Deterministic — no external state. Confidence decreases with sparse history.
 *
 * Decision priority (highest → lowest):
 *   1. Insufficient history → add reps (low confidence)
 *   2. Poor consistency/frequency → hold + build consistency message
 *   3. Sharply negative e1RM AND harder RIR → pullback
 *   4. Isolation lift → reps-first unless conditions are ideal
 *   5. No RIR data → conservative (add reps or hold)
 *   6. Low RIR (< 1.5) → hold
 *   7. Good conditions (freq + consistency + RIR ≥ 2.5) → increase load
 *   8. Medium RIR (1.5–2.4) → add reps
 *   9. Default → add reps
 */
export function getExerciseCoachingRecommendation(
  _exerciseId: string,
  movementPattern: string,
  history: SessionHistoryEntry[],
  e1RMPctChange: number | null,
): CoachingRecommendation {
  const freq14d = getSessionsInLastDays(history, 14);
  const freq28d = getSessionsInLastDays(history, 28);
  const consistency = getConsistencyLabel(history);
  const { recent: avgRIRRecent, prior: avgRIRPrior, trend: rirTrend } =
    getRecentVsPriorAvgRIR(history);

  const isMajorCompound = MAJOR_COMPOUND_PATTERNS.has(movementPattern);
  const isSecondary = SECONDARY_PATTERNS.has(movementPattern);
  const isLowerBody = LOWER_BODY_PATTERNS.has(movementPattern);
  const hasGoodFrequency = freq14d >= 2 || freq28d >= 3;
  const hasGoodConsistency = consistency === "Consistent";
  const hasFairConsistency = consistency === "Building consistency";
  const hasRIRData = avgRIRRecent !== null;

  const confidence: "high" | "medium" | "low" =
    history.length >= 4 && hasRIRData ? "high" : history.length >= 2 ? "medium" : "low";

  const base = { frequency14d: freq14d, frequency28d: freq28d, consistency, avgRIRRecent, avgRIRPrior, rirTrend, confidence };

  const recentTopSet = history[0]?.topSet ?? null;
  const roundTo2_5 = (w: number) => Math.round(w / 2.5) * 2.5;

  function buildTarget(
    action: "increase_load" | "add_reps" | "hold" | "pullback",
    sub?: "low_rir" | "inconsistent" | "baseline" | "no_rir",
  ): string {
    if (!recentTopSet) {
      if (action === "increase_load") return `Add ${isLowerBody ? "5–10" : "2.5–5"} lb when you next log this lift`;
      if (action === "pullback") return `Reduce load by ${isLowerBody ? "5–10" : "2.5–5"} lb next session`;
      if (action === "add_reps") return "Push for 1–2 more reps on your top set next session";
      return "Hold current weight and focus on rep quality";
    }
    const { weightLb, reps } = recentTopSet;
    if (action === "increase_load") {
      const target = roundTo2_5(weightLb + (isLowerBody ? 10 : 5));
      return `Next target: ${target} lb for ${reps} reps @ RIR 2`;
    }
    if (action === "add_reps") {
      return `Next target: ${weightLb} lb for ${reps + 1}–${reps + 2} reps`;
    }
    if (action === "pullback") {
      const target = roundTo2_5(weightLb - (isLowerBody ? 10 : 5));
      return `Next target: pull back to ${target} lb, rebuild quality reps`;
    }
    // hold sub-cases
    if (sub === "low_rir") return `Hold at ${weightLb} lb — effort is high, lock in form first`;
    if (sub === "inconsistent") return `Hold at ${weightLb} lb — build training consistency first`;
    if (sub === "no_rir") return `Hold at ${weightLb} lb — log RIR to unlock load guidance`;
    return `Hold at ${weightLb} lb for ${reps} reps, focus on execution quality`;
  }

  // 1. Insufficient history
  if (history.length < 2) {
    return {
      ...base,
      action: "add_reps",
      label: "Add reps first",
      reason: "Build a few more sessions before adjusting load.",
      nextTargetText: buildTarget("add_reps"),
      confidence: "low",
    };
  }

  // 2. Poor consistency override
  if (consistency === "Inconsistent" && !hasGoodFrequency) {
    return {
      ...base,
      action: "hold",
      label: "Hold load steady",
      reason: "Build consistency first — log this lift regularly before adding load.",
      nextTargetText: buildTarget("hold", "inconsistent"),
    };
  }

  // 3. Pullback: strength dropping while effort is rising
  if (e1RMPctChange !== null && e1RMPctChange <= -5 && rirTrend === "harder") {
    const dropLb = isLowerBody ? 10 : 5;
    return {
      ...base,
      action: "pullback",
      label: "Slight pullback",
      reason: "Strength dropping while effort is increasing — a small load reduction can help reset.",
      nextTargetText: buildTarget("pullback"),
      suggestedIncreaseLb: -dropLb,
      suggestedRangeText: isLowerBody ? "-5 to -10 lb" : "-2.5 to -5 lb",
    };
  }

  // 4. Isolation lifts: reps-first by default
  if (!isMajorCompound && !isSecondary) {
    if (hasGoodConsistency && hasRIRData && (avgRIRRecent ?? 0) >= 2 && (e1RMPctChange ?? 0) >= 0) {
      return {
        ...base,
        action: "increase_load",
        label: "Increase load",
        reason: "Consistent effort with room to add load — small jump is appropriate.",
        nextTargetText: buildTarget("increase_load"),
        suggestedIncreaseLb: 2.5,
        suggestedRangeText: "+2.5 lb",
      };
    }
    return {
      ...base,
      action: "add_reps",
      label: "Add reps first",
      reason: "Accessory lifts respond well to rep progression before adding load.",
      nextTargetText: buildTarget("add_reps"),
    };
  }

  // 5. No RIR data — conservative
  if (!hasRIRData) {
    if ((hasGoodFrequency || hasFairConsistency) && (e1RMPctChange ?? 0) >= 0) {
      return {
        ...base,
        action: "add_reps",
        label: "Add reps first",
        reason: "Log RIR on working sets to unlock load recommendations.",
        nextTargetText: buildTarget("add_reps"),
      };
    }
    return {
      ...base,
      action: "hold",
      label: "Hold load steady",
      reason: "Log RIR on working sets to unlock progression guidance.",
      nextTargetText: buildTarget("hold", "no_rir"),
    };
  }

  // 6. Low RIR: already at near-maximal effort
  if ((avgRIRRecent ?? 0) < 1.5) {
    return {
      ...base,
      action: "hold",
      label: "Hold load steady",
      reason: "Effort is high — lock in form and consistency before adding weight.",
      nextTargetText: buildTarget("hold", "low_rir"),
    };
  }

  // 7. Good conditions: increase load
  const rirGood = (avgRIRRecent ?? 0) >= 2.5;
  if (rirGood && (hasGoodFrequency || hasGoodConsistency) && (e1RMPctChange ?? 0) >= 0) {
    const incLb = isLowerBody ? 10 : 5;
    return {
      ...base,
      action: "increase_load",
      label: "Increase load",
      reason: hasGoodConsistency && hasGoodFrequency
        ? "Good frequency, consistency, and manageable effort — ready for a small load increase."
        : "Manageable effort with adequate frequency — a small load jump is appropriate.",
      nextTargetText: buildTarget("increase_load"),
      suggestedIncreaseLb: incLb,
      suggestedRangeText: isLowerBody ? "+5 to +10 lb" : "+2.5 to +5 lb",
    };
  }

  // 8. Medium RIR: add reps first
  return {
    ...base,
    action: "add_reps",
    label: "Add reps first",
    reason: (avgRIRRecent ?? 0) < 2.5
      ? "Effort is moderate — push reps higher before adding load."
      : "Build consistency further before the next load jump.",
    nextTargetText: buildTarget("add_reps"),
  };
}
