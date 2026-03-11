/**
 * Training recommendation utilities — pure, deterministic, zero side effects.
 *
 * Augments nextSessionTargets.ts with human-readable coaching explanations
 * based on last RIR, weight, reps, and goal context.
 */

import type { Goal } from "../features/training/types";

export interface SessionRecommendation {
  nextWeightLb: number;
  targetRepsRange: { min: number; max: number };
  targetRir: number;
  rationale: string;
  /** Single-sentence coaching explanation shown to the user. */
  explanation: string;
}

const REP_RANGES: Record<Goal, { min: number; max: number }> = {
  strength:    { min: 3, max: 6 },
  hypertrophy: { min: 6, max: 10 },
  general:     { min: 8, max: 12 },
};

/**
 * Compute next-session weight + explanation from the last best working set.
 *
 * Rules (based on last RIR):
 *   RIR ≤ 0  → reduce by ~5% (recovery)
 *   RIR === 1 → hold weight, +1 rep suggestion
 *   RIR >= 3  → increase by incrementLb
 *   RIR === 2 → hold weight (ideal zone)
 *   undefined → hold, prompt to log RIR
 */
export function getNextSessionRecommendation({
  lastWeightLb,
  lastReps,
  lastRir,
  incrementLb,
  goal,
}: {
  lastWeightLb: number;
  lastReps: number;
  lastRir: number | undefined;
  incrementLb: number;
  goal: Goal;
}): SessionRecommendation {
  const targetRepsRange = REP_RANGES[goal];
  const targetRir = 2;

  if (lastRir === undefined) {
    return {
      nextWeightLb: lastWeightLb,
      targetRepsRange,
      targetRir,
      rationale: "no RIR logged — holding weight",
      explanation:
        "Log your RIR after each set so FormIQ can calculate your next session load automatically.",
    };
  }

  if (lastRir <= 0) {
    const nextWeight = Math.max(0, Math.round((lastWeightLb * 0.95) / 2.5) * 2.5);
    return {
      nextWeightLb: nextWeight,
      targetRepsRange,
      targetRir,
      rationale: "RIR 0 — reduce to recover",
      explanation:
        `You reached near failure last session. A small reduction to ${nextWeight} lb helps maintain quality reps while recovering volume.`,
    };
  }

  if (lastRir === 1) {
    return {
      nextWeightLb: lastWeightLb,
      targetRepsRange,
      targetRir,
      rationale: "RIR 1 — hold weight, add reps",
      explanation:
        `Good effort last session. Hold at ${lastWeightLb} lb and aim for ${lastReps + 1} reps — then increase load next time.`,
    };
  }

  if (lastRir === 2) {
    return {
      nextWeightLb: lastWeightLb,
      targetRepsRange,
      targetRir,
      rationale: "RIR 2 — ideal effort zone, hold or micro-progress",
      explanation:
        `Your last set hit the ideal effort zone at ${lastWeightLb} lb. Maintain load and try to match or beat your reps.`,
    };
  }

  // lastRir >= 3 → increase
  const nextWeight = lastWeightLb + incrementLb;
  return {
    nextWeightLb: nextWeight,
    targetRepsRange,
    targetRir,
    rationale: "RIR ≥ 3 — increase load",
    explanation:
      `You finished with reps in reserve. Increasing to ${nextWeight} lb will continue strength progression.`,
  };
}
