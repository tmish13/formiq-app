// Universal per-session record for the progression engine.
// SquatTrainingSession (formCheck.ts) remains for rich squat UI (component scores).
//
// NOTE: Do NOT rename SquatExerciseId to ExerciseId — that name is used by
// features/training/types.ts for the full 58-exercise workout-mode union.

export type SquatExerciseId = 'squat';
// Future: | 'ohp' | 'barbell_row' | 'bench'

export interface TrainingSession {
  id: string;
  exerciseId: SquatExerciseId;
  date: string;        // ISO date string
  weightLb: number;
  sets: number;
  reps: number;        // avg reps across sets
  avgRir: number;      // 0–5 (0 = all out, 5 = very easy)
  formScore?: number;  // optional, from ML analysis
}
