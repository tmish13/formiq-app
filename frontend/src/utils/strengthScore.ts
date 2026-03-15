/**
 * Strength score — population percentile estimation.
 *
 * Computes a recency-weighted estimated 1RM (e1RM) per exercise using the
 * Epley formula with RIR adjustment (see e1rm.ts), then maps it to a
 * population percentile via bodyweight-relative strength standards.
 *
 * Score (0–100) = approximate % of adult recreational lifters you are
 * stronger than for a given movement pattern.
 *
 * e1RM source: working sets from the last 1–3 sessions per exercise,
 * weighted [0.5, 0.3, 0.2] (newest first). See e1rm.ts for details.
 *
 * Overall score: compound-weighted average across exercises — major
 * compounds (squat, hinge, push, pull) count 1.0×; isolations count 0.4×.
 * Compound weighting is internal and not surfaced in the UI.
 */

import { listSessions, listSetLogsForSession } from "../features/training/storage";
import { EXERCISES } from "../features/training/catalog";
import { sessionExerciseE1RM } from "./e1rm";
import type { SetLog } from "../features/training/types";

/** Preloaded session shape — matches loadedSessions in ProgressPage. */
export interface PreloadedSession {
  id: string;
  startedAt: string;
  sets: SetLog[];
}

/**
 * Bodyweight-ratio → population percentile anchors.
 * Each tuple: [bodyweight_ratio, population_percentile]
 * Based on recreational gym population strength distributions.
 */
const PERCENTILE_ANCHORS: Record<string, [number, number][]> = {
  squat: [
    [0.20, 3],  [0.40, 10], [0.65, 22], [0.85, 35], [1.00, 50],
    [1.25, 65], [1.50, 78], [1.75, 88], [2.00, 94], [2.50, 99],
  ],
  hinge: [
    [0.30, 3],  [0.55, 10], [0.80, 22], [1.00, 35], [1.25, 50],
    [1.50, 65], [1.75, 78], [2.00, 88], [2.25, 94], [2.75, 99],
  ],
  horizontal_push: [
    [0.15, 3],  [0.30, 10], [0.45, 22], [0.60, 35], [0.75, 50],
    [0.90, 65], [1.05, 78], [1.20, 88], [1.40, 94], [1.75, 99],
  ],
  vertical_push: [
    [0.10, 3],  [0.20, 10], [0.30, 22], [0.40, 35], [0.55, 50],
    [0.65, 65], [0.75, 78], [0.90, 88], [1.00, 94], [1.25, 99],
  ],
  horizontal_pull: [
    [0.15, 3],  [0.30, 10], [0.45, 22], [0.60, 35], [0.75, 50],
    [0.90, 65], [1.05, 78], [1.20, 88], [1.40, 94], [1.75, 99],
  ],
  vertical_pull: [
    [0.15, 3],  [0.30, 10], [0.45, 22], [0.60, 35], [0.75, 50],
    [0.90, 65], [1.05, 78], [1.20, 88], [1.40, 94], [1.75, 99],
  ],
};

const DEFAULT_ANCHORS: [number, number][] = [
  [0.15, 3],  [0.30, 10], [0.50, 22], [0.65, 35], [0.80, 50],
  [1.00, 65], [1.20, 78], [1.40, 88], [1.60, 94], [2.00, 99],
];

/**
 * Age correction multiplier applied to the effective bodyweight ratio.
 * Older lifters get slight credit — achieving the same absolute lift
 * at 50 is harder than at 25.
 */
function ageCorrection(age?: number): number {
  if (!age || age < 30) return 1.0;
  if (age < 40) return 1.0;
  if (age < 50) return 1.08;
  if (age < 60) return 1.16;
  return 1.24;
}

/** Piecewise linear interpolation through (ratio, percentile) anchors. */
function interpolatePercentile(ratio: number, anchors: [number, number][]): number {
  if (ratio <= anchors[0][0]) return anchors[0][1];
  if (ratio >= anchors[anchors.length - 1][0]) return anchors[anchors.length - 1][1];
  for (let i = 1; i < anchors.length; i++) {
    const [r0, p0] = anchors[i - 1];
    const [r1, p1] = anchors[i];
    if (ratio <= r1) {
      const t = (ratio - r0) / (r1 - r0);
      return Math.round(p0 + t * (p1 - p0));
    }
  }
  return anchors[anchors.length - 1][1];
}

/**
 * Internal compound weighting multiplier for the overall score.
 * Major compounds: 1.0  |  Secondary compounds: 0.75  |  Isolations: 0.4
 * Not surfaced in the UI.
 */
const COMPOUND_WEIGHT: Record<string, number> = {
  // Major compounds
  squat: 1.0,
  hinge: 1.0,
  horizontal_push: 1.0,
  vertical_push: 1.0,
  horizontal_pull: 1.0,
  vertical_pull: 1.0,
  // Secondary compounds
  hip_extension: 0.75,
  knee_extension: 0.75,
  knee_flexion: 0.75,
  // All other patterns (isolations, etc.) fall through to 0.4 via default
};

export function patternWeight(pattern: string): number {
  return COMPOUND_WEIGHT[pattern] ?? 0.4;
}

// Recency weights indexed by (number of sessions - 1), newest first
const RECENCY_WEIGHTS = [[1.0], [0.6, 0.4], [0.5, 0.3, 0.2]] as const;

export interface ExerciseBest {
  exerciseId: string;
  exerciseName: string;
  /** Recency-weighted estimated 1RM in lb (Epley formula + RIR). */
  e1RM: number;
  /** Population percentile 0–100. null if no bodyweight provided or machine-based. */
  score: number | null;
  pattern: string;
  /** True for Smith machine exercises — excluded from overall percentile ranking. */
  isMachineBased: boolean;
}

export interface StrengthScore {
  /**
   * Compound-weighted average percentile across all exercises.
   * null if no bodyweight provided or only machine-based exercises logged.
   */
  overall: number | null;
  exercises: ExerciseBest[];
  isEmpty: boolean;
  hasBodyweight: boolean;
  /** False when only machine-based (Smith machine) exercises are logged — no percentile ranking available. */
  hasRankableExercises: boolean;
}

export function calculateStrengthScore(
  bodyWeightKg?: number,
  age?: number,
  preloadedData?: PreloadedSession[],
): StrengthScore {
  // Prefer preloaded backend data; fall back to localStorage when not provided.
  // listSessions returns newest-first — guaranteed by storage.ts
  const sessions: Array<{ id: string; sets: SetLog[] }> = preloadedData
    ?? listSessions(100).map((s) => ({ id: s.id, sets: listSetLogsForSession(s.id) }));
  if (!sessions.length) {
    return { overall: null, exercises: [], isEmpty: true, hasBodyweight: !!bodyWeightKg, hasRankableExercises: false };
  }

  // Single pass: collect up to 3 session-level e1RMs per exercise (newest first).
  // Once an exercise has 3 sessions, older sessions are skipped for it.
  const e1RMHistory: Record<string, number[]> = {};

  for (const sess of sessions) {
    const sets = sess.sets;
    const exIds = Array.from(new Set(
      sets
        .filter((s) => s.setType === "working" && s.weightLb > 0 && s.reps > 0)
        .map((s) => s.exerciseId),
    ));

    for (const exId of exIds) {
      if ((e1RMHistory[exId]?.length ?? 0) >= 3) continue;
      const sessE1RM = sessionExerciseE1RM(sets, exId);
      if (sessE1RM === null) continue;
      if (!e1RMHistory[exId]) e1RMHistory[exId] = [];
      e1RMHistory[exId].push(sessE1RM);
    }
  }

  const entries = Object.entries(e1RMHistory);
  if (!entries.length) {
    return { overall: null, exercises: [], isEmpty: true, hasBodyweight: !!bodyWeightKg, hasRankableExercises: false };
  }

  const bwLb = bodyWeightKg ? bodyWeightKg * 2.20462 : null;
  const ageFactor = ageCorrection(age);

  const exercises: ExerciseBest[] = entries.map(([exId, sessionE1RMs]) => {
    // sessionE1RMs[0] is most recent — apply recency weights
    const weights = RECENCY_WEIGHTS[Math.min(sessionE1RMs.length, 3) - 1];
    const currentE1RM = Math.round(
      sessionE1RMs.reduce((sum, v, i) => sum + v * (weights as readonly number[])[i], 0),
    );

    const ex = EXERCISES.find((e) => e.id === exId);
    const pattern = ex?.movementPattern ?? "";

    // Exclude exercises where comparison against population strength standards is invalid:
    //   1. Machine-only load types: all allowedEquipment are pure machine (no barbell/dumbbell/cable).
    //      cable_stack is NOT excluded — compound cable movements (e.g. cable row) are comparable.
    //   2. Isolation movement patterns that have no meaningful population strength standard.
    const PURE_MACHINE_EQUIPMENT = new Set(["machine_selectorized", "machine_plate_loaded", "smith"]);
    const ISOLATION_PATTERNS = new Set(["knee_extension", "knee_flexion"]);
    const isMachineBased =
      ISOLATION_PATTERNS.has(pattern) ||
      (ex?.allowedEquipment != null &&
        ex.allowedEquipment.length > 0 &&
        ex.allowedEquipment.every((eq) => PURE_MACHINE_EQUIPMENT.has(eq)));

    let score: number | null = null;
    if (bwLb && !isMachineBased) {
      const ratio = (currentE1RM / bwLb) * ageFactor;
      const anchors = PERCENTILE_ANCHORS[pattern] ?? DEFAULT_ANCHORS;
      score = interpolatePercentile(ratio, anchors);
    }

    return {
      exerciseId: exId,
      exerciseName: ex?.name ?? exId,
      e1RM: currentE1RM,
      score,
      pattern,
      isMachineBased,
    };
  });

  exercises.sort((a, b) => b.e1RM - a.e1RM);

  // Compound-weighted average — only non-machine exercises with a non-null score contribute.
  const scored = exercises.filter((e) => e.score !== null);
  const wSum = scored.reduce((s, e) => s + (e.score as number) * patternWeight(e.pattern), 0);
  const wDenom = scored.reduce((s, e) => s + patternWeight(e.pattern), 0);
  const overall = wDenom > 0 ? Math.round(wSum / wDenom) : null;
  const hasRankableExercises = scored.length > 0;

  return {
    overall,
    exercises, // all exercises — UI controls display limit with expand/collapse
    isEmpty: false,
    hasBodyweight: !!bwLb,
    hasRankableExercises,
  };
}
