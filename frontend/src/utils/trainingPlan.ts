/**
 * Daily training plan generation — pure, deterministic, zero side effects.
 *
 * Derives a main lift + 2 accessories from the last logged session.
 * Accessories are selected by movement pattern complement (real catalog values).
 */

import type { Goal } from "../features/training/types";
import { EXERCISES } from "../features/training/catalog";
import {
  listSessions,
  listSetLogsForSession,
  getNextTarget,
} from "../features/training/storage";

export interface PlannedExercise {
  exerciseId: string;
  exerciseName: string;
  sets: number;
  repsMin: number;
  repsMax: number;
  /** null = bodyweight or no stored target */
  targetWeightLb: number | null;
  targetRir: number;
  isMain: boolean;
}

export interface DailyPlan {
  goal: Goal;
  mainLift: PlannedExercise | null;
  accessories: PlannedExercise[];
  isEmpty: boolean;
}

// Movement pattern → 2 complementary accessory patterns
// Uses actual movementPattern values from the exercise catalog
const ACCESSORY_PATTERNS: Record<string, [string, string]> = {
  squat:           ["hinge",          "spinal_flexion"],
  hinge:           ["squat",          "knee_extension"],
  horizontal_push: ["horizontal_pull", "shoulder_abduction"],
  vertical_push:   ["horizontal_pull", "elbow_flexion"],
  horizontal_pull: ["horizontal_push", "fly"],
  vertical_pull:   ["vertical_push",   "fly"],
};

const ACCESSORY_REPS: Record<string, { min: number; max: number }> = {
  hinge:              { min: 6,  max: 8  },
  squat:              { min: 8,  max: 10 },
  knee_extension:     { min: 10, max: 15 },
  spinal_flexion:     { min: 12, max: 20 },
  horizontal_push:    { min: 8,  max: 12 },
  horizontal_pull:    { min: 8,  max: 12 },
  vertical_push:      { min: 8,  max: 12 },
  vertical_pull:      { min: 8,  max: 12 },
  shoulder_abduction: { min: 12, max: 15 },
  elbow_flexion:      { min: 10, max: 12 },
  fly:                { min: 10, max: 15 },
};

const DEFAULT_REPS = { min: 8, max: 12 };

const MAIN_REPS: Record<Goal, { min: number; max: number }> = {
  strength:    { min: 4, max: 6  },
  hypertrophy: { min: 6, max: 10 },
  general:     { min: 8, max: 12 },
};

export function generateDailyPlan(goal: Goal): DailyPlan {
  const sessions = listSessions(1);
  if (!sessions.length) {
    return { goal, mainLift: null, accessories: [], isEmpty: true };
  }

  const lastSession = sessions[0];
  const sets = listSetLogsForSession(lastSession.id);
  if (!sets.length) {
    return { goal, mainLift: null, accessories: [], isEmpty: true };
  }

  const exerciseIds = Array.from(new Set(sets.map((s) => s.exerciseId)));

  // Main lift = exercise with the most working sets in last session
  const withCounts = exerciseIds.map((exId) => ({
    exId,
    count: sets.filter((s) => s.exerciseId === exId && s.setType === "working").length,
  }));
  withCounts.sort((a, b) => b.count - a.count);

  const mainExId = withCounts[0]?.exId;
  if (!mainExId) return { goal, mainLift: null, accessories: [], isEmpty: true };

  const mainEx = EXERCISES.find((e) => e.id === mainExId);
  if (!mainEx) return { goal, mainLift: null, accessories: [], isEmpty: true };

  const equipId = sets.find((s) => s.exerciseId === mainExId)?.equipmentProfileId;
  const target = getNextTarget(mainExId, equipId, undefined);
  const mainReps = MAIN_REPS[goal];

  const mainLift: PlannedExercise = {
    exerciseId: mainExId,
    exerciseName: mainEx.name,
    sets: goal === "general" ? 3 : 4,
    repsMin: target?.targetRepsRange.min ?? mainReps.min,
    repsMax: target?.targetRepsRange.max ?? mainReps.max,
    targetWeightLb: target?.targetWeightLb ?? null,
    targetRir: target?.targetRir ?? 2,
    isMain: true,
  };

  // Accessories by movement pattern complement
  const mainPattern = mainEx.movementPattern ?? "";
  const accessoryPatterns = ACCESSORY_PATTERNS[mainPattern] ?? [];

  const accessories: PlannedExercise[] = accessoryPatterns.flatMap((pattern) => {
    const ex = EXERCISES.find(
      (e) => e.id !== mainExId && e.movementPattern === pattern,
    );
    if (!ex) return [];
    const reps = ACCESSORY_REPS[pattern] ?? DEFAULT_REPS;
    return [
      {
        exerciseId: ex.id,
        exerciseName: ex.name,
        sets: 3,
        repsMin: reps.min,
        repsMax: reps.max,
        targetWeightLb: null,
        targetRir: 2,
        isMain: false,
      } as PlannedExercise,
    ];
  });

  return { goal, mainLift, accessories, isEmpty: false };
}
