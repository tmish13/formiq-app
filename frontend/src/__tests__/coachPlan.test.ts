/**
 * Unit tests for coachPlan.ts utility.
 * Tests use inline session construction — no DOM dependency.
 */

import { computeCoachPlan } from '../utils/coachPlan';
import { SquatTrainingSession } from '../types/formCheck';

function makeSession(overrides: Partial<SquatTrainingSession> = {}): SquatTrainingSession {
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

describe('computeCoachPlan', () => {
  it('returns null for 0 sessions', () => {
    expect(computeCoachPlan([])).toBeNull();
  });

  it('1 session, weight === 0: "Start with bodyweight fundamentals"', () => {
    const plan = computeCoachPlan([makeSession({ overallScore: 78, workingWeight: 0 })]);
    expect(plan).not.toBeNull();
    expect(plan!.title).toBe('Start with bodyweight fundamentals');
    expect(plan!.recommendedWeightLb).toBeNull();
  });

  it('1 session, weight === 0: bullets mention bodyweight squats', () => {
    const plan = computeCoachPlan([makeSession({ workingWeight: 0 })]);
    expect(plan!.bullets[0]).toContain('bodyweight squats');
  });

  it('1 session, weight > 0: "Hold and refine"', () => {
    const plan = computeCoachPlan([makeSession({ overallScore: 78, workingWeight: 135 })]);
    expect(plan).not.toBeNull();
    expect(plan!.title).toBe('Hold and refine');
  });

  it('1 session, weight > 0: recommendedWeightLb === workingWeight', () => {
    const plan = computeCoachPlan([makeSession({ overallScore: 78, workingWeight: 100 })]);
    expect(plan!.recommendedWeightLb).toBe(100);
  });

  it('avgScore < 65, loadRatio >= 1.10: "Deload and reset technique"', () => {
    const sessions = [
      makeSession({ overallScore: 60, workingWeight: 150 }),  // newest — 10% heavier
      makeSession({ overallScore: 58, workingWeight: 135 }),  // 150/135 = 1.11 ≥ 1.10
    ];
    const plan = computeCoachPlan(sessions);
    expect(plan!.title).toBe('Deload and reset technique');
    expect(plan!.recommendedWeightLb).toBe(Math.round(150 * 0.92));
  });

  it('avgScore < 65, loadRatio < 1.10: "Lock in technique before adding weight"', () => {
    const sessions = [
      makeSession({ overallScore: 60, workingWeight: 135 }),
      makeSession({ overallScore: 62, workingWeight: 135 }),
    ];
    const plan = computeCoachPlan(sessions);
    expect(plan!.title).toBe('Lock in technique before adding weight');
    expect(plan!.recommendedWeightLb).toBe(135);
  });

  it('avgScore 65–79, scoreDelta >= 2: "Controlled progression", +5 lb', () => {
    // Sessions are ordered newest-first: recent[0] is newest
    const sessions = [
      makeSession({ overallScore: 78, workingWeight: 135 }), // newest
      makeSession({ overallScore: 72, workingWeight: 135 }), // oldest
    ];
    // avgScore = (78+72)/2 = 75, scoreDelta = 78-72 = 6 >= 2
    const plan = computeCoachPlan(sessions);
    expect(plan!.title).toBe('Controlled progression');
    expect(plan!.recommendedWeightLb).toBe(140);
  });

  it('avgScore 65–79, scoreDelta < 2: "Hold and refine"', () => {
    const sessions = [
      makeSession({ overallScore: 74, workingWeight: 135 }), // newest
      makeSession({ overallScore: 75, workingWeight: 135 }), // oldest
    ];
    // avgScore ≈ 74.5, scoreDelta = 74-75 = -1 < 2
    const plan = computeCoachPlan(sessions);
    expect(plan!.title).toBe('Hold and refine');
    expect(plan!.recommendedWeightLb).toBe(135);
  });

  it('avgScore > 80: "Ready to push", +5 lb', () => {
    const sessions = [
      makeSession({ overallScore: 85, workingWeight: 155 }), // newest
      makeSession({ overallScore: 83, workingWeight: 155 }), // oldest
    ];
    const plan = computeCoachPlan(sessions);
    expect(plan!.title).toBe('Ready to push');
    expect(plan!.recommendedWeightLb).toBe(160);
  });

  it('all plans include sets=3 and reps=5', () => {
    const sessions = [makeSession(), makeSession()];
    const plan = computeCoachPlan(sessions);
    expect(plan!.sets).toBe(3);
    expect(plan!.reps).toBe(5);
  });

  it('focusCue is a non-empty string', () => {
    const plan = computeCoachPlan([makeSession(), makeSession()]);
    expect(typeof plan!.focusCue).toBe('string');
    expect(plan!.focusCue.length).toBeGreaterThan(0);
  });

  it('drillSummary is a non-empty string', () => {
    const plan = computeCoachPlan([makeSession(), makeSession()]);
    expect(typeof plan!.drillSummary).toBe('string');
    expect(plan!.drillSummary.length).toBeGreaterThan(0);
  });

  it('bullets is a non-empty array', () => {
    const sessions = [makeSession(), makeSession()];
    const plan = computeCoachPlan(sessions);
    expect(Array.isArray(plan!.bullets)).toBe(true);
    expect(plan!.bullets.length).toBeGreaterThan(0);
  });

  it('2+ case bullets[1] contains focusCue', () => {
    const sessions = [makeSession(), makeSession()];
    const plan = computeCoachPlan(sessions);
    expect(plan!.bullets[1]).toContain('Focus:');
  });

  it('2+ case bullets[2] contains drillSummary', () => {
    const sessions = [makeSession(), makeSession()];
    const plan = computeCoachPlan(sessions);
    expect(plan!.bullets[2]).toContain('Drill before work sets:');
  });

  it('deload: recommendedWeightLb is ~8% less than lastWeight', () => {
    const sessions = [
      makeSession({ overallScore: 55, workingWeight: 200 }),
      makeSession({ overallScore: 58, workingWeight: 180 }), // 200/180=1.11 ≥ 1.10
    ];
    const plan = computeCoachPlan(sessions);
    expect(plan!.title).toBe('Deload and reset technique');
    expect(plan!.recommendedWeightLb).toBe(Math.round(200 * 0.92)); // 184
  });

  it('0 lb guard: recent session weight=0 but history has 245 lb → recommendedWeightLb > 0', () => {
    // avg=73.5 (Case C: 65-79, +scoreDelta), so base=245 + 5 = 250
    const sessions = [
      makeSession({ overallScore: 75, workingWeight: 0 }),    // most recent: no weight logged
      makeSession({ overallScore: 72, workingWeight: 245 }),  // prior session: real weight used as base
    ];
    const plan = computeCoachPlan(sessions);
    expect(plan).not.toBeNull();
    // Must not be 0 or 5 (which would happen if guard didn't apply)
    expect(plan!.recommendedWeightLb).toBeGreaterThan(0);
    expect(plan!.recommendedWeightLb).toBe(250);  // 245 (last non-zero) + 5 (Case C)
  });

  it('0 lb guard: all 2+ sessions have weight=0 → hold at 0 (genuinely bodyweight, Case D)', () => {
    // Use scores that trigger Case D (hold): avg 65-79 but scoreDelta < 2
    const sessions = [
      makeSession({ overallScore: 74, workingWeight: 0 }), // newest, scoreDelta = 74-75 = -1 < 2
      makeSession({ overallScore: 75, workingWeight: 0 }),
    ];
    const plan = computeCoachPlan(sessions);
    // Case D: hold → recommendedWeightLb = lastWeight = 0 (genuinely all bodyweight)
    expect(plan!.title).toBe('Hold and refine');
    expect(plan!.recommendedWeightLb).toBe(0);
  });

  // context param tests
  it('1 session, weight=0, no context → Case 1a bodyweight plan', () => {
    const plan = computeCoachPlan([makeSession({ workingWeight: 0 })]);
    expect(plan!.title).toBe('Start with bodyweight fundamentals');
    expect(plan!.recommendedWeightLb).toBeNull();
  });

  it('1 session, weight=0, context.bestWeightLb=245 → "Hold and refine" at 245 lb', () => {
    const plan = computeCoachPlan(
      [makeSession({ workingWeight: 0 })],
      { bestWeightLb: 245 },
    );
    expect(plan!.title).toBe('Hold and refine');
    expect(plan!.recommendedWeightLb).toBe(245);
  });

  it('1 session, weight=0, context.avgLast5WeightLb=200 (no bestWeight) → recommendedWeightLb=200', () => {
    const plan = computeCoachPlan(
      [makeSession({ workingWeight: 0 })],
      { avgLast5WeightLb: 200 },
    );
    expect(plan!.title).toBe('Hold and refine');
    expect(plan!.recommendedWeightLb).toBe(200);
  });
});
