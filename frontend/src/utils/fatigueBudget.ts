/**
 * Fatigue Budget Wrapper — pure, deterministic session fatigue gating.
 * No side effects, no DOM. Wraps (but does not change) progressionEngine.ts.
 *
 * Score table:
 *   RIR ≥ 4          → +0
 *   RIR 2–3          → +1
 *   RIR 1            → +2
 *   RIR ≤ 0          → +3  (failure)
 *   RIR missing      → +1  (neutral; encourages logging but not punitive)
 *
 * Trend add-ons (only if ≥ 2 working sets AND both sets have RIR defined):
 *   +1 if reps dropped ≥ 2 from prev set at similar load (within incrementLb ?? 5 lb)
 *   +1 if load increased from prev set AND RIR dropped by ≥ 2 (overshoot signal)
 *
 * Goal budgets:
 *   strength:    3
 *   hypertrophy: 5
 *   general:     4
 *
 * Strength cap floor: isCapped is suppressed unless workingSets.length >= 2
 *   OR the last set is a true failure (RIR === 0).
 */

export type Goal = "strength" | "hypertrophy" | "general";
export type SetType = "warmup" | "working" | "backoff";

export interface WorkingSetLite {
  setType: SetType;
  /** Load in lbs. 0 = bodyweight. */
  weight: number;
  reps: number;
  /** Reps In Reserve. Undefined = missing (scored as +1, neutral). */
  rir?: number;
}

export interface FatigueBudgetResult {
  fatigueScore: number;
  budget: number;
  /** true when fatigueScore >= budget AND cap floor is satisfied. */
  isCapped: boolean;
  fatigueSignal: "normal" | "rising" | "high";
  /**
   * True when last RIR === 0, OR (repsDrop add-on fired AND lastRIR <= 1),
   * OR (rirDrop >= 2 AND repDrop >= 2). Used to gate back-off suggestion.
   */
  isHighFatigue: boolean;
  /** 1–3 lifter-friendly coaching bullets. */
  reasons: string[];
}

// ---------------------------------------------------------------------------
// Budgets by goal
// ---------------------------------------------------------------------------

const BUDGETS: Record<Goal, number> = {
  strength:    3, // fewer, heavier sets — cap early
  hypertrophy: 5, // more volume allowed
  general:     4, // slightly more flexible than strength
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Per-set fatigue point value from RIR. */
function setFatiguePoints(rir: number | undefined): number {
  if (rir === undefined || rir === null) return 1; // missing → neutral (A)
  if (rir <= 0) return 3;  // failure / max effort
  if (rir === 1) return 2; // near-maximal
  if (rir <= 3) return 1;  // productive working intensity (RIR 2–3)
  return 0;                // RIR ≥ 4 → easy, no fatigue penalty
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

export function computeFatigueBudget({
  goal,
  sets,
  lookbackWorkingSets = 3,
  incrementLb,
}: {
  goal: Goal;
  sets: WorkingSetLite[];
  /** Default 3. Only the last N working sets are scored. */
  lookbackWorkingSets?: number;
  /** Equipment increment in lbs — defines "similar load" for trend add-ons. */
  incrementLb?: number;
}): FatigueBudgetResult {
  const budget = BUDGETS[goal];

  // Filter to working sets; take the last N for scoring
  const workingSets = sets
    .filter((s) => s.setType === "working")
    .slice(-lookbackWorkingSets);

  if (workingSets.length === 0) {
    return {
      fatigueScore: 0,
      budget,
      isCapped: false,
      fatigueSignal: "normal",
      isHighFatigue: false,
      reasons: [],
    };
  }

  // ── Per-set scoring ────────────────────────────────────────────────────
  let score = 0;
  let hasMissingRir = false;

  for (const s of workingSets) {
    score += setFatiguePoints(s.rir);
    if (s.rir === undefined || s.rir === null) hasMissingRir = true;
  }

  // ── Trend add-ons (last 2 working sets; require RIR on both) ──────────
  const addOns = new Set<string>();
  const similarLoadTolerance = incrementLb ?? 5; // C: use equipment increment

  if (workingSets.length >= 2) {
    const prev = workingSets[workingSets.length - 2];
    const last = workingSets[workingSets.length - 1];
    const prevRir = prev.rir ?? null;
    const lastRir = last.rir ?? null;

    // Both sets must have RIR to apply RIR-dependent trend add-ons (A)
    const bothHaveRir = prevRir !== null && lastRir !== null;

    // +1 if reps dropped ≥ 2 at similar load (C: tolerance = incrementLb ?? 5)
    const similarLoad = Math.abs(last.weight - prev.weight) <= similarLoadTolerance;
    if (similarLoad && prev.reps - last.reps >= 2) {
      score += 1;
      addOns.add("reps_drop");
    }

    // +1 if load increased AND RIR dropped by ≥ 2 (overshoot; requires both RIRs)
    if (
      bothHaveRir &&
      last.weight > prev.weight &&
      prevRir! - lastRir! >= 2
    ) {
      score += 1;
      addOns.add("overshoot");
    }
  }

  // ── Fatigue signal (derived from last 2 working sets) ─────────────────
  const last = workingSets[workingSets.length - 1];
  const lastRir = last.rir ?? null;
  let fatigueSignal: "normal" | "rising" | "high" = "normal";

  if (workingSets.length >= 2) {
    const prev = workingSets[workingSets.length - 2];
    const prevRir = prev.rir ?? null;
    const rirDrop = prevRir !== null && lastRir !== null ? prevRir - lastRir : 0;
    const repDrop = prev.reps - last.reps;

    if ((lastRir !== null && lastRir <= 0) || (rirDrop >= 2 && repDrop >= 2)) {
      fatigueSignal = "high";
    } else if (rirDrop >= 2) {
      fatigueSignal = "rising";
    }
  } else if (lastRir !== null && lastRir <= 0) {
    fatigueSignal = "high";
  }

  // ── isHighFatigue flag (E: gates back-off suggestion) ─────────────────
  const isHighFatigue =
    (lastRir !== null && lastRir <= 0) ||
    (addOns.has("reps_drop") && lastRir !== null && lastRir <= 1) ||
    fatigueSignal === "high";

  // ── isCapped with strength cap floor (B) ──────────────────────────────
  const rawCapped = score >= budget;
  let isCapped = rawCapped;
  if (goal === "strength" && rawCapped) {
    // Suppress cap unless ≥ 2 working sets OR true failure (RIR === 0)
    const isTrueFailure = last.rir === 0;
    if (workingSets.length < 2 && !isTrueFailure) {
      isCapped = false;
    }
  }

  // ── Reason bullets (max 3, lifter-friendly) ───────────────────────────
  const reasons: string[] = [];

  if (hasMissingRir) {
    reasons.push("Log RIR on working sets for better coaching.");
  }
  if (
    (fatigueSignal === "high" || fatigueSignal === "rising") &&
    reasons.length < 3
  ) {
    reasons.push("Fatigue is climbing (RIR dropped fast).");
  }
  if (addOns.has("reps_drop") && reasons.length < 3) {
    reasons.push("Reps fell off at similar load.");
  }
  if (addOns.has("overshoot") && reasons.length < 3) {
    reasons.push("Intensity overshot — better to stop before grinding.");
  }

  return {
    fatigueScore: score,
    budget,
    isCapped,
    fatigueSignal,
    isHighFatigue,
    reasons: reasons.slice(0, 3),
  };
}
