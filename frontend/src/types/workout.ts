export interface Exercise {
  id: string;
  name: string;
  sets: number;
  reps: number;
  weight?: number;
  notes?: string;
}

export interface Workout {
  id: string;
  userId: string;
  name: string;
  description?: string;
  exercises: Exercise[];
  duration?: number; // in minutes
  difficulty?: 'beginner' | 'intermediate' | 'advanced';
  createdAt: string;
  updatedAt: string;
}

export interface WorkoutPlan {
  id: string;
  userId: string;
  name: string;
  description?: string;
  frequency: string; // e.g., "3x per week"
  duration: number; // in weeks
  notes?: string;
  workouts: Workout[];
  createdAt: string;
  updatedAt: string;
} 