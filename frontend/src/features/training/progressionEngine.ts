/**
 * Pure deterministic next-set recommendation engine.
 * No side effects, no I/O — fully testable with inline data.
 *
 * Decision hierarchy (UNCHANGED):
 *   1. No working sets logged   → hold (starter prompt)
 *   2. Last working set lacks RIR → hold (data prompt)
 *   3. RIR ≥ 4 (and no fatigue) → increase by 1 increment
 *   4. RIR 2–3                  → hold
 *   5. RIR 1 + strength goal    → hold (near-maximal is fine)
 *   6. RIR 1 + hyp/general + fatigue rising → reduce
 *   7. RIR 1 + hyp/general, no fatigue      → hold
 *   8. RIR ≤ 0                  → reduce (2 steps if 2+ consecutive failures)
 *
 * New fields added (non-breaking):
 *   setsCompleted, setsRecommended, exerciseStatus, fatigueSignal, statusMessage
 *
 * Form score: advisory only — never overrides the RIR-based action.
 */

import type {
  Goal,
  Exercise,
  EquipmentProfile,
  SetLog,
  NextSetRecommendation,
  ExerciseStatus,
  FatigueSignal,
} from "./types";

// ---------------------------------------------------------------------------
// Internal helpers (existing — unchanged)
// ---------------------------------------------------------------------------

/** Round weight to nearest increment multiple, floored at 0. */
function roundToIncrement(weight: number, increment: number): number {
  if (increment <= 0) return Math.max(0, Math.round(weight));
  return Math.max(0, Math.round(weight / increment) * increment);
}

/** Count how many trailing working sets in sequence have rir ≤ 0. */
function countConsecutiveZeroRir(sets: SetLog[]): number {
  let count = 0;
  for (let i = sets.length - 1; i >= 0; i--) {
    const rir = sets[i].rir;
    if (rir != null && rir <= 0) {
      count++;
    } else {
      break;
    }
  }
  return count;
}

/**
 * Detect rising fatigue: does the last working set have lower RIR than the
 * previous working set performed at the same (±1 increment) weight?
 */
function isFatigueRising(sets: SetLog[], increment: number): boolean {
  if (sets.length < 2) return false;
  const last = sets[sets.length - 1];
  if (last.rir == null) return false;

  const prevAtSameWeight = [...sets]
    .slice(0, -1)
    .reverse()
    .find(
      (s) =>
        s.rir != null &&
        Math.abs(s.weightLb - last.weightLb) <= Math.max(increment, 1),
    );

  if (!prevAtSameWeight || prevAtSameWeight.rir == null) return false;
  return last.rir < prevAtSameWeight.rir;
}

/** Return a form advisory string if form score dropped sharply (≥15 pts). */
function formAdvisory(sets: SetLog[]): string[] {
  if (sets.length < 2) return [];
  const last = sets[sets.length - 1];
  const prev = sets[sets.length - 2];
  if (
    last.formScore != null &&
    prev.formScore != null &&
    last.formScore < prev.formScore - 15
  ) {
    return ["Form score dropped — focus on technique before adding load."];
  }
  return [];
}

// ---------------------------------------------------------------------------
// New helpers — fatigue signal, exercise status, coaching messages
// ---------------------------------------------------------------------------

/** Recommended working set targets by goal (conservative but evidence-aligned). */
const SETS_RECOMMENDED: Record<Goal, number> = {
  strength:    3, // powerlifting: 2–4 heavy sets; 3 is the common sweet spot
  hypertrophy: 4, // hypertrophy: 3–5 sets per muscle; 4 balances stimulus vs fatigue
  general:     2, // general fitness: 1–3 sets; 2 prevents overreaching
};

/**
 * Derive a fatigue signal from the RIR trajectory across working sets.
 * "high"   — failure or sharp drop (≥3 RIR points)
 * "rising" — RIR is decreasing at same weight (isFatigueRising)
 * "normal" — no trend detected
 */
function computeFatigueSignal(
  workingSets: SetLog[],
  increment: number,
): FatigueSignal {
  if (workingSets.length === 0) return "normal";
  const last = workingSets[workingSets.length - 1];
  if (last.rir == null) return "normal";

  // Failure (RIR 0) or very close to it
  if (last.rir <= 0) return "high";

  // Large RIR drop in consecutive sets signals accumulating fatigue
  if (workingSets.length >= 2) {
    const prev = workingSets[workingSets.length - 2];
    if (prev.rir != null && prev.rir - last.rir >= 3) return "high";
  }

  // Standard isFatigueRising catches same-weight RIR deterioration
  if (isFatigueRising(workingSets, increment)) return "rising";

  return "normal";
}

/**
 * Decide whether the lifter should continue, wrap up, or stop the exercise.
 * Rules respect goal-specific volume targets and intensity signals.
 */
function computeExerciseStatus(
  goal: Goal,
  setsCompleted: number,
  setsRecommended: number,
  lastRir: number,
  fatigueSignal: FatigueSignal,
): ExerciseStatus {
  // Max sets always signals finish regardless of RIR
  if (setsCompleted >= setsRecommended) return "finish";

  if (goal === "strength") {
    // Strength: honour the full set target (setsRecommended=3).
    // Only surface "optional" early when near-maximal effort (RIR ≤ 1) after at least 2 sets,
    // so the lifter knows they can wrap up if needed — but finish is NOT forced before target.
    if (setsCompleted >= 2 && lastRir <= 1) return "optional";
  }

  if (goal === "hypertrophy") {
    // Hypertrophy: needs volume. Below 3 sets = definitely continue.
    if (setsCompleted < 3) return "continue";
    // At 3 sets: stop if very fatigued, otherwise optional
    if (lastRir <= 1 || fatigueSignal === "high") return "finish";
    return "optional";
  }

  if (goal === "general") {
    // General: sustainable effort, 2 solid sets is the target
    if (setsCompleted >= 2 && lastRir <= 3) return "finish";
    if (setsCompleted >= 2) return "optional";
  }

  return "continue";
}

/**
 * Generate a one-line coaching message for the current exercise status.
 * Returns undefined when there is nothing meaningful to say (normal progress).
 */
function computeStatusMessage(
  goal: Goal,
  exerciseStatus: ExerciseStatus,
  fatigueSignal: FatigueSignal,
): string | undefined {
  if (exerciseStatus === "finish") {
    if (goal === "strength")
      return "Strength target reached. Finish or do an optional back-off set.";
    if (goal === "hypertrophy")
      return "Hypertrophy volume target reached. Exercise complete.";
    return "General fitness target reached. Move to the next exercise.";
  }

  if (exerciseStatus === "optional") {
    if (fatigueSignal === "high")
      return "High fatigue — finish this exercise or add a light back-off set.";
    if (fatigueSignal === "rising")
      return "Fatigue rising — additional set optional. Rest well before deciding.";
    return "On track. Additional set optional.";
  }

  // exerciseStatus === "continue"
  if (fatigueSignal === "high")
    return "High fatigue detected. Consider finishing this exercise.";
  if (fatigueSignal === "rising")
    return "Fatigue is rising across sets — monitor rep quality.";

  return undefined;
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

export function getNextSetRecommendation({
  goal,
  exercise,
  equipment,
  recentSets,
}: {
  goal: Goal;
  exercise: Exercise;
  equipment: EquipmentProfile | null;
  recentSets: SetLog[];
}): NextSetRecommendation {
  const increment = equipment?.incrementLb ?? exercise.defaultIncrementLb;
  const restSeconds = goal === "strength" ? 180 : 120;
  const repRange = exercise.defaultRepIntent;
  const setsRecommended = SETS_RECOMMENDED[goal];

  // Starter weight suggestion: sensible multiple of increment, minimum 45
  const starterWeight =
    increment > 0
      ? roundToIncrement(Math.max(increment * 6, 45), increment)
      : 0;

  // Collect working sets in chronological order
  const workingSets = [...recentSets]
    .filter((s) => s.setType === "working")
    .sort((a, b) => a.setIndex - b.setIndex);

  // ── Guard 1: no working sets yet ─────────────────────────────────────────
  if (workingSets.length === 0) {
    return {
      action: "hold",
      nextWeightLb: starterWeight,
      nextRepsRange: repRange,
      restSeconds,
      reasons: ["Log your first working set to unlock recommendations."],
      setsCompleted: 0,
      setsRecommended,
      exerciseStatus: "continue",
      fatigueSignal: "normal",
    };
  }

  const last = workingSets[workingSets.length - 1];
  const setsCompleted = workingSets.length;

  // ── Guard 2: last working set lacks RIR ───────────────────────────────────
  if (last.rir == null) {
    return {
      action: "hold",
      nextWeightLb: last.weightLb,
      nextRepsRange: repRange,
      restSeconds,
      reasons: ["Add RIR to your working sets to unlock load recommendations."],
      setsCompleted,
      setsRecommended,
      exerciseStatus: "continue",
      fatigueSignal: "normal",
    };
  }

  // ── Derived context ───────────────────────────────────────────────────────
  const lastRir = last.rir;
  const lastWeight = last.weightLb;
  const fatigueRising = isFatigueRising(workingSets, increment);
  const consecutiveZeroRir = countConsecutiveZeroRir(workingSets);
  const advisory = formAdvisory(workingSets);

  // New fields (additive)
  const fatigueSignal = computeFatigueSignal(workingSets, increment);
  const exerciseStatus = computeExerciseStatus(
    goal,
    setsCompleted,
    setsRecommended,
    lastRir,
    fatigueSignal,
  );
  const statusMessage = computeStatusMessage(goal, exerciseStatus, fatigueSignal);

  const debugBase = {
    lastWorkingSetRir: lastRir,
    lastWorkingSetWeight: lastWeight,
    increment,
  };

  const meta = { setsCompleted, setsRecommended, exerciseStatus, fatigueSignal, statusMessage };

  // ── RIR ≥ 4 → Increase (unless fatigue is rising) ────────────────────────
  if (lastRir >= 4) {
    if (fatigueRising) {
      return {
        action: "hold",
        nextWeightLb: lastWeight,
        nextRepsRange: repRange,
        restSeconds,
        reasons: [
          "RIR is high but fatigue is rising — hold weight this set.",
          ...advisory,
        ],
        ...meta,
        debug: {
          ...debugBase,
          prevWorkingSetRir: workingSets
            .slice(0, -1)
            .reverse()
            .find(
              (s) =>
                s.rir != null &&
                Math.abs(s.weightLb - lastWeight) <= Math.max(increment, 1),
            )?.rir,
        },
      };
    }

    const nextWeight = roundToIncrement(lastWeight + increment, increment);
    return {
      action: "increase",
      nextWeightLb: nextWeight,
      nextRepsRange: repRange,
      restSeconds,
      reasons: [
        `RIR ${lastRir} — plenty of reserve, ready to add weight.`,
        ...advisory,
      ],
      ...meta,
      debug: debugBase,
    };
  }

  // ── RIR 2–3 → Hold ───────────────────────────────────────────────────────
  if (lastRir >= 2) {
    return {
      action: "hold",
      nextWeightLb: lastWeight,
      nextRepsRange: repRange,
      restSeconds,
      reasons: [
        `RIR ${lastRir} — working at the right intensity. Hold weight.`,
        ...advisory,
      ],
      ...meta,
      debug: debugBase,
    };
  }

  // ── RIR 1 ─────────────────────────────────────────────────────────────────
  if (lastRir === 1) {
    if (goal === "strength") {
      // Near-maximal effort is appropriate for strength
      return {
        action: "hold",
        nextWeightLb: lastWeight,
        nextRepsRange: repRange,
        restSeconds,
        reasons: [
          "RIR 1 — near-maximal effort, appropriate for strength. Hold weight.",
          ...advisory,
        ],
        ...meta,
        debug: debugBase,
      };
    }

    if (fatigueRising) {
      const nextWeight = roundToIncrement(lastWeight - increment, increment);
      return {
        action: "reduce",
        nextWeightLb: Math.max(0, nextWeight),
        nextRepsRange: repRange,
        restSeconds,
        reasons: [
          "RIR 1 with rising fatigue — reduce weight to preserve rep quality.",
          ...advisory,
        ],
        ...meta,
        debug: {
          ...debugBase,
          prevWorkingSetRir: workingSets
            .slice(0, -1)
            .reverse()
            .find(
              (s) =>
                s.rir != null &&
                Math.abs(s.weightLb - lastWeight) <= Math.max(increment, 1),
            )?.rir,
        },
      };
    }

    return {
      action: "hold",
      nextWeightLb: lastWeight,
      nextRepsRange: repRange,
      restSeconds,
      reasons: ["RIR 1 — at productive intensity. Hold weight.", ...advisory],
      ...meta,
      debug: debugBase,
    };
  }

  // ── RIR ≤ 0 → Reduce ─────────────────────────────────────────────────────
  const steps = consecutiveZeroRir >= 2 ? 2 : 1;
  const nextWeight = roundToIncrement(lastWeight - increment * steps, increment);

  return {
    action: "reduce",
    nextWeightLb: Math.max(0, nextWeight),
    nextRepsRange: repRange,
    restSeconds,
    reasons: [
      consecutiveZeroRir >= 2
        ? `RIR 0 on ${consecutiveZeroRir} consecutive sets — reduce by 2 steps.`
        : "RIR 0 — reduce weight to restore reserve.",
      ...advisory,
    ],
    ...meta,
    debug: { ...debugBase },
  };
}
