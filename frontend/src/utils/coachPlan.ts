// FUTURE EXTENSIBILITY:
// computeCoachPlan can accept an exercise parameter to swap component labels
// and weight-increment rules per exercise while reusing the same scoring structure.

import { SquatTrainingSession } from '../types/formCheck';
import { getBiggestOpportunityFromSessions } from './squatSessions';

const COMPONENT_LABELS: Record<string, string> = {
  torsoStability: 'torso stability',
  kneeSymmetry: 'knee symmetry',
  bottomControl: 'bottom position control',
  forwardLean: 'forward lean',
};

const FOCUS_CUES: Record<string, string> = {
  torsoStability: 'Brace your core and keep your chest tall throughout the descent',
  kneeSymmetry:   'Keep knees stacked directly over toes — no caving inward',
  bottomControl:  'Pause 1 second at the bottom and control the descent',
  forwardLean:    'Drive elbows back and keep your torso as upright as possible',
};

const DRILL_SUMMARIES: Record<string, string> = {
  torsoStability: 'Box squats with 2-sec pause x8, 3 sets',
  kneeSymmetry:   'Banded squats x10, 3 sets before work sets',
  bottomControl:  'Goblet squats x10 with 2-sec pause at bottom, 3 sets',
  forwardLean:    'Wall-facing squats x10, 3 sets',
};

export interface CoachPlan {
  title: string;
  bullets: string[];
  rationale: string;
  recommendedWeightLb: number | null;  // null = bodyweight session
  sets: number;
  reps: number;
  focusCue: string;       // e.g. "Keep knees stacked over toes"
  drillSummary: string;   // e.g. "Banded squats x10, 3 sets"
}

/**
 * Deterministic coach plan based on recent squat sessions.
 * Returns null when no sessions are provided.
 *
 * @param recent - Up to 3 most-recent local squat sessions (newest first).
 * @param context - Optional backend analytics context. Used to detect whether the
 *   lifter has prior load history even when the local session weight is 0.
 */
export function computeCoachPlan(
  recent: SquatTrainingSession[],
  context?: { bestWeightLb?: number; avgLast5WeightLb?: number },
): CoachPlan | null {
  if (recent.length === 0) return null;

  const opp = getBiggestOpportunityFromSessions(recent, recent.length);
  const limiterKey = opp?.componentKey ?? 'torsoStability';
  const _limiterLabel = COMPONENT_LABELS[limiterKey] ?? 'your primary limiter';
  const focusCue = FOCUS_CUES[limiterKey] ?? FOCUS_CUES['torsoStability'];
  const drillSummary = DRILL_SUMMARIES[limiterKey] ?? DRILL_SUMMARIES['torsoStability'];

  // True when backend analytics shows prior weight history, even if local session has weight=0
  const hasLoadedHistory = (context?.bestWeightLb ?? 0) > 0 || (context?.avgLast5WeightLb ?? 0) > 0;

  if (recent.length === 1) {
    const lastWeight = recent[0].workingWeight;

    // Case 1a: bodyweight — no weight loaded and no prior history from backend
    if (lastWeight === 0 && !hasLoadedHistory) {
      return {
        title: 'Start with bodyweight fundamentals',
        bullets: [
          '3 sets of 5 bodyweight squats — build the movement pattern',
          `Focus: ${focusCue}`,
          'Log 2–3 more sessions to unlock weight progression',
        ],
        rationale: 'Based on your last 1 squat session.',
        recommendedWeightLb: null,
        sets: 3,
        reps: 5,
        focusCue,
        drillSummary,
      };
    }

    // Case 1b: has weight logged, OR no local weight but backend shows prior load history
    const effectiveWeight = lastWeight > 0
      ? lastWeight
      : (context?.bestWeightLb ?? context?.avgLast5WeightLb ?? 0);
    return {
      title: 'Hold and refine',
      bullets: [
        effectiveWeight > 0
          ? `Work at ${effectiveWeight} lb — 3 sets of 5`
          : '3 sets of 5 bodyweight squats',
        `Focus: ${focusCue}`,
        'Log 2 more sessions to unlock load progression advice',
      ],
      rationale: 'Based on your last 1 squat session.',
      recommendedWeightLb: effectiveWeight,
      sets: 3,
      reps: 5,
      focusCue,
      drillSummary,
    };
  }

  // 2+ sessions
  const avgScore = recent.reduce((sum, s) => sum + s.overallScore, 0) / recent.length;
  // Guard: if the most-recent session has no weight logged but history has weight, use last known weight
  const rawLastWeight = recent[0].workingWeight;
  const lastNonZeroWeight = recent.find(s => s.workingWeight > 0)?.workingWeight ?? 0;
  const lastWeight = rawLastWeight > 0 ? rawLastWeight : lastNonZeroWeight;
  const prevWeight = recent.length >= 2 ? recent[1].workingWeight : 0;
  const loadRatio = prevWeight > 0 ? lastWeight / prevWeight : 1.0;
  const scoreDelta = recent[0].overallScore - recent[recent.length - 1].overallScore;
  const sets = 3;
  const reps = 5;

  const makeBullets = (weightLb: number | null): string[] => [
    weightLb != null
      ? `Work at ${weightLb} lb — ${sets} sets of ${reps}`
      : `${sets} sets of ${reps} bodyweight squats`,
    `Focus: ${focusCue}`,
    `Drill before work sets: ${drillSummary}`,
  ];

  // Case A: avg < 65, loadRatio ≥ 1.10 → deload
  if (avgScore < 65 && loadRatio >= 1.10) {
    const weight = Math.round(lastWeight * 0.92);
    return {
      title: 'Deload and reset technique',
      bullets: makeBullets(weight),
      rationale: 'Heavier load is exposing form weaknesses. Drop ~8% to rebuild mechanics.',
      recommendedWeightLb: weight,
      sets,
      reps,
      focusCue,
      drillSummary,
    };
  }

  // Case B: avg < 65 → hold
  if (avgScore < 65) {
    return {
      title: 'Lock in technique before adding weight',
      bullets: makeBullets(lastWeight),
      rationale: 'Consistent form at current weight comes first. Aim for avg ≥ 65 before adding load.',
      recommendedWeightLb: lastWeight,
      sets,
      reps,
      focusCue,
      drillSummary,
    };
  }

  // Case C: avg 65–79, scoreDelta ≥ 2 → modest increase
  if (avgScore < 80 && scoreDelta >= 2) {
    return {
      title: 'Controlled progression',
      bullets: makeBullets(lastWeight + 5),
      rationale: 'Form is improving. Small increment rewards the work — back off if score drops below 65.',
      recommendedWeightLb: lastWeight + 5,
      sets,
      reps,
      focusCue,
      drillSummary,
    };
  }

  // Case D: avg 65–79, scoreDelta < 2 → hold
  if (avgScore < 80) {
    return {
      title: 'Hold and refine',
      bullets: makeBullets(lastWeight),
      rationale: 'Form in range but not trending up. Aim for 2 sessions above 75 before adding weight.',
      recommendedWeightLb: lastWeight,
      sets,
      reps,
      focusCue,
      drillSummary,
    };
  }

  // Case E: avg ≥ 80 → push
  return {
    title: 'Ready to push',
    bullets: makeBullets(lastWeight + 5),
    rationale: 'Solid mechanics. Modest increment — keep form the priority.',
    recommendedWeightLb: lastWeight + 5,
    sets,
    reps,
    focusCue,
    drillSummary,
  };
}
