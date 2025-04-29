import { useState, useEffect } from 'react';
import { WorkoutPlan, Workout } from '../types/workout';

interface WorkoutEntry {
  id: string;
  workout: Workout;
  duration: number;
}

interface CurrentWorkout {
  workouts: Workout[];
  currentWorkoutIndex: number;
  currentExerciseIndex: number;
  currentSetIndex: number;
}

interface WorkoutEntryInput {
  exerciseId: string;
  setNumber: number;
  reps: number;
  weight: number;
}

export const useWorkoutTracking = () => {
  const [workoutPlans, setWorkoutPlans] = useState<WorkoutPlan[]>([]);
  const [workoutHistory, setWorkoutHistory] = useState<WorkoutEntry[]>([]);
  const [currentWorkout, setCurrentWorkout] = useState<CurrentWorkout | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchWorkoutPlans = async () => {
    setIsLoading(true);
    try {
      // TODO: Replace with actual API call
      const mockPlans: WorkoutPlan[] = [
        {
          id: '1',
          userId: '123',
          name: 'Beginner Workout',
          description: 'A simple workout for beginners',
          frequency: '3x per week',
          duration: 4,
          workouts: [
            {
              id: '1',
              userId: '123',
              name: 'Full Body',
              description: 'Complete body workout',
              exercises: [
                {
                  id: '1',
                  name: 'Push-ups',
                  sets: 3,
                  reps: 10,
                },
              ],
              createdAt: new Date().toISOString(),
              updatedAt: new Date().toISOString(),
            },
          ],
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        },
      ];
      setWorkoutPlans(mockPlans);
    } catch (err) {
      setError('Failed to fetch workout plans');
    } finally {
      setIsLoading(false);
    }
  };

  const fetchWorkoutHistory = async () => {
    setIsLoading(true);
    try {
      // TODO: Replace with actual API call
      const mockHistory: WorkoutEntry[] = [
        {
          id: '1',
          workout: {
            id: '1',
            userId: '123',
            name: 'Full Body',
            description: 'Complete body workout',
            exercises: [
              {
                id: '1',
                name: 'Push-ups',
                sets: 3,
                reps: 10,
              },
            ],
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
          },
          duration: 30,
        },
      ];
      setWorkoutHistory(mockHistory);
    } catch (err) {
      setError('Failed to fetch workout history');
    } finally {
      setIsLoading(false);
    }
  };

  const selectWorkoutPlan = (planId: string) => {
    const plan = workoutPlans.find(p => p.id === planId);
    if (plan) {
      setCurrentWorkout({
        workouts: plan.workouts,
        currentWorkoutIndex: 0,
        currentExerciseIndex: 0,
        currentSetIndex: 0,
      });
    }
  };

  const startWorkout = () => {
    if (!currentWorkout) {
      setError('No workout plan selected');
      return;
    }
    // Additional workout start logic here
  };

  const endWorkout = () => {
    setCurrentWorkout(null);
    fetchWorkoutHistory();
  };

  const saveWorkoutEntry = async (entry: WorkoutEntryInput) => {
    if (!currentWorkout) return;

    try {
      // TODO: Replace with actual API call
      const currentExercise = currentWorkout.workouts[currentWorkout.currentWorkoutIndex]
        .exercises[currentWorkout.currentExerciseIndex];

      if (currentWorkout.currentSetIndex + 1 >= currentExercise.sets) {
        if (currentWorkout.currentExerciseIndex + 1 >= currentWorkout.workouts[currentWorkout.currentWorkoutIndex].exercises.length) {
          if (currentWorkout.currentWorkoutIndex + 1 >= currentWorkout.workouts.length) {
            endWorkout();
            return;
          }
          setCurrentWorkout({
            ...currentWorkout,
            currentWorkoutIndex: currentWorkout.currentWorkoutIndex + 1,
            currentExerciseIndex: 0,
            currentSetIndex: 0,
          });
        } else {
          setCurrentWorkout({
            ...currentWorkout,
            currentExerciseIndex: currentWorkout.currentExerciseIndex + 1,
            currentSetIndex: 0,
          });
        }
      } else {
        setCurrentWorkout({
          ...currentWorkout,
          currentSetIndex: currentWorkout.currentSetIndex + 1,
        });
      }
    } catch (err) {
      setError('Failed to save workout entry');
    }
  };

  useEffect(() => {
    fetchWorkoutPlans();
    fetchWorkoutHistory();
  }, []);

  return {
    workoutPlans,
    workoutHistory,
    currentWorkout,
    isLoading,
    error,
    startWorkout,
    endWorkout,
    saveWorkoutEntry,
    fetchWorkoutHistory,
    selectWorkoutPlan,
  };
}; 