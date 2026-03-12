import type { Goal } from "../features/training/types";

const PREFS_KEY = "formiq-user-prefs-v1";

export interface UserPrefs {
  fitnessGoal?: string;   // raw value from User.fitness_goal
  fitnessLevel?: string;
  heightCm?: number;
  weightKg?: number;
  age?: number;
  trainingExperience?: "beginner" | "intermediate" | "advanced" | "athlete";
  injuries?: string;
  notifWorkout?: boolean;
  notifAnalysis?: boolean;
  notifWeekly?: boolean;
  trainingStyle?: string; // onboarding selection: e.g. "Barbell & Free Weights"
}

export function getUserPrefs(): UserPrefs {
  try {
    const raw = localStorage.getItem(PREFS_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

export function setUserPrefs(patch: Partial<UserPrefs>): void {
  try {
    const existing = getUserPrefs();
    localStorage.setItem(PREFS_KEY, JSON.stringify({ ...existing, ...patch }));
  } catch {
    // quota exceeded — fail silently
  }
}

/**
 * Maps the raw fitness_goal string (from onboarding or backend User object)
 * to the training engine's Goal type.
 *
 * Onboarding values:  "Build Strength" → strength
 *                     "Improve Endurance" → hypertrophy
 *                     "Lose Weight" → general
 *                     "Perfect Form" → strength (technique-focused)
 * Backend/prefs values: "strength" | "hypertrophy" | "general" passed through.
 */
export function mapFitnessGoalToGoal(raw?: string): Goal {
  if (!raw) return "strength";
  const g = raw.toLowerCase();
  if (g === "strength" || g.includes("strength")) return "strength";
  if (g === "hypertrophy" || g.includes("endurance")) return "hypertrophy";
  if (g === "general" || g.includes("weight") || g.includes("general")) return "general";
  if (g.includes("form") || g.includes("technique")) return "strength";
  return "strength";
}
