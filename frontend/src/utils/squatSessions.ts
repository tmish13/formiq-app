// FUTURE EXTENSIBILITY:
// ExerciseId will expand to 'squat' | 'ohp' | 'barbell_row'.
// SquatTrainingSession will generalize to TrainingSession<TComponents>.
// getBiggestOpportunityFromSessions can be parameterized by exercise component map.

import { MLAnalysisResponse, SquatTrainingSession, SquatTrainingSet } from '../types/formCheck';

const STORAGE_KEY = 'formiq-squat-sessions-v1';

// Deterministic component key order for tie-breaking
const COMPONENT_KEYS: Array<keyof SquatTrainingSession['components']> = [
  'torsoStability',
  'kneeSymmetry',
  'bottomControl',
  'forwardLean',
];

function safeGetStorage(): Storage | null {
  if (typeof window === 'undefined') return null;
  return window.localStorage ?? null;
}

/**
 * Returns the component key with the lowest score.
 * Tie-break: deterministic order (torsoStability → kneeSymmetry → bottomControl → forwardLean).
 * Returns null if no component scores are defined (all undefined/null).
 */
export function getPrimaryLimiterFromComponents(
  components: SquatTrainingSession['components'],
): string | null {
  let minKey: string | null = null;
  let minScore = Infinity;

  for (const key of COMPONENT_KEYS) {
    const score = components[key];
    if (score != null && score < minScore) {
      minScore = score;
      minKey = key;
    }
  }

  return minKey;
}

/**
 * Builds a SquatTrainingSession from an MLAnalysisResponse.
 * Falls back to 0 for null component scores.
 * Uses crypto.randomUUID() when available, otherwise Date.now().toString().
 */
export function computeSessionFromAnalysis(
  analysis: MLAnalysisResponse,
  workingWeightLb: number,
  sets: Array<{ reps: number }>,
  overrides?: Partial<Pick<SquatTrainingSession, 'id' | 'date' | 'notes'>>,
): SquatTrainingSession {
  const ns = analysis.named_scores;
  const components: SquatTrainingSession['components'] = {
    torsoStability: ns?.torso_stability_score ?? 0,
    kneeSymmetry: ns?.knee_symmetry_score ?? 0,
    bottomControl: ns?.bottom_control_score ?? 0,
    forwardLean: ns?.forward_lean_score ?? 0,
  };

  const primaryLimiter = getPrimaryLimiterFromComponents(components) ?? 'torsoStability';

  const id =
    overrides?.id ??
    (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
      ? crypto.randomUUID()
      : Date.now().toString());

  const overallScore = analysis.posture_v1?.posture_score ?? 0;

  const squatSets: SquatTrainingSet[] = sets.map((s, i) => ({
    setIndex: i,
    reps: s.reps,
  }));

  return {
    id,
    exercise: 'squat',
    date: overrides?.date ?? new Date().toISOString(),
    workingWeight: workingWeightLb,
    overallScore,
    components,
    primaryLimiter,
    notes: overrides?.notes,
    sets: squatSets,
  };
}

/** Load all squat sessions from localStorage. Returns [] on missing or corrupt data. */
export function loadSquatSessions(): SquatTrainingSession[] {
  const storage = safeGetStorage();
  if (!storage) return [];
  try {
    const raw = storage.getItem(STORAGE_KEY);
    if (!raw) return [];
    return JSON.parse(raw) as SquatTrainingSession[];
  } catch {
    return [];
  }
}

/** Persist squat sessions to localStorage. No-op when localStorage is unavailable. */
export function saveSquatSessions(sessions: SquatTrainingSession[]): void {
  const storage = safeGetStorage();
  if (!storage) return;
  storage.setItem(STORAGE_KEY, JSON.stringify(sessions));
}

/**
 * Adds a session to localStorage, sorts by date descending, and returns the merged array.
 * Existing session with the same id is replaced.
 */
export function addSquatSession(session: SquatTrainingSession): SquatTrainingSession[] {
  const existing = loadSquatSessions().filter(s => s.id !== session.id);
  const merged = [session, ...existing].sort(
    (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime(),
  );
  saveSquatSessions(merged);
  return merged;
}

/**
 * Returns the component with the lowest average score across the last `windowSize` sessions.
 * Returns null when sessions is empty or all component scores are missing.
 * Requires ≥1 session (unlike the backend version which requires ≥2).
 */
export function getBiggestOpportunityFromSessions(
  sessions: SquatTrainingSession[],
  windowSize = 5,
): { componentKey: string; avgScore: number } | null {
  if (sessions.length === 0) return null;

  const recent = sessions.slice(0, windowSize);

  const avgs = COMPONENT_KEYS.map(key => {
    const scores = recent
      .map(s => s.components[key])
      .filter((v): v is number => v != null);
    if (scores.length === 0) return null;
    const avg = Math.round(scores.reduce((a, b) => a + b, 0) / scores.length);
    return { componentKey: key as string, avgScore: avg };
  }).filter((v): v is { componentKey: string; avgScore: number } => v !== null);

  if (avgs.length === 0) return null;

  return avgs.sort((a, b) => a.avgScore - b.avgScore)[0];
}
