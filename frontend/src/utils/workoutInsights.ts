/**
 * Workout insight generation — pure, deterministic, zero side effects.
 *
 * Analyzes RIR patterns in a completed session and returns 1–2 concise insights.
 */

export type InsightType = "warning" | "positive" | "neutral";

export interface WorkoutInsight {
  headline: string;
  detail: string;
  recommendation: string;
  type: InsightType;
}

interface SetForInsights {
  rir?: number;
  weightLb: number;
  reps: number;
}

interface ExerciseForInsights {
  exerciseName: string;
  workingSets: SetForInsights[];
}

export interface SessionForInsights {
  exercises: ExerciseForInsights[];
  totalVolumeLb: number;
  totalWorkingSets: number;
}

export function generateWorkoutInsights(session: SessionForInsights): WorkoutInsight[] {
  const insights: WorkoutInsight[] = [];

  for (const ex of session.exercises) {
    if (ex.workingSets.length < 2) continue;

    const rirs = ex.workingSets
      .map((s) => s.rir)
      .filter((r): r is number => typeof r === "number");

    if (rirs.length >= 2) {
      const first = rirs[0];
      const last = rirs[rirs.length - 1];

      // Fatigue spike: RIR dropped by 2+ within the exercise
      if (first - last >= 2) {
        insights.push({
          headline: "Fatigue accumulated quickly",
          detail: `RIR dropped from ${first} to ${last} on ${ex.exerciseName}.`,
          recommendation:
            "Try longer rest between sets or reduce load by 5% next session.",
          type: "warning",
        });
        continue; // one insight per exercise is enough
      }

      // Early failure: hit RIR 0 before the last set
      const earlyFailure = ex.workingSets
        .slice(0, -1)
        .some((s) => s.rir === 0);
      if (earlyFailure) {
        insights.push({
          headline: "Reached failure before your last set",
          detail: `You hit failure early on ${ex.exerciseName}.`,
          recommendation:
            "Reduce load 5–10% to keep rep quality consistent across all sets.",
          type: "warning",
        });
        continue;
      }

      // High reserves: all sets very easy
      if (rirs.every((r) => r >= 4)) {
        insights.push({
          headline: `Plenty of reserve on ${ex.exerciseName}`,
          detail: "All sets finished with RIR ≥ 4 — you had more left.",
          recommendation: "Increase load next session to drive progressive overload.",
          type: "positive",
        });
      }
    }
  }

  // Session-level fallback: no warnings → positive summary
  if (insights.length === 0 && session.totalWorkingSets >= 3) {
    insights.push({
      headline: "Solid session",
      detail: `${session.totalWorkingSets} working sets logged.`,
      recommendation: "Maintain load and RIR targets next session.",
      type: "positive",
    });
  }

  return insights.slice(0, 2);
}
