/**
 * Rep Range Clamp Wrapper — UI-level guidance only.
 *
 * Per-goal clamp ranges align with programming best practices:
 * - strength:    5–8 reps for fatigue management and frequency
 * - hypertrophy: 6–12 reps for optimal muscle growth signal
 * - general:     6–20 reps wide range to accommodate exercise variety
 *
 * This affects display text and Fill-inputs prefill ONLY.
 * It does NOT change engine math (progressionEngine.ts is untouched).
 */

export type Goal = "strength" | "hypertrophy" | "general";

const CLAMP_CONFIG: Record<Goal, { min: number; max: number; coachLine: string }> = {
  strength:    { min: 5,  max: 8,  coachLine: "Coach target: 5–8 reps (lower fatigue → higher frequency)" },
  hypertrophy: { min: 6,  max: 12, coachLine: "Coach target: 6–12 reps (moderate volume → balanced stimulus)" },
  general:     { min: 6,  max: 20, coachLine: "Coach target: 6–20 reps (higher volume → flexible approach)" },
};

export function getClampedWorkingRepRange({
  goal,
  engineRange,
  fallback,
}: {
  goal: Goal;
  /** Rep range returned by the engine. Used when available. */
  engineRange?: { min: number; max: number };
  /** Fallback when engine range is not yet available. */
  fallback?: { min: number; max: number };
}): { min: number; max: number; wasClamped: boolean; coachLine?: string } {
  const base = engineRange ?? fallback ?? { min: 6, max: 12 };
  const { min: cMin, max: cMax, coachLine } = CLAMP_CONFIG[goal];
  const alreadyInRange = base.min >= cMin && base.max <= cMax;

  if (alreadyInRange) {
    return { min: base.min, max: base.max, wasClamped: false };
  }

  return {
    min: cMin,
    max: cMax,
    wasClamped: true,
    coachLine,
  };
}
