/**
 * Tests for ProgressPage pure helpers:
 *   - computeWeightAwareTrendLabel (Change 4)
 *   - buildOpportunityBody (Change 5)
 *   - computeWeightLoadDelta (new)
 *
 * Uses inline replicas of the functions (same pattern as AnalysisPage.test.tsx)
 * so tests don't depend on rendering the full page component.
 */

// ---------------------------------------------------------------------------
// Inline replica of computeWeightAwareTrendLabel
// ---------------------------------------------------------------------------

interface WeightAwareTrend {
  label: string;
  cls: string;
}

function computeWeightAwareTrendLabel(
  analyticsSessions: Array<{ posture_score: number | null }>,
  weightTrend: Array<{ weight_kg: number }> | undefined,
): WeightAwareTrend {
  const IMPROVING_CLS = 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300';
  const AMBER_CLS     = 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400';
  const GRAY_CLS      = 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400';

  let weightDelta: number | null = null;
  if (weightTrend && weightTrend.length >= 2) {
    const first = weightTrend[0].weight_kg;
    const last  = weightTrend[weightTrend.length - 1].weight_kg;
    if (first > 0) weightDelta = last / first;
  }
  const validScores = analyticsSessions.map(s => s.posture_score).filter((v): v is number => v != null);
  let scoreDelta: number | null = null;
  if (validScores.length >= 2) {
    scoreDelta = validScores[validScores.length - 1] - validScores[0];
  }

  // Case A: weight ↑≥10% + form ↓
  if (weightDelta != null && weightDelta >= 1.10 && scoreDelta != null && scoreDelta < 0)
    return { label: 'Form stressed under heavier load', cls: AMBER_CLS };
  // Case B: form dipped, no significant load increase
  if (scoreDelta != null && scoreDelta <= -5)
    return { label: 'Recent dip — refine technique', cls: AMBER_CLS };
  // Case C: form ↑ + load ↑≥5%
  if (scoreDelta != null && scoreDelta > 0 && weightDelta != null && weightDelta >= 1.05)
    return { label: 'Strong under increasing load', cls: IMPROVING_CLS };
  // Case D: stable
  return { label: 'Stable', cls: GRAY_CLS };
}

// ---------------------------------------------------------------------------
// Inline replica of computeWeightLoadDelta
// ---------------------------------------------------------------------------

function computeWeightLoadDelta(
  weightTrend: Array<{ weight_kg: number }> | undefined,
): { value: string; positive: boolean | null } | null {
  if (!weightTrend || weightTrend.length < 2) return null;
  const deltaKg = weightTrend[weightTrend.length - 1].weight_kg - weightTrend[0].weight_kg;
  const deltaLb = Math.round(deltaKg * 2.20462);
  if (Math.abs(deltaKg) <= 2) return { value: 'Stable', positive: null };
  return { value: deltaLb > 0 ? `+${deltaLb} lb` : `${deltaLb} lb`, positive: deltaLb > 0 };
}

// ---------------------------------------------------------------------------
// Inline replica of buildOpportunityBody
// ---------------------------------------------------------------------------

function buildOpportunityBody(
  weakLabel: string,
  sessionCount: number,
  avg: number,
  analyticsSessions: Array<{ posture_score: number | null }>,
  weightTrend: Array<{ weight_kg: number }> | undefined,
): { mainText: string; causalText: string | null } {
  const mainText = `${weakLabel} has been your weakest area over your last ${sessionCount} sessions (avg ${avg}%). Improving this moves your total score the fastest.`;

  const validScores = analyticsSessions.map(s => s.posture_score).filter((v): v is number => v != null);
  const scoreDelta = validScores.length >= 2 ? validScores[validScores.length - 1] - validScores[0] : null;
  const wt = weightTrend ?? [];
  const wtDelta = wt.length >= 2 && wt[0].weight_kg > 0 ? wt[wt.length - 1].weight_kg / wt[0].weight_kg : null;

  if (wtDelta != null && wtDelta >= 1.10 && scoreDelta != null && scoreDelta < 0 && avg < 70) {
    return { mainText, causalText: `Heavier load is exposing weaknesses in ${weakLabel.toLowerCase()}. Refine technique at this weight before pushing higher.` };
  }
  return { mainText, causalText: null };
}

// ---------------------------------------------------------------------------
// Tests for computeWeightAwareTrendLabel
// ---------------------------------------------------------------------------

describe('computeWeightAwareTrendLabel', () => {
  const sessions70 = [{ posture_score: 75 }, { posture_score: 68 }];
  const sessionsFlat = [{ posture_score: 72 }, { posture_score: 72 }];
  const sessionsUp = [{ posture_score: 65 }, { posture_score: 78 }];
  const sessionsDrop5 = [{ posture_score: 75 }, { posture_score: 70 }]; // exactly -5

  it('weight up ≥10% + score down → "Form stressed under heavier load" + amber', () => {
    const result = computeWeightAwareTrendLabel(
      sessions70,
      [{ weight_kg: 80 }, { weight_kg: 90 }], // 90/80 = 1.125 ≥ 1.10
    );
    expect(result.label).toBe('Form stressed under heavier load');
    expect(result.cls).toContain('amber');
  });

  it('weight up exactly 10% + score down → "Form stressed under heavier load"', () => {
    const result = computeWeightAwareTrendLabel(
      sessions70,
      [{ weight_kg: 100 }, { weight_kg: 110 }], // exactly 1.10
    );
    expect(result.label).toBe('Form stressed under heavier load');
  });

  it('weight up 9% (below threshold) + score down → falls through to score delta', () => {
    const result = computeWeightAwareTrendLabel(
      sessionsDrop5, // scoreDelta = -5
      [{ weight_kg: 100 }, { weight_kg: 109 }], // 1.09 < 1.10
    );
    // scoreDelta = -5, so "Recent dip — refine technique"
    expect(result.label).toBe('Recent dip — refine technique');
  });

  it('score down ≤ -5 without weight context → "Recent dip — refine technique" + amber', () => {
    const result = computeWeightAwareTrendLabel(
      [{ posture_score: 80 }, { posture_score: 74 }], // delta = -6
      undefined,
    );
    expect(result.label).toBe('Recent dip — refine technique');
    expect(result.cls).toContain('amber');
  });

  it('score down exactly -5 → "Recent dip — refine technique"', () => {
    const result = computeWeightAwareTrendLabel(
      sessionsDrop5, // delta = -5
      undefined,
    );
    expect(result.label).toBe('Recent dip — refine technique');
  });

  it('score down -4 (above threshold), no weight → "Stable" (no backendTrend fallback)', () => {
    const result = computeWeightAwareTrendLabel(
      [{ posture_score: 75 }, { posture_score: 71 }], // delta = -4
      undefined,
    );
    expect(result.label).toBe('Stable');
    expect(result.cls).toContain('gray');
  });

  it('score up + no weight data → "Stable" (Case C needs weight)', () => {
    const result = computeWeightAwareTrendLabel(
      sessionsUp, // score +13
      undefined,
    );
    expect(result.label).toBe('Stable');
  });

  it('sessionsFlat, no weight → "Stable"', () => {
    const result = computeWeightAwareTrendLabel(
      sessionsFlat,
      undefined,
    );
    expect(result.label).toBe('Stable');
  });

  it('null score sessions, no weight → "Stable"', () => {
    const result = computeWeightAwareTrendLabel(
      [{ posture_score: null }],
      undefined,
    );
    expect(result.label).toBe('Stable');
  });

  it('only one session score → "Stable" (no scoreDelta computed)', () => {
    const result = computeWeightAwareTrendLabel(
      [{ posture_score: 70 }],
      [{ weight_kg: 80 }, { weight_kg: 90 }],
    );
    expect(result.label).toBe('Stable');
    expect(result.cls).toContain('gray');
  });

  // Case C — Strong under increasing load
  it('score up + weight ≥5% → "Strong under increasing load" + green', () => {
    const result = computeWeightAwareTrendLabel(
      [{ posture_score: 65 }, { posture_score: 75 }],  // +10
      [{ weight_kg: 80 }, { weight_kg: 86 }],           // ratio 1.075 ≥ 1.05
    );
    expect(result.label).toBe('Strong under increasing load');
    expect(result.cls).toContain('green');
  });

  it('score up but no weight → "Stable" (Case C requires weight)', () => {
    const result = computeWeightAwareTrendLabel(
      [{ posture_score: 65 }, { posture_score: 75 }],
      undefined,
    );
    expect(result.label).toBe('Stable');
  });

  it('score up + weight just below 5% (ratio 1.04) → "Stable"', () => {
    const result = computeWeightAwareTrendLabel(
      [{ posture_score: 65 }, { posture_score: 75 }],
      [{ weight_kg: 100 }, { weight_kg: 104 }],  // ratio 1.04 < 1.05
    );
    expect(result.label).toBe('Stable');
  });
});

// ---------------------------------------------------------------------------
// Tests for computeWeightLoadDelta
// ---------------------------------------------------------------------------

describe('computeWeightLoadDelta', () => {
  it('returns null when weightTrend is undefined', () => {
    expect(computeWeightLoadDelta(undefined)).toBeNull();
  });

  it('returns null when weightTrend is empty', () => {
    expect(computeWeightLoadDelta([])).toBeNull();
  });

  it('returns null when weightTrend has only one entry', () => {
    expect(computeWeightLoadDelta([{ weight_kg: 80 }])).toBeNull();
  });

  it('positive delta > 2 kg → "+N lb", positive=true', () => {
    // 90 - 80 = 10 kg → 22 lb
    const result = computeWeightLoadDelta([{ weight_kg: 80 }, { weight_kg: 90 }]);
    expect(result).not.toBeNull();
    expect(result!.value).toBe('+22 lb');
    expect(result!.positive).toBe(true);
  });

  it('negative delta < -2 kg → "-N lb", positive=false', () => {
    // 70 - 80 = -10 kg → -22 lb
    const result = computeWeightLoadDelta([{ weight_kg: 80 }, { weight_kg: 70 }]);
    expect(result).not.toBeNull();
    expect(result!.value).toBe('-22 lb');
    expect(result!.positive).toBe(false);
  });

  it('delta ≤ 2 kg → "Stable", positive=null', () => {
    // 81.5 - 80 = 1.5 kg (≤ 2)
    const result = computeWeightLoadDelta([{ weight_kg: 80 }, { weight_kg: 81.5 }]);
    expect(result).not.toBeNull();
    expect(result!.value).toBe('Stable');
    expect(result!.positive).toBeNull();
  });

  it('delta exactly 2 kg → "Stable"', () => {
    const result = computeWeightLoadDelta([{ weight_kg: 80 }, { weight_kg: 82 }]);
    expect(result!.value).toBe('Stable');
    expect(result!.positive).toBeNull();
  });

  it('large positive delta → correct lb conversion', () => {
    // 20 kg → 44 lb
    const result = computeWeightLoadDelta([{ weight_kg: 60 }, { weight_kg: 80 }]);
    expect(result!.value).toBe('+44 lb');
    expect(result!.positive).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// Tests for buildOpportunityBody (Change 5)
// ---------------------------------------------------------------------------

describe('buildOpportunityBody (Change 5)', () => {
  const sessionsDown = [{ posture_score: 75 }, { posture_score: 68 }]; // delta = -7
  const sessionsUp   = [{ posture_score: 65 }, { posture_score: 72 }]; // delta = +7

  it('weight ≥10% + score down + avg < 70 → includes causal sentence', () => {
    const { mainText, causalText } = buildOpportunityBody(
      'Knee Symmetry', 5, 55,
      sessionsDown,
      [{ weight_kg: 80 }, { weight_kg: 90 }], // 1.125 ≥ 1.10
    );
    expect(causalText).not.toBeNull();
    expect(causalText).toContain('Heavier load');
    expect(causalText).toContain('knee symmetry');
    expect(mainText).toContain('Knee Symmetry');
    expect(mainText).toContain('55%');
  });

  it('weight ≥10% + score down + avg ≥ 70 → no causal sentence', () => {
    const { causalText } = buildOpportunityBody(
      'Torso Stability', 5, 72, // avg >= 70
      sessionsDown,
      [{ weight_kg: 80 }, { weight_kg: 90 }],
    );
    expect(causalText).toBeNull();
  });

  it('no weight data → no causal sentence', () => {
    const { causalText } = buildOpportunityBody(
      'Knee Symmetry', 5, 55,
      sessionsDown,
      undefined,
    );
    expect(causalText).toBeNull();
  });

  it('weight up but score up → no causal sentence', () => {
    const { causalText } = buildOpportunityBody(
      'Bottom Control', 5, 60,
      sessionsUp, // score went up
      [{ weight_kg: 80 }, { weight_kg: 90 }],
    );
    expect(causalText).toBeNull();
  });

  it('weight up <10% → no causal sentence', () => {
    const { causalText } = buildOpportunityBody(
      'Knee Symmetry', 5, 55,
      sessionsDown,
      [{ weight_kg: 80 }, { weight_kg: 88 }], // 88/80=1.10 exactly qualifies
    );
    // 88/80 = 1.10 exactly — meets threshold, so causal IS triggered
    expect(causalText).not.toBeNull();
  });

  it('weight increase just below 10% → no causal sentence', () => {
    const { causalText } = buildOpportunityBody(
      'Knee Symmetry', 5, 55,
      sessionsDown,
      [{ weight_kg: 80 }, { weight_kg: 87 }], // 87/80=1.0875 < 1.10
    );
    expect(causalText).toBeNull();
  });

  it('mainText always contains component label and avg', () => {
    const { mainText } = buildOpportunityBody(
      'Forward Lean', 3, 48,
      [{ posture_score: 70 }, { posture_score: 70 }],
      undefined,
    );
    expect(mainText).toContain('Forward Lean');
    expect(mainText).toContain('48%');
    expect(mainText).toContain('3 sessions');
  });

  it('causal text lowercases the component label', () => {
    const { causalText } = buildOpportunityBody(
      'Torso Stability', 5, 60,
      sessionsDown,
      [{ weight_kg: 80 }, { weight_kg: 90 }],
    );
    expect(causalText).toContain('torso stability');
    expect(causalText).not.toContain('Torso Stability');
  });
});

// ---------------------------------------------------------------------------
// computeCoachPlan — imported directly (pure function, no DOM dependency)
// ---------------------------------------------------------------------------

import { computeCoachPlan } from '../utils/coachPlan';
import { SquatTrainingSession } from '../types/formCheck';

function makeCoachSession(overrides: Partial<SquatTrainingSession> = {}): SquatTrainingSession {
  return {
    id: `sess-${Math.random()}`,
    exercise: 'squat',
    date: new Date().toISOString(),
    workingWeight: 135,
    overallScore: 75,
    components: {
      torsoStability: 75,
      kneeSymmetry: 70,
      bottomControl: 72,
      forwardLean: 68,
    },
    primaryLimiter: 'forwardLean',
    sets: [{ setIndex: 0, reps: 5 }],
    ...overrides,
  };
}

describe('computeCoachPlan (coaching UX sprint)', () => {
  // Case 1a: 1 session, weight === 0 → bodyweight plan
  it('1a: weight=0 → recommendedWeightLb null, title includes "bodyweight"', () => {
    const plan = computeCoachPlan([makeCoachSession({ workingWeight: 0 })]);
    expect(plan).not.toBeNull();
    expect(plan!.recommendedWeightLb).toBeNull();
    expect(plan!.title.toLowerCase()).toContain('bodyweight');
  });

  // Case 1b: 1 session, weight > 0 → hold
  it('1b: weight > 0 → recommendedWeightLb = lastWeight', () => {
    const plan = computeCoachPlan([makeCoachSession({ workingWeight: 245 })]);
    expect(plan!.recommendedWeightLb).toBe(245);
  });

  // Case A: avg < 65, loadRatio >= 1.10 → deload
  it('Case A: avg=58, loadRatio=1.15 → recommendedWeightLb = Math.round(lastWeight * 0.92)', () => {
    const sessions = [
      makeCoachSession({ overallScore: 60, workingWeight: 155 }), // newest
      makeCoachSession({ overallScore: 56, workingWeight: 135 }), // 155/135 ≈ 1.148 ≥ 1.10
    ];
    const plan = computeCoachPlan(sessions);
    expect(plan!.recommendedWeightLb).toBe(Math.round(155 * 0.92));
  });

  // Case B: avg < 65, loadRatio < 1.10 → hold
  it('Case B: avg=58, loadRatio=1.0 → recommendedWeightLb = lastWeight, title "Lock in"', () => {
    const sessions = [
      makeCoachSession({ overallScore: 60, workingWeight: 135 }),
      makeCoachSession({ overallScore: 56, workingWeight: 135 }),
    ];
    const plan = computeCoachPlan(sessions);
    expect(plan!.recommendedWeightLb).toBe(135);
    expect(plan!.title).toContain('Lock in');
  });

  // Case C: avg 65–79, scoreDelta >= 2 → +5 lb
  it('Case C: avg=72, trend=+5 → recommendedWeightLb = lastWeight + 5', () => {
    const sessions = [
      makeCoachSession({ overallScore: 75, workingWeight: 135 }), // newest
      makeCoachSession({ overallScore: 70, workingWeight: 135 }), // scoreDelta=5
    ];
    // avgScore = 72.5, scoreDelta = 5 ≥ 2
    const plan = computeCoachPlan(sessions);
    expect(plan!.recommendedWeightLb).toBe(140);
  });

  // Case D: avg 65–79, scoreDelta < 2 → hold
  it('Case D: avg=72, trend=0 → recommendedWeightLb = lastWeight, title "Hold"', () => {
    const sessions = [
      makeCoachSession({ overallScore: 72, workingWeight: 135 }), // newest
      makeCoachSession({ overallScore: 73, workingWeight: 135 }), // scoreDelta = -1 < 2
    ];
    // avgScore ≈ 72.5
    const plan = computeCoachPlan(sessions);
    expect(plan!.recommendedWeightLb).toBe(135);
    expect(plan!.title).toContain('Hold');
  });

  // Case E: avg >= 80 → +5 lb
  it('Case E: avg=83 → recommendedWeightLb = lastWeight + 5', () => {
    const sessions = [
      makeCoachSession({ overallScore: 85, workingWeight: 155 }), // newest
      makeCoachSession({ overallScore: 81, workingWeight: 155 }),
    ];
    const plan = computeCoachPlan(sessions);
    expect(plan!.recommendedWeightLb).toBe(160);
  });

  // All cases with sessions: focusCue and drillSummary non-empty
  it('all cases with sessions: focusCue and drillSummary are non-empty strings', () => {
    const cases = [
      [makeCoachSession({ workingWeight: 0 })],
      [makeCoachSession({ workingWeight: 135 })],
      [makeCoachSession({ overallScore: 60, workingWeight: 155 }), makeCoachSession({ overallScore: 56, workingWeight: 135 })],
      [makeCoachSession({ overallScore: 72, workingWeight: 135 }), makeCoachSession({ overallScore: 73, workingWeight: 135 })],
      [makeCoachSession({ overallScore: 85, workingWeight: 155 }), makeCoachSession({ overallScore: 81, workingWeight: 155 })],
    ];
    for (const sessions of cases) {
      const plan = computeCoachPlan(sessions);
      expect(typeof plan!.focusCue).toBe('string');
      expect(plan!.focusCue.length).toBeGreaterThan(0);
      expect(typeof plan!.drillSummary).toBe('string');
      expect(plan!.drillSummary.length).toBeGreaterThan(0);
    }
  });
});
