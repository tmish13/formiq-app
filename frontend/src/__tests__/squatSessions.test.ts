/**
 * Unit tests for squatSessions.ts utility.
 * Uses inline localStorage mock — no DOM dependency.
 */

import {
  getPrimaryLimiterFromComponents,
  computeSessionFromAnalysis,
  loadSquatSessions,
  saveSquatSessions,
  addSquatSession,
  getBiggestOpportunityFromSessions,
} from '../utils/squatSessions';
import { MLAnalysisResponse, SquatTrainingSession } from '../types/formCheck';

// ── localStorage mock ──────────────────────────────────────────────────────

const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => { store[key] = value; },
    removeItem: (key: string) => { delete store[key]; },
    clear: () => { store = {}; },
  };
})();

Object.defineProperty(globalThis, 'localStorage', { value: localStorageMock, writable: true });
Object.defineProperty(globalThis, 'window', { value: { localStorage: localStorageMock }, writable: true });

beforeEach(() => localStorageMock.clear());

// ── helpers ────────────────────────────────────────────────────────────────

function makeComponents(
  torsoStability: number,
  kneeSymmetry: number,
  bottomControl: number,
  forwardLean: number,
): SquatTrainingSession['components'] {
  return { torsoStability, kneeSymmetry, bottomControl, forwardLean };
}

function makeSession(overrides: Partial<SquatTrainingSession> = {}): SquatTrainingSession {
  return {
    id: 'test-id',
    exercise: 'squat',
    date: new Date().toISOString(),
    workingWeight: 100,
    overallScore: 75,
    components: makeComponents(80, 70, 75, 65),
    primaryLimiter: 'forwardLean',
    sets: [{ setIndex: 0, reps: 5 }],
    ...overrides,
  };
}

function makeMlAnalysis(
  torsoStability: number | null,
  kneeSymmetry: number | null,
  bottomControl: number | null,
  forwardLean: number | null,
  postureScore = 75,
): MLAnalysisResponse {
  return {
    ml_scores: { posture_score: postureScore, stability_score: null, depth_score: null, confidence: null },
    posture_v1: {
      decision: 'fault',
      prob_fault: 0.6,
      confidence: 0.8,
      posture_score: postureScore,
      component_scores: { trunk_control: null, knee_stability: null, hip_drive: null },
      named_scores: { torso_stability_score: torsoStability, knee_symmetry_score: kneeSymmetry, bottom_control_score: bottomControl, forward_lean_score: forwardLean },
      top_signals: [],
      quality: { quality_flags: [], quality_ok: true },
      model: { name: 'posture_v1', version: '1.0', threshold: 0.5 },
      preprocessing: { original_frames: 100, valid_frames: 90, sequence_length: 90 },
    },
    detected_issues: [],
    decision: 'fault',
    confidence: 0.8,
    named_scores: { torso_stability_score: torsoStability, knee_symmetry_score: kneeSymmetry, bottom_control_score: bottomControl, forward_lean_score: forwardLean },
    component_scores: { trunk_control: null, knee_stability: null, hip_drive: null },
    top_signals: [],
  };
}

// ── getPrimaryLimiterFromComponents ───────────────────────────────────────

describe('getPrimaryLimiterFromComponents', () => {
  it('returns the key with the lowest score', () => {
    const result = getPrimaryLimiterFromComponents(makeComponents(80, 50, 70, 65));
    expect(result).toBe('kneeSymmetry');
  });

  it('breaks ties by deterministic order (torsoStability first)', () => {
    // All equal — torsoStability comes first in order
    const result = getPrimaryLimiterFromComponents(makeComponents(60, 60, 60, 60));
    expect(result).toBe('torsoStability');
  });

  it('returns null when all scores are 0 but defined (lowest wins, which is torsoStability)', () => {
    // All 0 is still a valid tie → torsoStability wins
    const result = getPrimaryLimiterFromComponents(makeComponents(0, 0, 0, 0));
    expect(result).toBe('torsoStability');
  });

  it('returns forwardLean when it is uniquely lowest', () => {
    const result = getPrimaryLimiterFromComponents(makeComponents(80, 75, 70, 40));
    expect(result).toBe('forwardLean');
  });

  it('returns bottomControl when it is uniquely lowest', () => {
    const result = getPrimaryLimiterFromComponents(makeComponents(80, 75, 30, 60));
    expect(result).toBe('bottomControl');
  });
});

// ── computeSessionFromAnalysis ─────────────────────────────────────────────

describe('computeSessionFromAnalysis', () => {
  it('maps named_scores to components correctly', () => {
    const analysis = makeMlAnalysis(80, 65, 70, 55, 72);
    const session = computeSessionFromAnalysis(analysis, 135, [{ reps: 5 }]);
    expect(session.components.torsoStability).toBe(80);
    expect(session.components.kneeSymmetry).toBe(65);
    expect(session.components.bottomControl).toBe(70);
    expect(session.components.forwardLean).toBe(55);
  });

  it('defaults null components to 0', () => {
    const analysis = makeMlAnalysis(null, null, 60, null, 70);
    const session = computeSessionFromAnalysis(analysis, 100, [{ reps: 3 }]);
    expect(session.components.torsoStability).toBe(0);
    expect(session.components.kneeSymmetry).toBe(0);
    expect(session.components.forwardLean).toBe(0);
    expect(session.components.bottomControl).toBe(60);
  });

  it('passes sets through correctly', () => {
    const analysis = makeMlAnalysis(80, 70, 75, 65);
    const session = computeSessionFromAnalysis(analysis, 100, [{ reps: 3 }, { reps: 4 }, { reps: 5 }]);
    expect(session.sets).toHaveLength(3);
    expect(session.sets[0].reps).toBe(3);
    expect(session.sets[2].reps).toBe(5);
  });

  it('sets overallScore from posture_v1.posture_score', () => {
    const analysis = makeMlAnalysis(80, 70, 75, 65, 83);
    const session = computeSessionFromAnalysis(analysis, 100, [{ reps: 5 }]);
    expect(session.overallScore).toBe(83);
  });

  it('uses provided id override', () => {
    const analysis = makeMlAnalysis(80, 70, 75, 65);
    const session = computeSessionFromAnalysis(analysis, 100, [{ reps: 5 }], { id: 'custom-id' });
    expect(session.id).toBe('custom-id');
  });

  it('sets exercise to squat', () => {
    const analysis = makeMlAnalysis(80, 70, 75, 65);
    const session = computeSessionFromAnalysis(analysis, 100, [{ reps: 5 }]);
    expect(session.exercise).toBe('squat');
  });
});

// ── loadSquatSessions ──────────────────────────────────────────────────────

describe('loadSquatSessions', () => {
  it('returns empty array when localStorage is empty', () => {
    expect(loadSquatSessions()).toEqual([]);
  });

  it('returns empty array on corrupt JSON', () => {
    localStorageMock.setItem('formiq-squat-sessions-v1', 'not-json{{{');
    expect(loadSquatSessions()).toEqual([]);
  });

  it('returns parsed sessions for valid data', () => {
    const sessions = [makeSession({ id: 's1' }), makeSession({ id: 's2' })];
    localStorageMock.setItem('formiq-squat-sessions-v1', JSON.stringify(sessions));
    const loaded = loadSquatSessions();
    expect(loaded).toHaveLength(2);
    expect(loaded[0].id).toBe('s1');
  });
});

// ── addSquatSession ────────────────────────────────────────────────────────

describe('addSquatSession', () => {
  it('persists the session to localStorage', () => {
    const session = makeSession({ id: 'new-session' });
    addSquatSession(session);
    const stored = loadSquatSessions();
    expect(stored.some(s => s.id === 'new-session')).toBe(true);
  });

  it('sorts sessions by date descending', () => {
    const older = makeSession({ id: 'older', date: '2025-01-01T00:00:00.000Z' });
    const newer = makeSession({ id: 'newer', date: '2025-06-01T00:00:00.000Z' });
    addSquatSession(older);
    addSquatSession(newer);
    const stored = loadSquatSessions();
    expect(stored[0].id).toBe('newer');
    expect(stored[1].id).toBe('older');
  });

  it('replaces an existing session with the same id', () => {
    const session = makeSession({ id: 'dup', overallScore: 70 });
    addSquatSession(session);
    const updated = makeSession({ id: 'dup', overallScore: 85 });
    addSquatSession(updated);
    const stored = loadSquatSessions();
    expect(stored.filter(s => s.id === 'dup')).toHaveLength(1);
    expect(stored.find(s => s.id === 'dup')?.overallScore).toBe(85);
  });
});

// ── getBiggestOpportunityFromSessions ─────────────────────────────────────

describe('getBiggestOpportunityFromSessions', () => {
  it('returns null for 0 sessions', () => {
    expect(getBiggestOpportunityFromSessions([])).toBeNull();
  });

  it('returns the component with the lowest average across sessions', () => {
    const sessions = [
      makeSession({ id: '1', components: makeComponents(80, 40, 70, 65) }),
      makeSession({ id: '2', components: makeComponents(75, 45, 68, 60) }),
      makeSession({ id: '3', components: makeComponents(78, 42, 72, 63) }),
    ];
    const result = getBiggestOpportunityFromSessions(sessions);
    expect(result?.componentKey).toBe('kneeSymmetry');
    expect(result?.avgScore).toBe(Math.round((40 + 45 + 42) / 3));
  });

  it('handles single session correctly', () => {
    const sessions = [makeSession({ id: '1', components: makeComponents(80, 30, 70, 65) })];
    const result = getBiggestOpportunityFromSessions(sessions);
    expect(result?.componentKey).toBe('kneeSymmetry');
  });

  it('respects windowSize parameter', () => {
    // 5 sessions but windowSize=2 → only looks at first 2
    const sessions = [
      makeSession({ id: '1', components: makeComponents(80, 90, 20, 70) }), // bottomControl=20
      makeSession({ id: '2', components: makeComponents(80, 90, 25, 70) }), // bottomControl=25
      makeSession({ id: '3', components: makeComponents(10, 90, 80, 70) }), // torsoStability=10 but outside window
      makeSession({ id: '4', components: makeComponents(10, 90, 80, 70) }),
      makeSession({ id: '5', components: makeComponents(10, 90, 80, 70) }),
    ];
    const result = getBiggestOpportunityFromSessions(sessions, 2);
    expect(result?.componentKey).toBe('bottomControl');
  });
});
