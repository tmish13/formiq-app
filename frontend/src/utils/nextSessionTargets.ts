/**
 * Next-session target computation — pure, deterministic, zero side effects.
 *
 * Accepts all sets for an exercise; filters to working sets internally.
 * Returns null when no working sets exist.
 *
 * Best working set selection:
 *   Primary:    highest weightLb
 *   Tiebreaker: highest reps
 *
 * Weight decision rules (based on best working set RIR):
 *   RIR ≥ 3   → increase by incrementLb
 *   RIR 1–2   → hold weight
 *   RIR 0     → reduce by incrementLb (to recover)
 *   undefined → hold (prompt user to log RIR next time)
 */

import type { Goal } from "./repClamp";

export interface NextSessionTarget {
  targetWeightLb: number;
  targetRepsRange: { min: number; max: number };
  targetRir: number;
  rationale: string;
}

export interface SetForTarget {
  setType: string;
  weightLb: number;
  reps: number;
  rir?: number;
}

export function computeNextSessionTarget({
  goal: _goal,
  sets,
  incrementLb,
  repClampRange,
}: {
  goal: Goal;
  /** All logged sets for the exercise. Warmups and backoffs are ignored. */
  sets: SetForTarget[];
  incrementLb: number;
  repClampRange: { min: number; max: number };
}): NextSessionTarget | null {
  const workingSets = sets.filter((s) => s.setType === "working");
  if (workingSets.length === 0) return null;

  // Best: highest weight, then highest reps as tiebreaker
  const best = workingSets.reduce((b, s) => {
    if (s.weightLb > b.weightLb) return s;
    if (s.weightLb === b.weightLb && s.reps > b.reps) return s;
    return b;
  });

  const { weightLb, rir } = best;
  let targetWeightLb: number;
  let rationale: string;

  if (rir === undefined) {
    targetWeightLb = weightLb;
    rationale = "no RIR → hold (log RIR next time)";
  } else if (rir >= 3) {
    targetWeightLb = weightLb + incrementLb;
    rationale = "RIR ≥ 3 → increase load";
  } else if (rir >= 1) {
    targetWeightLb = weightLb;
    rationale = "RIR 1–2 → hold weight";
  } else {
    // rir === 0
    targetWeightLb = Math.max(0, weightLb - incrementLb);
    rationale = "RIR 0 → reduce to recover";
  }

  return {
    targetWeightLb,
    targetRepsRange: { min: repClampRange.min, max: repClampRange.max },
    targetRir: 2,
    rationale,
  };
}
