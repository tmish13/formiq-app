import { TrainingSession } from '@/types/training';

const TRAINING_SESSIONS_KEY = 'formiq-training-sessions-v1';

function safeGetStorage(): Storage | null {
  if (typeof window === 'undefined') return null;
  return window.localStorage ?? null;
}

/** Load all training sessions from localStorage. Returns [] on missing or corrupt data. */
export function loadTrainingSessions(): TrainingSession[] {
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

/** Persist training sessions to localStorage. No-op when localStorage is unavailable. */
export function saveTrainingSessions(sessions: TrainingSession[]): void {
  const storage = safeGetStorage();
  if (!storage) return;
  storage.setItem(TRAINING_SESSIONS_KEY, JSON.stringify(sessions));
}

/**
 * Adds a session to localStorage, sorts by date descending, and returns the merged array.
 * Existing session with the same id is replaced.
 */
export function addTrainingSession(newSession: TrainingSession): TrainingSession[] {
  const existing = loadTrainingSessions().filter(s => s.id !== newSession.id);
  const merged = [newSession, ...existing].sort(
    (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime(),
  );
  saveTrainingSessions(merged);
  return merged;
}

/** Returns all training sessions for a given exerciseId. */
export function loadTrainingSessionsForExercise(exerciseId: string): TrainingSession[] {
  return loadTrainingSessions().filter(s => s.exerciseId === exerciseId);
}
