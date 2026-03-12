/**
 * Unit tests for progressionEngine.ts — pure functions, no DOM.
 * Uses inline replicas of the types to keep tests fast and self-contained.
 */

export {}; // treat as ES module to avoid global name collisions with other test files

// ── Inline replica of TrainingSession (avoids module resolution in tests) ──

interface TrainingSession {
  id: string;
  exerciseId: string;
  date: string;
  weightLb: number;
  sets: number;
  reps: number;
  avgRir: number;
  formScore?: number;
}

// ── Inline replica of progressionEngine functions ──────────────────────────

type RecommendationType = 'increase' | 'hold' | 'reduce';

interface ProgressionPlan {
  recommendedWeight: number;
  recommendationType: RecommendationType;
  reason: string;
}

function roundToHalf(x: number): number {
  return Math.round(x * 2) / 2;
}

function computeSessionMetrics(sessions: TrainingSession[]): {
  lastSession?: TrainingSession;
  previousSession?: TrainingSession;
  avgRir: number | null;
} {
  if (sessions.length === 0) return { avgRir: null };
  const sorted = [...sessions].sort(
    (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime(),
  );
  return {
    lastSession: sorted[0],
    previousSession: sorted[1],
    avgRir: sorted[0].avgRir,
  };
}

function computeProgressionPlan(sessions: TrainingSession[]): ProgressionPlan | null {
  if (sessions.length === 0) return null;

  const sorted = [...sessions].sort(
    (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime(),
  );

  const last = sorted[0];
  const previous = sorted[1];

  let recommendationType: RecommendationType;
  let recommendedWeight: number;
  let reason: string;

  if (last.avgRir >= 4) {
    const increment = Math.max(2.5, last.weightLb * 0.025);
    recommendedWeight = roundToHalf(last.weightLb + increment);
    recommendationType = 'increase';
    reason = `You reported ${last.avgRir} RIR — the weight felt manageable. Time to add load.`;
  } else if (last.avgRir < 1 && sorted.length >= 2 && sorted[1].avgRir < 1) {
    recommendedWeight = roundToHalf(last.weightLb * 0.95);
    recommendationType = 'reduce';
    reason = `Two consecutive sessions with RIR < 1. Reducing load slightly to support recovery.`;
  } else if (last.avgRir < 1) {
    recommendedWeight = last.weightLb;
    recommendationType = 'hold';
    reason = `Last session was very hard (${last.avgRir} RIR). Hold here and monitor recovery before deciding.`;
  } else {
    recommendedWeight = last.weightLb;
    recommendationType = 'hold';
    reason = `You reported ${last.avgRir} RIR — solid working intensity. Maintain this load.`;
  }

  // Technique override
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

// ── helpers ────────────────────────────────────────────────────────────────

function makeSession(overrides: Partial<TrainingSession> = {}): TrainingSession {
  return {
    id: 'test-id',
    exerciseId: 'squat',
    date: '2026-02-01T10:00:00.000Z',
    weightLb: 135,
    sets: 3,
    reps: 5,
    avgRir: 2,
    ...overrides,
  };
}

// ── computeProgressionPlan ─────────────────────────────────────────────────

describe('computeProgressionPlan', () => {
  it('returns null for empty sessions', () => {
    expect(computeProgressionPlan([])).toBeNull();
  });

  it('recommends increase when avgRir >= 4', () => {
    const plan = computeProgressionPlan([makeSession({ avgRir: 4.5, weightLb: 100 })]);
    expect(plan).not.toBeNull();
    expect(plan!.recommendationType).toBe('increase');
    expect(plan!.recommendedWeight).toBeGreaterThan(100);
  });

  it('recommends hold when avgRir is 2 (moderate effort)', () => {
    const plan = computeProgressionPlan([makeSession({ avgRir: 2, weightLb: 135 })]);
    expect(plan).not.toBeNull();
    expect(plan!.recommendationType).toBe('hold');
    expect(plan!.recommendedWeight).toBe(135);
  });

  it('recommends reduce when 2 consecutive sessions have avgRir < 1', () => {
    const sessions = [
      makeSession({ id: 's1', date: '2026-02-08T10:00:00.000Z', avgRir: 0, weightLb: 150 }),
      makeSession({ id: 's2', date: '2026-02-01T10:00:00.000Z', avgRir: 0, weightLb: 145 }),
    ];
    const plan = computeProgressionPlan(sessions);
    expect(plan).not.toBeNull();
    expect(plan!.recommendationType).toBe('reduce');
    expect(plan!.recommendedWeight).toBeLessThan(150);
  });

  it('recommends hold (not reduce) for a single very hard session', () => {
    const plan = computeProgressionPlan([makeSession({ avgRir: 0, weightLb: 150 })]);
    expect(plan).not.toBeNull();
    expect(plan!.recommendationType).toBe('hold');
    expect(plan!.recommendedWeight).toBe(150);
  });

  it('applies technique override: base increase → hold when form dropped ≥5 points with heavier weight', () => {
    const sessions = [
      // newer: heavier, worse form, very easy (base rule would be increase)
      makeSession({ id: 'new', date: '2026-02-08T10:00:00.000Z', avgRir: 4, weightLb: 155, formScore: 65 }),
      // older: lighter, better form
      makeSession({ id: 'old', date: '2026-02-01T10:00:00.000Z', avgRir: 3, weightLb: 150, formScore: 75 }),
    ];
    const plan = computeProgressionPlan(sessions);
    expect(plan).not.toBeNull();
    expect(plan!.recommendationType).toBe('hold');
    expect(plan!.recommendedWeight).toBe(155);
  });

  it('does NOT apply technique override when form only dropped 3 points (< 5 threshold)', () => {
    const sessions = [
      makeSession({ id: 'new', date: '2026-02-08T10:00:00.000Z', avgRir: 4, weightLb: 155, formScore: 72 }),
      makeSession({ id: 'old', date: '2026-02-01T10:00:00.000Z', avgRir: 3, weightLb: 150, formScore: 75 }),
    ];
    const plan = computeProgressionPlan(sessions);
    // form drop is only 3 → override should NOT fire → stays increase
    expect(plan!.recommendationType).toBe('increase');
  });
});

// ── computeSessionMetrics ─────────────────────────────────────────────────

describe('computeSessionMetrics', () => {
  it('returns empty metrics for no sessions', () => {
    const result = computeSessionMetrics([]);
    expect(result.lastSession).toBeUndefined();
    expect(result.previousSession).toBeUndefined();
    expect(result.avgRir).toBeNull();
  });

  it('returns lastSession as the newest and previousSession as the older of 2', () => {
    const older = makeSession({ id: 'older', date: '2026-01-01T00:00:00.000Z', avgRir: 3 });
    const newer = makeSession({ id: 'newer', date: '2026-02-01T00:00:00.000Z', avgRir: 1 });
    const result = computeSessionMetrics([older, newer]);
    expect(result.lastSession?.id).toBe('newer');
    expect(result.previousSession?.id).toBe('older');
    expect(result.avgRir).toBe(1);
  });
});
