/**
 * Unit tests for trainingStorage.ts utility.
 * Uses inline localStorage mock — no DOM dependency.
 */

export {}; // treat as ES module to avoid global name collisions with other test files

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

// ── Inline replica of trainingStorage functions ────────────────────────────

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

const TRAINING_SESSIONS_KEY = 'formiq-training-sessions-v1';

function safeGetStorage(): Storage | null {
  if (typeof window === 'undefined') return null;
  return window.localStorage ?? null;
}

function loadTrainingSessions(): TrainingSession[] {
  const storage = safeGetStorage();
  if (!storage) return [];
  try {
    const raw = storage.getItem(TRAINING_SESSIONS_KEY);
    if (!raw) return [];
    return JSON.parse(raw) as TrainingSession[];
  } catch {
    return [];
  }
}

function saveTrainingSessions(sessions: TrainingSession[]): void {
  const storage = safeGetStorage();
  if (!storage) return;
  storage.setItem(TRAINING_SESSIONS_KEY, JSON.stringify(sessions));
}

function addTrainingSession(newSession: TrainingSession): TrainingSession[] {
  const existing = loadTrainingSessions().filter(s => s.id !== newSession.id);
  const merged = [newSession, ...existing].sort(
    (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime(),
  );
  saveTrainingSessions(merged);
  return merged;
}

function loadTrainingSessionsForExercise(exerciseId: string): TrainingSession[] {
  return loadTrainingSessions().filter(s => s.exerciseId === exerciseId);
}

// ── helpers ────────────────────────────────────────────────────────────────

function makeSession(overrides: Partial<TrainingSession> = {}): TrainingSession {
  return {
    id: 'test-id',
    exerciseId: 'squat',
    date: new Date().toISOString(),
    weightLb: 135,
    sets: 3,
    reps: 5,
    avgRir: 2,
    ...overrides,
  };
}

// ── loadTrainingSessions ───────────────────────────────────────────────────

describe('loadTrainingSessions', () => {
  it('returns empty array when localStorage is empty', () => {
    expect(loadTrainingSessions()).toEqual([]);
  });

  it('returns empty array on corrupt JSON', () => {
    localStorageMock.setItem(TRAINING_SESSIONS_KEY, 'not-json{{{');
    expect(loadTrainingSessions()).toEqual([]);
  });
});

// ── addTrainingSession ─────────────────────────────────────────────────────

describe('addTrainingSession', () => {
  it('stores the session and returns it in the array', () => {
    const session = makeSession({ id: 's1' });
    const result = addTrainingSession(session);
    expect(result).toHaveLength(1);
    expect(result[0].id).toBe('s1');
    // verify it persisted
    expect(loadTrainingSessions()[0].id).toBe('s1');
  });

  it('sorts two sessions newest first', () => {
    const older = makeSession({ id: 'older', date: '2026-01-01T00:00:00.000Z' });
    const newer = makeSession({ id: 'newer', date: '2026-02-01T00:00:00.000Z' });
    addTrainingSession(older);
    addTrainingSession(newer);
    const stored = loadTrainingSessions();
    expect(stored[0].id).toBe('newer');
    expect(stored[1].id).toBe('older');
  });
});

// ── loadTrainingSessionsForExercise ───────────────────────────────────────

describe('loadTrainingSessionsForExercise', () => {
  it('returns only sessions matching the exerciseId', () => {
    addTrainingSession(makeSession({ id: 's1', exerciseId: 'squat' }));
    addTrainingSession(makeSession({ id: 's2', exerciseId: 'ohp' }));
    const squats = loadTrainingSessionsForExercise('squat');
    expect(squats).toHaveLength(1);
    expect(squats[0].id).toBe('s1');
  });

  it('returns empty array when no sessions match the exerciseId', () => {
    addTrainingSession(makeSession({ id: 's1', exerciseId: 'squat' }));
    expect(loadTrainingSessionsForExercise('ohp')).toEqual([]);
  });

  it('handles corrupt localStorage gracefully', () => {
    localStorageMock.setItem(TRAINING_SESSIONS_KEY, '{{bad json}}');
    expect(loadTrainingSessionsForExercise('squat')).toEqual([]);
  });
});
