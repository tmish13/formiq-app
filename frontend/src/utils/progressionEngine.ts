// Pure functions only — no React / DOM dependencies.
// Decision rules based on RIR (Reps in Reserve) from the last training session.

import { TrainingSession } from '@/types/training';

export type RecommendationType = 'increase' | 'hold' | 'reduce';

export interface ProgressionPlan {
  recommendedWeight: number;
  recommendationType: RecommendationType;
  reason: string;
}

/** Round to nearest 0.5 lb. */
function roundToHalf(x: number): number {
  return Math.round(x * 2) / 2;
}

export function computeSessionMetrics(sessions: TrainingSession[]): {
  lastSession?: TrainingSession;
  previousSession?: TrainingSession;
  avgRir: number | null;
} {
  if (sessions.length === 0) {
    return { avgRir: null };
  }

  // Sort newest → oldest defensively
  const sorted = [...sessions].sort(
    (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime(),
  );

  const lastSession = sorted[0];
  const previousSession = sorted[1];

  return {
    lastSession,
    previousSession,
    avgRir: lastSession.avgRir,
  };
}

/**
 * Computes a load recommendation based on RIR data from training sessions.
 * Returns null when there are no sessions to base a recommendation on.
 */
export function computeProgressionPlan(sessions: TrainingSession[]): ProgressionPlan | null {
  if (sessions.length === 0) return null;

  // Sort newest → oldest defensively
  const sorted = [...sessions].sort(
    (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime(),
  );

  const last = sorted[0];
  const previous = sorted[1];

  let recommendationType: RecommendationType;
  let recommendedWeight: number;
  let reason: string;

  if (last.avgRir >= 4) {
    // Easy — increase load
    const increment = Math.max(2.5, last.weightLb * 0.025);
    recommendedWeight = roundToHalf(last.weightLb + increment);
    recommendationType = 'increase';
    reason = `You reported ${last.avgRir} RIR — the weight felt manageable. Time to add load.`;
  } else if (last.avgRir < 1 && sorted.length >= 2 && sorted[1].avgRir < 1) {
    // Two consecutive very hard sessions → reduce
    recommendedWeight = roundToHalf(last.weightLb * 0.95);
    recommendationType = 'reduce';
    reason = `Two consecutive sessions with RIR < 1. Reducing load slightly to support recovery.`;
  } else if (last.avgRir < 1) {
    // Single very hard session — monitor before reducing
    recommendedWeight = last.weightLb;
    recommendationType = 'hold';
    reason = `Last session was very hard (${last.avgRir} RIR). Hold here and monitor recovery before deciding.`;
  } else {
    // RIR 1–3 — hold
    recommendedWeight = last.weightLb;
    recommendationType = 'hold';
    reason = `You reported ${last.avgRir} RIR — solid working intensity. Maintain this load.`;
  }

  // Technique override: if weight went up but form dropped ≥5 points, don't increase further
  if (
    recommendationType === 'increase' &&
    previous != null &&
    last.formScore != null &&
    previous.formScore != null &&
    last.weightLb > previous.weightLb &&
    last.formScore - previous.formScore <= -5
  ) {
    recommendedWeight = last.weightLb;
    recommendationType = 'hold';
    reason = `Form dropped ${Math.abs(last.formScore - previous.formScore)} points when you added weight. Hold and rebuild technique before progressing.`;
  }

  return { recommendedWeight, recommendationType, reason };
}
